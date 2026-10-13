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
