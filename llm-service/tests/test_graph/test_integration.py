"""End-to-end integration tests for the LangGraph StateGraph (Step 13)."""

from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from app.graph.builder import build_graph
from app.graph.nodes.intake import IntakeClassification

# ---------------------------------------------------------------------------
# Shared SPARQL fixtures
# ---------------------------------------------------------------------------

# Valid lookup query: full IRIs, GRAPH clause, LIMIT — passes all validation
_VALID_SPARQL = (
    "PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/> "
    "SELECT ?s ?label WHERE { "
    "GRAPH <https://linkedmusic.ca/graphs/diamm/> { "
    "?s a ?type ; <http://www.w3.org/2000/01/rdf-schema#label> ?label "
    "} } LIMIT 10"
)

# Valid aggregation query: has COUNT + GRAPH + LIMIT
_VALID_SPARQL_WITH_COUNT = (
    "SELECT (COUNT(?s) AS ?count) WHERE { "
    "GRAPH <https://linkedmusic.ca/graphs/diamm/> { "
    "?s a ?type "
    "} } LIMIT 10"
)

# Syntactically invalid — rdflib parse will fail
_INVALID_SPARQL = "SELECT ?x WHERE { ?x a UNCLOSED BRACE"

_VIRTUOSO_SUCCESS = {
    "results": {
        "results": {
            "bindings": [
                {"s": {"value": "uri1"}, "label": {"value": "Item 1"}},
                {"s": {"value": "uri2"}, "label": {"value": "Item 2"}},
            ]
        }
    },
    "error": None,
}

_VIRTUOSO_ERROR = {
    "results": None,
    "error": "Virtuoso SPARQL syntax error",
}

# ---------------------------------------------------------------------------
# Pre-built intake classifications
# ---------------------------------------------------------------------------

_DIAMM_LOOKUP = IntakeClassification(
    intents=["lookup"],
    target_graphs=["diamm"],
    needs_federation=False,
    entity_contexts=[],
)

_DIAMM_AGGREGATION = IntakeClassification(
    intents=["aggregation"],
    target_graphs=["diamm"],
    needs_federation=False,
    entity_contexts=[],
)

# ---------------------------------------------------------------------------
# Mock factory helpers
# ---------------------------------------------------------------------------


def _intake_mock(classification: IntakeClassification):
    """get_structured_model mock for intake_node (returns the structured chain)."""
    chain = AsyncMock()
    chain.ainvoke.return_value = classification
    return chain


def _generate_mock(*sparql_responses: str):
    """
    ChatGoogleGenerativeAI mock for generate_node.
    Successive ainvoke() calls return successive sparql_responses.
    Works for both entities (bind_tools path) and no-entities (direct path).
    """
    responses = [AIMessage(content=s) for s in sparql_responses]
    inner_model = AsyncMock()
    inner_model.ainvoke.side_effect = responses
    chat = MagicMock()
    chat.bind_tools.return_value = inner_model
    # Also wire ainvoke directly for the no-entities path
    chat.ainvoke = AsyncMock(side_effect=responses)
    return chat


def _judge_mock(*verdicts: tuple[bool, str]):
    """
    ChatGoogleGenerativeAI mock for answer_node judge (uses with_structured_output).
    Each (satisfied, reason) pair is returned on successive ainvoke() calls.
    """
    verdict_objects = []
    for satisfied, reason in verdicts:
        v = MagicMock()
        v.satisfied = satisfied
        v.reason = reason
        verdict_objects.append(v)
    chain = AsyncMock()
    chain.ainvoke.side_effect = verdict_objects
    return chain


def _answer_settings(*, semantic_judge_enabled: bool = False):
    """Return a settings mock suitable for patching app.graph.nodes.judge.settings."""
    s = MagicMock()
    s.semantic_judge_enabled = semantic_judge_enabled
    s.llm_model = "gemini-2.5-flash-lite"
    s.llm_api_key = "test-key"
    s.max_repair_iterations = 3
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_happy_path():
    """
    Full graph: intake → retrieve → generate → validate → execute → judge.
    Valid SPARQL + Virtuoso 200 → confidence='high', results populated, no repairs.
    """
    with (
        patch(
            "app.graph.nodes.intake.get_structured_model",
            return_value=_intake_mock(_DIAMM_LOOKUP),
        ),
        patch(
            "app.graph.nodes.generate.get_chat_model",
            return_value=_generate_mock(_VALID_SPARQL),
        ),
        patch(
            "app.graph.nodes.judge.settings",
            new=_answer_settings(semantic_judge_enabled=False),
        ),
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new_callable=AsyncMock,
            return_value=_VIRTUOSO_SUCCESS,
        ),
    ):
        graph = build_graph()
        final = await graph.ainvoke(
            {
                "user_query": "Find DIAMM manuscripts",
                "repair_count": 0,
                "max_repairs": 3,
            }
        )

    assert final["confidence"] == "high"
    assert final["result_count"] == 2
    assert final["results"] is not None
    assert final["execution_error"] is None
    assert final["repair_count"] == 0


