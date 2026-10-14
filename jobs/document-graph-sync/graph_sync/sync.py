"""One workspace's Document Index -> document graph pass.

Rows with Graph Inclusion TRUE are imported or refreshed when their Drive
revision changed; everything else that came from the sheet is removed.
Only changed text is embedded, section by section, for passage search. Status goes back to the sheet's three graph
columns. Agent-written documents are never touched.
"""
import logging

import httpx
from horology_runtime.error_handling import category

from graph_core.documents import fields, service as documents
from graph_core.sections import service as sections
from graph_core.topics import service as topics

from . import index
from .google import INDEXABLE_TYPES

log = logging.getLogger("graph_sync")


def _fields(row):
    """(domain, business_entity, pipeline_id) for a row; a malformed Pipeline ID is dropped, not fatal."""
    try:
        pipeline_id = fields.pipeline_id(row.pipeline_id)
    except ValueError:
        log.warning("row %s: Pipeline ID %r is not a number; stored without one", row.row_number, row.pipeline_id)
        pipeline_id = None
    return row.domain, row.business_entity, pipeline_id


class NotShared(Exception):
    """Drive answers 403/404 for files not shared with the job's identity."""


async def sync_workspace(google, workspace, spreadsheet_id):
    values = await google.sheet_rows(spreadsheet_id, index.TAB)
    rows, headers = index.parse(values)
    rows = [row for row in rows if row.workspace == workspace]
    stored = await documents.sheet_revisions(workspace)
    results, graph_ids = {}, {key: value[0] for key, value in stored.items()}

    for row in rows:
        if not row.included:
            continue
        try:
            results[row.index_id] = await _import(google, workspace, row, stored.get(row.index_id))
            graph_ids[row.index_id] = results[row.index_id][1]
        except NotShared:
            log.warning("row %s: file not shared with the sync identity", row.row_number)
            results[row.index_id] = ("not_shared", "", "")
        except Exception as error:
            # One bad row never stops the rest; details stay in the job log.
            log.warning("row %s failed: %s", row.row_number, category(error))
            results[row.index_id] = ("error", "", "")

    # Domain/Entity/Pipeline ID edits don't change the Drive revision: refresh them for unchanged rows.
    unchanged = [(row.index_id, *_fields(row)) for row in rows if results.get(row.index_id, ("",))[0] == "unchanged"]
    refreshed = await documents.update_sheet_fields(workspace, unchanged)

    # results holds only rows marked TRUE. Anything else imported earlier (now
    # FALSE or gone from the sheet) is removed; a row that errored keeps its old copy.
    removed = await documents.delete_sheet_documents(workspace, [key for key in stored if key not in results])
    for key in removed:
        graph_ids.pop(key, None)

    await _link_supersedes(workspace, rows, results, graph_ids)
    await google.write_cells(spreadsheet_id, _status_updates(headers, rows, results))
    summary = {"workspace": workspace,
               "synced": sum(1 for r in results.values() if r[0] == "synced"),
               "unchanged": sum(1 for r in results.values() if r[0] == "unchanged"),
               "errors": sum(1 for r in results.values() if r[0] == "error"),
               "not_shared": sum(1 for r in results.values() if r[0] == "not_shared"),
               "removed": len(removed),
               "fields_updated": len(refreshed)}
    log.info("sync finished %s", summary)
    return summary


async def _import(google, workspace, row, stored):
    if row.doc_type not in documents.VALID_DOC_TYPES:
        raise ValueError("Unknown Document Type")
    file_id = index.drive_file_id(row.drive_url)
    if not file_id:
        raise ValueError("Drive URL has no file id")
    try:
        meta = await google.file_metadata(file_id)
    except httpx.HTTPStatusError as error:
        if error.response.status_code in (403, 404):
            raise NotShared() from None
        raise
    if meta.get("trashed"):
        raise ValueError("Drive file is in the trash")
    if meta.get("mimeType") not in INDEXABLE_TYPES:
        raise ValueError("Only Markdown, plain text and Google Docs can be indexed")
    revision = str(meta.get("version", ""))
    if stored and stored[1] == revision:
        return ("unchanged", stored[0], revision)
    content = await google.file_text(meta)
    # Embed before storing anything: if embedding fails, the graph is unchanged
    # and the row shows error rather than a document search can never find.
    embedded = await sections.embed_document(row.title, content)
    domain, business_entity, pipeline_id = _fields(row)
    doc_id = await documents.store_sheet_document(
        workspace, row.index_id, file_id, row.drive_url, row.doc_type, row.title, content, revision, embedded,
        domain, business_entity, pipeline_id)
    await documents.link_similar(workspace, doc_id)
    try:
        await topics.place_document(workspace, doc_id)
    except Exception as error:
        # Topics never block a sync: the document is stored and searchable.
        log.warning("row %s: topic placement failed: %s", row.row_number, category(error))
    return ("synced", doc_id, revision)


async def _link_supersedes(workspace, rows, results, graph_ids):
    for row in rows:
        if row.index_id not in results or results[row.index_id][0] in ("error", "not_shared") or not row.supersedes:
            continue
        older = graph_ids.get(row.supersedes)
        if older is None:
            continue  # the superseded document isn't in the graph
        newer = graph_ids[row.index_id]
        await documents.set_supersedes(workspace, newer, older)


def _status_updates(headers, rows, results):
    updates = []
    for row in rows:
        if row.included:
            status, doc_id, revision = results[row.index_id]
            values = [status, "", ""] if status in ("error", "not_shared") else ["synced", str(doc_id), revision]
        else:
            values = ["not_applicable", "", ""]
        updates.append((index.status_range(headers, row.row_number), [values]))
    return updates
