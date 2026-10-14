"""python -m graph_sync: sync one workspace (GRAPH_SYNC_WORKSPACE) or every configured workbook.

GRAPH_SYNC_MODE: "sync" (default) imports the Document Index; "topics"
re-clusters topics without reading the sheet.

GRAPH_SYNC_WORKBOOKS maps workspace -> Document Index spreadsheet id, e.g.
{"welladino": "1kOb..."}. DATABASE_URL_POOLED and OPENROUTER_API_KEY as for
the document graph.
"""
import asyncio
import json
import logging
import os
import sys

from horology_runtime.database import Database
from horology_runtime.settings import DATABASE
import graph_core

from graph_core.topics import service as topics

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


MODES = ("sync", "topics")


async def main():
    targets = workbooks()
    mode = os.environ.get("GRAPH_SYNC_MODE", "sync").strip() or "sync"
    if mode not in MODES:
        raise SystemExit(f"GRAPH_SYNC_MODE must be one of {MODES}")
    google = GoogleClient() if mode == "sync" else None
    async with Database(os.environ.get("DATABASE_URL_POOLED"), DATABASE.document_graph_pool_size) as database:
        graph_core.configure(database)
        failed = False
        for workspace, spreadsheet_id in targets.items():
            try:
                if mode == "topics":
                    print(json.dumps(await topics.rebuild(workspace)))
                else:
                    print(json.dumps(await sync_workspace(google, workspace, spreadsheet_id)))
            except Exception as error:
                failed = True
                logging.getLogger("graph_sync").error("workspace %s failed: %s", workspace, type(error).__name__)
    return 1 if failed else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    sys.exit(asyncio.run(main()))
