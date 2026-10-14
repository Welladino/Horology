"""Turn section-similarity links into topics. Pure functions: no database or network.

A section is a (document_id, chunk_index) key. Links join sections of
different documents, so a topic always spans documents rather than one
document's own sections clustering together.
"""
from collections import Counter, defaultdict

import networkx as nx

SEED = 42  # same input, same topics
RESOLUTION = 2.0  # higher gives more, smaller topics; 2.0 tuned on the repo docs (2026-10-14)
MIN_SECTIONS = 3
MIN_DOCUMENTS = 2


def build_graph(links):
    """Undirected weighted graph; a link found in both directions keeps its higher similarity.

    Links are added in sorted order: the database returns them in no fixed
    order, and Louvain's seed only gives repeatable topics on an identically
    built graph."""
    graph = nx.Graph()
    for doc_a, idx_a, doc_b, idx_b, similarity in sorted(links):
        a, b, weight = (doc_a, idx_a), (doc_b, idx_b), float(similarity)
        if graph.has_edge(a, b):
            graph[a][b]["weight"] = max(graph[a][b]["weight"], weight)
        else:
            graph.add_edge(a, b, weight=weight)
    return graph


def communities(graph, seed=SEED, resolution=RESOLUTION):
    """Louvain communities, each split into its connected pieces.

    Louvain can leave a community whose sections aren't linked to each other
    (the flaw Leiden fixes); splitting into connected components removes that."""
    if graph.number_of_edges() == 0:
        return []
    found = nx.community.louvain_communities(graph, weight="weight", resolution=resolution, seed=seed)
    pieces = []
    for community in found:
        pieces.extend(set(piece) for piece in nx.connected_components(graph.subgraph(community)))
    return sorted(pieces, key=lambda c: (-len(c), min(c)))


def big_enough(community, min_sections=MIN_SECTIONS, min_documents=MIN_DOCUMENTS):
    return len(community) >= min_sections and len({doc for doc, _ in community}) >= min_documents


def confidence(graph, community, node):
    """Share of a section's link weight that stays inside its topic (0-1)."""
    total = sum(data["weight"] for _, _, data in graph.edges(node, data=True))
    inside = sum(data["weight"] for _, other, data in graph.edges(node, data=True) if other in community)
    return inside / total if total else 0.0


def central(graph, community, count):
    """The community's most connected sections: the best passages to describe it."""
    strength = {node: sum(d["weight"] for _, other, d in graph.edges(node, data=True) if other in community)
                for node in community}
    return sorted(community, key=lambda node: (-strength[node], node))[:count]


def match_previous(new_communities, previous, min_share=0.5):
    """Map each new community to the old topic most of its sections came from.

    previous: {section: old topic id}. A match needs at least min_share of the
    community's sections, and each old topic goes to the community holding
    most of its sections. Returns a list of old topic ids (or None), in order."""
    candidates = []
    for position, community in enumerate(new_communities):
        counts = Counter(previous[node] for node in community if node in previous)
        for topic_id, shared in counts.items():
            if shared / len(community) >= min_share:
                candidates.append((shared, position, topic_id))
    matched, taken = [None] * len(new_communities), set()
    for shared, position, topic_id in sorted(candidates, key=lambda c: (-c[0], c[1])):
        if matched[position] is None and topic_id not in taken:
            matched[position] = topic_id
            taken.add(topic_id)
    return matched


def vote(neighbour_topics, min_share=0.5, min_voters=2):
    """Pick a topic for a new section from its neighbours' topics, weighted by similarity.

    neighbour_topics: [(topic id, similarity)]. Returns (topic id, share) or None
    when the neighbours don't agree enough."""
    weights, voters = defaultdict(float), Counter()
    for topic_id, similarity in neighbour_topics:
        weights[topic_id] += float(similarity)
        voters[topic_id] += 1
    if not weights:
        return None
    topic_id = max(weights, key=lambda t: (weights[t], -t))
    share = weights[topic_id] / sum(weights.values())
    return (topic_id, share) if share >= min_share and voters[topic_id] >= min_voters else None
