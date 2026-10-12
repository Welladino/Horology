"""Async Postgres pool and transaction policy; schema changes stay in Alembic."""
from contextlib import asynccontextmanager

import certifi
from psycopg.conninfo import conninfo_to_dict
from psycopg_pool import AsyncConnectionPool
from horology_runtime.settings import TIMEOUTS, DATABASE
from policy import Denied


class Database:
    def __init__(self, dsn):
        if not dsn:
            raise Denied('GATEWAY_DATABASE_URL is not configured')
        options = {'sslrootcert': certifi.where(), 'connect_timeout': TIMEOUTS.database_connect,
                   'prepare_threshold': None}
        # Do not inherit the Supabase-specific certificate used by its adapter.
        if conninfo_to_dict(dsn).get('host', '').endswith('.neon.tech'):
            options['sslmode'] = 'verify-full'
        self.pool = AsyncConnectionPool(dsn, kwargs=options, min_size=0,
                                       max_size=DATABASE.gateway_pool_size,
                                       timeout=TIMEOUTS.database_connect, open=False)

    async def __aenter__(self):
        await self.pool.open()
        return self

    async def __aexit__(self, *exc):
        await self.pool.close()

    @asynccontextmanager
    async def transaction(self):
        # Pool connection contexts commit on success and roll back on failure,
        # including cancellation. SET LOCAL is safe with Neon transaction pooling.
        async with self.pool.connection() as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT set_config('statement_timeout', %s, true)", (str(TIMEOUTS.neon_statement_ms),))
                await cur.execute("SELECT set_config('lock_timeout', %s, true)", (str(TIMEOUTS.neon_lock_ms),))
            yield db

    async def check_ready(self):
        async with self.transaction() as db, db.cursor() as cur:
            await cur.execute('SELECT client_id FROM gateway_quotas.reservations LIMIT 0')
            await cur.execute('SELECT client_id FROM gateway_quotas.cache LIMIT 0')
            await cur.execute('SELECT id FROM gateway_quotas.reservation_lock WHERE id = 1')
            if await cur.fetchone() != (1,):
                raise Denied('Gateway quota migration is not ready')
