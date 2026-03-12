import logging
import re

from app.config import settings
from app.graph.state import GraphState
from app.graph.tools.wikidata import wikidata_qid_lookup
from app.llm.examples import FEW_SHOT_EXAMPLES
from app.llm.prompt import format_examples
from app.rag.schema_corpus import INSTRUCTION_CHUNKS, ONTOLOGY_CHUNKS

logger = logging.getLogger(__name__)

# Matches multi-word proper nouns (e.g., "Taylor Swift") or all-caps abbreviations (e.g., "NYC")
_ENTITY_RE = re.compile(
    r"\b(?:[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+|[A-Z]{2,})\b"
)
_MAX_ENTITIES = 5


def _build_schema_context(
    target_graphs: list[str],
    mentions_entities: bool,
    needs_federation: bool,
) -> str:
    ontology = "\n\n".join(
        ONTOLOGY_CHUNKS[db] for db in target_graphs if db in ONTOLOGY_CHUNKS
    )

    keys = ["named_graph_rules", "output_format_rules", "entity_type_rules"]
    if mentions_entities:
        keys += ["qid_resolution_rules", "string_matching_rules"]
    if needs_federation or len(target_graphs) > 1:
        keys.append("federated_query_rules")
    if "musicbrainz" in target_graphs:
        keys.append("musicbrainz_specific")

    instructions = "\n\n".join(INSTRUCTION_CHUNKS[k] for k in keys)
    return f"{ontology}\n\n{instructions}"


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


async def _resolve_qids(query: str) -> dict[str, str]:
    names = list(dict.fromkeys(_ENTITY_RE.findall(query)))[:_MAX_ENTITIES]
    resolved: dict[str, str] = {}
    for name in names:
        try:
            matches = await wikidata_qid_lookup.ainvoke({"entity_name": name})
            if matches:
                resolved[name] = matches[0]["qid"]
        except Exception:
            logger.exception("QID lookup failed for %r", name)
    return resolved


async def retrieve_node(state: GraphState) -> dict:
    target_graphs: list[str] = state.get("target_graphs") or []
    mentions_entities: bool = state.get("mentions_entities", False)
    needs_federation: bool = state.get("needs_federation", False)
    query: str = state["user_query"]

    schema_context = _build_schema_context(
        target_graphs, mentions_entities, needs_federation
    )

    if settings.rag_enabled:
        examples = _get_rag_examples(query, target_graphs)
    elif settings.few_shot_enabled:
        examples = FEW_SHOT_EXAMPLES
    else:
        examples = []

    few_shot_examples = format_examples(examples)

    resolved_qids: dict[str, str] = {}
    if mentions_entities:
        resolved_qids = await _resolve_qids(query)

    return {
        "schema_context": schema_context,
        "few_shot_examples": few_shot_examples,
        "resolved_qids": resolved_qids,
    }
