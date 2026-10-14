"""OAuth records in the persistent store: consumed once, hashed, serialised and revoked.
Needs a disposable migrated Postgres (GATEWAY_TEST_DATABASE_URL); no requests to Google."""
import asyncio
import hashlib
import json
import time

import pytest
from mcp.server.auth.provider import AuthorizationParams, AuthorizeError, RegistrationError, TokenError

from support.gateway import GATEWAY  # noqa: F401  (puts the gateway on sys.path)
from support.oauth import MemoryStore, client, code, provider  # noqa: F401  (provider is a fixture)
from policy import authorize, load_policy  # noqa: E402
from horology_runtime.oauth.provider import GoogleOAuthProvider, GatewayCode  # noqa: E402
from shared.consent import NOTE, gateway_consent  # noqa: E402


def test_persistent_store_consumes_once_and_hashes_credentials():
    import os
    import psycopg
    from database.connection import Database
    from horology_runtime.oauth.store import OAuthRepository
    dsn = os.environ.get('GATEWAY_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Disposable migrated Postgres is required')
    with psycopg.connect(dsn) as db, db.cursor() as cur:
        cur.execute('TRUNCATE gateway_auth.records')
    async def run():
        async with Database(os.environ.get('GATEWAY_TEST_RUNTIME_URL', dsn)) as database:
            store = OAuthRepository(database, 'gateway_auth.records')
            key = 'opaque-code-do-not-store-raw'
            await store.put('code', key, {'client_id':'test'}, time.time()+120)
            with psycopg.connect(dsn) as db, db.cursor() as cur:
                cur.execute('SELECT key_hash,data FROM gateway_auth.records')
                digest, data = cur.fetchone()
                assert digest == hashlib.sha256(key.encode()).hexdigest()
                assert key not in json.dumps(data)
                cur.execute("SELECT has_table_privilege('horology_gateway','public.alembic_version','SELECT')")
                assert cur.fetchone() == (False,)
            results = await asyncio.gather(*(store.get('code',key,consume=True) for _ in range(8)))
            assert sum(result is not None for result in results) == 1
    asyncio.run(run())


def test_persistent_refresh_and_revoke_are_serialized(provider):
    import os
    from database.connection import Database
    from horology_runtime.oauth.store import OAuthRepository
    dsn = os.environ.get('GATEWAY_TEST_RUNTIME_URL')
    if not dsn:
        pytest.skip('Disposable runtime Postgres is required')
    async def run():
        async with Database(dsn) as database:
            provider.store = OAuthRepository(database, 'gateway_auth.records')
            first = await provider.exchange_authorization_code(client(), await code(provider))
            refresh = await provider.load_refresh_token(client(),first.refresh_token)
            token = await provider.load_access_token(first.access_token)
            async def rotate():
                try:
                    return await provider.exchange_refresh_token(client(),refresh,['gateway'])
                except TokenError:
                    return None
            result, _ = await asyncio.gather(rotate(), provider.revoke_token(token))
            assert await provider.load_access_token(first.access_token) is None
            if result:
                assert await provider.load_access_token(result.access_token) is None
                assert await provider.load_refresh_token(client(),result.refresh_token) is None
    asyncio.run(run())


def test_persistent_wrong_client_exchange_rolls_back_code_consumption(provider):
    import os
    from database.connection import Database
    from horology_runtime.oauth.store import OAuthRepository
    dsn = os.environ.get('GATEWAY_TEST_RUNTIME_URL')
    if not dsn:
        pytest.skip('Disposable runtime Postgres is required')
    async def run():
        async with Database(dsn) as database:
            provider.store = OAuthRepository(database, 'gateway_auth.records')
            value = await code(provider)
            other = client()
            other.client_id = 'wrong-client'
            with pytest.raises(TokenError):
                await provider.exchange_authorization_code(other, value)
            # Failure rolled back DELETE; the authorized client can still redeem.
            result = await provider.exchange_authorization_code(client(),value)
            assert await provider.load_access_token(result.access_token) is not None
    asyncio.run(run())


def test_persistent_revoke_email_removes_only_that_person(provider):
    import os
    from database.connection import Database
    from horology_runtime.oauth.store import OAuthRepository
    dsn = os.environ.get('GATEWAY_TEST_RUNTIME_URL')
    if not dsn:
        pytest.skip('Disposable runtime Postgres is required')
    async def run():
        async with Database(dsn) as database:
            provider.store = OAuthRepository(database, 'gateway_auth.records')
            mine = await provider.exchange_authorization_code(client(), await code(provider, 'owner@example.com'))
            theirs = await provider.exchange_authorization_code(client(), await code(provider, 'other@example.com'))
            assert await provider.store.revoke_email('owner@example.com') == 2
            assert await provider.load_access_token(mine.access_token) is None
            assert await provider.load_access_token(theirs.access_token) is not None
    asyncio.run(run())
