import re

from rdflib.plugins.sparql import prepareQuery

from app.graph.tools.federation import (
    has_wikidata_service,
    service_block_spans,
    strip_service_blocks,
)

_VAR = re.compile(r"[?$]([A-Za-z_][A-Za-z0-9_]*)")

KNOWN_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "wdt": "http://www.wikidata.org/prop/direct/",
    "wikibase": "http://wikiba.se/ontology#",
    "wd": "http://www.wikidata.org/entity/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "cto": "https://nfdi4culture.de/ontology/",
    "diamm": "https://linkedmusic.ca/graphs/diamm/",
    "ts": "https://linkedmusic.ca/graphs/thesession/",
    "mb": "https://linkedmusic.ca/graphs/musicbrainz/",
    "gj": "https://linkedmusic.ca/graphs/theglobaljukebox/",
    "dtl": "https://linkedmusic.ca/graphs/dig-that-lick/",
    "cdb": "https://linkedmusic.ca/graphs/cantusdb/",
    "rism": "https://linkedmusic.ca/graphs/rism/",
    "wjazzd": "https://linkedmusic.ca/graphs/wjazzd/",
    "simssa": "https://linkedmusic.ca/graphs/simssadb/",
    "utsi": "https://linkedmusic.ca/graphs/utsi/",
    "cantusindex": "https://linkedmusic.ca/graphs/cantusindex/",
    "apsearch": "https://linkedmusic.ca/graphs/ckg-apsearch/",
    "detmold": "https://linkedmusic.ca/graphs/ckg-detmold/",
    "musiconn": "https://linkedmusic.ca/graphs/ckg-musiconn/",
}

_FORBIDDEN = re.compile(r"\b(INSERT|DELETE|DROP|CREATE|LOAD|CLEAR)\b", re.IGNORECASE)
_PREFIX_USED = re.compile(r"\b([a-zA-Z][a-zA-Z0-9_]*):", re.MULTILINE)
_PREFIX_DECL = re.compile(r"PREFIX\s+([a-zA-Z][a-zA-Z0-9_]*):\s*<", re.IGNORECASE)


def validate_sparql(sparql: str, target_graphs: list[str] | None = None) -> list[str]:
    errors: list[str] = []

    # 1. Forbidden write keywords
    match = _FORBIDDEN.search(sparql)
    if match:
        errors.append(f"Forbidden keyword: {match.group(0).upper()}")

    # 2. rdflib syntax check
    try:
        prepareQuery(sparql, initNs=KNOWN_PREFIXES)
    except Exception as exc:
        errors.append(f"Syntax error: {exc}")

    # 3. Unknown prefix detection (inline PREFIX declarations override)
    declared = set(_PREFIX_DECL.findall(sparql))
    all_known = set(KNOWN_PREFIXES.keys()) | declared
    for prefix in _PREFIX_USED.findall(sparql):
        if prefix not in all_known and prefix not in ("http", "https"):
            errors.append(f"Unknown prefix: {prefix}:")

    # 4. Missing GRAPH clause warning (soft)
    if target_graphs and "GRAPH" not in sparql.upper():
        errors.append("WARNING: No GRAPH clause; results may span all graphs")

    # 5. Missing LIMIT warning for SELECT (soft)
    upper = sparql.upper()
    if "SELECT" in upper and "LIMIT" not in upper:
        errors.append(
            "WARNING: SELECT query has no LIMIT; may return unbounded results"
        )

    # 6. wikibase:label SERVICE is a Wikidata-only extension that causes Virtuoso timeouts
    if re.search(r"\bSERVICE\s+wikibase:label\b", sparql, re.IGNORECASE):
        errors.append(
            "Forbidden: SERVICE wikibase:label is a Wikidata-only extension not supported "
            "by Virtuoso; remove it and fetch labels via OPTIONAL { ?x rdfs:label ?label } instead"
        )

    return errors


def validate_intent(
    sparql: str,
    intents: list[str],
    has_entities: bool,
    needs_federation: bool,
) -> list[str]:
    errors: list[str] = []
    upper = sparql.upper()

    if "aggregation" in intents:
        if not re.search(r"\b(COUNT|SUM|AVG|GROUP\s+BY)\b", upper):
            errors.append("Intent 'aggregation' requires COUNT, SUM, AVG, or GROUP BY")

    if has_entities:
        if not re.search(r"\bwd:Q\d+\b", sparql):
            errors.append(
                "Extracted entities present but no Wikidata QID (wd:Q\\d+) found in query"
            )

    if needs_federation:
        if "SERVICE" not in upper:
            errors.append("needs_federation=True but no SERVICE block found in query")

    return errors


