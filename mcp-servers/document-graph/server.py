"""Document graph MCP entrypoint; local mode has no sign-in and one workspace."""
import os
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer
from horology_runtime.database import Database
from horology_runtime.settings import DATABASE, http_server_options
from document_graph import graph
from document_graph.tools import register_tools


def build_server():
    mcp = MCPServer("horology-document-graph")
    register_tools(mcp)
    return mcp


def database_app(mcp, database, **options):
    """Open the pool on the serving event loop before any MCP request."""
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
    options = http_server_options(8765, "DOCUMENT_GRAPH_BIND", "0.0.0.0")
    port = options.pop("port")
    import uvicorn
    uvicorn.run(database_app(build_server(), database, **options), host=options["host"], port=port)


if __name__ == "__main__":
    main()
