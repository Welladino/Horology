"""Gateway authorization, shared-budget and provider-boundary regression tests.

All upstream requests are mocked. HTTP smoke testing is in smoke.py.
"""
import asyncio
import concurrent.futures
import copy
import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3] / 'mcp-servers/mcp-gateway'
sys.path.insert(0, str(ROOT))
from integrations.supabase import client as supabase
from integrations.firecrawl import client as firecrawl
from integrations.tavily import client as tavily
from policy import Denied, authorize, load_policy
from database.connection import Database
from database.repositories.quotas import QuotaRepository
from database.repositories.cache import CacheRepository
import psycopg
import os
import psycopg2
from server import build_server


@pytest.fixture
def ledger_dsn():
    dsn = os.environ.get('GATEWAY_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Set GATEWAY_TEST_DATABASE_URL to a disposable migrated Postgres database')
    with psycopg2.connect(dsn) as db, db.cursor() as cur:
        cur.execute('TRUNCATE gateway_quotas.reservations, gateway_quotas.cache')
    yield os.environ.get('GATEWAY_TEST_RUNTIME_URL', dsn)


@pytest.fixture
def policy():
    p = load_policy(ROOT / 'config/policy.example.json')
    return p


def test_baked_cloud_policy_loads_and_holds_no_credentials():
    path = ROOT / 'config/policy.cloud.json'
    load_policy(path)
    text = path.read_text().lower()
    assert not any(word in text for word in ('password', 'secret', 'token', 'postgres://', 'postgresql://', 'api_key'))


def test_shared_policy_rejects_unapproved_tools(policy):
    with pytest.raises(Denied):
        authorize(policy, 'delete_database')
    assert authorize(policy, 'gateway_status') is policy['access']



def test_global_scope_cannot_be_widened(tmp_path, policy):
    policy['access']['schemas'].append('other_private')
    path = tmp_path / 'policy.json'
    path.write_text(json.dumps(policy))
    with pytest.raises(Denied):
        load_policy(path)



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










def test_supabase_wrong_project_and_role_never_connect(policy, monkeypatch):
    config = policy['access']
    with patch.object(supabase.psycopg2, 'connect') as connect:
        for dsn in ['host=db.other.supabase.co user=horology_agents', 'host=db.pyywbjossvjngoxocdxk.supabase.co user=postgres', 'host=db.pyywbjossvjngoxocdxk.supabase.co user=welladino_metadata']:
            monkeypatch.setenv('SUPABASE_METADATA_DSN', dsn)
            with pytest.raises(Denied):
                supabase.schema_query(policy, config, 'public')
        connect.assert_not_called()



def test_tavily_no_auto_upgrade(policy, monkeypatch):
    monkeypatch.setenv('TAVILY_API_KEY', 'test-only')
    with patch.object(tavily, 'request', new_callable=AsyncMock, return_value={'results': []}) as request:
        assert asyncio.run(tavily.tavily('example')) == []
        payload = request.call_args.kwargs['body']
        assert payload['search_depth'] == 'basic'
        assert payload['auto_parameters'] is False
        assert payload['max_results'] == 5



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




def test_auth_schema_never_connects(policy):
    with patch.object(supabase.psycopg2, 'connect') as connect:
        with pytest.raises(Denied):
            supabase.schema_query(policy, policy['access'], 'auth', performance=True)
        connect.assert_not_called()



def test_firecrawl_private_urls_are_denied(policy):
    with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
        with pytest.raises(Denied, match='Private'):
            firecrawl.public_url('https://example.com')



def test_fixed_schema_queries_parameterize_table_and_omit_sensitive_data(policy, monkeypatch):
    from unittest.mock import MagicMock
    monkeypatch.setenv('SUPABASE_METADATA_DSN', 'host=db.pyywbjossvjngoxocdxk.supabase.co user=horology_agents')
    connection = MagicMock()
    cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []
    with patch.object(supabase.psycopg2, 'connect', return_value=connection):
        supabase.schema_query(policy, policy['access'], 'public', "x'; DROP TABLE y;--")
    sql, args = cursor.execute.call_args_list[1].args
    assert args == ('public', "x'; DROP TABLE y;--")
    assert 'DROP TABLE' not in sql
    assert 'attnum>0' in sql
    assert 'pg_get_expr' not in sql
    connection.__enter__.return_value.set_session.assert_called_once_with(readonly=True)












def test_previous_day_and_month_do_not_consume_current_budget(ledger_dsn):
    async def run():
        async with Database(ledger_dsn) as database:
            quotas = QuotaRepository(database)
            cache = CacheRepository(database)
            budget = {'daily': 1, 'monthly': 1}
            await quotas.reserve('old', 'search', 'tavily', 1, budget)
            with psycopg2.connect(os.environ['GATEWAY_TEST_DATABASE_URL']) as db, db.cursor() as cur:
                cur.execute("UPDATE gateway_quotas.reservations SET day=CURRENT_DATE-40, month=date_trunc('month', CURRENT_DATE-40)::date")
            await quotas.reserve('new', 'search', 'tavily', 1, budget)
            with pytest.raises(Denied, match='Shared provider budget'):
                await quotas.reserve('other', 'search', 'tavily', 1, budget)
    asyncio.run(run())



def test_database_failure_has_no_local_fallback():
    async def run():
        async with Database('host=unused') as database:
            with patch.object(database.pool, 'getconn', AsyncMock(side_effect=psycopg.OperationalError('unavailable'))):
                with pytest.raises(psycopg.OperationalError):
                    await QuotaRepository(database).reserve('a','read')
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



def test_neon_tls_uses_public_trust_instead_of_supabase_ca(monkeypatch):
    monkeypatch.setenv('PGSSLROOTCERT','/certs/supabase-ca.crt')
    with patch('horology_runtime.database.AsyncConnectionPool') as pool:
        Database('host=example.neon.tech user=horology_gateway sslmode=require')
    options = pool.call_args.kwargs
    assert options['kwargs']['sslmode'] == 'verify-full'
    assert options['kwargs']['sslrootcert'] != '/certs/supabase-ca.crt'
    assert options['kwargs']['prepare_threshold'] is None
    assert options['open'] is False
    assert options['max_size'] == 4



@pytest.mark.parametrize('retired', ['github_read_file', 'drive_create_draft'])
def test_retired_tool_grants_fail_startup(tmp_path, policy, retired):
    policy['access']['tools'].append(retired)
    path = tmp_path / 'policy.json'
    path.write_text(json.dumps(policy))
    with pytest.raises(Denied, match='parked'):
        load_policy(path)


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


def test_http_lifespan_opens_database_for_oauth_and_closes_on_failure():
    from contextlib import asynccontextmanager
    from server import database_app
    from unittest.mock import MagicMock
    events = []
    class FakeDatabase:
        async def __aenter__(self):
            events.append('open')
            return self
        async def __aexit__(self, *exc):
            events.append('close')
        async def check_ready(self):
            events.append('ready')
    from starlette.applications import Starlette
    @asynccontextmanager
    async def mcp_lifespan(app):
        events.append('mcp-open')
        try:
            yield
        finally:
            events.append('mcp-close')
    async def run():
        mcp = MagicMock()
        mcp.streamable_http_app.return_value = Starlette(lifespan=mcp_lifespan)
        app = database_app(mcp, FakeDatabase())
        with pytest.raises(RuntimeError):
            async with app.router.lifespan_context(app):
                assert events == ['open','ready','mcp-open']
                raise RuntimeError('request failed')
        assert events == ['open','ready','mcp-open','mcp-close','close']
    asyncio.run(run())
