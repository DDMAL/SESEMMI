"""Tests for the zero-row ASK-probe (identifies the unsatisfiable triple pattern)."""

from unittest.mock import patch

from app.graph.tools.empty_probe import probe_empty_patterns

_Q3 = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX cto: <https://nfdi4culture.de/ontology/>
PREFIX detmold: <https://linkedmusic.ca/graphs/ckg-detmold/>
SELECT ?work WHERE {
  GRAPH detmold: {
    ?work a detmold:Work ; cto:CTO_0001011 ?place .
    ?place wdt:P2888 wd:Q63039171 .
  }
} LIMIT 100
"""

_Q_SERVICE = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX musiconn: <https://linkedmusic.ca/graphs/ckg-musiconn/>
SELECT ?c WHERE {
  SERVICE <https://query.wikidata.org/sparql> { ?c wdt:P19 wd:Q1741 . }
  GRAPH musiconn: { ?c a musiconn:Person . }
} LIMIT 10
"""


async def test_probe_flags_only_the_empty_pattern():
    async def fake_exec(query: str) -> dict:
        # every pattern matches except the P2888 -> Q63039171 reconciliation filter
        return {"results": {"boolean": "Q63039171" not in query}, "error": None}

    with patch("app.graph.tools.empty_probe.execute_sparql", new=fake_exec):
        empties = await probe_empty_patterns(_Q3)

    assert len(empties) == 1
    assert "Q63039171" in empties[0] and "P2888" in empties[0]


async def test_probe_skips_service_blocks():
    seen: list[str] = []

    async def fake_exec(query: str) -> dict:
        seen.append(query)
        return {"results": {"boolean": True}, "error": None}

    with patch("app.graph.tools.empty_probe.execute_sparql", new=fake_exec):
        await probe_empty_patterns(_Q_SERVICE)

    assert seen, "expected the local GRAPH triple to be probed"
    assert all("query.wikidata.org" not in q and "P19" not in q for q in seen)
    assert any("musiconn" in q for q in seen)


async def test_probe_ignores_execution_errors():
    async def fake_exec(query: str) -> dict:
        return {"results": None, "error": "boom"}

    with patch("app.graph.tools.empty_probe.execute_sparql", new=fake_exec):
        empties = await probe_empty_patterns(_Q3)

    assert empties == []  # None (error) is not treated as empty


async def test_probe_parse_failure_returns_empty():
    assert await probe_empty_patterns("NOT VALID SPARQL {{{") == []
