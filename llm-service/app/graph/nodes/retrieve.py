import asyncio
import logging
from itertools import combinations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.config import settings
from app.graph.examples import FEW_SHOT_EXAMPLES
from app.graph.model import get_structured_model
from app.graph.schema_corpus import INSTRUCTION_CHUNKS, ONTOLOGY_CHUNKS
from app.graph.state import GraphState
from app.graph.tools.graph_traverse import Node, Edge, Graph
from app.graph.tools.ontology_parser import (
    parse_ontology_to_graph,
    slice_database_ontology,
)
from app.graph.tools.wikidata import wikidata_qid_lookup

logger = logging.getLogger(__name__)


def format_examples_to_xml(examples: list[dict]) -> str:
    if not examples:
        return ""
    items = "\n".join(
        f"<example>\n<question>{ex['nl']}</question>\n<sparql>{ex['sparql']}</sparql>\n</example>"
        for ex in examples
    )
    return f"\n\n<examples>\n{items}\n</examples>\n\n"


def _build_schema_context(
    db_to_ontology: dict[str, str],
    has_entities: bool,
    needs_federation: bool,
    intents: list[str] | None = None,
) -> str:
    # Values are already faithful <database>…</database> docs (see slice_database_ontology).
    ontologies = "\n\n".join(db_to_ontology.values())

    keys = ["named_graph_rules", "output_format_rules", "entity_type_rules"]
    if has_entities:
        keys += ["qid_resolution_rules", "string_matching_rules"]
    if needs_federation or len(db_to_ontology) > 1:
        keys.append("federated_query_rules")
    if len(db_to_ontology) > 1:
        keys.append("cross_database_join_rules")
    if "musicbrainz" in db_to_ontology:
        keys.append("musicbrainz_specific")
    if intents and "aggregation" in intents:
        keys.append("aggregation_rules")

    instructions = "\n\n".join(INSTRUCTION_CHUNKS[k] for k in keys)
    return (
        f"<schema-context>\n<databases>\n{ontologies}\n</databases>\n\n"
        f"<instructions>\n{instructions}\n</instructions>\n</schema-context>"
    )


def _get_rag_examples(query: str, target_graphs: list[str]) -> list[dict]:
    from app.rag.store import get_vector_store

    k = settings.rag_top_k
    store = get_vector_store()
    docs = store.similarity_search(query, k=k * 3)

    seen: set[str] = set()
    unique_docs = []
    for doc in docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_docs.append(doc)

    filtered = [
        {"nl": doc.page_content, "sparql": doc.metadata["sparql"]}
        for doc in unique_docs
        if any(db in doc.metadata.get("databases", []) for db in target_graphs)
    ]
    if len(filtered) < k:
        filtered = [
            {"nl": doc.page_content, "sparql": doc.metadata["sparql"]}
            for doc in unique_docs
        ]
    return filtered[:k]


async def _resolve_qids(
    entities: list[str], entity_contexts: dict[str, str]
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for name in entities:
        try:
            context = entity_contexts.get(name, "")
            matches = await wikidata_qid_lookup.ainvoke(
                {
                    "entity_name": name,
                    "context": context,
                }
            )
            if matches:
                resolved[name] = matches[0]["qid"]
        except Exception:
            logger.exception("QID lookup failed for %r", name)
    return resolved


class _NeededNodes(BaseModel):
    nodes: list[str]


get_sub_nodes_prompt = """\
You are a SPARQL query planner for linked music databases.

Given a natural language query and the entity types available in one target database, \
select only the entity types that are necessary to answer the query.

<rules>
- Include an entity type if it must appear in the SPARQL query as a subject, object, or intermediate join node.
- Exclude entity types that are irrelevant to the query — do not include them just because they exist.
- Return node names exactly as given (e.g. "diamm:Composition", "mb:Artist").
</rules>

<available_nodes>
{node_names}
</available_nodes>

Return only the list of required node names."""


def _relevant_classes(ontology_graph: Graph, related_nodes: list[Node]) -> set[str]:
    """Selected classes plus any classes that connect them along the ontology paths."""
    sub_edges: set[Edge] = set()
    for a, b in combinations(related_nodes, 2):
        sub_edges |= ontology_graph.get_edges_on_paths(source=a, target=b)
        sub_edges |= ontology_graph.get_edges_on_paths(source=b, target=a)
    names = {n.name for n in related_nodes}
    names |= {e.source.name for e in sub_edges}
    names |= {e.target.name for e in sub_edges}
    return names


async def _get_needed_ontologies(
    query: str, target_graphs: list[str]
) -> dict[str, str]:
    ontology_graphs = {
        db: parse_ontology_to_graph(ONTOLOGY_CHUNKS[db])
        for db in target_graphs
        if db in ONTOLOGY_CHUNKS
    }

    model = get_structured_model(_NeededNodes)

    async def _query_db(db: str, node_names: list[str]) -> list[str]:
        system = get_sub_nodes_prompt.format(node_names=", ".join(node_names))
        try:
            result = await model.ainvoke(
                [SystemMessage(content=system), HumanMessage(content=query)]
            )
            return result.nodes
        except Exception:
            logger.exception("Node selection failed for db %r, returning all nodes", db)
            return node_names

    results = await asyncio.gather(
        *[
            _query_db(db, [n.name for n in graph.nodes])
            for db, graph in ontology_graphs.items()
        ]
    )
    db_to_selected: dict[str, list[str]] = dict(zip(ontology_graphs.keys(), results))

    db_to_ontology: dict[str, str] = {}
    for db, graph in ontology_graphs.items():
        related = [graph.get_node_by_name(name=n) for n in db_to_selected[db]]
        related = [n for n in related if n is not None]
        class_names = _relevant_classes(graph, related)
        # Emit the verbatim authored schema for the relevant classes — direction and
        # literal properties intact — rather than the lossy graph round-trip.
        db_to_ontology[db] = slice_database_ontology(ONTOLOGY_CHUNKS[db], class_names)
    return db_to_ontology


async def retrieve_node(state: GraphState) -> dict:
    target_graphs: list[str] = state.get("target_graphs") or []
    entity_contexts: dict[str, str] = state.get("entity_contexts") or {}
    needs_federation: bool = state.get("needs_federation", False)
    query: str = state["user_query"]
    db_to_sub_ontology = await _get_needed_ontologies(
        query=query, target_graphs=target_graphs
    )
    schema_context = _build_schema_context(
        db_to_sub_ontology,
        bool(entity_contexts),
        needs_federation,
        state.get("intents"),
    )

    if settings.rag_enabled:
        examples = _get_rag_examples(query, target_graphs)
    elif settings.few_shot_enabled:
        examples = FEW_SHOT_EXAMPLES
    else:
        examples = []

    few_shot_examples = format_examples_to_xml(examples)

    resolved_qids: dict[str, str] = {}
    if entity_contexts:
        resolved_qids = await _resolve_qids(
            list(entity_contexts.keys()), entity_contexts
        )

    return {
        "schema_context": schema_context,
        "few_shot_examples": few_shot_examples,
        "resolved_qids": resolved_qids,
    }
