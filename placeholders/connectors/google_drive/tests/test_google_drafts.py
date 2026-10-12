"""Google refresh and draft permission regressions; provider calls are mocked.

Real template copying and durable receipt concurrency require separate live/local-DB checks.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'mcp-servers/mcp-gateway'))
from integrations.google_drive.auth import GoogleCredentials
from integrations.google_drive.rules import drafts
from policy import Denied
from horology_runtime.settings import TIMEOUTS


@pytest.fixture
def provider_credentials(monkeypatch):
    for key in ('GOOGLE_DRIVE_CLIENT_ID', 'GOOGLE_DRIVE_CLIENT_SECRET', 'GOOGLE_DRIVE_REFRESH_TOKEN'):
        monkeypatch.setenv(key, 'test-only')


def test_concurrent_refresh_is_shared_and_expiry_refreshes(provider_credentials):
    credentials = GoogleCredentials()
    response = httpx.Response(200, json={'access_token': 'test-access', 'expires_in': 3600})
    with patch('integrations.google_drive.auth.httpx.AsyncClient') as factory:
        client = factory.return_value.__aenter__.return_value
        client.post = AsyncMock(return_value=response)
        async def run():
            assert await asyncio.gather(*(credentials.access_token() for _ in range(8))) == ['test-access'] * 8
            assert client.post.await_count == 1
            credentials.expires = 0
            assert await credentials.access_token() == 'test-access'
            assert client.post.await_count == 2
        asyncio.run(run())
        assert factory.call_args.kwargs['timeout'] == TIMEOUTS.gateway_http
        assert factory.call_args.kwargs['follow_redirects'] is False


@pytest.mark.parametrize('status,data', [(400, {'error': 'invalid_grant', 'error_description': 'secret'}), (200, {'access_token': None, 'expires_in': 3600}), (200, {'access_token': 'test', 'expires_in': 30})])
def test_failed_refresh_never_caches_credentials(provider_credentials, status, data):
    credentials = GoogleCredentials()
    with patch('integrations.google_drive.auth.httpx.AsyncClient') as factory:
        factory.return_value.__aenter__.return_value.post = AsyncMock(return_value=httpx.Response(status, json=data))
        with pytest.raises(Denied) as caught:
            asyncio.run(credentials.access_token())
        assert 'secret' not in str(caught.value)
        assert credentials.token is None


def test_refresh_timeout_keeps_cache_empty(provider_credentials):
    credentials = GoogleCredentials()
    with patch('integrations.google_drive.auth.httpx.AsyncClient') as factory:
        factory.return_value.__aenter__.return_value.post = AsyncMock(side_effect=httpx.ReadTimeout('injected'))
        with pytest.raises(httpx.ReadTimeout):
            asyncio.run(credentials.access_token())
        assert credentials.token is None


@pytest.fixture
def scope():
    return {'drive': {'output_folders': ['folder'], 'templates': ['template']}}, {'drive_output_folders': ['folder'], 'drive_pipeline_ids': ['pipeline'], 'drive_templates': ['template']}


@pytest.mark.parametrize('folder,pipeline,template', [('other', 'pipeline', ''), ('folder', 'other', ''), ('folder', 'pipeline', 'other')])
def test_unapproved_draft_scope_is_denied(scope, folder, pipeline, template):
    with pytest.raises(Denied):
        drafts.scope_check(*scope, folder, pipeline, template)


def test_template_copy_uses_approved_parent_and_draft_tags(scope):
    with patch.object(drafts, 'metadata', AsyncMock(side_effect=[{'mimeType': 'application/vnd.google-apps.folder'}, {'mimeType': 'application/vnd.google-apps.document'}])), patch.object(drafts.credentials, 'access_token', AsyncMock(return_value='test')), patch.object(drafts, 'request', AsyncMock(return_value={'id': 'new', 'name': 'Draft'})) as request:
        result = asyncio.run(drafts.create(*scope, 'assignment', 'folder', 'pipeline', 'Draft', 'template'))
        assert result['id'] == 'new'
        assert request.call_args.args[1].endswith('/template/copy')
        body = request.call_args.kwargs['body']
        assert body['parents'] == ['folder']
        assert body['appProperties']['horology_assignment'] == 'assignment'
        assert body['appProperties']['horology_state'] == 'draft'


@pytest.mark.parametrize('changes', [{'parents': ['elsewhere']}, {'trashed': True}, {'appProperties': {'horology_assignment': 'other', 'horology_state': 'draft'}}, {'appProperties': {'horology_assignment': 'assignment', 'horology_state': 'accepted'}}])
def test_moved_trashed_other_assignment_or_accepted_doc_cannot_be_edited(scope, changes):
    class Store:
        def draft(self, assignment, file_id):
            return {'folder': 'folder', 'pipeline_id': 'pipeline'}
    meta = {'mimeType': 'application/vnd.google-apps.document', 'parents': ['folder'], 'appProperties': {'horology_assignment': 'assignment', 'horology_state': 'draft'}}
    meta.update(changes)
    with patch.object(drafts, 'metadata', AsyncMock(return_value=meta)):
        with pytest.raises(Denied):
            asyncio.run(drafts.own_draft(*scope, 'assignment', 'file', Store()))


def test_edits_send_required_revision_and_propagate_conflict():
    with patch.object(drafts.credentials, 'access_token', AsyncMock(return_value='test')), patch.object(drafts, 'request', AsyncMock(side_effect=Denied('stale revision'))) as request:
        with pytest.raises(Denied):
            asyncio.run(drafts.edit('file', 'revision', [], 'text'))
        assert request.call_args.kwargs['body']['writeControl'] == {'requiredRevisionId': 'revision'}
        assert request.await_count == 1


@pytest.fixture
def write_store():
    import os
    import psycopg2
    from shared.ledger import Ledger
    from shared.writes import WriteStore
    admin = os.environ.get('GATEWAY_TEST_DATABASE_URL')
    runtime = os.environ.get('GATEWAY_TEST_RUNTIME_URL')
    if not admin or not runtime:
        pytest.skip('Disposable migrated Postgres credentials required')
    with psycopg2.connect(admin) as db, db.cursor() as cur:
        cur.execute('TRUNCATE gateway_operations.operations')
    return WriteStore(Ledger(runtime))


def test_durable_receipt_replay_conflict_and_assignment_isolation(write_store):
    payload = {'title': 'Draft'}
    assert write_store.begin('a', 'drive_create_draft', 'key', payload) is None
    with pytest.raises(Denied, match='uncertain'):
        write_store.begin('a', 'drive_create_draft', 'key', payload)
    receipt = {'id': 'file', 'folder': 'folder', 'pipeline_id': 'pipeline'}
    write_store.finish('a', 'drive_create_draft', 'key', receipt)
    assert write_store.begin('a', 'drive_create_draft', 'key', payload) == receipt
    assert write_store.draft('a', 'file') == receipt
    with pytest.raises(Denied):
        write_store.begin('a', 'drive_create_draft', 'key', {'title': 'Different'})
    with pytest.raises(Denied):
        write_store.draft('b', 'file')


def test_concurrent_receipt_claim_allows_one_external_write(write_store):
    from concurrent.futures import ThreadPoolExecutor
    def claim(_):
        try:
            return write_store.begin('a', 'drive_create_draft', 'concurrent', {}) is None
        except Denied:
            return False
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(claim, range(6))) == 1