def _service_nesting_errors(sparql: str) -> list[str]:
    """Report a Wikidata SERVICE block nested inside a GRAPH or OPTIONAL, via the SPARQL
    algebra (robust to formatting). Returns [] on a parse miss — a syntax error is already
    reported by validate_sparql."""
    try:
        # prepareQuery with the known prefixes resolves wdt:/GRAPH etc.; a bare parse would
        # choke on the undeclared prefixes the generator relies on.
        algebra = prepareQuery(sparql, initNs=KNOWN_PREFIXES).algebra
    except Exception:
        return []

    found: set[str] = set()

    def walk(node, in_graph: bool, in_optional: bool) -> None:
        if node is None or not hasattr(node, "name"):
            return
        name = node.name
        if name in ("Service", "ServiceGraphPattern"):
            if in_graph:
                found.add("GRAPH")
            if in_optional:
                found.add("OPTIONAL")
            return  # do not descend into the remote pattern
        if name == "Graph":
            walk(node.p, True, in_optional)
            return
        if name == "LeftJoin":  # OPTIONAL: p1 required, p2 optional
            walk(node.p1, in_graph, in_optional)
            walk(node.p2, in_graph, True)
            return
        for attr in ("p", "p1", "p2", "graph"):
            child = getattr(node, attr, None)
            if child is not None and child is not node:
                walk(child, in_graph, in_optional)

    walk(getattr(algebra, "p", algebra), False, False)

    errors: list[str] = []
    if "GRAPH" in found:
        errors.append(
            "SERVICE block must not be nested inside a GRAPH block; place it at the top "
            "level of the WHERE clause."
        )
    if "OPTIONAL" in found:
        errors.append(
            "SERVICE block must not be nested inside an OPTIONAL block; place it at the top "
            "level of the WHERE clause."
        )
    return errors


def validate_federation(sparql: str) -> list[str]:
    """Structural invariants for federated queries. No-op unless a Wikidata SERVICE block is
    present. Enforces the federated_query_rules as hard gates so an ill-shaped federation is
    rejected before it wastes an execution (and provokes remote throttling)."""
    if not has_wikidata_service(sparql):
        return []

    errors: list[str] = []

    # Local (non-SERVICE) variables that could bind a SERVICE's input — taken from the WHERE
    # body only, so the SELECT projection (which may name SERVICE outputs) never counts.
    local_body = strip_service_blocks(sparql)
    brace = local_body.find("{")
    local_vars = set(_VAR.findall(local_body[brace:] if brace != -1 else local_body))

    for start, end in service_block_spans(sparql):
        block = sparql[start:end]
        # No entity-type verification inside a SERVICE block (wdt:P31, rdf:type, or the bare
        # `a` predicate — guarded so it doesn't match ?a / prefixed names / IRI internals).
        if re.search(r"\bwdt:P31\b|\brdf:type\b|(?<![\w?$:])a(?![\w?$:])", block):
            errors.append(
                "SERVICE block must not verify entity type (wdt:P31 / rdf:type / a); check "
                "types in a local GRAPH block instead."
            )
        # The SERVICE must be bounded, else the push is unbounded (Cartesian) and will time out /
        # provoke throttling. It counts as bounded if it shares a variable with the local query
        # OR carries an inline VALUES that binds its input directly.
        svc_vars = set(_VAR.findall(block))
        inline_bound = re.search(r"\bVALUES\b", block, re.IGNORECASE)
        if svc_vars and not (svc_vars & local_vars) and not inline_bound:
            errors.append(
                "SERVICE block shares no variable with the local query and has no inline VALUES, "
                "so its input is unbounded; pre-bind its join variable with a subquery over the "
                "local graphs (or a VALUES list) before the SERVICE block."
            )

    errors.extend(_service_nesting_errors(sparql))
    return errors


def is_valid(errors: list[str]) -> bool:
    """Returns True if there are no hard errors (WARNING-prefixed entries are allowed)."""
    return all(e.startswith("WARNING:") for e in errors)
