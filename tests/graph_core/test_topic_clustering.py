"""Topic clustering rules: pure functions, no database."""
import networkx as nx
import pytest

from graph_core.topics import clustering


def links_for(groups, inside=0.9, bridge=None):
    """Fully link sections within each group (across documents); optionally one weak bridge."""
    links = []
    for group in groups:
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                links.append((*a, *b, inside))
    if bridge:
        links.append((*bridge[0], *bridge[1], 0.61))
    return links


A = [(1, 0), (2, 0), (3, 0), (4, 0)]
B = [(5, 0), (6, 0), (7, 0), (8, 0)]


def test_two_themes_become_two_topics():
    graph = clustering.build_graph(links_for([A, B], bridge=(A[0], B[0])))
    found = clustering.communities(graph)
    assert sorted(map(sorted, found)) == [sorted(A), sorted(B)]


def test_same_input_gives_the_same_topics():
    graph = clustering.build_graph(links_for([A, B], bridge=(A[0], B[0])))
    assert clustering.communities(graph) == clustering.communities(graph)


def test_link_order_does_not_change_the_topics():
    """The database returns links in no fixed order; topics must not depend on it."""
    import random
    rng = random.Random(1)
    nodes = [(d, i) for d in range(30) for i in range(3)]
    links = [(*a, *b, round(rng.uniform(0.6, 0.9), 3)) for a in nodes for b in nodes if a[0] < b[0] and rng.random() < 0.15]
    expected = clustering.communities(clustering.build_graph(links))
    for seed in range(10):
        shuffled = links[:]
        random.Random(seed).shuffle(shuffled)
        assert clustering.communities(clustering.build_graph(shuffled)) == expected


def test_disconnected_pieces_of_a_community_are_split():
    graph = nx.Graph()
    graph.add_edge((1, 0), (2, 0), weight=0.9)
    graph.add_edge((3, 0), (4, 0), weight=0.9)
    pieces = clustering.communities(graph)
    assert all(nx.is_connected(graph.subgraph(piece)) for piece in pieces) and len(pieces) == 2


def test_tiny_or_single_document_groups_are_not_topics():
    assert not clustering.big_enough({(1, 0), (2, 0)})  # two sections
    assert not clustering.big_enough({(1, 0), (1, 1), (1, 2)})  # one document
    assert clustering.big_enough({(1, 0), (2, 0), (2, 1)})


def test_confidence_is_the_share_of_link_weight_inside_the_topic():
    graph = clustering.build_graph([(1, 0, 2, 0, 0.9), (1, 0, 3, 0, 0.3)])
    assert round(clustering.confidence(graph, {(1, 0), (2, 0)}, (1, 0)), 2) == 0.75


def test_a_link_seen_both_ways_keeps_the_higher_similarity():
    graph = clustering.build_graph([(1, 0, 2, 0, 0.7), (2, 0, 1, 0, 0.8)])
    assert graph[(1, 0)][(2, 0)]["weight"] == 0.8


def test_names_follow_the_sections():
    previous = {**{key: 10 for key in A}, **{key: 20 for key in B}}
    # B grew; A shrank but still holds most of its old sections; a brand-new group matches nothing.
    new = [set(B) | {(9, 0)}, set(A[:3]), {(11, 0), (12, 0), (13, 0)}]
    assert clustering.match_previous(new, previous) == [20, 10, None]


def test_an_old_topic_goes_to_one_new_topic_only():
    previous = {key: 10 for key in A + B}  # one old topic split in two
    assert sorted(clustering.match_previous([set(A), set(B)], previous), key=str) == [10, None]


def test_placement_needs_agreement():
    topic, share = clustering.vote([(1, 0.9), (1, 0.8), (2, 0.7)])
    assert topic == 1 and share == pytest.approx(1.7 / 2.4)
    assert clustering.vote([(1, 0.9)]) is None  # a single neighbour isn't enough
    assert clustering.vote([(1, 0.8), (2, 0.8), (3, 0.8)]) is None  # no majority
    assert clustering.vote([]) is None


def test_central_sections_are_the_most_connected():
    graph = clustering.build_graph([(1, 0, 2, 0, 0.9), (1, 0, 3, 0, 0.9), (2, 0, 3, 0, 0.6)])
    assert clustering.central(graph, {(1, 0), (2, 0), (3, 0)}, 1) == [(1, 0)]
