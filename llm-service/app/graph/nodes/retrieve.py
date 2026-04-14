import logging

from app.config import settings
from app.graph.state import GraphState
from app.graph.tools.wikidata import wikidata_qid_lookup
from app.graph.examples import FEW_SHOT_EXAMPLES
from app.graph.schema_corpus import INSTRUCTION_CHUNKS, ONTOLOGY_CHUNKS

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
    target_graphs: list[str],
    has_entities: bool,
    needs_federation: bool,
    intents: list[str] | None = None,
) -> str:
    ontology = "\n\n".join(
        ONTOLOGY_CHUNKS[db] for db in target_graphs if db in ONTOLOGY_CHUNKS
    )

    keys = ["named_graph_rules", "output_format_rules", "entity_type_rules"]
    if has_entities:
        keys += ["qid_resolution_rules", "string_matching_rules"]
    if needs_federation or len(target_graphs) > 1:
        keys.append("federated_query_rules")
    if "musicbrainz" in target_graphs:
        keys.append("musicbrainz_specific")
    if intents and "aggregation" in intents:
        keys.append("aggregation_rules")

    instructions = "\n\n".join(INSTRUCTION_CHUNKS[k] for k in keys)
    return (
        f"<schema-context>\n<databases>\n{ontology}\n</databases>\n\n"
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
            matches = await wikidata_qid_lookup.ainvoke({
                "entity_name": name,
                "context": context,
            })
            if matches:
                resolved[name] = matches[0]["qid"]
        except Exception:
            logger.exception("QID lookup failed for %r", name)
    return resolved


async def retrieve_node(state: GraphState) -> dict:
    target_graphs: list[str] = state.get("target_graphs") or []
    entity_contexts: dict[str, str] = state.get("entity_contexts") or {}
    needs_federation: bool = state.get("needs_federation", False)
    query: str = state["user_query"]

    schema_context = _build_schema_context(
        target_graphs, bool(entity_contexts), needs_federation, state.get("intents")
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
        resolved_qids = await _resolve_qids(list(entity_contexts.keys()), entity_contexts)

    return {
        "schema_context": schema_context,
        "few_shot_examples": few_shot_examples,
        "resolved_qids": resolved_qids,
    }
