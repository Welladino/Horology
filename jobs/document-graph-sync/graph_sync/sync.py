"""One workspace's Document Index -> document graph pass.

Rows with Graph Inclusion TRUE are imported or refreshed when their Drive
revision changed; everything else that came from the sheet is removed.
Only changed text is embedded. Status goes back to the sheet's three graph
columns. Agent-written documents are never touched.
"""
import logging

from document_graph import graph
from document_graph.integrations.openrouter import client as openrouter

from . import index
from .google import INDEXABLE_TYPES

log = logging.getLogger("graph_sync")
EMBED_CHARS = 8000  # keeps one request inside the embedding model's input limit


def embedding_text(title, content):
    return (title + "\n\n" + content)[:EMBED_CHARS]


async def sync_workspace(google, workspace, spreadsheet_id):
    values = await google.sheet_rows(spreadsheet_id, index.TAB)
    rows, headers = index.parse(values)
    rows = [row for row in rows if row.workspace == workspace]
    stored = await graph.documents.sheet_revisions(workspace)
    results, graph_ids = {}, {key: value[0] for key, value in stored.items()}

    for row in rows:
        if not row.included:
            continue
        try:
            results[row.index_id] = await _import(google, workspace, row, stored.get(row.index_id))
            graph_ids[row.index_id] = results[row.index_id][1]
        except Exception as error:
            # One bad row never stops the rest; details stay in the job log.
            log.warning("row %s failed: %s", row.row_number, type(error).__name__)
            results[row.index_id] = ("error", "", "")

    # results holds only rows marked TRUE. Anything else imported earlier (now
    # FALSE or gone from the sheet) is removed; a row that errored keeps its old copy.
    removed = await graph.documents.delete_sheet_documents(workspace, [key for key in stored if key not in results])
    for key in removed:
        graph_ids.pop(key, None)

    await _link_supersedes(workspace, rows, results, graph_ids)
    await google.write_cells(spreadsheet_id, _status_updates(headers, rows, results))
    summary = {"workspace": workspace,
               "synced": sum(1 for r in results.values() if r[0] == "synced"),
               "unchanged": sum(1 for r in results.values() if r[0] == "unchanged"),
               "errors": sum(1 for r in results.values() if r[0] == "error"),
               "removed": len(removed)}
    log.info("sync finished %s", summary)
    return summary


async def _import(google, workspace, row, stored):
    if row.doc_type not in graph.VALID_DOC_TYPES:
        raise ValueError("Unknown Document Type")
    file_id = index.drive_file_id(row.drive_url)
    if not file_id:
        raise ValueError("Drive URL has no file id")
    meta = await google.file_metadata(file_id)
    if meta.get("trashed"):
        raise ValueError("Drive file is in the trash")
    if meta.get("mimeType") not in INDEXABLE_TYPES:
        raise ValueError("Only Markdown, plain text and Google Docs can be indexed")
    revision = str(meta.get("version", ""))
    if stored and stored[1] == revision:
        return ("unchanged", stored[0], revision)
    content = await google.file_text(meta)
    doc_id = await graph.documents.upsert_sheet_document(
        workspace, row.index_id, file_id, row.drive_url, row.doc_type, row.title, content, revision)
    # Embed outside any transaction, then link within the workspace.
    await graph.embeddings.save(doc_id, await openrouter._embed(embedding_text(row.title, content)))
    await graph.link_similar(workspace, doc_id, 0.85)
    return ("synced", doc_id, revision)


async def _link_supersedes(workspace, rows, results, graph_ids):
    for row in rows:
        if row.index_id not in results or results[row.index_id][0] == "error" or not row.supersedes:
            continue
        older = graph_ids.get(row.supersedes)
        if older is None:
            continue  # the superseded document isn't in the graph
        newer = graph_ids[row.index_id]
        await graph.documents.set_supersedes(workspace, newer, older)
        await graph.links.add(newer, older, "supersedes")


def _status_updates(headers, rows, results):
    updates = []
    for row in rows:
        if row.included:
            status, doc_id, revision = results[row.index_id]
            values = ["error", "", ""] if status == "error" else ["synced", str(doc_id), revision]
        else:
            values = ["not_applicable", "", ""]
        updates.append((index.status_range(headers, row.row_number), [values]))
    return updates
