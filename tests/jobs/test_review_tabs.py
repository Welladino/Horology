"""Entities and Entity types tabs: created, edits applied, rewritten. Real Postgres, fake spreadsheet."""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent / "jobs" / "document-graph-sync"))
sys.path.append(str(Path(__file__).parent.parent / "graph_core"))

import graph_core  # noqa: E402
from graph_core.providers import embeddings, llm  # noqa: E402
from graph_sync import review_tab  # noqa: E402
import test_entities_postgres as fixtures  # noqa: E402

WS = fixtures.WS


class FakeSheet:
    def __init__(self):
        self.tabs = {}
    async def tab_titles(self, spreadsheet_id):
        return list(self.tabs)
    async def add_tab(self, spreadsheet_id, title):
        self.tabs[title] = []
    async def sheet_rows(self, spreadsheet_id, tab):
        return [list(row) for row in self.tabs.get(tab, [])]
    async def replace_tab(self, spreadsheet_id, tab, rows):
        self.tabs[tab] = [list(row) for row in rows]


@pytest.fixture
def database():
    dsn = os.environ.get("GRAPH_TEST_RUNTIME_URL")
    if not dsn:
        pytest.skip("Disposable migrated Postgres with the horology_graph login is required")
    return dsn


def test_tabs_are_created_edited_and_rewritten(database):
    from horology_runtime.database import Database
    sheet = FakeSheet()

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                await fixtures.clean(db)
                await fixtures.add_document("Platforms", ["Beehiiv vs Substack.", "ConvertKit in Singapore. Webinars."])
                with patch.object(llm, "complete_json", fixtures.fake_llm([])), \
                        patch.object(embeddings, "embed_many", AsyncMock(side_effect=fixtures.fake_embed_many)):
                    first = await review_tab.run(sheet, "sheet", WS)
                assert first["extraction"]["documents"] == 1 and first["tab_rows"] == 5
                entities_tab = sheet.tabs[review_tab.ENTITIES_TAB]
                assert entities_tab[0] == review_tab.ENTITY_HEADER
                by_name = {row[1]: row for row in entities_tab[1:]}
                assert by_name["Beehiiv"][5] == "new" and "suggested bucket: events" in by_name["Webinars"][8]
                types_tab = sheet.tabs[review_tab.TYPES_TAB]
                assert ["entity", "platform or tool"] in [row[1:3] for row in types_tab]

                # Operator edits: rename one, merge another, add an "events" bucket, rename a relation type.
                by_name["Substack"][6] = "Substack Inc"
                by_name["ConvertKit"][7] = by_name["Beehiiv"][0]
                competes = next(row for row in types_tab if row[2] == "competes with")
                competes[4] = "rivals"
                types_tab.append(["", "entity", "events", "Online or offline events", ""])
                second = await review_tab.run(sheet, "sheet", WS)
                assert second["edits"]["renamed"] == 1 and second["edits"]["merged"] == 1
                assert second["edits"]["types_renamed"] == 1 and second["edits"]["moved_from_other"] == 1
                rewritten = {row[1]: row for row in sheet.tabs[review_tab.ENTITIES_TAB][1:]}
                assert "Substack Inc" in rewritten and "ConvertKit" not in rewritten
                assert "ConvertKit" in rewritten["Beehiiv"][3] and rewritten["Webinars"][2] == "events"
                assert all(row[6] == "" and row[7] == "" for row in rewritten.values())  # edits cleared
                assert "rivals" in [row[2] for row in sheet.tabs[review_tab.TYPES_TAB]]
            finally:
                await fixtures.clean(db)
                graph_core.configure(None)
    asyncio.run(run())


def test_a_tab_with_a_different_header_is_left_alone():
    assert review_tab._rows([["Something else"], ["1", "x"]], review_tab.ENTITY_HEADER) == []
