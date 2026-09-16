"""Offline syntax/schema checks; these do not certify NL/SPARQL equivalence."""

import re

from pyparsing import ParseResults
from rdflib import Dataset, RDF, URIRef
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

from app.graph.examples import FEW_SHOT_EXAMPLES
from app.graph.schema_corpus import ONTOLOGY_CHUNKS


def schema_inventory(chunks):
    inventory = {}
    for chunk in chunks.values():
        prefixes = dict(re.findall(r"@prefix\s+(\w+):\s*<([^>]+)>", chunk))
        graph = re.search(r'graph-iri="([^"]+)"', chunk).group(1)
        body = re.search(r"<ontology>(.*?)</ontology>", chunk, re.S).group(1)

        def expand(token):
            prefix, name = token.split(":", 1)
            return prefixes[prefix] + name

        classes = {expand(x) for x in re.findall(r"^(\w+:\w+)\s*$", body, re.M)}
        predicates = {expand(x) for x in re.findall(r"^\s+(\w+:\w+)\t", body, re.M)}
        auxiliary = re.search(r"<auxiliary-links>(.*?)</auxiliary-links>", chunk, re.S)
        if auxiliary:
            predicates |= {
                expand(x)
                for x in re.findall(r"\?\w+\s+(\w+:\w+)\s", auxiliary.group(1))
            }
        inventory[graph] = {
            "classes": classes,
            "predicates": predicates | {str(RDF.type)},
        }
    return inventory


def local_triples(node, graph=None):
    if not isinstance(node, CompValue):
        return
    if node.name in ("Service", "ServiceGraphPattern"):
        return
    if node.name == "Graph":
        yield from local_triples(node.p, node.term)
        return
    if node.name == "BGP":
        for triple in node.triples:
            yield graph, triple
        return
    for value in node.values():
        if isinstance(value, CompValue):
            yield from local_triples(value, graph)
        elif isinstance(value, (list, tuple)):
            for child in value:
                yield from local_triples(child, graph)


def used_prefixes(node):
    if isinstance(node, CompValue):
        if node.name == "pname":
            yield node.prefix or ""
        for value in node.values():
            yield from used_prefixes(value)
    elif isinstance(node, (list, tuple, ParseResults)):
        for value in node:
            yield from used_prefixes(value)


def audit_errors(examples, chunks):
    inventory = schema_inventory(chunks)
    failures = []
    for index, example in enumerate(examples, 1):
        query = example["sparql"]
        flags = []
        try:
            parsed = parseQuery(query)
            declared = {
                item.prefix or "" for item in parsed[0] if item.name == "PrefixDecl"
            }
            for prefix in sorted(set(used_prefixes(parsed)) - declared):
                flags.append(f"undeclared_prefix: {prefix}")
            algebra = translateQuery(parsed).algebra
            for graph, (_, predicate, obj) in local_triples(algebra):
                if not isinstance(graph, URIRef):
                    continue
                known = inventory.get(str(graph))
                if known is None:
                    flags.append(f"undocumented_graph: {graph}")
                elif predicate == RDF.type and isinstance(obj, URIRef):
                    if str(obj) not in known["classes"]:
                        flags.append(f"undocumented_class: {graph} -> {obj}")
                elif (
                    isinstance(predicate, URIRef)
                    and str(predicate) not in known["predicates"]
                ):
                    flags.append(f"undocumented_predicate: {graph} -> {predicate}")
        except Exception as exc:
            flags.append(f"parse_error: {exc}")
        if flags:
            failures.append(
                {"index": index, "question": example["nl"], "flags": sorted(set(flags))}
            )
    return failures


def test_examples_have_valid_syntax_prefixes_and_documented_schema():
    # Undocumented terms need investigation against the endpoint, not automatic removal.
    assert audit_errors(FEW_SHOT_EXAMPLES, ONTOLOGY_CHUNKS) == []


def test_audit_does_not_accept_implicit_rdflib_prefixes():
    failures = audit_errors(
        [{"nl": "Count", "sparql": "SELECT (xsd:integer(1) AS ?n) WHERE {}"}], {}
    )
    assert failures[0]["flags"] == ["undeclared_prefix: xsd"]


