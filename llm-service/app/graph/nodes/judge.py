import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.config import settings
from app.graph.state import GraphState
from app.graph.model import get_structured_model
from app.graph.tools.empty_probe import probe_empty_patterns

logger = logging.getLogger(__name__)


def _base_assumptions(state: GraphState) -> list[str]:
    """Prior assumptions plus one line per resolved QID."""
    assumptions = list(state.get("assumptions") or [])
    for name, qid in (state.get("resolved_qids") or {}).items():
        assumptions.append(f"Assumed QID {qid} for {name}")
    return list(dict.fromkeys(assumptions))


def _format_empty_diagnostics(empties: list[str]) -> str:
    patterns = "\n".join(f"- {e}" for e in empties)
    return (
        "The query returned no results. These independently probed patterns matched "
        f"no data:\n{patterns}\n"
        "This is diagnostic evidence, not proof that the query is wrong. It can reflect "
        "missing data or reconciliation links. Check for a concrete schema or syntax "
        "mistake. Preserve all requirements in the user's question; never remove an "
        "entity, date, place, type, role or relationship merely to obtain rows. If no "
        "fixable mistake is supported by the schema, accept the empty result."
    )


class _JudgeVerdict(BaseModel):
    # reason precedes satisfied on purpose: structured output is emitted in field order, so the
    # model reasons before committing to the verdict (chain-of-thought) instead of rationalizing it.
    reason: str
    satisfied: bool
    # A distinction the question asked for that the schema simply cannot express.
    # Recorded as an assumption on an accepted query — it does NOT force a repair.
    limitation: str | None = None


_JUDGE_SYSTEM = """\
You are evaluating whether a SPARQL query and its results satisfy the user's intent.
Judge the query against the provided schema — its ontology (classes, predicates, edge
directions) and generation rules — not against world knowledge. Evaluate only what the
schema can express.

<instructions>
1. Relevance — does the query express the user's intent as faithfully as the schema allows,
   using the right classes and predicates in the direction the ontology declares?
2. Schema honesty — when the schema cannot express a required distinction, record it in
   "limitation" and describe the result as partial. Do not invent a property to fill the gap.
   Preserve every requirement that CAN be expressed. Dropping a supported date, entity,
   location or relationship is a fixable fault even when the query returns rows.
3. Empty results — zero rows is not itself a fault. Missing entities or reconciliation links
   do not justify relaxing the question. Set satisfied=false only if the schema supports a
   concrete correction, such as a reversed edge or invented predicate/class. Do not infer
   that results ought to exist from world knowledge or from the wording of the question.
4. Column shape — entity lookups should return the answer URI plus requested fields.
   Counts, comparisons and grouped summaries need their requested values and grouping
   columns, not a forced single URI. Do not reject these columns as a shape error.
5. Match evidence — shared titles/names alone establish candidate matches, not identity of
   people, works or recordings. Record a limitation if identity was requested but only text
   was matched. A question explicitly asking for shared titles is correctly answered by a
   title join; do not demand unavailable identifiers for that question. Shared years or
   categories are comparisons only. Role-agnostic related-person links do not prove that
   someone composed a work or performed at an event; record that distinction as a limitation.

Set "satisfied" false only for a fixable fault — wrong edge direction, invented predicate/class,
wrong columns, or off-target results — and put the concrete fix in "reason". Otherwise set it true.
Note: wdt:P2888 records an asserted reconciliation link; it does not independently verify
the match, its completeness, or the local entity's type.
</instructions>"""

_JUDGE_USER_TEMPLATE = """\
<schema>
{schema_context}
</schema>

<user_question>
{user_query}
</user_question>

<sparql_query>
{sparql}
</sparql_query>

<sample_results description="up to 5 rows">
{sample_results}
</sample_results>

<empty_result_diagnostics>
{empty_diagnostics}
</empty_result_diagnostics>"""


async def judge_node(state: GraphState) -> dict:
    """Assess the query without changing its execution results or errors."""
    assumptions = _base_assumptions(state)
    execution_error = state.get("execution_error")
    updates: dict = {
        "judge_feedback": None,
        "confidence": (
            "medium" if state.get("is_valid") and execution_error is None else "low"
        ),
        "assumptions": assumptions,
    }

    if execution_error is not None:
        if state.get("error_kind") == "external_service":
            # SERVICE can enforce required filters, so a local-only answer is unsafe.
            assumptions.append(
                "This answer requires live Wikidata data, which was unavailable (the federated "
                "query service could not be reached). The requested conditions could not be "
                "verified; please try again later."
            )
        return updates

    # Empty probes explain missing data even when no repair attempts remain.
    empty_diagnostics = "Not probed."
    if settings.empty_probe_enabled and state.get("result_count", 0) == 0:
        try:
            empties = await probe_empty_patterns(state.get("sparql", ""))
        except Exception:
            logger.exception("empty-probe failed, skipping")
            empties = []
        if empties:
            empty_diagnostics = _format_empty_diagnostics(empties)
            assumptions.append(
                "No records matched one or more requested relationships. Missing data "
                "or reconciliation links may explain the empty result."
            )

    if not settings.semantic_judge_enabled or not state.get("results"):
        return updates

    bindings = state["results"].get("results", {}).get("bindings", [])
    judge_user = _JUDGE_USER_TEMPLATE.format(
        schema_context=state.get("schema_context", "") or "(no schema provided)",
        user_query=state["user_query"],
        sparql=state.get("sparql", ""),
        sample_results=bindings[:5] or "(no results)",
        empty_diagnostics=empty_diagnostics,
    )
    judge_model = get_structured_model(_JudgeVerdict)
    try:
        verdict = await judge_model.ainvoke(
            [SystemMessage(content=_JUDGE_SYSTEM), HumanMessage(content=judge_user)]
        )
    except Exception:
        logger.exception("Semantic judge failed, skipping")
        assumptions.append(
            "These results could not be checked against your question. "
            "Review them before relying on them."
        )
        return updates

    has_rows = state.get("result_count", 0) > 0
    if not verdict.satisfied:
        max_repairs = state.get("max_repairs", settings.max_repair_iterations)
        # The judge can falsely reject valid joins. Keep nonempty results for review;
        # only empty results are eligible for another generation attempt.
        if not has_rows and state.get("repair_count", 0) < max_repairs:
            updates["judge_feedback"] = verdict.reason
        else:
            updates["confidence"] = "low"
            assumptions.append(
                f"These results may not fully answer your question: {verdict.reason}"
            )
    elif verdict.limitation:
        assumptions.append(verdict.limitation)
    elif has_rows:
        updates["confidence"] = "high"

    return updates
