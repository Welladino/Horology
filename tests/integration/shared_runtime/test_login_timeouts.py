"""The service logins carry their own statement and lock timeouts (alembic 20261014_001)."""
import asyncio
import os

import pytest

from horology_runtime.database import Database


@pytest.mark.parametrize('variable', ['GATEWAY_TEST_RUNTIME_URL', 'GRAPH_TEST_RUNTIME_URL'])
def test_service_login_sessions_start_with_timeouts(variable):
    dsn = os.environ.get(variable)
    if not dsn:
        pytest.skip('Disposable runtime Postgres is required')
    async def run():
        async with Database(dsn, 1) as database:
            async with database.transaction() as db, db.cursor() as cur:
                await cur.execute('SHOW statement_timeout')
                statement = (await cur.fetchone())[0]
                await cur.execute('SHOW lock_timeout')
                lock = (await cur.fetchone())[0]
        assert (statement, lock) == ('10s', '3s')
    asyncio.run(run())


def test_connection_closed_while_idle_is_replaced_before_use(monkeypatch):
    import psycopg
    from horology_runtime import database as module
    dsn, admin = os.environ.get('GRAPH_TEST_RUNTIME_URL'), os.environ.get('GATEWAY_TEST_DATABASE_URL')
    if not dsn or not admin:
        pytest.skip('Disposable runtime Postgres is required')
    async def run():
        async with Database(dsn, 1) as database:
            async with database.transaction() as db, db.cursor() as cur:
                await cur.execute('SELECT pg_backend_pid()')
                pid = (await cur.fetchone())[0]
            # Simulate the server dropping an idle pooled connection.
            with psycopg.connect(admin, autocommit=True) as owner:
                owner.execute('SELECT pg_terminate_backend(%s)', (pid,))
            monkeypatch.setattr(module, 'DATABASE', type(module.DATABASE)(idle_check_seconds=0))
            async with database.transaction() as db, db.cursor() as cur:
                await cur.execute('SELECT pg_backend_pid()')
                assert (await cur.fetchone())[0] != pid
    asyncio.run(run())
