"""The gateway's shared budget and response cache in a disposable migrated Postgres
(GATEWAY_TEST_DATABASE_URL): atomic reservations, client-scoped cache, runtime-role limits."""
import asyncio
import json
import os

import psycopg
import pytest

from support.gateway import GATEWAY, policy  # noqa: F401  (policy is a fixture)
from integrations.tavily import client as tavily  # noqa: E402
from policy import Denied, authorize, load_policy  # noqa: E402
from database.connection import Database  # noqa: E402
from database.repositories.quotas import QuotaRepository  # noqa: E402
from database.repositories.cache import CacheRepository  # noqa: E402


@pytest.fixture
def ledger_dsn():
    dsn = os.environ.get('GATEWAY_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Set GATEWAY_TEST_DATABASE_URL to a disposable migrated Postgres database')
    with psycopg.connect(dsn) as db, db.cursor() as cur:
        cur.execute('TRUNCATE gateway_quotas.reservations, gateway_quotas.cache')
    yield os.environ.get('GATEWAY_TEST_RUNTIME_URL', dsn)


def test_atomic_budget_across_clients_and_connections(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as first, Database(ledger_dsn) as second:
            repositories = [QuotaRepository(first), QuotaRepository(second)]
            async def reserve(i):
                try:
                    await repositories[i % 2].reserve(str(i),'search','tavily',1,{'daily':3,'monthly':10})
                    return True
                except Denied:
                    return False
            results = await asyncio.gather(*(reserve(i) for i in range(20)))
            assert sum(results) == 3
    asyncio.run(run())


def test_fail_closed_budget_and_restart_counts(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            quotas = QuotaRepository(database)
            with pytest.raises(Denied):
                await quotas.reserve('a','search','tavily',1,{'daily':0,'monthly':10})
            await quotas.reserve('a','search','tavily',1,{'daily':1,'monthly':10})
        async with Database(ledger_dsn) as restarted:
            with pytest.raises(Denied):
                await QuotaRepository(restarted).reserve('b','search','tavily',1,{'daily':1,'monthly':10})
    asyncio.run(run())


def test_shared_daily_credit_cap_combines_basic_and_advanced(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            quotas = QuotaRepository(database)
            cache = CacheRepository(database)
            budget = {'daily': 5, 'monthly': 100}
            await quotas.reserve('a', 'basic', 'tavily', 1, budget)
            await quotas.reserve('a', 'advanced', 'tavily', 2, budget)
            await quotas.reserve('a', 'advanced', 'tavily', 2, budget)
            with pytest.raises(Denied):
                await quotas.reserve('a', 'basic', 'tavily', 1, budget)
    asyncio.run(run())


def test_cache_is_client_scoped(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            quotas = QuotaRepository(database)
            cache = CacheRepository(database)
            await cache.save_cache('a', 'q', [])
            assert await cache.cached('a', 'q') == []
            assert await cache.cached('b', 'q') is None
    asyncio.run(run())


def test_more_than_two_paid_calls_allowed_within_shared_budget(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            quotas = QuotaRepository(database)
            cache = CacheRepository(database)
            budget = {'daily': 50, 'monthly': 500}
            await quotas.reserve('a', 'basic', 'tavily', 1, budget)
            await quotas.reserve('a', 'advanced', 'tavily', 2, budget)
            await quotas.reserve('a', 'basic', 'tavily', 1, budget)
    asyncio.run(run())


def test_monthly_budget_shared_across_clients(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            quotas = QuotaRepository(database)
            cache = CacheRepository(database)
            budget = {'daily': 50, 'monthly': 2}
            await quotas.reserve('a', 'search', 'tavily', 2, budget)
            with pytest.raises(Denied, match='Shared provider budget'):
                await quotas.reserve('b', 'search', 'tavily', 1, budget)
    asyncio.run(run())


def test_previous_day_and_month_do_not_consume_current_budget(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            quotas = QuotaRepository(database)
            cache = CacheRepository(database)
            budget = {'daily': 1, 'monthly': 1}
            await quotas.reserve('old', 'search', 'tavily', 1, budget)
            with psycopg.connect(os.environ['GATEWAY_TEST_DATABASE_URL']) as db, db.cursor() as cur:
                cur.execute("UPDATE gateway_quotas.reservations SET day=CURRENT_DATE-40, month=date_trunc('month', CURRENT_DATE-40)::date")
            await quotas.reserve('new', 'search', 'tavily', 1, budget)
            with pytest.raises(Denied, match='Shared provider budget'):
                await quotas.reserve('other', 'search', 'tavily', 1, budget)
    asyncio.run(run())


def test_runtime_role_cannot_reset_history_or_create_tables(ledger_dsn):
    if not os.environ.get('GATEWAY_TEST_RUNTIME_URL'):
        pytest.skip('Set GATEWAY_TEST_RUNTIME_URL to the restricted gateway role')
    async def run():
        async with Database(ledger_dsn) as database:
            for query in ('DELETE FROM gateway_quotas.reservations', 'TRUNCATE gateway_quotas.reservations', 'CREATE TABLE gateway_quotas.escape (id integer)'):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    async with database.transaction() as db:
                        await db.execute(query)
            await database.check_ready()
    asyncio.run(run())


def test_cancelled_transaction_rolls_back_and_returns_connection(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            inserted = asyncio.Event()
            async def cancelled_writer():
                async with database.transaction() as db:
                    await db.execute("INSERT INTO gateway_quotas.cache(client_id,key,value,expires) VALUES('cancelled','key','{}',clock_timestamp()+interval '1 hour')")
                    inserted.set()
                    await asyncio.Event().wait()
            task = asyncio.create_task(cancelled_writer())
            await inserted.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert await CacheRepository(database).cached('cancelled','key') is None
            await database.check_ready()
            assert database.pool.get_stats()['requests_waiting'] == 0
    asyncio.run(run())


def test_cache_expires_and_failed_transaction_rolls_back(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            cache = CacheRepository(database)
            await cache.save_cache('client','expired', {'result': 'old'})
            async with database.transaction() as db:
                await db.execute("UPDATE gateway_quotas.cache SET expires=clock_timestamp()-interval '1 second' WHERE client_id='client' AND key='expired'")
            assert await cache.cached('client','expired') is None
            with pytest.raises(RuntimeError):
                async with database.transaction() as db:
                    await db.execute("UPDATE gateway_quotas.cache SET expires=clock_timestamp()+interval '1 hour' WHERE client_id='client' AND key='expired'")
                    raise RuntimeError('rollback')
            assert await cache.cached('client','expired') is None
    asyncio.run(run())
