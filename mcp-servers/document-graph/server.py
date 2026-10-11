"""Internal-network document graph MCP entrypoint; cloud authentication deferred."""
import os
from mcp.server.mcpserver import MCPServer
from document_graph.tools import register_tools

mcp = MCPServer("horology-document-graph")
register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=os.environ.get("DOCUMENT_GRAPH_BIND", "0.0.0.0"), port=8765)
