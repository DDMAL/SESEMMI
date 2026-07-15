import re

from app.graph.tools.graph_traverse import Edge, Graph, Node

_ONTOLOGY_BLOCK_RE = re.compile(r"<ontology>(.*?)</ontology>", re.DOTALL)
_DB_TAG_RE = re.compile(r"<database[^>]*>")
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
                edges.add(Edge(nodes[obj], nodes[current_subject], predicate))

    return Graph(set(nodes.values()), edges)


def extract_class_blocks(ontology_chunk: str) -> dict[str, str]:
    """Map each class to its verbatim authored block (subject line + indented body).

    Preserves the source text exactly — edge direction, literal-valued properties
    (labels, dates, wdt:P2888 links), and inline hints — none of which survive the
    lossy graph round-trip. Insertion order follows the source.
    """
    m = _ONTOLOGY_BLOCK_RE.search(ontology_chunk)
    body = m.group(1) if m else ontology_chunk

    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("@prefix"):
            continue
        if not raw_line.startswith((" ", "\t")):
            candidate = stripped.rstrip(" .;")
            if _is_class_ref(candidate):
                current = candidate
                blocks[current] = [raw_line.rstrip()]
            else:
                current = None
        elif current is not None:
            blocks[current].append(raw_line.rstrip())

    return {name: "\n".join(lines) for name, lines in blocks.items()}


def slice_database_ontology(ontology_chunk: str, class_names: set[str]) -> str:
    """Render a faithful mini-<database> doc for the given classes.

    Keeps the authored <database> tag (graph IRI, prefix), the @prefix block, and the
    verbatim blocks of the selected classes — so the model sees real directions and
    real properties instead of a class-to-class skeleton.
    """
    m = _ONTOLOGY_BLOCK_RE.search(ontology_chunk)
    body = m.group(1) if m else ontology_chunk
    prefixes = [
        ln.rstrip() for ln in body.splitlines() if ln.lstrip().startswith("@prefix")
    ]

    blocks = extract_class_blocks(ontology_chunk)
    selected = [text for name, text in blocks.items() if name in class_names]

    tag_match = _DB_TAG_RE.search(ontology_chunk)
    db_tag = tag_match.group(0) if tag_match else "<database>"

    inner = "\n".join(prefixes + ([""] + selected if selected else []))
    return f"{db_tag}\n<ontology>\n{inner}\n</ontology>\n</database>"
