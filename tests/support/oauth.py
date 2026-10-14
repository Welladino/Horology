"""OAuth test fakes: an in-memory record store, a provider using it, a client and an issued code."""
import copy
import time
from contextlib import asynccontextmanager

import pytest
from mcp.shared.auth import OAuthClientInformationFull

from .gateway import GATEWAY
from policy import authorize, load_policy  # noqa: E402  (gateway modules, on sys.path via .gateway)
from horology_runtime.oauth.provider import GoogleOAuthProvider, GatewayCode  # noqa: E402
from shared.consent import NOTE, gateway_consent  # noqa: E402


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
    policy = load_policy(GATEWAY / 'config/policy.example.json')
    return GoogleOAuthProvider(MemoryStore(),'http://localhost:8767','google-client','test-secret',scope='gateway',
                               consent=lambda: (*gateway_consent(policy), NOTE),
                               check=lambda email: authorize(policy, 'gateway_status'))


def client():
    return OAuthClientInformationFull(client_id='client',client_name='Test client',redirect_uris=['http://localhost:9000/callback'],scope='gateway',token_endpoint_auth_method='none',grant_types=['authorization_code','refresh_token'])


async def code(provider, email=''):
    value = GatewayCode(email=email,code='test-code',scopes=['gateway'],expires_at=time.time()+120,client_id='client',code_challenge='challenge',redirect_uri='http://localhost:9000/callback',redirect_uri_provided_explicitly=True,resource=provider.url+'/mcp',subject='google-subject',grant_id='grant')
    await provider.store.put('code',value.code,value.model_dump(mode='json',exclude={'code'}),value.expires_at)
    return value
