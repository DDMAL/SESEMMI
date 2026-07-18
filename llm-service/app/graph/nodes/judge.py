import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.config import settings
from app.graph.state import GraphState
from app.graph.model import get_structured_model
from app.graph.tools.empty_probe import probe_empty_patterns
from app.graph.tools.federation import has_local_pattern, strip_service_blocks
from app.graph.tools.sparql_execute import execute_sparql

logger = logging.getLogger(__name__)


def _base_assumptions(state: GraphState) -> list[str]:
    """Prior assumptions plus one line per resolved QID."""
    assumptions = list(state.get("assumptions") or [])
    for name, qid in (state.get("resolved_qids") or {}).items():
        assumptions.append(f"Assumed QID {qid} for {name}")
    return assumptions


async def _degrade_external_service(state: GraphState) -> dict:
    """Layer 3 — turn a transient federated-SERVICE failure into an honest answer.

    The external enrichment (e.g. a live Wikidata VIAF lookup) was unreachable, but the local
    part of the query is still answerable. Strip the SERVICE block and re-run the local subquery
    (no model call), then report the partial result with a downgraded confidence and a caveat.
    If there is no local part, degrade to an explicit "requires live Wikidata data" result rather
    than surfacing the raw error.
    """
    assumptions = _base_assumptions(state)

    sparql = state.get("sparql", "")
    local_query = strip_service_blocks(sparql)
    salvaged: dict | None = None
    if has_local_pattern(sparql):  # a local part exists to answer
        try:
            res = await execute_sparql(local_query)
            if res["error"] is None:
                salvaged = res["results"]
        except Exception:
            logger.exception("Layer-3 strip-and-rerun failed")

    cleared = {"judge_feedback": None, "execution_error": None, "error_kind": None}
    if salvaged is not None:
        bindings = salvaged.get("results", {}).get("bindings", [])
        assumptions.append(
            "The live Wikidata lookup was unavailable, so externally-enriched fields could "
            "not be attached; results reflect the local graphs only."
        )
        return {
            **cleared,
            "results": salvaged,
            "result_count": len(bindings),
            "confidence": "medium",
            "assumptions": assumptions,
        }

    assumptions.append(
        "This answer requires live Wikidata data, which was unavailable (the federated "
        "query service could not be reached)."
    )
    return {
        **cleared,
        "results": None,
        "result_count": 0,
        "confidence": "low",
        "assumptions": assumptions,
    }


def _empty_probe_feedback(empties: list[str]) -> str:
    patterns = "\n".join(f"- {e}" for e in empties)
    return (
        "The query executed but returned no results. Each of these triple patterns "
        "individually matches no data in the target graph, so they are the reason the "
        f"result is empty:\n{patterns}\n"
        "The entity or value may not exist in this graph, or the constraint may be "
        "over-specified. Remove or relax the unsupported pattern(s) and rewrite the query."
    )


class _JudgeVerdict(BaseModel):
    satisfied: bool
    reason: str
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
2. Schema honesty — if the question asks for a property, class, or filter the ontology does not
   contain, do NOT demand it. Accept the closest supported query and record the gap in
   "limitation" (e.g. the graph stores no language, so results cannot be narrowed to one). A
   limitation does NOT make the query unsatisfied.
3. Empty results — if a valid query returns no rows for a question that should match data,
   inspect the triples for an inverted edge direction or a predicate/class not in the schema;
   if you find one, set satisfied=false and name the triple to fix.
4. Column shape — default to a single URI column; expect a label column only when the question
   explicitly asks for a name, title, or label.

Set "satisfied" false only for a fixable fault — wrong edge direction, invented predicate/class,
wrong columns, or off-target results — and put the concrete fix in "reason". Otherwise set it true.
Note: wdt:P2888 is an exact-match link (owl:sameAs equivalent in Wikidata).
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
</sample_results>"""


async def judge_node(state: GraphState) -> dict:
    updates: dict = {"judge_feedback": None}  # clear prior judge signal by default

    # Layer 3 — honest degradation: an external federated call failed transiently. Salvage the
    # local part and report it with a caveat rather than surfacing the raw external error.
    if state.get("error_kind") == "external_service" and state.get("execution_error"):
        return await _degrade_external_service(state)

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

    assumptions = _base_assumptions(state)
    updates.update({"confidence": confidence, "assumptions": assumptions})

    # Zero-row diagnostic: ASK-probe the query for the specific unsatisfiable pattern and
    # repair with that concrete signal, before falling back to the coarser LLM judge.
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
            updates["judge_feedback"] = _empty_probe_feedback(empties)
            return updates

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
        elif verdict.limitation:
            # Accepted the closest supported query; surface the schema gap instead of churning.
            assumptions_new = list(assumptions)
            assumptions_new.append(verdict.limitation)
            updates["assumptions"] = assumptions_new

    return updates
