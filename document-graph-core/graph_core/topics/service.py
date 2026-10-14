"""Build topics from the section-similarity graph, place new sections, and look topics up."""
import logging
from collections import defaultdict

from horology_runtime.error_handling import category

from .. import database
from ..documents import fields
from ..sections import service as sections
from . import clustering, naming
from .repository import TopicRepository

log = logging.getLogger("graph_core.topics")
NEIGHBOURS = 10  # links per section: how connected the graph is, not how much is clustered
MIN_SIMILARITY = 0.6  # weaker links are noise, not shared themes
NAME_PASSAGES = 5


def _repository():
    return TopicRepository(database.get())


async def rebuild(workspace):
    """Re-cluster every section in the workspace, keep names of matching topics, name new ones."""
    links = await sections.neighbour_links(workspace, NEIGHBOURS, MIN_SIMILARITY)
    graph = clustering.build_graph(links)
    found = [c for c in clustering.communities(graph) if clustering.big_enough(c)]
    repository = _repository()
    matched = clustering.match_previous(found, await repository.assignments(workspace))
    plans = [{"id": topic_id, "name": None, "summary": None,
              "members": [(doc, idx, round(clustering.confidence(graph, community, (doc, idx)), 4))
                          for doc, idx in sorted(community)],
              "central": clustering.central(graph, community, NAME_PASSAGES)}
             for community, topic_id in zip(found, matched)]
    ids = await repository.save_clustering(workspace, plans)
    named = await _name_unnamed(workspace, dict(zip(ids, plans)))
    summary = {"workspace": workspace, "sections_linked": graph.number_of_nodes(), "links": graph.number_of_edges(),
               "topics": len(ids), "kept": sum(1 for t in matched if t is not None),
               "new": sum(1 for t in matched if t is None), "named": named,
               "sections_in_topics": sum(len(plan["members"]) for plan in plans)}
    log.info("topics rebuilt %s", summary)
    return summary


async def _name_unnamed(workspace, plans_by_id):
    """Name topics that have no name yet. A failure leaves the name empty for the next rebuild."""
    repository = _repository()
    topics = await repository.topics(workspace)
    taken = {t["name"] for t in topics if t["name"]}
    named = 0
    for topic in topics:
        plan = plans_by_id.get(topic["id"])
        if topic["name"] or plan is None:
            continue
        passages = await sections.texts(plan["central"])
        try:
            name, summary = await naming.name_topic([passages[key] for key in plan["central"] if key in passages], taken)
        except Exception as error:
            log.warning("topic %s not named: %s", topic["id"], category(error))
            continue
        await repository.name(workspace, topic["id"], name, summary)
        taken.add(name)
        named += 1
    return named


async def place_document(workspace, document_id):
    """Put a document's sections into the topics of their nearest sections elsewhere; no re-clustering.

    Sections whose neighbours don't agree stay unassigned until the next rebuild."""
    links = await sections.neighbour_links(workspace, NEIGHBOURS, MIN_SIMILARITY, document_id)
    repository = _repository()
    known = await repository.topics_of({(doc, idx) for _, _, doc, idx, _ in links})
    votes = defaultdict(list)
    for doc, idx, other_doc, other_idx, similarity in links:
        if (other_doc, other_idx) in known:
            votes[(doc, idx)].append((known[(other_doc, other_idx)], similarity))
    placements = []
    for (doc, idx), neighbour_topics in votes.items():
        choice = clustering.vote(neighbour_topics)
        if choice:
            placements.append((doc, idx, choice[0], round(choice[1], 4)))
    await repository.place(placements)
    return len(placements)


async def list_topics(workspace, domain=None):
    rows = await _repository().summaries(workspace, fields.domain(domain))
    for row in rows:
        row["name"] = row["name"] or "(not named yet)"
        row["document_types"] = row["document_types"] or {}
    return rows


async def get_topic(workspace, topic_id, passages=3):
    """A topic with its documents (and how much of each falls in it) and its strongest passages."""
    repository = _repository()
    topic = await repository.get(workspace, topic_id)
    if topic is None:
        raise ValueError(f"No topic with id {topic_id}")
    documents = await repository.documents(topic_id)
    strongest = await repository.strongest_sections(topic_id, passages)
    texts = await sections.texts([(doc, idx) for doc, idx, _ in strongest])
    titles = {row["id"]: row["title"] for row in documents}
    for row in documents:
        row["share"] = float(row["share"])
    return {"id": topic["id"], "name": topic["name"] or "(not named yet)", "summary": topic["summary"],
            "documents": documents,
            "passages": [{"document_id": doc, "title": titles.get(doc), "section": idx,
                          "confidence": round(float(confidence), 4), "text": texts.get((doc, idx), "")}
                         for doc, idx, confidence in strongest]}