async def test_repair_loop_invalid_then_valid():
    """
    Repair loop: first generate returns invalid SPARQL (rdflib rejects it),
    second generate returns valid SPARQL.
    Final repair_count=1, confidence='high'.
    """
    with (
        patch(
            "app.graph.nodes.intake.get_structured_model",
            return_value=_intake_mock(_DIAMM_LOOKUP),
        ),
        patch(
            "app.graph.nodes.generate.get_chat_model",
            return_value=_generate_mock(_INVALID_SPARQL, _VALID_SPARQL),
        ),
        patch(
            "app.graph.nodes.judge.settings",
            new=_answer_settings(semantic_judge_enabled=False),
        ),
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new_callable=AsyncMock,
            return_value=_VIRTUOSO_SUCCESS,
        ),
    ):
        graph = build_graph()
        final = await graph.ainvoke(
            {
                "user_query": "Find DIAMM manuscripts",
                "repair_count": 0,
                "max_repairs": 3,
            }
        )

    assert final["repair_count"] == 1
    assert final["confidence"] == "high"
    assert final["is_valid"] is True


async def test_max_repairs_exceeded():
    """
    Always-invalid SPARQL: with max_repairs=1 the graph generates twice
    (original + 1 repair), then validate sets confidence='low' and exits.
    """
    with (
        patch(
            "app.graph.nodes.intake.get_structured_model",
            return_value=_intake_mock(_DIAMM_LOOKUP),
        ),
        patch(
            "app.graph.nodes.generate.get_chat_model",
            return_value=_generate_mock(_INVALID_SPARQL, _INVALID_SPARQL),
        ),
    ):
        graph = build_graph()
        final = await graph.ainvoke(
            {
                "user_query": "Find DIAMM manuscripts",
                "repair_count": 0,
                "max_repairs": 1,
            }
        )

    assert final["confidence"] == "low"
    assert final["is_valid"] is False


async def test_execution_error_triggers_repair():
    """
    Execution error on first Virtuoso call routes back to generate.
    Second generate + second execute succeed → confidence='high', repair_count=1.
    """
    with (
        patch(
            "app.graph.nodes.intake.get_structured_model",
            return_value=_intake_mock(_DIAMM_LOOKUP),
        ),
        patch(
            "app.graph.nodes.generate.get_chat_model",
            return_value=_generate_mock(_VALID_SPARQL, _VALID_SPARQL),
        ),
        patch(
            "app.graph.nodes.judge.settings",
            new=_answer_settings(semantic_judge_enabled=False),
        ),
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new_callable=AsyncMock,
            side_effect=[_VIRTUOSO_ERROR, _VIRTUOSO_SUCCESS],
        ),
    ):
        graph = build_graph()
        final = await graph.ainvoke(
            {
                "user_query": "Find DIAMM manuscripts",
                "repair_count": 0,
                "max_repairs": 3,
            }
        )

    assert final["repair_count"] == 1
    assert final["execution_error"] is None
    assert final["confidence"] == "high"


async def test_structural_intent_check_triggers_repair():
    """
    aggregation intent + SPARQL without COUNT fails validate_intent.
    Repair produces SPARQL with COUNT → validate passes → confidence='high'.
    """
    with (
        patch(
            "app.graph.nodes.intake.get_structured_model",
            return_value=_intake_mock(_DIAMM_AGGREGATION),
        ),
        patch(
            "app.graph.nodes.generate.get_chat_model",
            # First: valid syntax but no COUNT (fails structural intent check)
            # Second: valid SPARQL with COUNT (passes both checks)
            return_value=_generate_mock(_VALID_SPARQL, _VALID_SPARQL_WITH_COUNT),
        ),
        patch(
            "app.graph.nodes.judge.settings",
            new=_answer_settings(semantic_judge_enabled=False),
        ),
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new_callable=AsyncMock,
            return_value=_VIRTUOSO_SUCCESS,
        ),
    ):
        graph = build_graph()
        final = await graph.ainvoke(
            {
                "user_query": "How many DIAMM manuscripts are there?",
                "repair_count": 0,
                "max_repairs": 3,
            }
        )

    assert final["repair_count"] == 1
    assert final["is_valid"] is True
    assert final["confidence"] == "high"
    assert "COUNT" in final["sparql"]


async def test_semantic_judge_triggers_repair_then_satisfied():
    """
    Semantic judge enabled: first judge unsatisfied → repair → second judge satisfied.
    Final repair_count=1, confidence='high', judge_feedback cleared.
    """
    with (
        patch(
            "app.graph.nodes.intake.get_structured_model",
            return_value=_intake_mock(_DIAMM_LOOKUP),
        ),
        patch(
            "app.graph.nodes.generate.get_chat_model",
            return_value=_generate_mock(_VALID_SPARQL, _VALID_SPARQL),
        ),
        patch(
            "app.graph.nodes.judge.get_structured_model",
            return_value=_judge_mock(
                (False, "Results don't cover the requested date range"),
                (True, "Results now correctly cover the date range"),
            ),
        ),
        patch(
            "app.graph.nodes.judge.settings",
            new=_answer_settings(semantic_judge_enabled=True),
        ),
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new_callable=AsyncMock,
            return_value=_VIRTUOSO_SUCCESS,
        ),
    ):
        graph = build_graph()
        final = await graph.ainvoke(
            {
                "user_query": "Find DIAMM manuscripts from the 15th century",
                "repair_count": 0,
                "max_repairs": 3,
            }
        )

    assert final["repair_count"] == 1
    assert final["confidence"] == "high"
    assert final.get("judge_feedback") is None
