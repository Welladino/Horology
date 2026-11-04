"""Execution history: run claims and reports from agents, and the records pass from the sync job.

Agents make two calls per run: claim (before work) and finish (how it ended,
self-reported). Everything else, status changes, outputs and decisions, is
derived by the records pass from copies of the sheets, so the history doesn't
depend on agents remembering to report it.
"""
import re

from .. import database
from . import workflow
from .repository import HistoryRepository

CLAIM_HOURS = 2
KINDS = ("run", "plan")
FINISH_STATUSES = ("done", "failed", "released")
_DRIVE_ID = re.compile(r"/(?:file|document|spreadsheets|presentation)/d/([A-Za-z0-9_-]{10,})|[?&]id=([A-Za-z0-9_-]{10,})")
_DRIVE_FILE = re.compile(
    r"^https://(?:docs\.google\.com/(?:document|spreadsheets|presentation)/d/[A-Za-z0-9_-]{10,}"
    r"|drive\.google\.com/(?:file/d/[A-Za-z0-9_-]{10,}|open\?(?:[^#\s]*&)?id=[A-Za-z0-9_-]{10,}))(?:[/?#&]\S*)?$")
_LINK_SPLIT = re.compile(r"[\s,]+")


def _repository():
    return HistoryRepository(database.get())


def run_label(run_id):
    return f"R-{run_id}"


def parse_run_id(value):
    """'R-12' or 12 -> 12."""
    text = str(value).strip().upper().removeprefix("R-")
    if not text.isdigit():
        raise ValueError("run_id must look like R-12")
    return int(text)


def item_id(value):
    """A permanent Pipeline ID as stored: a positive whole number, as text."""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text.isdigit() or int(text) < 1:
        raise ValueError("pipeline_id must be a positive whole number")
    return str(int(text))


def _check(field, value):
    allowed = workflow.values(field)
    if allowed is not None and value not in allowed:
        raise ValueError(f"{field} must be one of: {', '.join(allowed)}")


async def claim(workspace, pipeline_id, agent_type, run_location="Local", kind="run"):
    """Claim an item for CLAIM_HOURS. Refused (claimed: false) while another live run holds it."""
    pipeline_id = item_id(pipeline_id)
    if agent_type not in ("Claude Code", "Codex"):
        raise ValueError("agent_type must be Claude Code or Codex")
    _check("Agent type", agent_type)
    run_location = run_location or "Local"
    _check("Run location", run_location)
    if run_location not in ("Local", "Cloud"):
        raise ValueError("run_location must be Local or Cloud")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    held_id, held_expires, created = await _repository().claim(
        workspace, pipeline_id, agent_type, kind, run_location, CLAIM_HOURS)
    if held_id is not None:
        return {"claimed": False, "reason": "already_claimed", "run_id": run_label(held_id),
                "claim_expires": held_expires.isoformat(),
                "next_step": "Another run has this item; skip it. The claim expires on its own if that run died."}
    return {"claimed": True, "run_id": run_label(created["id"]), "pipeline_id": pipeline_id,
            "started_at": created["started_at"], "claim_expires": created["claim_expires"]}


async def finish(workspace, run_id, status, skills_used=None, steps_done=None, notes=None, session_link=None):
    """Close a run with how it ended. Skills, steps and notes are recorded as reported by the agent."""
    run_id = parse_run_id(run_id)
    if status not in FINISH_STATUSES:
        raise ValueError(f"status must be one of {FINISH_STATUSES}")
    skills = [str(s).strip() for s in (skills_used or []) if str(s).strip()][:20]
    closed, existing = await _repository().finish(
        workspace, run_id, status, skills, _clip(steps_done, 2000), _clip(notes, 4000), _clip(session_link, 500))
    if closed:
        return {"finished": True, "run_id": run_label(closed["id"]), "pipeline_id": closed["pipeline_id"],
                "status": closed["status"], "started_at": closed["started_at"], "ended_at": closed["ended_at"]}
    if existing is None:
        raise ValueError(f"No run {run_label(run_id)} in this workspace")
    return {"finished": False, "reason": "already_finished", "run_id": run_label(run_id), "status": existing}


REGISTERS = ("decision", "document")


def _register(value):
    name = str(value or "").strip().lower()
    if name not in REGISTERS:
        raise ValueError(f"register must be one of {REGISTERS}")
    return name


def register_id(value):
    """A permanent Decision or Document ID as stored: a positive whole number, as text."""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text.isdigit() or int(text) < 1:
        raise ValueError("register IDs are positive whole numbers")
    return str(int(text))


