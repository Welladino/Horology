"""python -m graph_sync: sync one workspace (GRAPH_SYNC_WORKSPACE) or every configured workbook.

GRAPH_SYNC_MODE:
- "sync" (default): import the Document Index, then entities (tab edits,
  extraction for new or changed documents, fresh Entities tabs);
- "entities": the entity step only (also picks up agent documents);
- "topics": re-cluster topics without reading the sheet.

GRAPH_SYNC_WORKBOOKS maps workspace -> Document Index spreadsheet id, e.g.
{"welladino": "1kOb..."}. DATABASE_URL_POOLED and OPENROUTER_API_KEY as for
the document graph.

One run at a time per workspace: a run that finds another in progress skips
that workspace. Sync and entities each handle up to 30 documents per run;
when more are left, the run starts the next one (GRAPH_SYNC_JOB, the job's
own name; GRAPH_SYNC_CHAIN counts the runs), at most 10 in a row.
GRAPH_RUN_TOKEN confirms the workspace claim taken when the run was requested.
"""
import asyncio
import json
import logging
import os
import sys

from horology_runtime.database import Database
from horology_runtime.error_handling import category
from horology_runtime.logging import use_json_lines
from horology_runtime.settings import DATABASE
import graph_core

from graph_core.runs import service as runs
from graph_core.topics import service as topics

from . import review_tab
from .google import GoogleClient
from .sync import sync_workspace


def workbooks():
    mapping = json.loads(os.environ.get("GRAPH_SYNC_WORKBOOKS", "{}"))
    if not isinstance(mapping, dict) or not mapping:
        raise SystemExit("GRAPH_SYNC_WORKBOOKS must map workspace names to spreadsheet ids")
    only = os.environ.get("GRAPH_SYNC_WORKSPACE", "").strip()
    if only:
        if only not in mapping:
            raise SystemExit(f"No workbook configured for workspace {only!r}")
        return {only: mapping[only]}
    return mapping


MODES = runs.MODES
log = logging.getLogger("graph_sync")


def follow_up_mode(mode, result):
    """The mode of the next run when this one left work over (sync rows or entity documents), else None."""
    if mode == "sync" and result.get("deferred"):
        return "sync"  # a sync run also does the entity step
    extraction = (result.get("entities") if mode == "sync" else result) or {}
    extraction = extraction.get("extraction") if isinstance(extraction, dict) else None
    if mode in ("sync", "entities") and isinstance(extraction, dict) and extraction.get("remaining"):
        return "entities"
    return None


async def run_workspace(google, workspace, spreadsheet_id, mode, chain, token=None):
    running = await runs.claim(workspace, mode, chain, token)
    if running:
        log.warning("workspace %s skipped: a %s run is in progress", workspace, running)
        return {"workspace": workspace, "skipped": f"{running} run in progress"}
    try:
        if mode == "topics":
            result = await topics.rebuild(workspace)
        elif mode == "entities":
            result = await review_tab.run(google, spreadsheet_id, workspace)
        else:
            result = await sync_workspace(google, workspace, spreadsheet_id)
            result["entities"] = await review_tab.run(google, spreadsheet_id, workspace)
    except BaseException:
        await runs.release(workspace, mode)
        raise
    next_mode = follow_up_mode(mode, result)
    try:
        operation = await runs.finish(workspace, mode, next_mode, chain)  # hands the claim on, or releases it
        if next_mode:
            result["follow_up"] = (f"started {next_mode} run {chain + 1}" if operation
                                   else f"not started: {runs.MAX_CHAIN} runs in a row; the rest wait for the next sync")
    except Exception as error:
        log.warning("workspace %s: follow-up run not started: %s", workspace, category(error))
        result["follow_up"] = "failed to start; the rest wait for the next sync"
        try:
            await runs.release(workspace, mode)  # in case the hand-over itself failed
        except Exception:  # nosec B110: best effort; the claim expires on its own
            pass  # the claim expires on its own
    return result


async def main():
    targets = workbooks()
    mode = os.environ.get("GRAPH_SYNC_MODE", "sync").strip() or "sync"
    if mode not in MODES:
        raise SystemExit(f"GRAPH_SYNC_MODE must be one of {MODES}")
    chain = int(os.environ.get("GRAPH_SYNC_CHAIN", "1") or 1)
    token = os.environ.get("GRAPH_RUN_TOKEN", "").strip() or None
    google = GoogleClient() if mode in ("sync", "entities") else None
    async with Database(os.environ.get("DATABASE_URL_POOLED"), DATABASE.document_graph_pool_size) as database:
        graph_core.configure(database)
        await graph_core.database.check_ready()  # stop at once, with the reason, on an unmigrated database
        failed = False
        for workspace, spreadsheet_id in targets.items():
            try:
                print(json.dumps(await run_workspace(google, workspace, spreadsheet_id, mode, chain, token), default=str))
            except Exception as error:
                failed = True
                log.error("workspace %s failed: %s", workspace, category(error))
    return 1 if failed else 0


if __name__ == "__main__":
    use_json_lines(logging.INFO)
    sys.exit(asyncio.run(main()))
