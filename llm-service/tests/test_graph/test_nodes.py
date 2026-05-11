"""Per-node unit tests for the LangGraph StateGraph nodes."""

from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from app.graph.nodes.execute import execute_node
from app.graph.nodes.generate import clean_sparql, generate_node
from app.graph.nodes.intake import IntakeClassification, intake_node
from app.graph.nodes.judge import judge_node as answer_node
from app.graph.nodes.retrieve import retrieve_node
from app.graph.nodes.validate import validate_node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A valid SELECT query with a GRAPH clause and LIMIT for reuse across tests
_VALID_SPARQL = (
    "PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/> "
    "SELECT ?s ?label WHERE { "
    "GRAPH <https://linkedmusic.ca/graphs/diamm/> { "
    "?s a ?type ; <http://www.w3.org/2000/01/rdf-schema#label> ?label "
    "} } LIMIT 10"
)


# ---------------------------------------------------------------------------
# clean_sparql
# ---------------------------------------------------------------------------


def test_clean_sparql_strips_sparql_fence():
    assert clean_sparql("```sparql\nSELECT ?x WHERE {}\n```") == "SELECT ?x WHERE {}"


def test_clean_sparql_strips_plain_fence():
    assert clean_sparql("```\nSELECT ?x WHERE {}\n```") == "SELECT ?x WHERE {}"


def test_clean_sparql_passthrough():
    sparql = "SELECT ?x WHERE { ?x ?y ?z }"
    assert clean_sparql(sparql) == sparql


def test_clean_sparql_prose_before_query():
    text = "Here is your SPARQL query:\nSELECT ?x WHERE { ?x ?y ?z }"
    assert clean_sparql(text) == "SELECT ?x WHERE { ?x ?y ?z }"


def test_clean_sparql_with_prefix_and_prose():
    text = "Sure! Here is the query:\nPREFIX ex: <http://example.org/>\nSELECT ?x WHERE { ?x a ex:Song }"
    assert (
        clean_sparql(text)
        == "PREFIX ex: <http://example.org/>\nSELECT ?x WHERE { ?x a ex:Song }"
    )


def test_clean_sparql_non_sparql_code_fence_ignored():
    text = '```json\n{"key": "value"}\n```'
    assert clean_sparql(text) == text


# ---------------------------------------------------------------------------
# Intake node
# ---------------------------------------------------------------------------


async def test_intake_single_graph():
    """Single-database query classifies with correct intent and target_graphs."""
    classification = IntakeClassification(
        intents=["lookup"],
        target_graphs=["diamm"],
        needs_federation=False,
        entity_contexts=[],
    )
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = classification
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value = mock_chain

    with patch("app.graph.nodes.intake.get_chat_model", return_value=mock_model):
        result = await intake_node({"user_query": "Find DIAMM manuscripts from 1400"})

    assert result["intents"] == ["lookup"]
    assert result["target_graphs"] == ["diamm"]
    assert result["needs_federation"] is False


async def test_intake_cross_graph():
    """Cross-database query sets multiple target_graphs."""
    classification = IntakeClassification(
        intents=["lookup"],
        target_graphs=["diamm", "musicbrainz"],
        needs_federation=True,
        entity_contexts=[],
    )
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = classification
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value = mock_chain

    with patch("app.graph.nodes.intake.get_chat_model", return_value=mock_model):
        result = await intake_node(
            {"user_query": "Compare DIAMM composers with MusicBrainz artists"}
        )

    assert "lookup" in result["intents"]
    assert "diamm" in result["target_graphs"]
    assert "musicbrainz" in result["target_graphs"]
    assert result["needs_federation"] is True


# ---------------------------------------------------------------------------
# Retrieve node
# ---------------------------------------------------------------------------


async def test_retrieve_ontology_selection():
    """Schema context contains target database ontology and base instruction rules."""
    state = {
        "user_query": "Find all DIAMM manuscripts",
        "target_graphs": ["diamm"],
        "entity_contexts": {},
        "needs_federation": False,
    }
    result = await retrieve_node(state)

    sc = result["schema_context"]
    # named_graph_rules always included — contains GRAPH keyword guidance
    assert "GRAPH" in sc
    # No examples or QIDs when both disabled and no entities
    assert result["few_shot_examples"] == ""
    assert result["resolved_qids"] == {}


