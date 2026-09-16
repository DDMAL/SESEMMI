"""Regression for the live-verified MusicBrainz classes and composer path."""

from app.graph.schema_corpus import ONTOLOGY_CHUNKS
from app.graph.tools.ontology_parser import parse_ontology_to_graph


def test_recording_to_composer_path_keeps_the_work_entity():
    graph = parse_ontology_to_graph(ONTOLOGY_CHUNKS["musicbrainz"])
    for name in ("mb:Work", "mb:ReleaseGroup", "mb:Series"):
        assert graph.get_node_by_name(name) is not None
    recording = graph.get_node_by_name("mb:Recording")
    artist = graph.get_node_by_name("mb:Artist")
    edges = graph.get_edges_on_paths(recording, artist)
    path = {(edge.source.name, edge.name, edge.target.name) for edge in edges}
    assert ("mb:Recording", "wdt:P2550", "mb:Work") in path
    assert ("mb:Work", "wdt:P86", "mb:Artist") in path
