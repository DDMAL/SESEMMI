import logging

from app.graph.state import GraphState
from app.graph.tools.sparql_execute import execute_sparql

logger = logging.getLogger(__name__)


async def execute_node(state: GraphState) -> dict:
    try:
        result = await execute_sparql(state["sparql"])
        if result["error"] is not None:
            return {"execution_error": result["error"], "results": None, "result_count": 0}
        bindings = result["results"].get("results", {}).get("bindings", [])
        return {
            "results": result["results"],
            "result_count": len(bindings),
            "execution_error": None,
        }
    except Exception as exc:
        logger.exception("execute_node raised unexpectedly")
        return {"execution_error": str(exc) or repr(exc), "results": None, "result_count": 0}
