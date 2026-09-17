"""Integration tests for query execution, assessment, and bounded repair."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.graph.builder import build_graph
from app.graph.nodes.intake import IntakeClassification
from app.graph.nodes.judge import _JudgeVerdict

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

_VIRTUOSO_EMPTY = {
    "results": {"results": {"bindings": []}},
    "error": None,
}

# ---------------------------------------------------------------------------
# Pre-built intake classifications
# ---------------------------------------------------------------------------

_DIAMM_LOOKUP = IntakeClassification(
    intents=["lookup"],
    target_graphs=["diamm"],
    needs_federation=False,
    entity_contexts={},
)

_DIAMM_AGGREGATION = IntakeClassification(
    intents=["aggregation"],
    target_graphs=["diamm"],
    needs_federation=False,
    entity_contexts={},
)

# ---------------------------------------------------------------------------
# Mock factory helpers
# ---------------------------------------------------------------------------


def _intake_mock(classification: IntakeClassification) -> AsyncMock:
    """get_structured_model mock for intake_node (returns the structured chain)."""
    chain = AsyncMock()
    chain.ainvoke.return_value = classification
    return chain


def _generate_mock(*sparql_responses: str) -> AsyncMock:
    model = AsyncMock()
    model.ainvoke.side_effect = [AIMessage(content=s) for s in sparql_responses]
    return model


def _judge_mock(*verdicts: tuple[bool, str]) -> AsyncMock:
    model = AsyncMock()
    model.ainvoke.side_effect = [
        _JudgeVerdict(satisfied=satisfied, reason=reason)
        for satisfied, reason in verdicts
    ]
    return model


def _judge_settings(*, semantic_judge_enabled: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        semantic_judge_enabled=semantic_judge_enabled,
        empty_probe_enabled=False,
        max_repair_iterations=3,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_happy_path():
    """
    Full graph: intake → retrieve → generate → validate → execute → judge.
    Valid SPARQL + Virtuoso 200 without a judge → confidence='medium', results populated, no repairs.
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
            new=_judge_settings(semantic_judge_enabled=False),
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

    assert final["confidence"] == "medium"
    assert final["result_count"] == 2
    assert final["results"] is not None
    assert final["execution_error"] is None
    assert final["repair_count"] == 0


async def test_repair_loop_invalid_then_valid():
    """
    Repair loop: first generate returns invalid SPARQL (rdflib rejects it),
    second generate returns valid SPARQL.
    Final repair_count=1, confidence='medium' without semantic assessment.
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
            new=_judge_settings(semantic_judge_enabled=False),
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
    assert final["confidence"] == "medium"
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


@pytest.mark.parametrize("error", ["Virtuoso SPARQL syntax error", ""])
async def test_execution_error_triggers_repair(error: str) -> None:
    """
    Execution error on first Virtuoso call routes back to generate.
    Second generate + second execute succeed → confidence='medium', repair_count=1.
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
            new=_judge_settings(semantic_judge_enabled=False),
        ),
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new_callable=AsyncMock,
            side_effect=[{"results": None, "error": error}, _VIRTUOSO_SUCCESS],
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
    assert final["confidence"] == "medium"


async def test_structural_intent_check_triggers_repair():
    """
    aggregation intent + SPARQL without COUNT fails validate_intent.
    Repair produces SPARQL with COUNT → validate passes → confidence='medium'.
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
            new=_judge_settings(semantic_judge_enabled=False),
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
    assert final["confidence"] == "medium"
    assert "COUNT" in final["sparql"]


async def test_semantic_judge_triggers_repair_then_satisfied():
    """
    Semantic judge enabled: an empty first result makes the judge unsatisfied → repair → the
    second result has rows and the judge is satisfied. Final repair_count=1, confidence='high',
    judge_feedback cleared. Nonempty rejected results keep a caveat without another repair.
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
            new=_judge_settings(semantic_judge_enabled=True),
        ),
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new=AsyncMock(side_effect=[_VIRTUOSO_EMPTY, _VIRTUOSO_SUCCESS]),
        ),
    ):
        graph = build_graph()
        final = await graph.ainvoke(
            {
                "user_query": "Find DIAMM manuscripts from the 15th century",
                "repair_count": 0,
                "max_repairs": 3,
                "assumptions": ["A previous query used the wrong date range."],
            }
        )

    assert final["repair_count"] == 1
    assert final["confidence"] == "high"
    assert final.get("judge_feedback") is None
    assert "A previous query used the wrong date range." not in final["assumptions"]


