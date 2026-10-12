"""Restricted MCP with assignment tokens or Google-backed client OAuth."""
import hashlib
import hmac
import json
import os

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer

from integrations.github import tools as github_tools
from integrations.google_drive import tools as google_drive_tools
from integrations.supabase import tools as supabase_tools
from integrations.tavily import tools as tavily_tools
from integrations.firecrawl import tools as firecrawl_tools
from shared.access import ToolAccess, current_assignment
from horology_runtime.operations import observe
from horology_runtime.settings import http_server_options, gateway_public_url
from policy import Denied, load_policy
from shared.ledger import Ledger

def build_server(policy, ledger, tokens, oauth_config=None):
    class Verifier:
        async def verify_token(self, token):
            digest = hashlib.sha256(token.encode()).hexdigest()
            for expected, assignment in tokens.items():
                if hmac.compare_digest(digest, expected):
                    config = policy['assignments'].get(assignment)
                    if config:
                        return AccessToken(token=token, client_id=assignment, scopes=['gateway'], expires_at=config['expires_at'])
            return None

    public_url = gateway_public_url()
    auth = AuthSettings(issuer_url=public_url, resource_server_url=public_url+'/mcp', required_scopes=['gateway'])
    if oauth_config:
        from shared.oauth.provider import GoogleOAuthProvider
        from shared.oauth.store import RecordStore
        provider = GoogleOAuthProvider(RecordStore(ledger), policy, public_url, legacy=Verifier(), **oauth_config)
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

    access = ToolAccess(policy, ledger)
    scope = access.scope

    @mcp.tool()
    @observe("gateway", current_assignment)
    def gateway_status() -> dict:
        """Inspect assignment permissions and disabled capabilities; contains no secrets."""
        assignment, config = scope('gateway_status')
        return {'assignment': assignment, 'tools': config['tools'], 'repositories': config.get('repositories', []), 'supabase_project': policy['supabase']['project'], 'schemas': config.get('schemas', []), 'disabled_access_ids': policy['disabled_access_ids'], 'mode': 'Google OAuth with policy assignment' if oauth_config else 'assignment bearer'}

    for integration in (github_tools, google_drive_tools, supabase_tools, firecrawl_tools, tavily_tools):
        integration.register_tools(mcp, access)
    return mcp

def main():
    policy = load_policy(os.environ.get('GATEWAY_POLICY', 'policy.json'))
    # Operator provisioned SHA-256 token -> assignment mapping. Raw tokens never
    # live in the policy file, tool arguments or ledger. Minimum 32-byte secrets.
    tokens = json.loads(os.environ.get('GATEWAY_TOKEN_HASHES', '{}'))
    oauth_config = None
    if os.environ.get('GATEWAY_OAUTH_ENABLED', '').lower() == 'true':
        oauth_config = {'client_id': os.environ.get('GOOGLE_OAUTH_CLIENT_ID'), 'client_secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'), 'assignments': json.loads(os.environ.get('GATEWAY_OAUTH_ASSIGNMENTS', '{}'))}
    if (not tokens and not oauth_config) or any(len(digest) != 64 or assignment not in policy['assignments'] for digest, assignment in tokens.items()):
        raise Denied('Provision hashed assignment credentials before startup')
    ledger = Ledger(os.environ.get('GATEWAY_DATABASE_URL'))
    ledger.check_ready()
    mcp = build_server(policy, ledger, tokens, oauth_config)
    # OAuth callback queries contain short-lived codes; omit application access logs.
    import uvicorn
    options = http_server_options(8767, 'GATEWAY_BIND', '127.0.0.1')
    port = options.pop('port')
    uvicorn.run(mcp.streamable_http_app(**options), host=options['host'], port=port, access_log=False)

if __name__ == '__main__':
    main()
