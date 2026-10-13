"""Restricted MCP with client_id tokens or Google-backed client OAuth."""
import hashlib
import hmac
import json
import os

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer

from integrations.supabase import tools as supabase_tools
from integrations.tavily import tools as tavily_tools
from integrations.firecrawl import tools as firecrawl_tools
from shared.access import ToolAccess, current_client_id
from horology_runtime.operations import observe
from horology_runtime.settings import http_server_options, gateway_public_url
from policy import Denied, authorize, load_policy
from contextlib import asynccontextmanager
from database.connection import Database
from database.repositories.quotas import QuotaRepository
from database.repositories.cache import CacheRepository
from horology_runtime.oauth.store import OAuthRepository
from shared.consent import NOTE, gateway_consent

def build_server(policy, database, tokens, oauth_config=None):
    class Verifier:
        async def verify_token(self, token):
            digest = hashlib.sha256(token.encode()).hexdigest()
            for expected in tokens:
                if hmac.compare_digest(digest, expected):
                    return AccessToken(token=token, client_id='local-bearer', scopes=['gateway'])
            return None

    public_url = gateway_public_url()
    auth = AuthSettings(issuer_url=public_url, resource_server_url=public_url+'/mcp', required_scopes=['gateway'])
    if oauth_config:
        from horology_runtime.oauth.provider import GoogleOAuthProvider
        provider = GoogleOAuthProvider(
            OAuthRepository(database, 'gateway_auth.records'), public_url, legacy=Verifier(), scope='gateway',
            consent=lambda: (*gateway_consent(policy), NOTE),
            # Every caller shares one policy; this only fails if status is removed from it.
            check=lambda email: authorize(policy, 'gateway_status'), **oauth_config)
        auth.client_registration_options = ClientRegistrationOptions(enabled=True, valid_scopes=['gateway'], default_scopes=['gateway'])
        auth.revocation_options = RevocationOptions(enabled=True)
        mcp = MCPServer('Welladino restricted gateway', auth_server_provider=provider, auth=auth)
        for path, methods, handler in (
            ('/auth/google/start', ['GET'], provider.start),
            ('/auth/google/callback', ['GET'], provider.callback),
            ('/auth/consent', ['POST'], provider.consent),
        ):
            mcp.custom_route(path, methods)(handler)
    else:
        mcp = MCPServer('Welladino restricted gateway', token_verifier=Verifier(), auth=auth)

    access = ToolAccess(policy, QuotaRepository(database), CacheRepository(database))
    scope = access.scope

    @mcp.tool()
    @observe("gateway", current_client_id)
    def gateway_status() -> dict:
        """Inspect shared permissions and disabled capabilities; contains no secrets."""
        client_id, config = scope('gateway_status')
        return {'tools': config['tools'], 'supabase_project': policy['supabase']['project'], 'schemas': config.get('schemas', []), 'mode': 'Google OAuth with shared policy' if oauth_config else 'local bearer'}

    for integration in (supabase_tools, firecrawl_tools, tavily_tools):
        integration.register_tools(mcp, access)
    return mcp

def database_app(mcp, database, **options):
    """Open the pool on the serving event loop, including OAuth HTTP routes."""
    app = mcp.streamable_http_app(**options)
    mcp_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        async with database:
            await database.check_ready()
            async with mcp_lifespan(app) as state:
                yield state

    app.router.lifespan_context = lifespan
    return app

def main():
    policy = load_policy(os.environ.get('GATEWAY_POLICY', 'policy.json'))
    # Operator provisioned SHA-256 token allowlist. Raw tokens never
    # live in the policy file, tool arguments or ledger. Minimum 32-byte secrets.
    tokens = json.loads(os.environ.get('GATEWAY_TOKEN_HASHES', '[]'))
    oauth_config = None
    if os.environ.get('GATEWAY_OAUTH_ENABLED', '').lower() == 'true':
        oauth_config = {'client_id': os.environ.get('GOOGLE_OAUTH_CLIENT_ID'), 'client_secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')}
    if (not tokens and not oauth_config) or not isinstance(tokens, list) or any(not isinstance(digest, str) or len(digest) != 64 for digest in tokens):
        raise Denied('Provision hashed local credentials before startup')
    database = Database(os.environ.get('GATEWAY_DATABASE_URL'))
    mcp = build_server(policy, database, tokens, oauth_config)
    # OAuth callback queries contain short-lived codes; omit application access logs.
    import uvicorn
    options = http_server_options(8767, 'GATEWAY_BIND', '127.0.0.1')
    port = options.pop('port')
    uvicorn.run(database_app(mcp, database, **options), host=options['host'], port=port, access_log=False)

if __name__ == '__main__':
    main()