async def test_retrieve_federation_rules_included():
    """Federated query rules and musicbrainz-specific rules appear for multi-graph queries."""
    state = {
        "user_query": "Compare composers across databases",
        "target_graphs": ["diamm", "musicbrainz"],
        "entity_contexts": {},
        "needs_federation": True,
    }
    result = await retrieve_node(state)

    sc = result["schema_context"]
    # federated_query_rules contains SERVICE keyword guidance
    assert "SERVICE" in sc
    # musicbrainz_specific rules are included
    assert "mb:Work" in sc or "mb:" in sc


async def test_retrieve_deduplicates_identical_docs():
    """Identical page_content in similarity_search results is collapsed to one entry."""
    state = {
        "user_query": "Find Irish tunes",
        "target_graphs": ["thesession"],
        "entity_contexts": {},
        "needs_federation": False,
    }
    dup_doc = MagicMock()
    dup_doc.page_content = "Find all tunes"
    dup_doc.metadata = {
        "sparql": "SELECT ?t WHERE { GRAPH <ts:> { ?t a ?x } } LIMIT 5",
        "databases": ["thesession"],
    }
    unique_doc = MagicMock()
    unique_doc.page_content = "Find tunes by name"
    unique_doc.metadata = {
        "sparql": "SELECT ?t WHERE { GRAPH <ts:> { ?t rdfs:label ?n } } LIMIT 5",
        "databases": ["thesession"],
    }
    mock_store = MagicMock()
    # Return the same doc twice plus one unique doc
    mock_store.similarity_search.return_value = [dup_doc, dup_doc, unique_doc]

    with patch("app.graph.nodes.retrieve.settings") as mock_settings:
        mock_settings.rag_enabled = True
        mock_settings.few_shot_enabled = False
        mock_settings.rag_top_k = 5
        with patch("app.rag.store.get_vector_store", return_value=mock_store):
            result = await retrieve_node(state)

    # The formatted examples string should contain each unique NL exactly once
    assert result["few_shot_examples"].count("Find all tunes") == 1
    assert result["few_shot_examples"].count("Find tunes by name") == 1


async def test_retrieve_entity_resolved():
    """Extracted entities are resolved to Wikidata QIDs."""
    state = {
        "user_query": "Find jazz solos from NYC",
        "target_graphs": ["digthatlick"],
        "entity_contexts": {"New York City": "city where music was recorded"},
        "needs_federation": False,
    }
    mock_result = [{"qid": "Q60", "label": "New York City"}]

    with patch("app.graph.nodes.retrieve.wikidata_qid_lookup") as mock_tool:
        mock_tool.ainvoke = AsyncMock(return_value=mock_result)
        result = await retrieve_node(state)

    assert result["resolved_qids"].get("New York City") == "Q60"


async def test_retrieve_filtered_rag_called():
    """When rag_enabled, vector store is queried and results are filtered by target_graphs."""
    state = {
        "user_query": "Find Irish tunes",
        "target_graphs": ["thesession"],
        "entity_contexts": {},
        "needs_federation": False,
    }
    mock_doc = MagicMock()
    mock_doc.page_content = "Irish tunes query"
    mock_doc.metadata = {
        "sparql": "SELECT ?t WHERE { GRAPH <ts:> { ?t a ?x } } LIMIT 5",
        "databases": ["thesession"],
    }
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = [mock_doc]

    with patch("app.graph.nodes.retrieve.settings") as mock_settings:
        mock_settings.rag_enabled = True
        mock_settings.few_shot_enabled = False
        mock_settings.rag_top_k = 5
        with patch("app.rag.store.get_vector_store", return_value=mock_store):
            result = await retrieve_node(state)

    mock_store.similarity_search.assert_called_once()
    call_args = mock_store.similarity_search.call_args
    assert call_args[0][0] == "Find Irish tunes"
    assert result["few_shot_examples"]  # at least one example formatted


