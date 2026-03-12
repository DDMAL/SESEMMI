import pytest

from app.graph.validation import is_valid, validate_intent, validate_sparql

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_SPARQL = """
SELECT ?title ?uri WHERE {
  GRAPH <https://linkedmusic.ca/graphs/diamm/> {
    ?uri rdf:type rdfs:Resource ;
         rdfs:label ?title .
  }
}
LIMIT 10
"""

# ---------------------------------------------------------------------------
# Syntax & safety tests (8)
# ---------------------------------------------------------------------------


def test_valid_select_query():
    errors = validate_sparql(_VALID_SPARQL)
    assert errors == []


def test_forbidden_insert():
    sparql = "INSERT DATA { <http://example.org/s> <http://example.org/p> <http://example.org/o> }"
    errors = validate_sparql(sparql)
    assert any("INSERT" in e for e in errors)


def test_syntax_error_unbalanced_braces():
    sparql = "SELECT ?x WHERE { ?x rdf:type rdfs:Resource"  # missing closing brace
    errors = validate_sparql(sparql)
    assert any("Syntax error" in e for e in errors)


def test_unknown_prefix():
    sparql = """
SELECT ?x WHERE {
  GRAPH <https://linkedmusic.ca/graphs/diamm/> {
    ?x xyz:Thing ?y .
  }
}
LIMIT 10
"""
    errors = validate_sparql(sparql)
    assert any("xyz:" in e for e in errors)


def test_missing_graph_clause():
    sparql = "SELECT ?x WHERE { ?x rdf:type rdfs:Resource } LIMIT 10"
    errors = validate_sparql(sparql, target_graphs=["diamm"])
    warnings = [e for e in errors if e.startswith("WARNING:")]
    assert any("GRAPH" in w for w in warnings)


def test_missing_limit_warning():
    sparql = """
SELECT ?x WHERE {
  GRAPH <https://linkedmusic.ca/graphs/diamm/> {
    ?x rdf:type rdfs:Resource .
  }
}
"""
    errors = validate_sparql(sparql)
    warnings = [e for e in errors if e.startswith("WARNING:")]
    assert any("LIMIT" in w for w in warnings)


def test_is_valid_with_only_warnings():
    # Only soft warnings — should still be considered valid
    sparql = "SELECT ?x WHERE { ?x rdf:type rdfs:Resource } LIMIT 10"
    errors = validate_sparql(sparql, target_graphs=["diamm"])
    assert any(e.startswith("WARNING:") for e in errors)
    assert is_valid(errors) is True


def test_is_valid_with_errors():
    sparql = "INSERT DATA { <http://example.org/s> <http://example.org/p> <http://example.org/o> }"
    errors = validate_sparql(sparql)
    assert is_valid(errors) is False


# ---------------------------------------------------------------------------
# Structural intent tests (5)
# ---------------------------------------------------------------------------


def test_aggregation_missing_count():
    sparql = """
SELECT ?genre WHERE {
  GRAPH <https://linkedmusic.ca/graphs/musicbrainz/> {
    ?work rdf:type mb:Work ;
          mb:genre ?genre .
  }
}
LIMIT 10
"""
    errors = validate_intent(sparql, "aggregation", False, False)
    assert any("aggregation" in e for e in errors)


def test_aggregation_valid():
    sparql = """
SELECT (COUNT(?work) AS ?count) WHERE {
  GRAPH <https://linkedmusic.ca/graphs/musicbrainz/> {
    ?work rdf:type mb:Work .
  }
}
"""
    errors = validate_intent(sparql, "aggregation", False, False)
    assert errors == []


def test_cross_graph_single_graph():
    sparql = """
SELECT ?title WHERE {
  GRAPH <https://linkedmusic.ca/graphs/diamm/> {
    ?ms rdf:type rdfs:Resource ;
        rdfs:label ?title .
  }
}
LIMIT 10
"""
    errors = validate_intent(sparql, "cross_graph", False, False)
    assert any("cross_graph" in e for e in errors)


def test_mentions_entities_no_qid():
    sparql = """
SELECT ?work WHERE {
  GRAPH <https://linkedmusic.ca/graphs/musicbrainz/> {
    ?work rdf:type mb:Work ;
          rdfs:label "Taylor Swift" .
  }
}
LIMIT 10
"""
    errors = validate_intent(sparql, "lookup", True, False)
    assert any("QID" in e for e in errors)


def test_needs_federation_no_service():
    sparql = """
SELECT ?work WHERE {
  GRAPH <https://linkedmusic.ca/graphs/musicbrainz/> {
    ?work rdf:type mb:Work .
  }
}
LIMIT 10
"""
    errors = validate_intent(sparql, "lookup", False, True)
    assert any("SERVICE" in e for e in errors)
