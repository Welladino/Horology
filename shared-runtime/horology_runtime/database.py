"""Async Postgres pool shared by the MCP services; schema changes stay in Alembic.

Statement and lock timeouts are defaults on the service logins (migration
20261014_001), so each session gets them without extra round trips.
"""
from contextlib import asynccontextmanager

import certifi
from psycopg.conninfo import conninfo_to_dict
from psycopg_pool import AsyncConnectionPool

from .settings import TIMEOUTS


class Database:
    def __init__(self, dsn, pool_size):
        if not dsn:
            raise ValueError('Database URL is not configured')
        options = {'sslrootcert': certifi.where(), 'connect_timeout': TIMEOUTS.database_connect,
                   'prepare_threshold': None}
        # Do not inherit the Supabase-specific certificate used by the gateway's adapter.
        if conninfo_to_dict(dsn).get('host', '').endswith('.neon.tech'):
            options['sslmode'] = 'verify-full'
        self.pool = AsyncConnectionPool(dsn, kwargs=options, min_size=0, max_size=pool_size,
                                        timeout=TIMEOUTS.database_connect, open=False)

    async def __aenter__(self):
        await self.pool.open()
        return self

    async def __aexit__(self, *exc):
        await self.pool.close()

    @asynccontextmanager
    async def transaction(self):
        # Pool connection contexts commit on success and roll back on failure,
        # including cancellation.
        async with self.pool.connection() as db:
            yield db
