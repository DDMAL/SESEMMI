import logging

from langchain_ollama import ChatOllama
from pydantic import BaseModel

from app.config import settings
from app.graph.state import GraphState
from app.graph.tools.wikidata import wikidata_qid_lookup
from app.llm.examples import FEW_SHOT_EXAMPLES
from app.rag.schema_corpus import INSTRUCTION_CHUNKS, ONTOLOGY_CHUNKS

logger = logging.getLogger(__name__)


class _QIDSelection(BaseModel):
    selected_qid: str


async def _pick_qid_with_llm(
    entity_name: str,
    user_query: str,
    matches: list[dict],
    model: ChatOllama,
) -> str:
    candidates = "\n".join(
        f"- {m['qid']}: {m['label']} — {m.get('description', 'no description')}"
        for m in matches
    )
    prompt = (
        f"<task>Select the most relevant Wikidata entity for \"{entity_name}\" "
        f"in the context of the following music database query.</task>\n\n"
        f"<query>{user_query}</query>\n\n"
        f"<candidates>\n{candidates}\n</candidates>\n\n"
        f"<instructions>Return the QID of the candidate that best matches the entity "
        f"as used in the query. Consider the musical context.</instructions>"
    )
    structured = model.with_structured_output(_QIDSelection)
    result = await structured.ainvoke(prompt)
    valid_qids = {m["qid"] for m in matches}
    if result.selected_qid not in valid_qids:
        raise ValueError(f"LLM returned invalid QID {result.selected_qid!r}")
    return result.selected_qid


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
    intent: str = "lookup",
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
    if intent == "aggregation":
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


async def _resolve_qids(entities: list[str], user_query: str) -> dict[str, str]:
    resolved: dict[str, str] = {}
    model = ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_ctx=settings.ollama_num_ctx,
        num_thread=settings.ollama_num_thread,
        think=settings.ollama_think,
    )
    for name in entities:
        try:
            matches = await wikidata_qid_lookup.ainvoke({"entity_name": name})
            if not matches:
                continue
            if len(matches) == 1:
                resolved[name] = matches[0]["qid"]
            else:
                try:
                    resolved[name] = await _pick_qid_with_llm(
                        name, user_query, matches, model
                    )
                except Exception:
                    logger.warning(
                        "LLM QID selection failed for %r, using first match", name
                    )
                    resolved[name] = matches[0]["qid"]
        except Exception:
            logger.exception("QID lookup failed for %r", name)
    return resolved


async def retrieve_node(state: GraphState) -> dict:
    target_graphs: list[str] = state.get("target_graphs") or []
    entities: list[str] = state.get("extracted_entities") or []
    needs_federation: bool = state.get("needs_federation", False)
    query: str = state["user_query"]

    schema_context = _build_schema_context(
        target_graphs, bool(entities), needs_federation, state.get("intent", "lookup")
    )

    if settings.rag_enabled:
        examples = _get_rag_examples(query, target_graphs)
    elif settings.few_shot_enabled:
        examples = FEW_SHOT_EXAMPLES
    else:
        examples = []

    few_shot_examples = format_examples_to_xml(examples)

    resolved_qids: dict[str, str] = {}
    if entities:
        resolved_qids = await _resolve_qids(entities, query)

    return {
        "schema_context": schema_context,
        "few_shot_examples": few_shot_examples,
        "resolved_qids": resolved_qids,
    }
