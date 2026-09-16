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


async def _degrade_external_service(state: GraphState) -> dict:
    """Report an unavailable answer without dropping external constraints.

    A SERVICE block can restrict birthplace, nationality, roles or identity, not
    just add display fields. Stripping it cannot generally preserve the question.
    Keep the failed query and error so callers distinguish unavailable from empty.
    """
    assumptions = _base_assumptions(state)
    assumptions.append(
        "This answer requires live Wikidata data, which was unavailable (the federated "
        "query service could not be reached). The requested conditions could not be "
        "verified; please try again later."
    )
    return {
        "judge_feedback": None,
        "execution_error": state.get("execution_error"),
        "error_kind": "external_service",
        "results": None,
        "result_count": 0,
        "confidence": "low",
        "assumptions": assumptions,
    }


def _empty_probe_feedback(empties: list[str]) -> str:
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
    updates: dict = {"judge_feedback": None}  # clear prior judge signal by default

    # An unavailable external constraint must not become an unfiltered local answer.
    if state.get("error_kind") == "external_service" and state.get("execution_error"):
        return await _degrade_external_service(state)

    # Determine base confidence
    if state.get("is_valid") and not state.get("execution_error"):
        confidence = "medium"
    else:
        confidence = "low"

    assumptions = _base_assumptions(state)
    updates.update({"confidence": confidence, "assumptions": assumptions})

    # A failed ASK is evidence of missing data, not automatic permission to repair.
    empty_diagnostics = "Not probed."
    if (
        settings.empty_probe_enabled
        and not state.get("execution_error")
        and state.get("result_count", 0) == 0
        and state.get("repair_count", 0)
        < state.get("max_repairs", settings.max_repair_iterations)
    ):
        try:
            empties = await probe_empty_patterns(state.get("sparql", ""))
        except Exception:
            logger.exception("empty-probe failed, skipping")
            empties = []
        if empties:
            empty_diagnostics = _empty_probe_feedback(empties)
            assumptions.append(
                "No records matched one or more requested relationships. Missing data "
                "or reconciliation links may explain the empty result."
            )

    # Semantic judge (only when enabled and execution succeeded)
    if (
        settings.semantic_judge_enabled
        and not state.get("execution_error")
        and state.get("results")
    ):
        bindings = state["results"].get("results", {}).get("bindings", [])
        sample = bindings[:5]

        judge_model = get_structured_model(_JudgeVerdict)

        judge_user = _JUDGE_USER_TEMPLATE.format(
            schema_context=state.get("schema_context", "") or "(no schema provided)",
            user_query=state["user_query"],
            sparql=state.get("sparql", ""),
            sample_results=sample if sample else "(no results)",
            empty_diagnostics=empty_diagnostics,
        )

        try:
            verdict = await judge_model.ainvoke(
                [SystemMessage(content=_JUDGE_SYSTEM), HumanMessage(content=judge_user)]
            )
        except Exception:
            # An unavailable judge cannot promote execution success to high confidence.
            logger.exception("Semantic judge failed, skipping")
            updates["assumptions"] = assumptions + [
                "Semantic judge could not be evaluated (malformed verdict); "
                "confidence not independently confirmed."
            ]
            return updates

        if not verdict.satisfied:
            has_rows = state.get("result_count", 0) > 0
            max_repairs = state.get("max_repairs", settings.max_repair_iterations)
            # Regenerate only when the query returned NO rows — there a repair can find data.
            # Keep nonempty results available for review, but mark a rejected answer low.
            # Do not repeatedly regenerate on a judge's potentially spurious preference.
            # The 27b judge routinely false-flags cross-graph rdfs:label joins as needing an
            # impossible wdt:P2888, so looping on that just discards correct answers.
            if not has_rows and state.get("repair_count", 0) < max_repairs:
                updates["judge_feedback"] = verdict.reason
                return updates
            updates["confidence"] = "low"
            assumptions_new = list(assumptions)
            verb = "flagged" if has_rows else "unsatisfied"
            assumptions_new.append(f"Semantic judge {verb}: {verdict.reason}")
            updates["assumptions"] = assumptions_new
        elif verdict.limitation:
            # Accepted the closest supported query; surface the schema gap instead of churning.
            assumptions_new = list(assumptions)
            assumptions_new.append(verdict.limitation)
            updates["assumptions"] = assumptions_new
        elif state.get("result_count", 0) > 0:
            updates["confidence"] = "high"

    return updates
