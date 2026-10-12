"""Internal-network document graph MCP entrypoint; cloud authentication deferred."""
from mcp.server.mcpserver import MCPServer
from document_graph.tools import register_tools
from horology_runtime.settings import http_server_options

mcp = MCPServer("horology-document-graph")
register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", **http_server_options(8765, "DOCUMENT_GRAPH_BIND", "0.0.0.0"))
