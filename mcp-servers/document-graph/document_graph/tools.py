"""Document graph MCP tool registration."""
from .integrations.neon import client
from horology_runtime.operations import observe


def register_tools(mcp):
    mcp.tool()(observe("neon")(client.write_document))
    mcp.tool()(observe("neon")(client.link_documents))
    mcp.tool()(observe("neon")(client.get_document))
    mcp.tool()(observe("neon")(client.list_documents))
    mcp.tool()(observe("neon")(client.get_related_documents))
    mcp.tool()(observe("neon")(client.list_unembedded_documents))
    mcp.tool()(observe("neon")(client.auto_link_similar_documents))
