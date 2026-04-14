import re

from rdflib.plugins.sparql import prepareQuery

KNOWN_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "wdt": "http://www.wikidata.org/prop/direct/",
    "wikibase": "http://wikiba.se/ontology#",
    "wd": "http://www.wikidata.org/entity/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "diamm": "https://linkedmusic.ca/graphs/diamm/",
    "ts": "https://linkedmusic.ca/graphs/thesession/",
    "mb": "https://linkedmusic.ca/graphs/musicbrainz/",
    "gj": "https://linkedmusic.ca/graphs/theglobaljukebox/",
    "dtl": "https://linkedmusic.ca/graphs/dig-that-lick/",
    "cdb": "https://linkedmusic.ca/graphs/cantusdb/",
    "rism": "https://linkedmusic.ca/graphs/rism/",
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


def is_valid(errors: list[str]) -> bool:
    """Returns True if there are no hard errors (WARNING-prefixed entries are allowed)."""
    return all(e.startswith("WARNING:") for e in errors)
