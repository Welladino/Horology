"""One workspace's Document Index -> document graph pass.

Rows with Graph Inclusion TRUE are imported or refreshed when their Drive
revision changed; everything else that came from the sheet is removed.
Only changed text is embedded, section by section, for passage search. Status goes back to the sheet's three graph
columns. Agent-written documents are never touched.

A run handles at most RUN_LIMIT documents that need work (new or changed);
the rest are left as they are, statuses included, for the next run.
"""
import asyncio
import logging
import time

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


NOT_IMPORTED = ("error", "not_shared", "too_long")  # these rows keep any earlier graph copy
RUN_LIMIT = 30  # documents that needed work (synced, failed or too long) per run; unchanged rows don't count
CONCURRENCY = 3  # rows imported at once
STATUS_BATCH = 10  # Graph Sync Status is written every 10 finished rows
STATUS_SECONDS = 30  # or every 30 seconds, so a crash loses at most a few rows' statuses
clock = time.monotonic  # patched in tests


class NotShared(Exception):
    """Drive answers 403/404 for files not shared with the job's identity."""


async def sync_workspace(google, workspace, spreadsheet_id, limit=RUN_LIMIT):
    values = await google.sheet_rows(spreadsheet_id, index.TAB)
    rows, headers = index.parse(values)
    rows = [row for row in rows if row.workspace == workspace]
    stored = await documents.sheet_revisions(workspace)
    results, graph_ids = {}, {key: value[0] for key, value in stored.items()}

    statuses = _StatusWriter(google, spreadsheet_id, headers)
    included = [row for row in rows if row.included]
    deferred, worked = set(), 0
    for start in range(0, len(included), CONCURRENCY):
        group = included[start:start + CONCURRENCY]
        if worked >= limit:  # the rest wait for the next run, untouched
            deferred.update(row.index_id for row in group)
            continue
        outcomes = await asyncio.gather(*(_import_row(google, workspace, row, stored.get(row.index_id)) for row in group))
        for row, result in zip(group, outcomes):
            results[row.index_id] = result
            if result[0] in ("synced", "unchanged"):
                graph_ids[row.index_id] = result[1]
            if result[0] in ("synced", "error", "too_long"):
                worked += 1
            await statuses.add(row, result)

    # Domain/Entity/Pipeline ID edits don't change the Drive revision: refresh them for unchanged rows.
    unchanged = [(row.index_id, *_fields(row)) for row in rows if results.get(row.index_id, ("",))[0] == "unchanged"]
    refreshed = await documents.update_sheet_fields(workspace, unchanged)

    # results holds the rows marked TRUE that this run reached. Anything else imported earlier
    # (now FALSE or gone from the sheet) is removed; a row that errored or waits for the next run keeps its copy.
    removed = await documents.delete_sheet_documents(
        workspace, [key for key in stored if key not in results and key not in deferred])
    for key in removed:
        graph_ids.pop(key, None)

    await _link_supersedes(workspace, rows, results, graph_ids)
    await statuses.finish([row for row in rows if not row.included])
    summary = {"workspace": workspace,
               "synced": sum(1 for r in results.values() if r[0] == "synced"),
               "unchanged": sum(1 for r in results.values() if r[0] == "unchanged"),
               "errors": sum(1 for r in results.values() if r[0] == "error"),
               "not_shared": sum(1 for r in results.values() if r[0] == "not_shared"),
               "too_long": sum(1 for r in results.values() if r[0] == "too_long"),
               "removed": len(removed),
               "fields_updated": len(refreshed),
               "deferred": len(deferred)}
    log.info("sync finished %s", summary)
    return summary


async def _import_row(google, workspace, row, stored):
    """(status, graph id, revision) for one row; one bad row never stops the rest."""
    try:
        return await _import(google, workspace, row, stored)
    except NotShared:
        log.warning("row %s: file not shared with the sync identity", row.row_number)
        return ("not_shared", "", "")
    except sections.TooLong as error:
        log.warning("row %s: %s sections, over the limit of %s", row.row_number, error.sections, sections.MAX_SECTIONS)
        return ("too_long", "", "")
    except Exception as error:
        log.warning("row %s failed: %s", row.row_number, category(error))
        return ("error", "", "")


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
        if row.index_id not in results or results[row.index_id][0] in NOT_IMPORTED or not row.supersedes:
            continue
        older = graph_ids.get(row.supersedes)
        if older is None:
            continue  # the superseded document isn't in the graph
        newer = graph_ids[row.index_id]
        await documents.set_supersedes(workspace, newer, older)


class _StatusWriter:
    """Writes Graph Sync Status as rows finish, in small batches: Sheets allows about 60 writes a
    minute, so one write per row would hit the limit on a large sheet. A failed mid-run write is
    kept and tried again with the next batch; only the final write raises."""

    def __init__(self, google, spreadsheet_id, headers):
        self.google, self.spreadsheet_id, self.headers = google, spreadsheet_id, headers
        self.pending, self.last_write = [], clock()

    async def add(self, row, result):
        status, doc_id, revision = result
        values = [status, "", ""] if status in NOT_IMPORTED else ["synced", str(doc_id), revision]
        self.pending.append((index.status_range(self.headers, row.row_number), [values]))
        if len(self.pending) >= STATUS_BATCH or clock() - self.last_write >= STATUS_SECONDS:
            try:
                await self._write()
            except Exception as error:
                log.warning("status write failed, kept for the next one: %s", category(error))
                self.last_write = clock()

    async def finish(self, excluded_rows):
        """Write what's left, plus not_applicable for rows with Graph Inclusion FALSE."""
        self.pending += [(index.status_range(self.headers, row.row_number), [["not_applicable", "", ""]])
                         for row in excluded_rows]
        await self._write()

    async def _write(self):
        if self.pending:
            await self.google.write_cells(self.spreadsheet_id, self.pending)
        self.pending, self.last_write = [], clock()
