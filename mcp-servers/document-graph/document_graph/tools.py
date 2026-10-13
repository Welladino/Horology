"""Document graph MCP tool registration."""
from . import graph
from horology_runtime.operations import observe

TOOLS = (graph.write_document, graph.link_documents, graph.get_document, graph.list_documents,
         graph.search_documents, graph.get_related_documents, graph.list_unembedded_documents,
         graph.auto_link_similar_documents)


def register_tools(mcp):
    for tool in TOOLS:
        mcp.tool()(observe("neon")(tool))
