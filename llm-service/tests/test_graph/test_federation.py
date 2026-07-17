"""Unit tests for the federated-query helpers (classification + SERVICE-block surgery)."""

from app.graph.tools.federation import (
    classify_execution_error,
    has_wikidata_service,
    service_block_spans,
    strip_service_blocks,
)

_LOCAL_JOIN = (
    "SELECT ?person ?viaf WHERE { "
    "{ SELECT ?person ?qid WHERE { "
    "GRAPH <https://linkedmusic.ca/graphs/ckg-musiconn/> { ?person wdt:P2888 ?qid } "
    "GRAPH <https://linkedmusic.ca/graphs/musicbrainz/> { ?mb wdt:P2888 ?qid } } } "
    "SERVICE <https://query.wikidata.org/sparql> { ?qid wdt:P214 ?viaf . } } LIMIT 10"
)


def test_has_wikidata_service_true():
    assert has_wikidata_service(_LOCAL_JOIN) is True


def test_has_wikidata_service_false():
    assert has_wikidata_service("SELECT ?x WHERE { GRAPH <g> { ?x a ?t } }") is False


def test_classify_wdqs_429_is_external():
    err = (
        "HTTP 500: Virtuoso SPARQL_REXEC: <https://query.wikidata.org/sparql> "
        "returned HTTP/1.1 429 Too Many Requests"
    )
    assert classify_execution_error(_LOCAL_JOIN, err) == "external_service"


def test_classify_local_sp031_is_query_fault():
    err = "HTTP 500: Virtuoso 37000 Error SP031: SPARQL compiler, variable not bound"
    assert classify_execution_error(_LOCAL_JOIN, err) == "query_fault"


def test_classify_timeout_with_wd_service_is_external():
    assert classify_execution_error(_LOCAL_JOIN, "timeout") == "external_service"


def test_classify_timeout_without_service_is_query_fault():
    local = "SELECT ?x WHERE { GRAPH <g> { ?x a ?t } } LIMIT 10"
    assert classify_execution_error(local, "timeout") == "query_fault"


def test_service_block_spans_isolates_the_block():
    spans = service_block_spans(_LOCAL_JOIN)
    assert len(spans) == 1
    start, end = spans[0]
    block = _LOCAL_JOIN[start:end]
    assert block.startswith("SERVICE")
    assert block.rstrip().endswith("}")
    assert "wdt:P214" in block


def test_strip_service_blocks_removes_only_the_service():
    stripped = strip_service_blocks(_LOCAL_JOIN)
    assert "SERVICE" not in stripped.upper()
    assert "wdt:P214" not in stripped
    # The local join and its projection survive intact.
    assert "wdt:P2888" in stripped
    assert "SELECT ?person ?viaf" in stripped


def test_strip_service_blocks_noop_without_service():
    local = "SELECT ?x WHERE { GRAPH <g> { ?x a ?t } } LIMIT 10"
    assert strip_service_blocks(local) == local
