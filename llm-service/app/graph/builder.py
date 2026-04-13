import time

from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.graph.nodes.judge import judge_node
from app.graph.nodes.execute import execute_node
from app.graph.nodes.generate import generate_node
from app.graph.nodes.intake import intake_node
from app.graph.nodes.retrieve import retrieve_node
from app.graph.nodes.validate import validate_node
from app.graph.state import GraphState


def after_validate(state: GraphState) -> str:
    if state.get("is_valid"):
        return "execute"
    if state.get("repair_count", 0) < state.get(
        "max_repairs", settings.max_repair_iterations
    ):
        return "generate"
    return END


def after_judge(state: GraphState) -> str:
    if state.get("judge_feedback") is not None:
        return "intake"
    if state.get("execution_error") is not None and state.get(
        "repair_count", 0
    ) < state.get("max_repairs", settings.max_repair_iterations):
        return "intake"
    return END


def build_graph():
    builder = StateGraph(GraphState)
    builder.add_node("intake", intake_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_node("validate", validate_node)
    builder.add_node("execute", execute_node)
    builder.add_node("judge", judge_node)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "validate")

    builder.add_conditional_edges(
        "validate", after_validate, ["execute", "generate", END]
    )
    builder.add_edge("execute", "judge")
    builder.add_conditional_edges("judge", after_judge, ["intake", END])

    return builder.compile()


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_graph(user_query: str) -> dict:
    graph = _get_graph()
    t0 = time.monotonic()
    initial_state: GraphState = {
        "user_query": user_query,
        "repair_count": 0,
        "max_repairs": settings.max_repair_iterations,
    }
    final_state = await graph.ainvoke(initial_state)
    duration_ms = int((time.monotonic() - t0) * 1000)
    return {
        "sparql": final_state.get("sparql", ""),
        "usage": {},
        "durationMs": duration_ms,
        "graphs": final_state.get("target_graphs"),
        "confidence": final_state.get("confidence"),
        "assumptions": final_state.get("assumptions"),
        "resultCount": final_state.get("result_count"),
        "executionError": final_state.get("execution_error"),
        "results": final_state.get("results"),
    }


graph = build_graph()