def drive_key(url):
    """The Drive file ID in a Drive or Docs URL, or the trimmed URL when there isn't one.
    Two links to the same file (/edit, /view, ?usp=...) compare equal."""
    text = str(url or "").strip()
    match = _DRIVE_ID.search(text)
    return (match.group(1) or match.group(2)) if match else text


def is_drive_file(url):
    """True for a link to one Drive file: a Google Doc, Sheet or Slides file, or any file in Drive (e.g. HTML)."""
    return bool(_DRIVE_FILE.match(str(url or "").strip()))


def research_link_problems(research_links):
    """The Research Links that are not Drive files. Accepts a list or the cell text (one link per line).
    Returns the offending links in order; empty means every link is a Drive file."""
    if research_links in (None, ""):
        return []
    items = [research_links] if isinstance(research_links, str) else list(research_links)
    links = [part for item in items for part in _LINK_SPLIT.split(str(item or "")) if part]
    return [link for link in links if not is_drive_file(link)]


async def reserve_id(workspace, register, pipeline_id=None, run_id=None, reserved_by=None, live_max=None):
    """Reserve the next permanent ID of a register, atomically. Two calls never get the same ID.

    pipeline_id and run_id record who took it (shown in get_item_history); a Pipeline item needs the
    live run that holds it. live_max is the highest ID the caller just read in the live sheet, so a row
    added since the last sync is respected too."""
    register = _register(register)
    item = item_id(pipeline_id) if pipeline_id not in (None, "") else None
    run = parse_run_id(run_id) if run_id not in (None, "") else None
    if item and run is None:
        raise ValueError("run_id is required with pipeline_id: pass the run that holds the item")
    if run is not None and not item:
        raise ValueError("pipeline_id is required with run_id")
    floor = int(register_id(live_max)) if live_max not in (None, "", 0, "0") else 0
    reserved, run_row = await _repository().reserve_id(
        workspace, register, item, run, _clip(reserved_by, 200), floor)
    if reserved is None:
        if run_row is None:
            reason = f"No run {run_label(run)} in this workspace"
        elif str(run_row["pipeline_id"]) != item:
            reason = f"Run {run_label(run)} belongs to Pipeline item {run_row['pipeline_id']}, not {item}"
        else:
            reason = f"Run {run_label(run)} is not live (status {run_row['status']} or its claim expired)"
        return {"reserved": False, "reason": reason,
                "next_step": "Reserve IDs only inside the live run that holds this item."}
    return {"reserved": True, "register": register, "id": str(reserved), "pipeline_id": item,
            "run_id": run_label(run) if run is not None else None,
            "next_step": "Write the row with exactly this ID; call check_register_write first."}


def ownership_conflicts(register, wanted_pipeline, wanted_drive, *owners):
    """Why writing (register ID -> wanted_pipeline, wanted_drive) would overwrite someone else's row.

    owners are what is already known about that ID: the live sheet row, the synced copy and the
    reservation, each a dict with pipeline_id and drive_url (missing or blank = not known). Returns a
    list of plain-language conflicts; empty means the write may go ahead."""
    problems = []
    for source, owner in owners:
        if not owner:
            continue
        have_pipeline = str(owner.get("pipeline_id") or "").strip()
        if have_pipeline and wanted_pipeline and have_pipeline != wanted_pipeline:
            problems.append(f"{source} has it for Pipeline item {have_pipeline}, not {wanted_pipeline}")
        have_drive = drive_key(owner.get("drive_url"))
        if register == "document" and have_drive and wanted_drive and have_drive != drive_key(wanted_drive):
            problems.append(f"{source} has it for a different Drive file ({owner.get('drive_url')})")
    return problems


