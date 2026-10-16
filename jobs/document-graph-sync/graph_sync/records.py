"""The records pass: copy Pipeline Master, the Decision Register and the Document Index into the execution history.

Read-only on the sheets and no AI: the history service records what changed
since the last copy (as events), and links run outputs. Parsing is pure, so it
is tested without a network or database.
"""
import datetime

from graph_core.history import service as history

from .index import TAB as INDEX_TAB, is_true, text

PIPELINE_TAB = "Master"
DECISIONS_TAB = "Master"
_EPOCH = datetime.date(1899, 12, 30)  # Sheets' day zero for unformatted dates
DATE_COLUMNS = {"Created", "Updated", "Last Updated", "Decision Date", "Review date", "Date"}

ITEM_COLUMNS = {
    "Title": "title", "Domain": "domain", "Type": "type", "Status": "status", "Stage": "stage",
    "Review stage": "review_stage", "Agent status": "agent_status", "Agent type": "agent_type",
    "Run location": "run_location", "Planner output": "planner_output", "Current decision ID": "current_decision_id",
    "Next step / Research question": "next_step",
}
DECISION_COLUMNS = {
    "Pipeline ID": "pipeline_id", "Status": "status", "Review stage": "review_stage", "Decision": "decision",
    "Reason": "reason", "Rework instructions": "rework_instructions",
}
INDEX_COLUMNS = {
    "Pipeline ID": "pipeline_id", "Title": "title", "Drive URL": "drive_url", "Document Type": "doc_type",
    "Document Status": "document_status", "Last Updated": "last_updated", "Graph Sync Status": "graph_sync_status",
}


def books_for(value):
    """A workspace's spreadsheets: a Document Index id (older form) or
    {"index": id, "pipeline": id, "decisions": id}."""
    if isinstance(value, dict):
        return {k: str(v).strip() for k, v in value.items() if k in ("index", "pipeline", "decisions") and v}
    return {"index": str(value).strip()}


def cell_text(header, value):
    """Text of a raw cell; unformatted dates (day numbers) in date columns become ISO dates."""
    if header in DATE_COLUMNS and isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return (_EPOCH + datetime.timedelta(days=int(value))).isoformat()
    return text(value)


def _table(values):
    """(headers, [ {header: text} ]) for a tab's raw values, header row first; blank rows dropped."""
    if not values:
        return [], []
    headers = [str(h).strip() for h in values[0]]
    rows = []
    for raw in values[1:]:
        row = {h: cell_text(h, raw[i] if i < len(raw) else None) for i, h in enumerate(headers) if h}
        if any(row.values()):
            rows.append(row)
    return headers, rows


def _pipeline_id(value):
    try:
        return history.item_id(value)
    except ValueError:
        return None


def pipeline_items(values):
    """Pipeline Master rows -> item dicts for apply_records. Rows without a valid ID are skipped."""
    _, rows = _table(values)
    items = []
    for row in rows:
        pid = _pipeline_id(row.get("ID", ""))
        if not pid:
            continue
        item = {"pipeline_id": pid, "data": row}
        item.update({column: row.get(header) or None for header, column in ITEM_COLUMNS.items()})
        item["title"] = row.get("Title", "")
        items.append(item)
    return items


def decisions(values):
    _, rows = _table(values)
    out = []
    for row in rows:
        decision_id = row.get("Decision ID", "")
        if not decision_id:
            continue
        record = {"decision_id": decision_id, "data": row}
        record.update({column: row.get(header) or None for header, column in DECISION_COLUMNS.items()})
        record["pipeline_id"] = _pipeline_id(record["pipeline_id"] or "")
        out.append(record)
    return out


def index_rows(values):
    headers, rows = _table(values)
    inclusion = headers.index("Graph Inclusion") if "Graph Inclusion" in headers else None
    out = []
    for row in rows:
        document_id = row.get("Document ID", "")
        if not document_id:
            continue
        record = {"index_document_id": document_id, "data": row}
        record.update({column: row.get(header) or None for header, column in INDEX_COLUMNS.items()})
        record["pipeline_id"] = _pipeline_id(record["pipeline_id"] or "")
        record["title"] = row.get("Title", "")
        record["graph_inclusion"] = is_true(row.get("Graph Inclusion")) if inclusion is not None else False
        out.append(record)
    return out


async def run(google, workspace, books):
    """Read whichever registers are configured and apply them; returns counts, or why it was skipped."""
    if not books.get("pipeline") and not books.get("decisions"):
        return {"skipped": "no Pipeline or Decision Register configured for this workspace"}
    items = pipeline_items(await google.sheet_rows(books["pipeline"], PIPELINE_TAB)) if books.get("pipeline") else None
    decided = decisions(await google.sheet_rows(books["decisions"], DECISIONS_TAB)) if books.get("decisions") else None
    indexed = index_rows(await google.sheet_rows(books["index"], INDEX_TAB)) if books.get("index") else None
    return await history.apply_records(workspace, items, decided, indexed)
