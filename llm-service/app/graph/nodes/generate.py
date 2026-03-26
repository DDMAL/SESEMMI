import logging

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_ollama import ChatOllama

from app.config import settings
from app.graph.state import GraphState
from app.graph.tools.wikidata import wikidata_qid_lookup
from app.llm.chain import clean_sparql

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 3


def _build_prompt(state: GraphState, is_repair: bool, repair_count: int) -> str:
    parts: list[str] = []

    output_rules = (
        "IMPORTANT \u2014 OUTPUT RULES:\n"
        "- Respond with a valid SPARQL query ONLY. No prose, no explanation."
    )
    if state.get("mentions_entities"):
        output_rules += (
            '\n- If you need a Wikidata QID not listed under "Pre-resolved QIDs", '
            "call the wikidata_qid_lookup tool BEFORE writing the query. Never ask the user."
        )
    parts.append(output_rules)

    parts.append(state.get("schema_context", ""))

    few_shot = state.get("few_shot_examples", "")
    if few_shot:
        parts.append(few_shot)

    resolved_qids = state.get("resolved_qids") or {}
    if resolved_qids:
        qid_lines = ", ".join(f"{name} = {qid}" for name, qid in resolved_qids.items())
        parts.append(f"Pre-resolved QIDs: {qid_lines}")

    if is_repair:
        repair_lines = [
            f"\n---",
            f"REPAIR ATTEMPT {repair_count} — the previous query had errors:",
            f"```sparql\n{state.get('sparql', '')}\n```",
        ]
        errors = state.get("validation_errors") or []
        exec_error = state.get("execution_error")
        if errors:
            repair_lines.append("Validation errors:\n" + "\n".join(f"- {e}" for e in errors))
        if exec_error:
            repair_lines.append(f"Execution error: {exec_error}")
            if "timeout" in exec_error.lower() or "ReadTimeout" in exec_error:
                repair_lines.append(
                    "The query timed out. Rewrite it to be faster: add LIMIT, "
                    "restrict to fewer named graphs, remove optional cross-products, "
                    "or break into a simpler single-graph query."
                )
        judge_feedback = state.get("judge_feedback")
        if judge_feedback:
            repair_lines.append(f"Semantic feedback: {judge_feedback}")
        repair_lines.append("Please write a corrected SPARQL query.\n---\n")
        parts.append("\n".join(repair_lines))

    parts.append(f"Question: {state['user_query']}")
    return "\n\n".join(p for p in parts if p)


async def generate_node(state: GraphState) -> dict:
    is_repair = bool(
        state.get("validation_errors")
        or state.get("execution_error")
        or state.get("judge_feedback")
    )
    repair_count = state.get("repair_count", 0)
    if is_repair:
        repair_count += 1

    prompt_text = _build_prompt(state, is_repair, repair_count)

    mentions_entities = state.get("mentions_entities", False)
    base_model = ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_ctx=settings.ollama_num_ctx,
        num_thread=settings.ollama_num_thread,
        think=settings.ollama_think,
    )
    model = base_model.bind_tools([wikidata_qid_lookup]) if mentions_entities else base_model

    resolved_qids = dict(state.get("resolved_qids") or {})
    messages = [HumanMessage(content=prompt_text)]
    response = None

    for _ in range(_MAX_TOOL_ITERATIONS):
        response = await model.ainvoke(messages)
        if not response.tool_calls:
            break
        messages.append(response)
        for tc in response.tool_calls:
            entity_name = tc["args"].get("entity_name", "")
            if entity_name in resolved_qids:
                qid = resolved_qids[entity_name]
                result = [{"qid": qid, "label": entity_name}]
                logger.debug("Cache hit for QID %r → %s", entity_name, qid)
            else:
                try:
                    result = await wikidata_qid_lookup.ainvoke(tc["args"])
                    if result:
                        resolved_qids[entity_name] = result[0]["qid"]
                except Exception:
                    logger.exception("Tool call failed for %r", tc)
                    result = []
            messages.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )

    # If the loop exhausted all iterations without the model producing text,
    # force one final generation with all tool results already in messages.
    if response is not None and response.tool_calls:
        logger.warning("Tool loop exhausted after %d iterations; forcing final generation", _MAX_TOOL_ITERATIONS)
        response = await model.ainvoke(messages)

    content = response.content if response is not None else ""
    if isinstance(content, list):
        content = "".join(
            part["text"] if isinstance(part, dict) and "text" in part else ""
            for part in content
        )
    sparql = clean_sparql(content)
    return {"sparql": sparql, "repair_count": repair_count, "resolved_qids": resolved_qids}
