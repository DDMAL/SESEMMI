import re
from collections import defaultdict

from app.graph.tools.graph_traverse import Edge, Graph, Node

_ONTOLOGY_BLOCK_RE = re.compile(r"<ontology>(.*?)</ontology>", re.DOTALL)
# Matches prefix:ClassName — requires at least one word char after the colon
_CLASS_REF_RE = re.compile(r"^[a-zA-Z]\w*:[a-zA-Z]\w+$")


def _strip_inline_comment(text: str) -> str:
    idx = text.find("#")
    return text[:idx] if idx != -1 else text


def _is_class_ref(token: str) -> bool:
    return bool(_CLASS_REF_RE.match(token.strip()))


def parse_ontology_to_graph(ontology_chunk: str) -> Graph:
    """Parse one ONTOLOGY_CHUNKS entry into a Graph of class nodes and property edges.

    Nodes  — entity types (subjects that appear as prefix:ClassName lines).
    Edges  — directed relationships where the object is another class in the ontology,
             labeled with the Wikidata property (e.g. wdt:P86).
    String literals and bare Wikidata URI placeholders (wd:) are ignored.
    """
    m = _ONTOLOGY_BLOCK_RE.search(ontology_chunk)
    body = m.group(1) if m else ontology_chunk

    nodes: dict[str, Node] = {}
    edges: set[Edge] = set()
    current_subject: str | None = None

    for raw_line in body.splitlines():
        line = _strip_inline_comment(raw_line)

        if not line.strip() or line.lstrip().startswith("@prefix"):
            continue

        if not line.startswith(("\t", " ")):
            # Subject line — e.g. "diamm:Composition"
            candidate = line.strip().rstrip(" .;")
            if _is_class_ref(candidate):
                current_subject = candidate
                if current_subject not in nodes:
                    nodes[current_subject] = Node(current_subject)
            continue

        if current_subject is None or "\t" not in line.strip():
            continue

        predicate, _, objects_str = line.strip().partition("\t")
        predicate = predicate.strip()

        for obj_raw in objects_str.split(","):
            obj = obj_raw.strip().rstrip(" .;")
            if _is_class_ref(obj):
                if obj not in nodes:
                    nodes[obj] = Node(obj)
                edges.add(Edge(nodes[current_subject], nodes[obj], predicate))

    return Graph(set(nodes.values()), edges)


def parse_graph_to_ontology(graph: Graph) -> str:
    outgoing: dict[str, list[Edge]] = defaultdict(list)
    for edge in graph.edges:
        outgoing[edge.source.name].append(edge)

    lines = []
    for node in graph.nodes:
        lines.append(node.name)
        edges = outgoing.get(node.name, [])
        for i, edge in enumerate(edges):
            sep = "." if i == len(edges) - 1 else ";"
            lines.append(f"\t{edge.name}\t{edge.target.name} {sep}")

    return "\n".join(lines)
