from app.graph.tools.graph_traverse import Edge, Graph, Node


def make_graph(edge_tuples: list[tuple[str, str]]) -> tuple[Graph, dict[str, Node]]:
    node_map: dict[str, Node] = {}
    for src, tgt in edge_tuples:
        for name in (src, tgt):
            if name not in node_map:
                node_map[name] = Node(name)
    edges = {
        Edge(node_map[src], node_map[tgt], f"{src}->{tgt}")
        for src, tgt in edge_tuples
    }
    return Graph(set(node_map.values()), edges), node_map


def test_linear_chain_returns_all_edges():
    # A → B → C
    g, n = make_graph([("A", "B"), ("B", "C")])
    result = g.get_edges_on_paths(n["A"], n["C"])
    assert len(result) == 2
    names = {e.name for e in result}
    assert names == {"A->B", "B->C"}


def test_direct_edge():
    # A → B  (single hop)
    g, n = make_graph([("A", "B")])
    result = g.get_edges_on_paths(n["A"], n["B"])
    assert len(result) == 1
    assert next(iter(result)).name == "A->B"


def test_diamond_returns_all_four_edges():
    # A → B → D
    # A → C → D
    g, n = make_graph([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])
    result = g.get_edges_on_paths(n["A"], n["D"])
    assert len(result) == 4


def test_dead_end_branch_excluded():
    # A → B → C
    # A → D        (D leads nowhere toward C)
    g, n = make_graph([("A", "B"), ("B", "C"), ("A", "D")])
    result = g.get_edges_on_paths(n["A"], n["C"])
    names = {e.name for e in result}
    assert names == {"A->B", "B->C"}
    assert "A->D" not in names


def test_no_path_returns_empty():
    # A → B    C → D  (disconnected)
    g, n = make_graph([("A", "B"), ("C", "D")])
    result = g.get_edges_on_paths(n["A"], n["D"])
    assert result == set()


def test_source_equals_target_returns_self_loop():
    # A → A
    g, n = make_graph([("A", "A")])
    result = g.get_edges_on_paths(n["A"], n["A"])
    assert len(result) == 1


def test_source_equals_target_no_self_loop_returns_empty():
    # A → B, no self-loop on A
    g, n = make_graph([("A", "B")])
    result = g.get_edges_on_paths(n["A"], n["A"])
    assert result == set()


def test_longer_chain_with_shortcut():
    # A → B → C → D
    # A → D          (shortcut)
    g, n = make_graph([("A", "B"), ("B", "C"), ("C", "D"), ("A", "D")])
    result = g.get_edges_on_paths(n["A"], n["D"])
    assert len(result) == 4


def test_irrelevant_edges_in_graph_excluded():
    # Path: A → B → C
    # Extra unrelated: X → Y
    g, n = make_graph([("A", "B"), ("B", "C"), ("X", "Y")])
    result = g.get_edges_on_paths(n["A"], n["C"])
    names = {e.name for e in result}
    assert "X->Y" not in names
    assert len(result) == 2


def test_cycle_does_not_hang():
    # A → B → C → B (cycle), path to D via C
    g, n = make_graph([("A", "B"), ("B", "C"), ("C", "B"), ("C", "D")])
    result = g.get_edges_on_paths(n["A"], n["D"])
    names = {e.name for e in result}
    # All of A→B, B→C, C→D are on a valid path; C→B is also valid (B can reach D via C)
    assert "A->B" in names
    assert "B->C" in names
    assert "C->D" in names
