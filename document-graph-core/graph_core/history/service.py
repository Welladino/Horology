"""Execution history: run claims and reports from agents, and the records pass from the sync job.

Agents make two calls per run: claim (before work) and finish (how it ended,
self-reported). Everything else, status changes, outputs and decisions, is
derived by the records pass from copies of the sheets, so the history doesn't
depend on agents remembering to report it.
"""
from .. import database
from . import workflow
from .repository import HistoryRepository

CLAIM_HOURS = 2
KINDS = ("run", "plan")
FINISH_STATUSES = ("done", "failed", "released")


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
    item, events, runs, decisions, index_rows, agent_documents = await _repository().item_history(
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
    timeline.sort(key=lambda entry: str(entry["at"]))
    return {"pipeline_id": pipeline_id, "item": item, "decisions": decisions, "timeline": timeline,
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