def test_audit_keeps_external_types_separate_from_local_schema():
    query = "SELECT ?x WHERE { SERVICE <https://query.wikidata.org/sparql> { ?x a <https://example.org/ExternalType> } }"
    assert (
        audit_errors([{"nl": "External lookup", "sparql": query}], ONTOLOGY_CHUNKS)
        == []
    )


def test_verified_musicbrainz_questions_remain_in_runtime_corpus():
    # Curated regression cases; endpoint response snapshots are local artifacts.
    verified_questions = {
        "Find all compositions or recordings with 'death' in the title",
        "Find all works in MusicBrainz that, according to Dig That Lick, contain a solo "
        "performed by Charlie Parker",
        "For the canonical Western art-music composers (Bach, Mozart, Beethoven, Haydn, "
        "Schubert, Mendelssohn, Schumann, Brahms, and Wagner), count the total number of "
        "items attributable to each one across every archive in our holdings — including "
        "their compositions, recordings of those works, releases and release-groups credited "
        "to them, public concerts featuring their music, court-theatre productions, "
        "manuscript sources, and song-anthology entries — and rank the composers by overall "
        "footprint.",
        "How is the legacy of the major 19th-century opera composers distributed across our "
        "archives? For the Italian (Rossini, Donizetti, Bellini, Verdi, Puccini), French "
        "(Berlioz, Bizet, Gounod, Meyerbeer), and German (Wagner) operatic traditions, count "
        "for each composer the European public-concert events that featured their works, the "
        "catalogued compositions and recordings attributed to them, and the surviving "
        "manuscript sources.",
    }
    active_questions = {example["nl"] for example in FEW_SHOT_EXAMPLES}
    assert verified_questions <= active_questions


def test_apsearch_audio_example_filters_media_and_publisher_without_date_cutoffs():
    query = next(
        example["sparql"]
        for example in FEW_SHOT_EXAMPLES
        if example["nl"].startswith(
            "Find up to 100 records explicitly classified as audio recordings"
        )
    )
    dataset = Dataset()
    dataset.parse(
        data="""
        @prefix ex: <https://example.org/> .
        @prefix apsearch: <https://linkedmusic.ca/graphs/ckg-apsearch/> .
        @prefix wd: <http://www.wikidata.org/entity/> .
        @prefix wdt: <http://www.wikidata.org/prop/direct/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        apsearch: {
            ex:bbaw wdt:P2888 wd:Q219989 .
            ex:early a apsearch:Work ; wdt:P31 wd:Q3302947 ;
                wdt:P123 ex:bbaw ; wdt:P571 "1899"^^xsd:gYear .
            ex:recent a apsearch:Work ; wdt:P31 wd:Q3302947 ;
                wdt:P123 ex:bbaw ; wdt:P571 "2025"^^xsd:gYear .
            ex:image a apsearch:Work ; wdt:P31 wd:Q478798 ;
                wdt:P123 ex:bbaw ; wdt:P571 "1910"^^xsd:gYear .
            ex:generic a apsearch:Work ; wdt:P31 wd:Q17537576 ;
                wdt:P123 ex:bbaw ; wdt:P571 "1910"^^xsd:gYear .
            ex:otherPublisher a apsearch:Work ; wdt:P31 wd:Q3302947 ;
                wdt:P123 ex:other ; wdt:P571 "1910"^^xsd:gYear .
            ex:undated a apsearch:Work ; wdt:P31 wd:Q3302947 ; wdt:P123 ex:bbaw .
        }
        ex:otherGraph {
            ex:bbaw wdt:P2888 wd:Q219989 .
            ex:elsewhere a apsearch:Work ; wdt:P31 wd:Q3302947 ;
                wdt:P123 ex:bbaw ; wdt:P571 "1910"^^xsd:gYear .
        }
        """,
        format="trig",
    )
    assert [(str(row.work), str(row.creationYear)) for row in dataset.query(query)] == [
        ("https://example.org/early", "1899"),
        ("https://example.org/recent", "2025"),
    ]