# ---------------------------------------------------------------------------
# Generate node
# ---------------------------------------------------------------------------


def _mock_generate_llm(sparql_response: str):
    """Return a mock model ready for generate_node patching.

    The mock is returned by get_chat_model() and has async ainvoke.
    """
    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = AIMessage(content=sparql_response)
    return mock_model


async def test_generate_produces_sparql():
    """Fresh state (repair_count=0) produces cleaned SPARQL output."""
    sparql = (
        "SELECT ?x WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> "
        "{ ?x a ?y } } LIMIT 10"
    )
    mock_model = _mock_generate_llm(sparql)
    state = {
        "user_query": "Find all manuscripts",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 0,
        "entity_contexts": {"entity": ""},
    }

    with patch("app.graph.nodes.generate.get_chat_model", return_value=mock_model):
        result = await generate_node(state)

    assert result["sparql"]
    assert "SELECT" in result["sparql"]
    assert result["repair_count"] == 0


async def test_generate_prompt_has_output_rules():
    """Generated prompt contains output rules."""
    sparql = "SELECT ?x WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> { ?x a ?y } } LIMIT 10"
    mock_model = _mock_generate_llm(sparql)
    state = {
        "user_query": "Find solos from NYC",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 0,
        "entity_contexts": {"entity": ""},
    }

    with patch("app.graph.nodes.generate.get_chat_model", return_value=mock_model):
        await generate_node(state)

    messages = mock_model.ainvoke.call_args[0][0]
    prompt_text = messages[0].content
    assert "output_rules" in prompt_text


async def test_generate_repair_context_injected():
    """Validation errors cause repair context and incremented repair_count."""
    sparql = (
        "SELECT ?x WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> "
        "{ ?x a ?y } } LIMIT 10"
    )
    mock_model = _mock_generate_llm(sparql)
    state = {
        "user_query": "Find manuscripts",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 0,
        "entity_contexts": {"entity": ""},
        "sparql": "SELECT ?x WHERE { ?x a ?y }",
        "validation_errors": ["Missing LIMIT clause"],
        "execution_error": None,
        "judge_feedback": None,
    }

    with patch("app.graph.nodes.generate.get_chat_model", return_value=mock_model):
        result = await generate_node(state)

    messages = mock_model.ainvoke.call_args[0][0]
    user_text = messages[1].content
    assert "repair" in user_text
    assert "Missing LIMIT clause" in user_text
    assert result["repair_count"] == 1


async def test_generate_judge_feedback_in_repair_context():
    """Judge feedback from a prior iteration appears in the repair prompt."""
    sparql = (
        "SELECT ?x WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> "
        "{ ?x a ?y } } LIMIT 10"
    )
    mock_model = _mock_generate_llm(sparql)
    state = {
        "user_query": "Find manuscripts",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 1,
        "entity_contexts": {"entity": ""},
        "sparql": "SELECT ?x WHERE { ?x a ?y } LIMIT 10",
        "validation_errors": [],
        "execution_error": None,
        "judge_feedback": "Results don't match the requested time period",
    }

    with patch("app.graph.nodes.generate.get_chat_model", return_value=mock_model):
        result = await generate_node(state)

    messages = mock_model.ainvoke.call_args[0][0]
    user_text = messages[1].content
    assert "Results don't match the requested time period" in user_text
    assert "semantic_feedback" in user_text
    assert result["repair_count"] == 2


# ---------------------------------------------------------------------------
# Validate node
# ---------------------------------------------------------------------------


async def test_validate_valid_query():
    """Valid SPARQL with GRAPH and LIMIT → is_valid=True."""
    state = {
        "sparql": _VALID_SPARQL,
        "intent": "lookup",
        "target_graphs": ["diamm"],
        "entity_contexts": {},
        "needs_federation": False,
    }
    result = await validate_node(state)

    assert result["is_valid"] is True


