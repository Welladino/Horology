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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integrations.github import client as github
from integrations.google_drive import client as google_drive
from integrations.supabase import client as supabase
from integrations.firecrawl import client as firecrawl
from integrations.tavily import client as tavily
from policy import Denied, Ledger, authorize, load_policy
from server import build_server


@pytest.fixture
def policy():
    p = load_policy(ROOT / 'config/policy.example.json')
    p['assignments']['local-smoke']['expires_at'] = int(time.time()) + 3600
    return p


def test_expired_and_unapproved_tools(policy):
    with pytest.raises(Denied):
        authorize(policy, 'local-smoke', 'delete_database')
    policy['assignments']['local-smoke']['expires_at'] = 0
    with pytest.raises(Denied):
        authorize(policy, 'local-smoke', 'gateway_status')



def test_global_scope_cannot_be_widened(tmp_path, policy):
    policy['assignments']['local-smoke']['repositories'].append('another/private')
    path = tmp_path / 'policy.json'
    path.write_text(json.dumps(policy))
    with pytest.raises(Denied):
        load_policy(path)



def test_atomic_budget_across_assignments_and_connections(tmp_path):
    path = tmp_path / 'ledger.sqlite3'
    Ledger(path)
    def reserve(i):
        try:
            Ledger(path).reserve(str(i), 'search', 5, 'tavily', 1, {'daily': 3, 'monthly': 10, 'assignment': 5, 'calls_per_assignment': 5})
            return True
        except Denied:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, range(20)))
    assert sum(results) == 3



def test_fail_closed_budget_and_restart_counts(tmp_path):
    path = tmp_path / 'ledger.sqlite3'
    ledger = Ledger(path)
    with pytest.raises(Denied):
        ledger.reserve('a', 'search', 5, 'tavily', 1, {'daily': 0, 'monthly': 10, 'assignment': 5, 'calls_per_assignment': 5})
    ledger.reserve('a', 'read', 1)
    with pytest.raises(Denied):
        Ledger(path).reserve('a', 'read', 1)



