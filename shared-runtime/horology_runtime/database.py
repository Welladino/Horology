"""Async Postgres pool shared by the MCP services; schema changes stay in Alembic.

Statement and lock timeouts are defaults on the service logins (migration
20261014_001), so each session gets them without extra round trips.

Connections are in autocommit mode. connection() runs single statements with
no BEGIN/COMMIT (Postgres makes each one atomic on its own): one round trip
instead of three. transaction() is for statements that must succeed or fail
together; it sends BEGIN and COMMIT.
"""
import time
from contextlib import asynccontextmanager

import certifi
from psycopg.conninfo import conninfo_to_dict
from psycopg_pool import AsyncConnectionPool

from .settings import DATABASE, TIMEOUTS


async def _mark_returned(connection):
    connection.horology_returned_at = time.monotonic()


async def _check_if_idle(connection):
    # Neon closes connections that sit idle, so ping one that has waited a while;
    # a failed ping makes the pool discard it and hand out a fresh connection.
    if time.monotonic() - getattr(connection, 'horology_returned_at', 0) > DATABASE.idle_check_seconds:
        await AsyncConnectionPool.check_connection(connection)


class Database:
    def __init__(self, dsn, pool_size):
        if not dsn:
            raise ValueError('Database URL is not configured')
        options = {'sslrootcert': certifi.where(), 'connect_timeout': TIMEOUTS.database_connect,
                   'prepare_threshold': None, 'autocommit': True}
        # Do not inherit the Supabase-specific certificate used by the gateway's adapter.
        if conninfo_to_dict(dsn).get('host', '').endswith('.neon.tech'):
            options['sslmode'] = 'verify-full'
        self.pool = AsyncConnectionPool(dsn, kwargs=options, min_size=0, max_size=pool_size,
                                        timeout=TIMEOUTS.database_connect, open=False,
                                        configure=_mark_returned, check=_check_if_idle, reset=_mark_returned)

    async def __aenter__(self):
        await self.pool.open()
        return self

    async def __aexit__(self, *exc):
        await self.pool.close()

    @asynccontextmanager
    async def connection(self):
        """For one statement: it commits on its own when it succeeds."""
        async with self.pool.connection() as db:
            yield db

    @asynccontextmanager
    async def transaction(self):
        """For several statements that must succeed or fail together: commits on success,
        rolls back on failure, including cancellation."""
        async with self.pool.connection() as db, db.transaction():
            yield db
