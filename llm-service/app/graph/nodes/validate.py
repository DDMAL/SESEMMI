from app.graph.state import GraphState
from app.graph.validation import is_valid, validate_intent, validate_sparql


async def validate_node(state: GraphState) -> dict:
    syntax_errors = validate_sparql(state["sparql"], state.get("target_graphs"))
    intent_errors = validate_intent(
        state["sparql"],
        state.get("intent", "lookup"),
        bool(state.get("extracted_entities")),
        state.get("needs_federation", False),
    )
    all_errors = syntax_errors + intent_errors
    return {"validation_errors": all_errors, "is_valid": is_valid(all_errors)}