async def test_validate_syntax_error():
    """Malformed SPARQL → is_valid=False with non-empty errors."""
    state = {
        "sparql": "SELECT ?x WHERE { ?x a UNCLOSED BRACE",
        "intent": "lookup",
        "target_graphs": [],
        "entity_contexts": {},
        "needs_federation": False,
    }
    result = await validate_node(state)

    assert result["is_valid"] is False
    assert len(result["validation_errors"]) > 0


async def test_validate_aggregation_missing_count():
    """aggregation intent without COUNT/SUM/AVG/GROUP BY → is_valid=False."""
    state = {
        "sparql": _VALID_SPARQL,
        "intents": ["aggregation"],
        "target_graphs": ["diamm"],
        "entity_contexts": {},
        "needs_federation": False,
    }
    result = await validate_node(state)

    assert result["is_valid"] is False
    assert any(
        kw in e
        for e in result["validation_errors"]
        for kw in ("COUNT", "SUM", "AVG", "GROUP BY", "aggregation")
    )


async def test_validate_exhausted_repairs_sets_confidence():
    """Invalid query with repairs exhausted → confidence=low, assumptions collected."""
    state = {
        "sparql": "INVALID SPARQL",
        "intent": "lookup",
        "target_graphs": ["diamm"],
        "entity_contexts": {},
        "needs_federation": False,
        "repair_count": 3,
        "max_repairs": 3,
        "assumptions": [],
        "resolved_qids": {"Charlie Parker": "Q103767"},
    }
    result = await validate_node(state)

    assert result["is_valid"] is False
    assert result["confidence"] == "low"
    assert any("Q103767" in a for a in result["assumptions"])


async def test_validate_repairs_remaining_no_confidence():
    """Invalid query with repairs remaining → no confidence/assumptions set."""
    state = {
        "sparql": "INVALID SPARQL",
        "intent": "lookup",
        "target_graphs": ["diamm"],
        "entity_contexts": {},
        "needs_federation": False,
        "repair_count": 0,
        "max_repairs": 3,
        "assumptions": [],
        "resolved_qids": {"Charlie Parker": "Q103767"},
    }
    result = await validate_node(state)

    assert result["is_valid"] is False
    assert "confidence" not in result


# ---------------------------------------------------------------------------
# Execute node
# ---------------------------------------------------------------------------


