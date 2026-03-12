import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.config import settings
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


class _JudgeVerdict(BaseModel):
    satisfied: bool
    reason: str


_JUDGE_PROMPT = """\
You are evaluating whether a SPARQL query result satisfies the user's intent.

User question: {user_query}

SPARQL query:
```sparql
{sparql}
```

Sample results (up to 5 rows):
{sample_results}

Does the result satisfy the user's question?
- satisfied: true if the results directly answer what was asked
- reason: brief explanation of your assessment"""


async def answer_node(state: GraphState) -> dict:
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
        bindings = (
            state["results"].get("results", {}).get("bindings", [])
        )
        sample = bindings[:5]

        judge_model = ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.llm_api_key,
            temperature=0,
        ).with_structured_output(_JudgeVerdict)

        judge_prompt = _JUDGE_PROMPT.format(
            user_query=state["user_query"],
            sparql=state.get("sparql", ""),
            sample_results=sample if sample else "(no results)",
        )

        try:
            verdict = await judge_model.ainvoke(judge_prompt)
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
