"""Diagnose why a zero-row query is empty by ASK-probing its triple patterns.

Runs only on empty results (so it never perturbs a query that returned data). For each
triple pattern inside a LinkedMusic GRAPH block (SERVICE/federated blocks are skipped), it
asks the store whether that pattern alone matches anything. A pattern that matches nothing
is the concrete reason the query is empty — e.g. an entity the graph doesn't reconcile, or
an over-specified filter. Deterministic and grounded in the live data, unlike the LLM judge.
"""

import asyncio
import logging

from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.term import Literal, URIRef, Variable

from app.graph.tools.sparql_execute import execute_sparql

logger = logging.getLogger(__name__)


def _term(t) -> str | None:
    if isinstance(t, URIRef):
        return f"<{t}>"
    if isinstance(t, Variable):
        return f"?{t}"
    if isinstance(t, Literal):
        return t.n3()
    return None


def _collect(node, graph, out: list) -> None:
    """Walk the SPARQL algebra, collecting (graph_iri, triple) for required BGP triples that
    sit inside a GRAPH block. Only patterns whose emptiness can actually cause a zero-row
    result are collected: SERVICE blocks (federated), the optional side of an OPTIONAL, and
    the excluded side of a MINUS are skipped, since a pattern that legitimately matches
    nothing there is never the reason the query is empty.
    """
    if node is None or isinstance(node, (str, URIRef, Variable, Literal)):
        return
    name = getattr(node, "name", None)
    if name == "Graph":
        _collect(node.p, node.term, out)
        return
    if name in ("Service", "ServiceGraphPattern"):
        return
    if name == "BGP":
        if graph is not None:
            out.extend((graph, t) for t in node.triples)
        return
    # OPTIONAL / MINUS: keep the required left side, drop the optional / excluded side.
    if name in ("LeftJoin", "Minus"):
        _collect(node.p1, graph, out)
        return
    for attr in ("p", "p1", "p2"):
        child = getattr(node, attr, None)
        if child is not None:
            _collect(child, graph, out)


async def probe_empty_patterns(sparql: str, max_probes: int = 12) -> list[str]:
    """Return descriptions of GRAPH triple patterns that individually match no data.

    Best-effort: any parse or execution failure yields an empty list, so the caller
    silently falls back to its normal path.
    """
    try:
        algebra = translateQuery(parseQuery(sparql)).algebra
        triples: list = []
        _collect(getattr(algebra, "p", algebra), None, triples)
    except Exception:
        logger.warning("empty-probe: could not parse query; skipping", exc_info=True)
        return []

    seen: set[tuple] = set()
    probes: list[tuple[str, str]] = []  # (ask_query, human description)
    for graph, (s, p, o) in triples:
        if not isinstance(p, URIRef):  # skip unbound-predicate patterns
            continue
        gt, st, pt, ot = _term(graph), _term(s), _term(p), _term(o)
        # gt renders a URIRef graph as <iri> and a variable graph as ?g — never a bare <?g>.
        if None in (gt, st, pt, ot):
            continue
        key = (gt, st, pt, ot)
        if key in seen:
            continue
        seen.add(key)
        probes.append((f"ASK {{ GRAPH {gt} {{ {st} {pt} {ot} }} }}", f"{st} {pt} {ot}"))
        if len(probes) >= max_probes:
            break

    async def _ask(query: str) -> bool | None:
        res = await execute_sparql(query)
        if res["error"] is not None:
            return None
        return res["results"].get("boolean")

    results = await asyncio.gather(*[_ask(q) for q, _ in probes])
    return [desc for (_, desc), ok in zip(probes, results) if ok is False]
