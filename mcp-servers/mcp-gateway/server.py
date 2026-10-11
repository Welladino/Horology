"""Local authenticated MCP. Cloud OAuth is a separate, unimplemented release gate."""
import hashlib
import hmac
import json
import os

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer

from integrations.github import tools as github_tools
from integrations.google_drive import tools as google_drive_tools
from integrations.supabase import tools as supabase_tools
from integrations.tavily import tools as tavily_tools
from integrations.firecrawl import tools as firecrawl_tools
from shared.access import ToolAccess, current_assignment
from horology_runtime.operations import observe
from policy import Denied, Ledger, load_policy

def build_server(policy, ledger, tokens):
    class Verifier:
        async def verify_token(self, token):
            digest = hashlib.sha256(token.encode()).hexdigest()
            for expected, assignment in tokens.items():
                if hmac.compare_digest(digest, expected):
                    config = policy['assignments'].get(assignment)
                    if config:
                        return AccessToken(token=token, client_id=assignment, scopes=['gateway'], expires_at=config['expires_at'])
            return None

    mcp = MCPServer('Welladino restricted gateway', token_verifier=Verifier(), auth=AuthSettings(issuer_url='http://localhost:8767', resource_server_url='http://localhost:8767/mcp', required_scopes=['gateway']))

    access = ToolAccess(policy, ledger)
    scope = access.scope

    @mcp.tool()
    @observe("gateway", current_assignment)
    def gateway_status() -> dict:
        """Inspect assignment permissions and disabled capabilities; contains no secrets."""
        assignment, config = scope('gateway_status')
        return {'assignment': assignment, 'tools': config['tools'], 'repositories': config.get('repositories', []), 'supabase_project': policy['supabase']['project'], 'schemas': config.get('schemas', []), 'disabled_access_ids': policy['disabled_access_ids'], 'mode': 'local-only; cloud OAuth and scheduler not implemented'}

    for integration in (github_tools, google_drive_tools, supabase_tools, firecrawl_tools, tavily_tools):
        integration.register_tools(mcp, access)
    return mcp

def main():
    policy = load_policy(os.environ.get('GATEWAY_POLICY', 'policy.json'))
    # Operator provisioned SHA-256 token -> assignment mapping. Raw tokens never
    # live in the policy file, tool arguments or ledger. Minimum 32-byte secrets.
    tokens = json.loads(os.environ.get('GATEWAY_TOKEN_HASHES', '{}'))
    if not tokens or any(len(digest) != 64 or assignment not in policy['assignments'] for digest, assignment in tokens.items()):
        raise Denied('Provision hashed assignment credentials before startup')
    ledger = Ledger(os.environ.get('GATEWAY_LEDGER', 'state/ledger.sqlite3'))
    mcp = build_server(policy, ledger, tokens)
    mcp.run(transport='streamable-http', host=os.environ.get('GATEWAY_BIND', '127.0.0.1'), port=8767)

if __name__ == '__main__':
    main()
