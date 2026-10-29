"""Document graph MCP tool registration."""
from . import graph
from horology_runtime.operations import observe

TOOLS = (graph.write_document, graph.link_documents, graph.get_document, graph.list_documents,
         graph.search_documents, graph.get_related_documents, graph.list_unembedded_documents,
         graph.auto_link_similar_documents, graph.sync_graph,
         graph.list_topics, graph.get_topic, graph.rebuild_topics,
         graph.list_entities, graph.find_entity, graph.entity_documents,
         graph.claim_item, graph.reserve_id, graph.check_register_write,
         graph.finish_run, graph.list_runs, graph.get_item_history)


def register_tools(mcp):
    for tool in TOOLS:
        mcp.tool()(observe("document_graph")(tool))