def test_assignment_credit_cap_combines_basic_and_advanced(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.sqlite3')
    budget = {'daily': 100, 'monthly': 100, 'assignment': 5, 'calls_per_assignment': 5}
    ledger.reserve('a', 'basic', 5, 'tavily', 1, budget)
    ledger.reserve('a', 'advanced', 2, 'tavily', 2, budget)
    ledger.reserve('a', 'advanced', 2, 'tavily', 2, budget)
    with pytest.raises(Denied):
        ledger.reserve('a', 'basic', 5, 'tavily', 1, budget)



def test_cache_is_assignment_scoped(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.sqlite3')
    ledger.save_cache('a', 'q', [])
    assert ledger.cached('a', 'q') == []
    assert ledger.cached('b', 'q') is None



def test_repo_escape_and_path_traversal_never_call_provider(policy):
    config = policy['assignments']['local-smoke']
    with patch.object(github, 'request', new_callable=AsyncMock) as request:
        for repo, path in [('other/repo', 'README.md'), ('Welladino/Horology', '../.env')]:
            with pytest.raises(Denied):
                asyncio.run(github.github_file(policy, config, repo, path, 'main'))
        request.assert_not_called()



def test_drive_unapproved_file_and_range(policy):
    config = policy['assignments']['local-smoke']
    with patch.object(google_drive, 'request', new_callable=AsyncMock) as request:
        with pytest.raises(Denied):
            asyncio.run(google_drive.drive_read(policy, config, 'unknown', ''))
        with pytest.raises(Denied):
            asyncio.run(google_drive.drive_read(policy, config, config['drive_files'][0], 'Pipeline!A:ZZ'))
        request.assert_not_called()



def test_supabase_wrong_project_and_role_never_connect(policy, monkeypatch):
    config = policy['assignments']['local-smoke']
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



def test_two_paid_calls_combined_across_tools(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.sqlite3')
    budget = {'daily': 50, 'monthly': 500, 'assignment': 4, 'calls_per_assignment': 2}
    ledger.reserve('a', 'basic', 2, 'tavily', 1, budget)
    ledger.reserve('a', 'advanced', 2, 'tavily', 2, budget)
    with pytest.raises(Denied, match='session call limit'):
        ledger.reserve('a', 'basic', 2, 'tavily', 1, budget)



def test_monthly_budget_shared_across_assignments(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.sqlite3')
    budget = {'daily': 50, 'monthly': 2, 'assignment': 2, 'calls_per_assignment': 2}
    ledger.reserve('a', 'search', 2, 'tavily', 2, budget)
    with pytest.raises(Denied, match='Shared provider budget'):
        ledger.reserve('b', 'search', 2, 'tavily', 1, budget)



def test_auth_schema_never_connects(policy):
    with patch.object(supabase.psycopg2, 'connect') as connect:
        with pytest.raises(Denied):
            supabase.schema_query(policy, policy['assignments']['local-smoke'], 'auth', performance=True)
        connect.assert_not_called()



def test_firecrawl_no_arbitrary_or_private_urls(policy):
    with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
        with pytest.raises(Denied, match='explicitly approved'):
            firecrawl.approved_url(policy, policy['assignments']['local-smoke'], 'https://example.com')
        policy['firecrawl']['approved_urls'] = ['https://example.com']
        policy['assignments']['local-smoke']['approved_urls'] = ['https://example.com']
        with pytest.raises(Denied, match='Private'):
            firecrawl.approved_url(policy, policy['assignments']['local-smoke'], 'https://example.com')



def test_fixed_schema_queries_parameterize_table_and_omit_sensitive_data(policy, monkeypatch):
    from unittest.mock import MagicMock
    monkeypatch.setenv('SUPABASE_METADATA_DSN', 'host=db.pyywbjossvjngoxocdxk.supabase.co user=horology_agents')
    connection = MagicMock()
    cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []
    with patch.object(supabase.psycopg2, 'connect', return_value=connection):
        supabase.schema_query(policy, policy['assignments']['local-smoke'], 'public', "x'; DROP TABLE y;--")
    sql, args = cursor.execute.call_args_list[1].args
    assert args == ('public', "x'; DROP TABLE y;--")
    assert 'DROP TABLE' not in sql
    assert 'attnum>0' in sql
    assert 'pg_get_expr' not in sql
    connection.__enter__.return_value.set_session.assert_called_once_with(readonly=True)



def test_github_search_qualifier_injection_never_calls_provider(policy):
    with patch.object(github, 'request', new_callable=AsyncMock) as request:
        with pytest.raises(Denied):
            asyncio.run(github.github_search(policy, policy['assignments']['local-smoke'], 'Welladino/Horology', 'repo:other/repo'))
        request.assert_not_called()



@pytest.mark.parametrize('name', ['github_repo_status', 'github_recent_commits', 'github_ci_status', 'github_dependabot_alerts'])
def test_monitoring_tools_reject_other_repositories(policy, name):
    with patch.object(github, '_monitor_get', new_callable=AsyncMock) as request:
        with pytest.raises(Denied):
            asyncio.run(getattr(github, name)(policy, policy['assignments']['local-smoke'], 'other/repo'))
        request.assert_not_called()


def test_ci_default_branch_is_awaited_before_lookup(policy):
    with patch.object(github, '_monitor_get', new_callable=AsyncMock, side_effect=[{'default_branch': 'main'}, {'workflow_runs': []}]) as request:
        result = asyncio.run(github.github_ci_status(policy, policy['assignments']['local-smoke'], 'Welladino/Horology'))
        assert result == {'branch': 'main', 'status': 'no_runs_found'}
        assert request.call_args.kwargs['params'] == {'branch': 'main', 'per_page': 1}


def test_dependabot_bounds_payload_and_rejects_invalid_state(policy):
    with patch.object(github, '_monitor_get', new_callable=AsyncMock, return_value=[]) as request:
        with pytest.raises(Denied):
            asyncio.run(github.github_dependabot_alerts(policy, policy['assignments']['local-smoke'], 'Welladino/Horology', 'anything'))
        request.assert_not_called()
        assert asyncio.run(github.github_dependabot_alerts(policy, policy['assignments']['local-smoke'], 'Welladino/Horology')) == []
        assert request.call_args.kwargs['params']['per_page'] == 5
