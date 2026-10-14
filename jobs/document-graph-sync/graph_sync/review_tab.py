"""The Entities and Entity types tabs: apply the operator's edits, then rewrite them from the graph.

Entities tab: one row per entity. Fill "Rename to" to rename (the old name
stays an alias) or "Merge into (Entity ID)" to fold this entity into
another; both are cleared once applied.

Entity types tab: buckets (kind "entity") and relationship types (kind
"relation"). Add a row to add one, edit a description, or fill "Rename to".
Rows removed from the tab are kept; types aren't deleted.
"""
import logging
from datetime import datetime, timedelta, timezone

from horology_runtime.error_handling import category

from graph_core.entities import service as entities

from .index import text

log = logging.getLogger("graph_sync")
ENTITIES_TAB = "Entities"
TYPES_TAB = "Entity types"
ENTITY_HEADER = ["Entity ID", "Name", "Bucket", "Aliases", "Documents", "Status", "Rename to", "Merge into (Entity ID)", "Notes"]
TYPE_HEADER = ["Type ID", "Kind", "Name", "Description", "Rename to"]


def _rows(values, header):
    """Data rows as {column: value}; a tab with a different header is treated as empty."""
    if not values or [str(v).strip() for v in values[0][:len(header)]] != header:
        return []
    return [{name: (row[i] if i < len(row) else "") for i, name in enumerate(header)} for row in values[1:]]


def _id(value):
    value = text(value)
    return int(value) if value.isdigit() else None


async def apply_edits(google, spreadsheet_id, workspace):
    """Apply type and entity edits from the tabs. Returns counts; a missing tab is created later."""
    titles = await google.tab_titles(spreadsheet_id)
    done = {"types_added_or_updated": 0, "types_renamed": 0, "moved_from_other": 0, "renamed": 0, "merged": 0, "skipped": 0}
    if TYPES_TAB in titles:
        rows = _rows(await google.sheet_rows(spreadsheet_id, TYPES_TAB), TYPE_HEADER)
        by_kind = {"entity": [], "relation": []}
        renames = []
        for row in rows:
            kind, name = text(row["Kind"]).lower(), text(row["Name"])
            if kind not in by_kind or not name:
                continue
            by_kind[kind].append((name, text(row["Description"])))
            if text(row["Rename to"]) and _id(row["Type ID"]):
                renames.append((_id(row["Type ID"]), text(row["Rename to"])))
        done["moved_from_other"] = await entities.apply_types(workspace, by_kind["entity"], by_kind["relation"], renames)
        done["types_added_or_updated"] = len(by_kind["entity"]) + len(by_kind["relation"])
        done["types_renamed"] = len(renames)
    if ENTITIES_TAB in titles:
        for row in _rows(await google.sheet_rows(spreadsheet_id, ENTITIES_TAB), ENTITY_HEADER):
            entity_id, target = _id(row["Entity ID"]), _id(row["Merge into (Entity ID)"])
            if entity_id is None:
                continue
            if target is not None:
                done["merged" if await entities.merge(workspace, entity_id, target) else "skipped"] += 1
            elif text(row["Rename to"]):
                done["renamed" if await entities.rename(workspace, entity_id, text(row["Rename to"])) else "skipped"] += 1
    return done


async def write_tabs(google, spreadsheet_id, workspace):
    """Rewrite both tabs from the graph, creating them if missing. Returns the entity row count."""
    titles = await google.tab_titles(spreadsheet_id)
    for tab in (TYPES_TAB, ENTITIES_TAB):
        if tab not in titles:
            await google.add_tab(spreadsheet_id, tab)
    types = await entities.type_rows(workspace)
    await google.replace_tab(spreadsheet_id, TYPES_TAB, [TYPE_HEADER] + [
        [t["id"], t["kind"], t["name"], t["description"], ""] for t in types])
    recent = datetime.now(timezone.utc) - timedelta(days=7)
    rows = []
    for e in await entities.review_rows(workspace):
        notes = []
        if e["recent_merges"]:
            notes.append(f"auto-merged: {e['recent_merges']}")
        if e["suggested_type"]:
            notes.append(f"suggested bucket: {e['suggested_type']}")
        rows.append([e["id"], e["name"], e["bucket"], e["aliases"], e["documents"],
                     "new" if e["created_at"] >= recent else "", "", "", "; ".join(notes)])
    await google.replace_tab(spreadsheet_id, ENTITIES_TAB, [ENTITY_HEADER] + rows)
    return len(rows)


async def run(google, spreadsheet_id, workspace):
    """Edits first (so new buckets apply), then extraction, then fresh tabs. Each step's failure is contained."""
    summary = {}
    for name, step in (("edits", lambda: apply_edits(google, spreadsheet_id, workspace)),
                       ("extraction", lambda: entities.process_pending(workspace)),
                       ("tab_rows", lambda: write_tabs(google, spreadsheet_id, workspace))):
        try:
            summary[name] = await step()
        except Exception as error:
            log.warning("entities %s failed for %s: %s", name, workspace, category(error))
            summary[name] = "failed"
    return summary
