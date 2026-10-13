"""OAuth boundaries: mocked Google identity, replay, consent and assignment expiry.

No requests to Google or paid providers. Persistent-store tests use disposable DB.
"""
import asyncio
import copy
from contextlib import asynccontextmanager
import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from mcp.server.auth.provider import AuthorizationParams, TokenError, RegistrationError, AuthorizeError
from mcp.shared.auth import OAuthClientInformationFull

ROOT = Path(__file__).resolve().parents[3] / 'mcp-servers/mcp-gateway'
sys.path.insert(0, str(ROOT))
from policy import authorize, load_policy
from horology_runtime.oauth.provider import GoogleOAuthProvider, GatewayCode
from shared.consent import NOTE, gateway_consent
from server import build_server


class MemoryStore:
    def __init__(self):
        self.data = {}
    async def put(self, kind, key, value, expires):
        self.data[kind,key] = (copy.deepcopy(value), expires)
    async def get(self, kind, key, consume=False):
        value = self.data.pop((kind,key),None) if consume else self.data.get((kind,key))
        return copy.deepcopy(value[0]) if value and value[1]>time.time() else None
    @asynccontextmanager
    async def grant_transaction(self):
        yield self
    async def revoke(self, grant):
        self.data = {k:v for k,v in self.data.items() if v[0].get('grant_id') != grant}
    async def revoke_email(self, email):
        before = len(self.data)
        self.data = {k:v for k,v in self.data.items() if not (k[0] in ('access','refresh') and v[0].get('email') == email.lower())}
        return before - len(self.data)


@pytest.fixture
def provider():
    policy = load_policy(ROOT/'config/policy.example.json')
    return GoogleOAuthProvider(MemoryStore(),'http://localhost:8767','google-client','test-secret',scope='gateway',
                               consent=lambda: (*gateway_consent(policy), NOTE),
                               check=lambda email: authorize(policy, 'gateway_status'))


def client():
    return OAuthClientInformationFull(client_id='client',client_name='Test client',redirect_uris=['http://localhost:9000/callback'],scope='gateway',token_endpoint_auth_method='none',grant_types=['authorization_code','refresh_token'])


async def code(provider, email=''):
    value = GatewayCode(email=email,code='test-code',scopes=['gateway'],expires_at=time.time()+120,client_id='client',code_challenge='challenge',redirect_uri='http://localhost:9000/callback',redirect_uri_provided_explicitly=True,resource=provider.url+'/mcp',subject='google-subject',grant_id='grant')
    await provider.store.put('code',value.code,value.model_dump(mode='json',exclude={'code'}),value.expires_at)
    return value


def test_code_replay_refresh_rotation_revocation(provider):
    async def run():
        code_value = await code(provider)
        first = await provider.exchange_authorization_code(client(),code_value)
        with pytest.raises(TokenError):
            await provider.exchange_authorization_code(client(),code_value)
        token = await provider.load_access_token(first.access_token)
        assert 'assignment' not in token.claims
        assert token.client_id == 'client'
        refresh = await provider.load_refresh_token(client(),first.refresh_token)
        second = await provider.exchange_refresh_token(client(),refresh,['gateway'])
        assert second.refresh_token != first.refresh_token
        with pytest.raises(TokenError):
            await provider.exchange_refresh_token(client(),refresh,['gateway'])
        await provider.revoke_token(token)
        assert await provider.load_access_token(second.access_token) is None
        assert await provider.load_refresh_token(client(),second.refresh_token) is None
    asyncio.run(run())


def test_refresh_renews_without_assignment_expiry(provider):
    async def run():
        code_value = await code(provider)
        first = await provider.exchange_authorization_code(client(),code_value)
        refresh = await provider.load_refresh_token(client(),first.refresh_token)
        second = await provider.exchange_refresh_token(client(),refresh,['gateway'])
        assert second.expires_in > 0
        assert await provider.load_access_token(second.access_token) is not None
    asyncio.run(run())


