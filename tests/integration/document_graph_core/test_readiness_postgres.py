"""The readiness check against the real migrated database, as the restricted horology_graph login."""
import asyncio
from unittest.mock import patch

import pytest

import graph_core
from graph_core import database as graph_database


def test_the_migrated_database_is_ready_and_a_missing_table_is_named(database):
    from horology_runtime.database import Database

    async def run():
        async with Database(database, 1) as db:
            graph_core.configure(db)
            try:
                await graph_database.check_ready()  # every table exists, and this login can read each one
                with patch.object(graph_database, "REQUIRED_TABLES", graph_database.REQUIRED_TABLES + ("not_migrated_yet",)):
                    with pytest.raises(graph_database.NotReady, match="missing not_migrated_yet"):
                        await graph_database.check_ready()
            finally:
                graph_core.configure(None)
    asyncio.run(run())
