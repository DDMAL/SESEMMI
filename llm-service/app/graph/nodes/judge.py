import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.config import settings
from app.graph.state import GraphState
from app.graph.model import get_chat_model

logger = logging.getLogger(__name__)


class _JudgeVerdict(BaseModel):
    satisfied: bool
    reason: str


_JUDGE_SYSTEM = """\
You are evaluating whether a SPARQL query result satisfies the user's intent.

<instructions>
Determine whether the sample results directly answer the user's question.
- Set "satisfied" to true only if the results address what was asked.
- Provide a brief "reason" explaining your assessment.
- Note: wdt:P2888 is used for exact match (owl:sameAs equivalent in Wikidata).
</instructions>"""

_JUDGE_USER_TEMPLATE = """\
<user_question>
{user_query}
</user_question>

<sparql_query>
{sparql}
</sparql_query>

<sample_results description="up to 5 rows">
{sample_results}
</sample_results>"""


async def judge_node(state: GraphState) -> dict:
    updates: dict = {"judge_feedback": None}  # clear prior judge signal by default

    # Determine base confidence
    if (
        state.get("is_valid")
        and not state.get("execution_error")
        and state.get("result_count", 0) > 0
    ):
        confidence = "high"
    elif state.get("is_valid") and not state.get("execution_error"):
        confidence = "medium"
    else:
        confidence = "low"

    assumptions: list[str] = list(state.get("assumptions") or [])
    for name, qid in (state.get("resolved_qids") or {}).items():
        assumptions.append(f"Assumed QID {qid} for {name}")

    updates.update({"confidence": confidence, "assumptions": assumptions})

    # Semantic judge (only when enabled and execution succeeded)
    if (
        settings.semantic_judge_enabled
        and not state.get("execution_error")
        and state.get("results")
    ):
        bindings = state["results"].get("results", {}).get("bindings", [])
        sample = bindings[:5]

        judge_model = get_chat_model().with_structured_output(_JudgeVerdict)

        judge_user = _JUDGE_USER_TEMPLATE.format(
            user_query=state["user_query"],
            sparql=state.get("sparql", ""),
            sample_results=sample if sample else "(no results)",
        )

        try:
            verdict = await judge_model.ainvoke(
                [SystemMessage(content=_JUDGE_SYSTEM), HumanMessage(content=judge_user)]
            )
        except Exception:
            logger.exception("Semantic judge failed, skipping")
            return updates

        if not verdict.satisfied:
            max_repairs = state.get("max_repairs", settings.max_repair_iterations)
            if state.get("repair_count", 0) < max_repairs:
                updates["judge_feedback"] = verdict.reason
                return updates
            else:
                updates["confidence"] = "low"
                assumptions_new = list(assumptions)
                assumptions_new.append(f"Semantic judge unsatisfied: {verdict.reason}")
                updates["assumptions"] = assumptions_new

    return updates
