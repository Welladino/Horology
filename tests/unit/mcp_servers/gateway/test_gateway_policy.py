"""Gateway authorization and provider boundaries: policy loading, scope, URL and schema checks.
All upstream requests and the database are mocked. HTTP smoke testing is in tests/manual/gateway/smoke.py."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import psycopg
import pytest

from support.gateway import GATEWAY, policy  # noqa: F401  (policy is a fixture)
from integrations.supabase import client as supabase  # noqa: E402
from integrations.firecrawl import client as firecrawl  # noqa: E402
from integrations.tavily import client as tavily  # noqa: E402
from policy import Denied, authorize, load_policy  # noqa: E402
from database.connection import Database  # noqa: E402
from database.repositories.quotas import QuotaRepository  # noqa: E402


def test_baked_cloud_policy_loads_and_holds_no_credentials():
    path = GATEWAY / 'config/policy.cloud.json'
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


def test_supabase_wrong_project_and_role_never_connect(policy, monkeypatch):
    config = policy['access']
    with patch.object(supabase, 'pool_for') as connect:
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


def test_auth_schema_never_connects(policy):
    with patch.object(supabase, 'pool_for') as connect:
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
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []
    supabase._pools.clear()
    with patch.object(supabase, 'ConnectionPool') as pool:
        pool.return_value.connection.return_value = connection
        supabase.schema_query(policy, policy['access'], 'public', "x'; DROP TABLE y;--")
        supabase.schema_query(policy, policy['access'], 'public', 'other')
    supabase._pools.clear()
    pool.assert_called_once()
    options = pool.call_args.kwargs
    assert options['kwargs']['sslmode'] == 'verify-full' and options['kwargs']['prepare_threshold'] is None
    assert options['max_size'] == 2 and options['check'] is pool.check_connection
    configured = MagicMock()
    options['configure'](configured)
    assert configured.read_only is True
    sql, args = cursor.execute.call_args_list[1].args
    assert args == ('public', "x'; DROP TABLE y;--")
    assert 'DROP TABLE' not in sql
    assert 'attnum>0' in sql
    assert 'pg_get_expr' not in sql


def test_database_failure_has_no_local_fallback():
    async def run():
        async with Database('host=unused') as database:
            with patch.object(database.pool, 'getconn', AsyncMock(side_effect=psycopg.OperationalError('unavailable'))):
                with pytest.raises(psycopg.OperationalError):
                    await QuotaRepository(database).reserve('a','read')
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
