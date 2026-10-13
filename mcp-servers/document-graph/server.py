"""Document graph MCP entrypoint.

Local mode (default) has no sign-in and one workspace; keep it on 127.0.0.1.
With DOCUMENT_GRAPH_OAUTH_ENABLED=true it uses the shared Google sign-in,
its own token table and an email -> workspace map.
"""
import json
import os
from contextlib import asynccontextmanager

from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer
from horology_runtime.database import Database
from horology_runtime.oauth.store import OAuthRepository
from horology_runtime.settings import DATABASE, document_graph_public_url, http_server_options
from document_graph import graph
from document_graph.shared import workspace
from document_graph.tools import TOOLS, register_tools

SCOPE = 'graph'
CONSENT_NOTE = ('Google sign-in verifies your identity. It does not grant Gmail or Google Drive access. '
                'You only see documents in the workspace mapped to this account.')


def consent():
    sections = [
        ("Find documents", "Search by meaning, list and read documents and their links in your workspace."),
        ("Write documents", "Add documents and links in your workspace. Embeddings are made through OpenRouter."),
        ("Sync from the Document Index", "Start the sheet sync for your workspace. It imports rows marked TRUE and updates their status."),
    ]
    return sections, [tool.__name__ for tool in TOOLS], CONSENT_NOTE


def build_server(database=None, oauth_config=None):
    if not oauth_config:
        mcp = MCPServer("horology-document-graph")
        register_tools(mcp)
        return mcp
    from horology_runtime.oauth.provider import GoogleOAuthProvider
    public_url = document_graph_public_url()
    provider = GoogleOAuthProvider(
        OAuthRepository(database, 'graph_auth.records'), public_url, oauth_config['client_id'],
        oauth_config['client_secret'], scope=SCOPE, consent=consent, check=workspace.workspace_for)
    auth = AuthSettings(issuer_url=public_url, resource_server_url=public_url + '/mcp', required_scopes=[SCOPE],
                        client_registration_options=ClientRegistrationOptions(enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]),
                        revocation_options=RevocationOptions(enabled=True))
    mcp = MCPServer("horology-document-graph", auth_server_provider=provider, auth=auth)
    for path, methods, handler in (
        ('/auth/google/start', ['GET'], provider.start),
        ('/auth/google/callback', ['GET'], provider.callback),
        ('/auth/consent', ['POST'], provider.consent),
    ):
        mcp.custom_route(path, methods)(handler)
    register_tools(mcp)
    return mcp


def database_app(mcp, database, **options):
    """Open the pool on the serving event loop before any MCP or sign-in request."""
    app = mcp.streamable_http_app(**options)
    mcp_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        async with database:
            graph.configure(database)
            async with mcp_lifespan(app) as state:
                yield state

    app.router.lifespan_context = lifespan
    return app


def main():
    database = Database(os.environ.get("DATABASE_URL_POOLED"), DATABASE.document_graph_pool_size)
    oauth_config = None
    if os.environ.get('DOCUMENT_GRAPH_OAUTH_ENABLED', '').lower() == 'true':
        workspace.configure(json.loads(os.environ.get('DOCUMENT_GRAPH_WORKSPACES', '{}')))
        oauth_config = {'client_id': os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
                        'client_secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')}
    options = http_server_options(8765, "DOCUMENT_GRAPH_BIND", "0.0.0.0")
    port = options.pop("port")
    import uvicorn
    # OAuth callback queries contain short-lived codes; omit access logs when sign-in is on.
    uvicorn.run(database_app(build_server(database, oauth_config), database, **options),
                host=options["host"], port=port, access_log=oauth_config is None)


if __name__ == "__main__":
    main()
