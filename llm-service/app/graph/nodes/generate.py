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

    parts.append(
        "<output_rules>\n"
        "Respond with a valid SPARQL query ONLY. No prose, no explanation.\n"
        "</output_rules>"
    )

    schema_context = state.get("schema_context", "")
    if schema_context:
        parts.append(f"\n{schema_context}\n>")

    few_shot = state.get("few_shot_examples", "")
    if few_shot:
        parts.append(f"<examples>\n{few_shot}\n</examples>")

    resolved_qids = state.get("resolved_qids") or {}
    if resolved_qids:
        qid_lines = "\n".join(
            f"- {name} = {qid}" for name, qid in resolved_qids.items()
        )
        parts.append(f"<resolved_qids>\n{qid_lines}\n</resolved_qids>")

    if is_repair:
        repair_parts: list[str] = [f'<repair attempt="{repair_count}">']
        repair_parts.append(
            f"<previous_query>\n{state.get('sparql', '')}\n</previous_query>"
        )
        errors = state.get("validation_errors") or []
        exec_error = state.get("execution_error")
        if errors:
            error_lines = "\n".join(f"- {e}" for e in errors)
            repair_parts.append(
                f"<validation_errors>\n{error_lines}\n</validation_errors>"
            )
        if exec_error:
            exec_lines = [exec_error]
            if "timeout" in exec_error.lower() or "ReadTimeout" in exec_error:
                exec_lines.append(
                    "The query timed out. Rewrite it to be faster: add LIMIT, "
                    "restrict to fewer named graphs, remove optional cross-products, "
                    "or break into a simpler single-graph query."
                )
            repair_parts.append(
                "<execution_error>\n" + "\n".join(exec_lines) + "\n</execution_error>"
            )
        judge_feedback = state.get("judge_feedback")
        if judge_feedback:
            repair_parts.append(
                f"<semantic_feedback>\n{judge_feedback}\n</semantic_feedback>"
            )
        repair_parts.append("Please write a corrected SPARQL query.")
        repair_parts.append("</repair>")
        parts.append("\n".join(repair_parts))

    parts.append(f"<question>\n{state['user_query']}\n</question>")
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

    has_entities = bool(state.get("entity_contexts"))
    base_model = ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_ctx=settings.ollama_num_ctx,
        num_thread=settings.ollama_num_thread,
        think=settings.ollama_think,
    )
    model = base_model.bind_tools([wikidata_qid_lookup]) if has_entities else base_model

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
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    # If the loop exhausted all iterations without the model producing text,
    # force one final generation with all tool results already in messages.
    if response is not None and response.tool_calls:
        logger.warning(
            "Tool loop exhausted after %d iterations; forcing final generation",
            _MAX_TOOL_ITERATIONS,
        )
        response = await model.ainvoke(messages)

    content = response.content if response is not None else ""
    if isinstance(content, list):
        content = "".join(
            part["text"] if isinstance(part, dict) and "text" in part else ""
            for part in content
        )
    sparql = clean_sparql(content)
    return {
        "sparql": sparql,
        "repair_count": repair_count,
        "resolved_qids": resolved_qids,
    }