async def test_execute_success():
    """Successful Virtuoso response → results populated, result_count correct."""
    bindings = [{"s": {"value": "uri1"}}, {"s": {"value": "uri2"}}]
    mock_response = {"results": {"results": {"bindings": bindings}}, "error": None}

    with patch(
        "app.graph.nodes.execute.execute_sparql", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.return_value = mock_response
        result = await execute_node({"sparql": _VALID_SPARQL})

    mock_exec.assert_called_once_with(_VALID_SPARQL)
    assert result["result_count"] == 2
    assert result["execution_error"] is None
    assert result["results"] is not None


async def test_execute_error():
    """Virtuoso error → execution_error set, results cleared."""
    mock_response = {"results": None, "error": "Virtuoso timeout"}

    with patch(
        "app.graph.nodes.execute.execute_sparql", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.return_value = mock_response
        result = await execute_node({"sparql": _VALID_SPARQL})

    assert result["execution_error"] == "Virtuoso timeout"
    assert result["results"] is None
    assert result["result_count"] == 0


# ---------------------------------------------------------------------------
# Answer node — no semantic judge
# ---------------------------------------------------------------------------

_ANSWER_BASE_STATE = {
    "user_query": "Find manuscripts",
    "sparql": _VALID_SPARQL,
    "resolved_qids": {},
    "assumptions": [],
    "repair_count": 0,
    "max_repairs": 3,
}


async def test_answer_high_confidence():
    """Valid query with results and no error → confidence=high."""
    state = {
        **_ANSWER_BASE_STATE,
        "is_valid": True,
        "execution_error": None,
        "result_count": 3,
        "results": {"results": {"bindings": [{}, {}, {}]}},
    }
    with patch("app.graph.nodes.judge.settings") as mock_settings:
        mock_settings.semantic_judge_enabled = False
        mock_settings.llm_model = "gemini-2.5-flash-lite"
        mock_settings.llm_api_key = "test-key"
        mock_settings.max_repair_iterations = 3
        result = await answer_node(state)

    assert result["confidence"] == "high"


async def test_answer_low_confidence_max_repairs():
    """Invalid query with no remaining repairs → confidence=low."""
    state = {
        **_ANSWER_BASE_STATE,
        "is_valid": False,
        "execution_error": "syntax error",
        "result_count": 0,
        "results": None,
        "repair_count": 3,
    }
    with patch("app.graph.nodes.judge.settings") as mock_settings:
        mock_settings.semantic_judge_enabled = False
        mock_settings.llm_model = "gemini-2.5-flash-lite"
        mock_settings.llm_api_key = "test-key"
        mock_settings.max_repair_iterations = 3
        result = await answer_node(state)

    assert result["confidence"] == "low"


# ---------------------------------------------------------------------------
# Answer node — semantic judge enabled
# ---------------------------------------------------------------------------

_JUDGE_STATE = {
    **_ANSWER_BASE_STATE,
    "is_valid": True,
    "execution_error": None,
    "result_count": 2,
    "results": {"results": {"bindings": [{}, {}]}},
}


def _mock_judge_llm(satisfied: bool, reason: str = "test reason"):
    """Return (mock_chat_cls_instance, mock_judge_chain) for patching in answer_node."""
    verdict = MagicMock()
    verdict.satisfied = satisfied
    verdict.reason = reason
    mock_judge_chain = AsyncMock()
    mock_judge_chain.ainvoke.return_value = verdict
    mock_chat = MagicMock()
    mock_chat.with_structured_output.return_value = mock_judge_chain
    return mock_chat, mock_judge_chain


async def test_answer_judge_satisfied():
    """Judge satisfied=True → confidence=high, judge_feedback cleared."""
    mock_chat, _ = _mock_judge_llm(satisfied=True)
    state = {**_JUDGE_STATE, "repair_count": 0}

    with patch("app.graph.nodes.judge.settings") as mock_settings:
        mock_settings.semantic_judge_enabled = True
        mock_settings.llm_model = "gemini-2.5-flash-lite"
        mock_settings.llm_api_key = "test-key"
        mock_settings.max_repair_iterations = 3
        with patch("app.graph.nodes.judge.get_chat_model", return_value=mock_chat):
            result = await answer_node(state)

    assert result["confidence"] == "high"
    assert result.get("judge_feedback") is None


async def test_answer_judge_unsatisfied_repairs_left():
    """Judge unsatisfied + repairs remaining → judge_feedback set to trigger re-generation."""
    mock_chat, _ = _mock_judge_llm(satisfied=False, reason="Missing time filter")
    state = {**_JUDGE_STATE, "repair_count": 0, "max_repairs": 3}

    with patch("app.graph.nodes.judge.settings") as mock_settings:
        mock_settings.semantic_judge_enabled = True
        mock_settings.llm_model = "gemini-2.5-flash-lite"
        mock_settings.llm_api_key = "test-key"
        mock_settings.max_repair_iterations = 3
        with patch("app.graph.nodes.judge.get_chat_model", return_value=mock_chat):
            result = await answer_node(state)

    assert result["judge_feedback"] == "Missing time filter"


async def test_answer_judge_unsatisfied_exhausted():
    """Judge unsatisfied + repairs exhausted → confidence=low, reason in assumptions."""
    mock_chat, _ = _mock_judge_llm(satisfied=False, reason="Still wrong")
    state = {**_JUDGE_STATE, "repair_count": 3, "max_repairs": 3}

    with patch("app.graph.nodes.judge.settings") as mock_settings:
        mock_settings.semantic_judge_enabled = True
        mock_settings.llm_model = "gemini-2.5-flash-lite"
        mock_settings.llm_api_key = "test-key"
        mock_settings.max_repair_iterations = 3
        with patch("app.graph.nodes.judge.get_chat_model", return_value=mock_chat):
            result = await answer_node(state)

    assert result["confidence"] == "low"
    assert result.get("judge_feedback") is None
    assert any("Still wrong" in a for a in result.get("assumptions", []))
