from app.config import settings
from app.graph.state import GraphState
from app.graph.validation import is_valid, validate_intent, validate_sparql


async def validate_node(state: GraphState) -> dict:
    syntax_errors = validate_sparql(state["sparql"], state.get("target_graphs"))
    intent_errors = validate_intent(
        state["sparql"],
        state.get("intent", "lookup"),
        bool(state.get("entity_contexts")),
        state.get("needs_federation", False),
    )
    all_errors = syntax_errors + intent_errors
    valid = is_valid(all_errors)
    result: dict = {"validation_errors": all_errors, "is_valid": valid}

    # When validation fails and repairs are exhausted, finalize here.
    if not valid:
        max_repairs = state.get("max_repairs", settings.max_repair_iterations)
        if state.get("repair_count", 0) >= max_repairs:
            assumptions: list[str] = list(state.get("assumptions") or [])
            for name, qid in (state.get("resolved_qids") or {}).items():
                assumptions.append(f"Assumed QID {qid} for {name}")
            result.update({"confidence": "low", "assumptions": assumptions})

    return result