@pytest.mark.parametrize("error", ["Wikidata HTTP 429", ""])
async def test_external_outage_preserves_required_filter_without_retry(
    error: str,
) -> None:
    sparql = (
        "SELECT ?person WHERE { "
        "GRAPH <https://linkedmusic.ca/graphs/diamm/> { "
        "?person a diamm:Person ; wdt:P2888 ?qid } "
        "SERVICE <https://query.wikidata.org/sparql> { ?qid wdt:P19 wd:Q1748 } "
        "} LIMIT 10"
    )
    generator = _generate_mock(sparql)
    with (
        patch(
            "app.graph.nodes.intake.get_structured_model",
            return_value=_intake_mock(_DIAMM_LOOKUP),
        ),
        patch("app.graph.nodes.generate.get_chat_model", return_value=generator),
        patch("app.graph.nodes.judge.get_structured_model") as judge,
        patch("app.graph.nodes.judge.probe_empty_patterns") as probe,
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new=AsyncMock(
                return_value={
                    "results": None,
                    "error": error,
                    "error_kind": "external_service",
                }
            ),
        ) as execute,
    ):
        final = await build_graph().ainvoke(
            {
                "user_query": "Find DIAMM people born in Vienna",
                "repair_count": 0,
                "max_repairs": 3,
            }
        )

    generator.ainvoke.assert_awaited_once()
    execute.assert_awaited_once_with(sparql)
    judge.assert_not_called()
    probe.assert_not_called()
    assert final["sparql"] == sparql
    assert final["repair_count"] == 0
    assert final["execution_error"] == error
    assert final["results"] is None
    assert final["confidence"] == "low"
    assert any("could not be verified" in note for note in final["assumptions"])


@pytest.mark.parametrize("max_repairs", [0, 1, 3])
@pytest.mark.parametrize("reason", ["Missing required date filter", ""])
async def test_semantic_repair_stops_at_budget(max_repairs: int, reason: str) -> None:
    attempts = max_repairs + 1
    generator = _generate_mock(*([_VALID_SPARQL] * attempts))
    judge = _judge_mock(*([(False, reason)] * attempts))
    with (
        patch(
            "app.graph.nodes.intake.get_structured_model",
            return_value=_intake_mock(_DIAMM_LOOKUP),
        ),
        patch("app.graph.nodes.generate.get_chat_model", return_value=generator),
        patch("app.graph.nodes.judge.get_structured_model", return_value=judge),
        patch(
            "app.graph.nodes.judge.settings",
            new=_judge_settings(semantic_judge_enabled=True),
        ),
        patch(
            "app.graph.nodes.execute.execute_sparql",
            new=AsyncMock(return_value=_VIRTUOSO_EMPTY),
        ) as execute,
    ):
        final = await build_graph().ainvoke(
            {
                "user_query": "Find DIAMM manuscripts from the 15th century",
                "repair_count": 0,
                "max_repairs": max_repairs,
            }
        )

    assert generator.ainvoke.await_count == attempts
    assert execute.await_count == attempts
    assert judge.ainvoke.await_count == attempts
    assert final["repair_count"] == max_repairs
    assert final["judge_feedback"] is None
    assert final["confidence"] == "low"
    assert any(
        "may not fully answer" in note and reason in note
        for note in final["assumptions"]
    )
