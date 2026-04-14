import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import GraphState
from app.graph.model import get_chat_model

logger = logging.getLogger(__name__)


def clean_sparql(text: str) -> str:
    """Extract and clean SPARQL query from LLM output."""
    text = text.strip()

    m = re.search(r"```sparql\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    m = re.search(r"```(?:\w+)?\s*([\s\S]*?)\s*```", text)
    if m:
        candidate = m.group(1).strip()
        if re.search(r"\b(SELECT|CONSTRUCT|ASK|DESCRIBE)\b", candidate, re.IGNORECASE):
            return candidate

    m = re.search(
        r"((?:PREFIX\s+\w|SELECT\b|CONSTRUCT\b|ASK\b|DESCRIBE\b)[\s\S]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    return text


def _build_system(state: GraphState) -> str:
    parts: list[str] = []

    parts.append(
        "<output_rules>\n"
        "Respond with a valid SPARQL query ONLY. No prose, no explanation.\n"
        "Return exactly one column — the URI that answers the question. Add a label column only when the question explicitly asks for a name, title, or label.\n"
        "Add LIMIT 100 unless the question specifies a different count.\n"
        "Do not add ORDER BY unless the question explicitly asks for ordering (e.g. \"most\", \"earliest\", \"top N\").\n"
        "</output_rules>"
    )

    schema_context = state.get("schema_context", "")
    if schema_context:
        parts.append(f"\n{schema_context}\n")

    few_shot = state.get("few_shot_examples", "")
    if few_shot:
        parts.append(f"<examples>\n{few_shot}\n</examples>")

    return "\n\n".join(p for p in parts if p)


def _build_user(state: GraphState, is_repair: bool, repair_count: int) -> str:
    parts: list[str] = []

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
        repair_parts.append(
            "Analyze what caused the error in the previous query, then write a corrected SPARQL query.\n"
            "Think through:\n"
            "- What specific construct or pattern caused the error?\n"
            "- What is the correct way to express that in SPARQL for Virtuoso?\n"
            "Then output the corrected query only — no prose, no explanation."
        )
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

    system_text = _build_system(state)
    user_text = _build_user(state, is_repair, repair_count)

    model = get_chat_model()
    messages = [SystemMessage(content=system_text), HumanMessage(content=user_text)]
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
    }
