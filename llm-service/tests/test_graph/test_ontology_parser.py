"""Tests for the verbatim-slice schema rendering (replaces the lossy graph round-trip)."""

from app.graph.tools.ontology_parser import (
    extract_class_blocks,
    slice_database_ontology,
)

_CHUNK = """\
<database name="Demo" graph-iri="https://example.org/g/" prefix="ex:">
<description>ignored prose</description>
<ontology>
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:  <http://www.wikidata.org/prop/direct/> .
@prefix ex:   <https://example.org/g/> .

ex:Event
\trdfs:label\t"label" ;
\twdt:P585\t"point in time" ;
\tex:rel\tex:Person .
ex:Person
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" .
</ontology>
</database>\
"""


def test_extract_class_blocks_verbatim():
    blocks = extract_class_blocks(_CHUNK)
    assert set(blocks) == {"ex:Event", "ex:Person"}
    # literal-valued properties (dropped by the graph round-trip) are preserved
    assert 'wdt:P585\t"point in time"' in blocks["ex:Event"]
    assert 'wdt:P2888\t"exact match"' in blocks["ex:Person"]


def test_slice_preserves_direction_no_reverse_leak():
    out = slice_database_ontology(_CHUNK, {"ex:Event", "ex:Person"})
    # declared direction Event -> Person survives...
    assert "ex:rel\tex:Person" in out
    # ...and the reverse Person -> Event is NOT invented
    assert "ex:rel\tex:Event" not in out


def test_slice_includes_prefixes_and_db_tag():
    out = slice_database_ontology(_CHUNK, {"ex:Person"})
    assert '<database name="Demo"' in out
    assert "@prefix ex:" in out
    # only the requested class block is emitted
    assert "ex:Person" in out
    assert "ex:Event\n" not in out


def test_slice_empty_selection_still_valid_doc():
    out = slice_database_ontology(_CHUNK, set())
    assert out.startswith("<database")
    assert "@prefix" in out
    assert "ex:Event" not in out