@pytest.mark.parametrize('uri',['http://example.com/callback','https://user:pass@example.com/callback','https://example.com/callback#fragment','https://example.com;form-action/callback'])
def test_reject_bad_redirect(provider,uri):
    async def run():
        info=client(); info.redirect_uris=[uri]
        with pytest.raises(RegistrationError):
            await provider.register_client(info)
    asyncio.run(run())


def test_reject_unknown_resource(provider):
    async def run():
        params=AuthorizationParams(state='state',scopes=['gateway'],code_challenge='challenge',redirect_uri='http://localhost:9000/callback',redirect_uri_provided_explicitly=True,resource='https://other.example/mcp')
        with pytest.raises(AuthorizeError):
            await provider.authorize(client(),params)
    asyncio.run(run())


def test_google_callback_requires_cookie_approved_identity_and_consent(provider):
    from starlette.applications import Starlette
    from starlette.routing import Route
    from urllib.parse import urlparse,parse_qs
    async def run():
        await provider.register_client(client())
        params=AuthorizationParams(state='client-state',scopes=['gateway'],code_challenge='challenge',redirect_uri='http://localhost:9000/callback',redirect_uri_provided_explicitly=True)
        app=Starlette(routes=[Route('/auth/google/start',provider.start),Route('/auth/google/callback',provider.callback),Route('/auth/consent',provider.consent,methods=['POST'])])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url=provider.url) as http:
            start=await provider.authorize(client(),params)
            state=parse_qs(urlparse(start).query)['state'][0]
            assert (await http.get('/auth/google/callback',params={'state':state,'code':'google-code'})).status_code==400
            await http.get(start)
            # Google refuses accounts outside the Audience test users; any failed verification is rejected.
            provider.verify_google=AsyncMock(side_effect=ValueError('Unverified Google identity'))
            assert (await http.get('/auth/google/callback',params={'state':state,'code':'google-code'})).status_code==403
            start=await provider.authorize(client(),params)
            state=parse_qs(urlparse(start).query)['state'][0]
            await http.get(start)
            provider.verify_google=AsyncMock(return_value={'email':'owner@example.com','sub':'subject'})
            response=await http.get('/auth/google/callback',params={'state':state,'code':'google-code'})
            assert response.status_code==200 and 'Authorize Horology access' in response.text
            assert "form-action 'self' http://localhost:9000;" in response.headers["content-security-policy"]
            assert "style-src 'sha256-" in response.headers["content-security-policy"]
            assert "owner@example.com" in response.text
            assert not any(k[0]=='code' for k in provider.store.data)
            secret=http.cookies.get('horology_oauth')
            assert (await http.post('/auth/consent',data={'consent':'wrong','decision':'allow'})).status_code==400
            response=await http.post('/auth/consent',data={'consent':secret,'decision':'allow'})
            assert response.status_code==303
            assert [v[0]['email'] for k,v in provider.store.data.items() if k[0]=='code']==['owner@example.com']
            assert parse_qs(urlparse(response.headers['location']).query)['state']==['client-state']
            assert (await http.post('/auth/consent',data={'consent':secret,'decision':'allow'})).status_code==400
    asyncio.run(run())


def test_sdk_pkce_and_anonymous_boundary(provider):
    from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
    from mcp.server.mcpserver import MCPServer
    import base64
    async def run():
        mcp=MCPServer('test',auth_server_provider=provider,auth=AuthSettings(issuer_url=provider.url,resource_server_url=provider.url+'/mcp',required_scopes=['gateway'],client_registration_options=ClientRegistrationOptions(enabled=True,valid_scopes=['gateway'],default_scopes=['gateway']),revocation_options=RevocationOptions(enabled=True)))
        app=mcp.streamable_http_app(stateless_http=True,json_response=True)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url=provider.url) as http:
                assert (await http.post('/mcp',json={})).status_code==401
                assert (await http.get('/.well-known/oauth-authorization-server')).status_code==200
                response=await http.post('/register',json={'redirect_uris':['http://localhost:9000/callback'],'token_endpoint_auth_method':'none','grant_types':['authorization_code','refresh_token'],'response_types':['code'],'scope':'gateway'})
                assert response.status_code==201,response.text
                info=response.json()
                value=await code(provider); value.client_id=info['client_id']
                verifier='a'*64
                value.code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
                await provider.store.put('code',value.code,value.model_dump(mode='json',exclude={'code'}),value.expires_at)
                data={'grant_type':'authorization_code','code':value.code,'client_id':info['client_id'],'redirect_uri':str(value.redirect_uri),'code_verifier':'wrong'}
                assert (await http.post('/token',data=data)).status_code==400
                data['code_verifier']=verifier
                response=await http.post('/token',data=data)
                assert response.status_code==200,response.text
                assert (await http.post('/token',data=data)).status_code==400
    asyncio.run(run())


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



