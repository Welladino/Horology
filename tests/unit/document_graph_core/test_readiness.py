"""The graph's readiness check: which tables are missing or unreadable, decided from one query's rows."""
import asyncio
from contextlib import asynccontextmanager

import pytest

import graph_core
from graph_core import database


class OneQuery:
    """A database whose single query returns the given rows."""
    def __init__(self, rows):
        self.rows, self.queries = rows, 0

    @asynccontextmanager
    async def connection(self):
        db = self

        class Cursor:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *exc):
                return False
            async def execute(self, sql, params):
                db.queries += 1
            async def fetchall(self):
                return db.rows

        class Conn:
            def cursor(self):
                return Cursor()
        yield Conn()


def check(rows):
    fake = OneQuery(rows)
    graph_core.configure(fake)
    try:
        asyncio.run(database.check_ready())
    finally:
        graph_core.configure(None)
    return fake.queries


def all_tables(**overrides):
    return [(t, *overrides.get(t, (True, True))) for t in database.REQUIRED_TABLES]


def test_ready_when_every_table_exists_and_is_readable():
    assert check(all_tables()) == 1  # one round trip


def test_missing_tables_are_named_with_the_fix():
    with pytest.raises(database.NotReady, match="missing graph_runs, graph_auth.records: run alembic upgrade head"):
        check(all_tables(graph_runs=(False, False), **{"graph_auth.records": (False, False)}))


def test_an_unreadable_table_points_at_the_grants():
    with pytest.raises(database.NotReady, match="can't read entities: check the migration grants"):
        check(all_tables(entities=(True, False)))


def test_a_table_the_query_didnt_return_counts_as_missing():
    with pytest.raises(database.NotReady, match="missing topics"):
        check([row for row in all_tables() if row[0] != "topics"])