async def check_register_write(workspace, register, register_id_value, pipeline_id=None, drive_url=None,
                               live_row=None, research_links=None):
    """The ownership check before every register write: may this ID be written for this item and file?

    Compares the intended owner with the live sheet row the caller just read (live_row: its Pipeline
    ID and Drive URL, or None when no row has that ID), the last synced copy and the reservation. On the
    first clean check of a Document ID its Drive URL is bound to the reservation, so a later writer
    with another file is refused even before the next sync. Never raises for a conflict: returns
    ok False with the reasons, and the caller must stop instead of overwriting.

    research_links (Decision Register only) are the links about to go in Research Links. Each must be a
    Drive file (Doc, Sheet, Slides or a Drive file such as HTML); any other link is refused before the
    ownership check, so nothing is bound."""
    register = _register(register)
    wanted_id = register_id(register_id_value)
    if research_links not in (None, "", []) and register != "decision":
        raise ValueError("research_links is only for a Decision Register write")
    bad_links = research_link_problems(research_links)
    if bad_links:
        return {"ok": False, "reason": "research_links_not_drive", "id": wanted_id, "register": register,
                "links": bad_links,
                "message": ("Research Links holds Drive files only (Google Docs, Sheets, Slides or an HTML file in "
                            "Drive). Not Drive files: " + ", ".join(bad_links) + "."),
                "next_step": ("Don't write the row yet. Save the evidence to a Drive document (a repository file "
                              "goes in that document's Related Repo Document in the Document Index) and link it "
                              "instead.")}
    wanted_pipeline = item_id(pipeline_id) if pipeline_id not in (None, "") else None
    wanted_drive = str(drive_url or "").strip() or None
    if register == "document" and not wanted_drive:
        raise ValueError("drive_url is required for a Document Index write")
    live = None
    if live_row:
        live = {"pipeline_id": _item_or_text(live_row.get("pipeline_id")), "drive_url": live_row.get("drive_url")}
    problems = []

    def bind(reservation, synced):
        problems.extend(ownership_conflicts(
            register, wanted_pipeline, wanted_drive, ("The live sheet row", live), ("The last synced copy", synced),
            ("The reservation", reservation)))
        return wanted_drive if register == "document" and not problems else None

    reservation, synced = await _repository().register_owner(
        workspace, register, wanted_id, bind)
    if reservation is None:
        problems.extend(ownership_conflicts(register, wanted_pipeline, wanted_drive,
                                            ("The live sheet row", live), ("The last synced copy", synced)))
    label = f"{register.title()} ID {wanted_id}"
    if problems:
        return {"ok": False, "reason": "id_owned_by_another_row", "id": wanted_id, "register": register,
                "conflicts": problems,
                "message": f"{label} already belongs to another row: " + "; ".join(problems) + ".",
                "next_step": ("Stop: don't write this row. Reserve a new ID with reserve_id, or report the clash "
                              "if this row should be yours.")}
    result = {"ok": True, "id": wanted_id, "register": register, "reserved": reservation is not None}
    if reservation is None and live is None and synced is None:
        result["warning"] = (f"{label} was not handed out by reserve_id; use reserve_id for new rows so "
                             "parallel runs can't take the same ID.")
    return result


def _item_or_text(value):
    try:
        return item_id(value)
    except ValueError:
        return str(value or "").strip() or None


async def list_runs(workspace, since_hours=24, pipeline_id=None, limit=50):
    item = item_id(pipeline_id) if pipeline_id not in (None, "") else None
    runs = await _repository().list_runs(workspace, max(1, min(int(since_hours), 24 * 31)), item,
                                         max(1, min(int(limit), 200)))
    for run in runs:
        run["run_id"] = run_label(run.pop("id"))
        run["self_reported"] = ["skills_used", "steps_done", "notes"]
    return runs


async def item_history(workspace, pipeline_id):
    """Everything known about one item, as one timeline. Events are checked against workflow.yaml."""
    pipeline_id = item_id(pipeline_id)
    item, events, runs, decisions, index_rows, agent_documents, reservations = await _repository().item_history(
        workspace, pipeline_id)
    timeline = []
    for event in events:
        if event.get("run_id"):
            event["run_id"] = run_label(event["run_id"])
        event["expected"] = workflow.expected(event["field"], event["from_value"], event["to_value"])
        timeline.append({"at": event["observed_at"], "what": "change", **event})
    for run in runs:
        run["run_id"] = run_label(run.pop("id"))
        timeline.append({"at": run["started_at"], "what": "run", **run})
    for row in index_rows:
        timeline.append({"at": row["first_seen_at"], "what": "document", **row})
    for doc in agent_documents:
        timeline.append({"at": doc["created_at"], "what": "agent_document", **doc})
    for reservation in reservations:
        reservation.pop("reserved_id", None)
        if reservation.get("run_id"):
            reservation["run_id"] = run_label(reservation["run_id"])
        timeline.append({"at": reservation["reserved_at"], "what": "id_reserved", **reservation})
    timeline.sort(key=lambda entry: str(entry["at"]))
    return {"pipeline_id": pipeline_id, "item": item, "decisions": decisions, "reserved_ids": reservations,
            "timeline": timeline,
            "notes": ("Changes come from comparing successive copies of the sheets, so several edits between "
                      "two syncs appear as one. Run skills, steps and notes are self-reported by the agent.")}


async def apply_records(workspace, items=None, decisions=None, index_rows=None):
    """The records pass: copy the registers, record changes and link run outputs (one transaction)."""
    return await _repository().apply_records(workspace, items, decisions, index_rows)


def _clip(value, limit):
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] or None