@pytest.mark.parametrize('change',[{'iss':'https://evil.example'},{'aud':'other-client'},{'nonce':'wrong'},{'email_verified':False},{'exp':1}])
def test_signed_google_identity_rejects_wrong_claims(provider,change):
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from types import SimpleNamespace
    from unittest.mock import patch
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    claims={'iss':'https://accounts.google.com','aud':provider.client_id,'sub':'subject','iat':int(time.time()),'exp':int(time.time())+120,'nonce':'expected','email':'owner@example.com','email_verified':True}
    claims.update(change)
    encoded=jwt.encode(claims,key,algorithm='RS256')
    response=httpx.Response(200,json={'id_token':encoded},request=httpx.Request('POST','https://oauth2.googleapis.com/token'))
    with patch('httpx.AsyncClient.post',AsyncMock(return_value=response)),patch.object(provider.jwks,'get_signing_key_from_jwt',return_value=SimpleNamespace(key=key.public_key())):
        with pytest.raises((ValueError,jwt.PyJWTError)):
            asyncio.run(provider.verify_google('fake-code','expected'))


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


def test_provider_needs_no_email_allowlist():
    import inspect
    assert 'allowed_emails' not in inspect.signature(GoogleOAuthProvider).parameters


def test_email_survives_refresh_and_revoke_email_removes_tokens(provider):
    async def run():
        first = await provider.exchange_authorization_code(client(), await code(provider, 'owner@example.com'))
        refresh = await provider.load_refresh_token(client(), first.refresh_token)
        assert refresh.email == 'owner@example.com'
        second = await provider.exchange_refresh_token(client(), refresh, ['gateway'])
        assert (await provider.load_refresh_token(client(), second.refresh_token)).email == 'owner@example.com'
        other = await provider.exchange_authorization_code(client(), await code(provider, 'other@example.com'))
        # The pre-refresh access token is still unexpired, so it is removed too.
        assert await provider.store.revoke_email('Owner@Example.com') == 3
        assert await provider.load_access_token(first.access_token) is None
        assert await provider.load_access_token(second.access_token) is None
        assert await provider.load_refresh_token(client(), second.refresh_token) is None
        assert await provider.load_access_token(other.access_token) is not None
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


def test_token_for_another_service_resource_is_refused(provider):
    async def run():
        first = await provider.exchange_authorization_code(client(), await code(provider, 'owner@example.com'))
        other = GoogleOAuthProvider(provider.store, 'http://localhost:8765', 'google-client', 'test-secret',
                                    scope='gateway', consent=provider.consent_info)
        assert await provider.load_access_token(first.access_token) is not None
        assert await other.load_access_token(first.access_token) is None
    asyncio.run(run())


def test_failed_account_check_blocks_token_use_and_refresh(provider):
    async def run():
        first = await provider.exchange_authorization_code(client(), await code(provider, 'owner@example.com'))
        token = await provider.load_access_token(first.access_token)
        assert token.claims['email'] == 'owner@example.com'
        def refuse(email):
            raise ValueError('not mapped')
        provider.check = refuse
        assert await provider.load_access_token(first.access_token) is None
        refresh = await provider.load_refresh_token(client(), first.refresh_token)
        with pytest.raises(TokenError):
            await provider.exchange_refresh_token(client(), refresh, ['gateway'])
    asyncio.run(run())


def test_store_accepts_only_known_tables():
    from horology_runtime.oauth.store import OAuthRepository
    with pytest.raises(ValueError):
        OAuthRepository(None, 'public.documents')
