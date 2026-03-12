"""Per-node unit tests for the LangGraph StateGraph nodes."""

from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from app.graph.nodes.answer import answer_node
from app.graph.nodes.execute import execute_node
from app.graph.nodes.generate import generate_node
from app.graph.nodes.intake import IntakeClassification, intake_node
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
# Intake node
# ---------------------------------------------------------------------------


async def test_intake_single_graph():
    """Single-database query classifies with correct intent and target_graphs."""
    classification = IntakeClassification(
        intent="lookup",
        target_graphs=["diamm"],
        mentions_entities=False,
        needs_federation=False,
    )
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = classification
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value = mock_chain

    with patch(
        "app.graph.nodes.intake.ChatGoogleGenerativeAI", return_value=mock_model
    ):
        result = await intake_node({"user_query": "Find DIAMM manuscripts from 1400"})

    assert result["intent"] == "lookup"
    assert result["target_graphs"] == ["diamm"]
    assert result["mentions_entities"] is False
    assert result["needs_federation"] is False


async def test_intake_cross_graph():
    """Cross-database query sets cross_graph intent and multiple target_graphs."""
    classification = IntakeClassification(
        intent="cross_graph",
        target_graphs=["diamm", "musicbrainz"],
        mentions_entities=True,
        needs_federation=True,
    )
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = classification
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value = mock_chain

    with patch(
        "app.graph.nodes.intake.ChatGoogleGenerativeAI", return_value=mock_model
    ):
        result = await intake_node(
            {"user_query": "Compare DIAMM composers with MusicBrainz artists"}
        )

    assert result["intent"] == "cross_graph"
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
        "mentions_entities": False,
        "needs_federation": False,
    }
    result = await retrieve_node(state)

    sc = result["schema_context"]
    assert "diamm" in sc.lower()
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
        "mentions_entities": False,
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
        "mentions_entities": False,
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


async def test_retrieve_abbrev_entity_resolved():
    """Single-word ALL-CAPS abbreviation like 'NYC' is captured and resolved."""
    state = {
        "user_query": "Find jazz solos from NYC",
        "target_graphs": ["digthatlick"],
        "mentions_entities": True,
        "needs_federation": False,
    }
    mock_result = [{"qid": "Q60", "label": "New York City"}]

    with patch("app.graph.nodes.retrieve.wikidata_qid_lookup") as mock_tool:
        mock_tool.ainvoke = AsyncMock(return_value=mock_result)
        result = await retrieve_node(state)

    assert result["resolved_qids"].get("NYC") == "Q60"


async def test_retrieve_filtered_rag_called():
    """When rag_enabled, vector store is queried and results are filtered by target_graphs."""
    state = {
        "user_query": "Find Irish tunes",
        "target_graphs": ["thesession"],
        "mentions_entities": False,
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
    """Return (mock_chat_cls_instance, mock_model) ready for generate_node patching.

    mock_chat  — returned by ChatGoogleGenerativeAI(); used directly when mentions_entities=False
    mock_model — returned by mock_chat.bind_tools(); used when mentions_entities=True
    Both have async ainvoke so either code path works.
    """
    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = AIMessage(content=sparql_response)
    mock_chat = MagicMock()
    mock_chat.bind_tools.return_value = mock_model
    # Also make the base model awaitable for the mentions_entities=False path
    mock_chat.ainvoke = AsyncMock(return_value=AIMessage(content=sparql_response))
    return mock_chat, mock_model


async def test_generate_produces_sparql():
    """Fresh state (repair_count=0) produces cleaned SPARQL output."""
    sparql = (
        "SELECT ?x WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> "
        "{ ?x a ?y } } LIMIT 10"
    )
    mock_chat, _ = _mock_generate_llm(sparql)
    state = {
        "user_query": "Find all manuscripts",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 0,
        "mentions_entities": True,
    }

    with patch(
        "app.graph.nodes.generate.ChatGoogleGenerativeAI", return_value=mock_chat
    ):
        result = await generate_node(state)

    assert result["sparql"]
    assert "SELECT" in result["sparql"]
    assert result["repair_count"] == 0


async def test_generate_prompt_has_output_rules():
    """Generated prompt contains output rules; QID tool instruction only when mentions_entities=True."""
    sparql = "SELECT ?x WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> { ?x a ?y } } LIMIT 10"
    mock_chat, mock_model = _mock_generate_llm(sparql)
    state = {
        "user_query": "Find solos from NYC",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 0,
        "mentions_entities": True,
    }

    with patch(
        "app.graph.nodes.generate.ChatGoogleGenerativeAI", return_value=mock_chat
    ):
        await generate_node(state)

    messages = mock_model.ainvoke.call_args[0][0]
    prompt_text = messages[0].content
    assert "OUTPUT RULES" in prompt_text
    assert "wikidata_qid_lookup" in prompt_text
    assert "Never ask the user" in prompt_text


async def test_generate_no_qid_tool_when_no_entities():
    """When mentions_entities=False, QID tool is not bound and prompt omits the tool instruction."""
    sparql = "SELECT ?s WHERE { GRAPH <https://linkedmusic.ca/graphs/thesession/> { ?s a ?t } } LIMIT 10"
    mock_chat, _ = _mock_generate_llm(sparql)
    state = {
        "user_query": "find all sessions that took place in 2015",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 0,
        "mentions_entities": False,
    }

    with patch(
        "app.graph.nodes.generate.ChatGoogleGenerativeAI", return_value=mock_chat
    ):
        await generate_node(state)

    # bind_tools should NOT have been called
    mock_chat.bind_tools.assert_not_called()
    # The base model's ainvoke was called directly
    messages = mock_chat.ainvoke.call_args[0][0]
    prompt_text = messages[0].content
    assert "OUTPUT RULES" in prompt_text
    assert "wikidata_qid_lookup" not in prompt_text


async def test_generate_tool_loop_exhaustion_forces_final_call():
    """When model returns tool_calls on all _MAX_TOOL_ITERATIONS, a final generation is forced."""
    good_sparql = "SELECT ?s WHERE { GRAPH <https://linkedmusic.ca/graphs/thesession/> { ?s a ?t } } LIMIT 10"

    # First _MAX_TOOL_ITERATIONS responses all have tool_calls; the final forced call returns SPARQL.
    tool_response = AIMessage(
        content="",
        tool_calls=[{"name": "wikidata_qid_lookup", "args": {"entity_name": "Ireland"}, "id": "call_1"}],
    )
    final_response = AIMessage(content=good_sparql)

    mock_model = AsyncMock()
    # Return tool_response 3 times, then good SPARQL on the 4th (forced) call
    mock_model.ainvoke.side_effect = [tool_response, tool_response, tool_response, final_response]

    mock_chat = MagicMock()
    mock_chat.bind_tools.return_value = mock_model

    state = {
        "user_query": "find sessions in Ireland in 2015",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 0,
        "mentions_entities": True,
    }

    with patch("app.graph.nodes.generate.ChatGoogleGenerativeAI", return_value=mock_chat):
        with patch("app.graph.nodes.generate.wikidata_qid_lookup") as mock_tool:
            mock_tool.ainvoke = AsyncMock(return_value=[{"qid": "Q27", "label": "Ireland"}])
            result = await generate_node(state)

    assert result["sparql"]
    assert "SELECT" in result["sparql"]
    # Total calls: 3 loop iterations + 1 forced final = 4
    assert mock_model.ainvoke.call_count == 4


async def test_generate_repair_context_injected():
    """Validation errors cause repair context and incremented repair_count."""
    sparql = (
        "SELECT ?x WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> "
        "{ ?x a ?y } } LIMIT 10"
    )
    mock_chat, mock_model = _mock_generate_llm(sparql)
    state = {
        "user_query": "Find manuscripts",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 0,
        "mentions_entities": True,
        "sparql": "SELECT ?x WHERE { ?x a ?y }",
        "validation_errors": ["Missing LIMIT clause"],
        "execution_error": None,
        "judge_feedback": None,
    }

    with patch(
        "app.graph.nodes.generate.ChatGoogleGenerativeAI", return_value=mock_chat
    ):
        result = await generate_node(state)

    # Inspect the messages passed to ainvoke
    messages = mock_model.ainvoke.call_args[0][0]
    prompt_text = messages[0].content
    assert "REPAIR ATTEMPT" in prompt_text
    assert "Missing LIMIT clause" in prompt_text
    assert result["repair_count"] == 1


async def test_generate_judge_feedback_in_repair_context():
    """Judge feedback from a prior iteration appears in the repair prompt."""
    sparql = (
        "SELECT ?x WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> "
        "{ ?x a ?y } } LIMIT 10"
    )
    mock_chat, mock_model = _mock_generate_llm(sparql)
    state = {
        "user_query": "Find manuscripts",
        "schema_context": "ontology context",
        "few_shot_examples": "",
        "resolved_qids": {},
        "repair_count": 1,
        "mentions_entities": True,
        "sparql": "SELECT ?x WHERE { ?x a ?y } LIMIT 10",
        "validation_errors": [],
        "execution_error": None,
        "judge_feedback": "Results don't match the requested time period",
    }

    with patch(
        "app.graph.nodes.generate.ChatGoogleGenerativeAI", return_value=mock_chat
    ):
        result = await generate_node(state)

    messages = mock_model.ainvoke.call_args[0][0]
    prompt_text = messages[0].content
    assert "Results don't match the requested time period" in prompt_text
    assert "Semantic feedback" in prompt_text
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
        "mentions_entities": False,
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
        "mentions_entities": False,
        "needs_federation": False,
    }
    result = await validate_node(state)

    assert result["is_valid"] is False
    assert len(result["validation_errors"]) > 0


async def test_validate_aggregation_missing_count():
    """aggregation intent without COUNT/SUM/AVG/GROUP BY → is_valid=False."""
    state = {
        "sparql": _VALID_SPARQL,
        "intent": "aggregation",
        "target_graphs": ["diamm"],
        "mentions_entities": False,
        "needs_federation": False,
    }
    result = await validate_node(state)

    assert result["is_valid"] is False
    assert any(
        kw in e
        for e in result["validation_errors"]
        for kw in ("COUNT", "SUM", "AVG", "GROUP BY", "aggregation")
    )


async def test_validate_cross_graph_single_graph():
    """cross_graph intent with only 1 GRAPH IRI → is_valid=False."""
    state = {
        "sparql": _VALID_SPARQL,
        "intent": "cross_graph",
        "target_graphs": ["diamm"],
        "mentions_entities": False,
        "needs_federation": False,
    }
    result = await validate_node(state)

    assert result["is_valid"] is False
    assert any(
        "graph" in e.lower() or "cross" in e.lower() or "2" in e
        for e in result["validation_errors"]
    )


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
    with patch("app.graph.nodes.answer.settings") as mock_settings:
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
    with patch("app.graph.nodes.answer.settings") as mock_settings:
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

    with patch("app.graph.nodes.answer.settings") as mock_settings:
        mock_settings.semantic_judge_enabled = True
        mock_settings.llm_model = "gemini-2.5-flash-lite"
        mock_settings.llm_api_key = "test-key"
        mock_settings.max_repair_iterations = 3
        with patch(
            "app.graph.nodes.answer.ChatGoogleGenerativeAI", return_value=mock_chat
        ):
            result = await answer_node(state)

    assert result["confidence"] == "high"
    assert result.get("judge_feedback") is None


async def test_answer_judge_unsatisfied_repairs_left():
    """Judge unsatisfied + repairs remaining → judge_feedback set to trigger re-generation."""
    mock_chat, _ = _mock_judge_llm(satisfied=False, reason="Missing time filter")
    state = {**_JUDGE_STATE, "repair_count": 0, "max_repairs": 3}

    with patch("app.graph.nodes.answer.settings") as mock_settings:
        mock_settings.semantic_judge_enabled = True
        mock_settings.llm_model = "gemini-2.5-flash-lite"
        mock_settings.llm_api_key = "test-key"
        mock_settings.max_repair_iterations = 3
        with patch(
            "app.graph.nodes.answer.ChatGoogleGenerativeAI", return_value=mock_chat
        ):
            result = await answer_node(state)

    assert result["judge_feedback"] == "Missing time filter"


async def test_answer_judge_unsatisfied_exhausted():
    """Judge unsatisfied + repairs exhausted → confidence=low, reason in assumptions."""
    mock_chat, _ = _mock_judge_llm(satisfied=False, reason="Still wrong")
    state = {**_JUDGE_STATE, "repair_count": 3, "max_repairs": 3}

    with patch("app.graph.nodes.answer.settings") as mock_settings:
        mock_settings.semantic_judge_enabled = True
        mock_settings.llm_model = "gemini-2.5-flash-lite"
        mock_settings.llm_api_key = "test-key"
        mock_settings.max_repair_iterations = 3
        with patch(
            "app.graph.nodes.answer.ChatGoogleGenerativeAI", return_value=mock_chat
        ):
            result = await answer_node(state)

    assert result["confidence"] == "low"
    assert result.get("judge_feedback") is None
    assert any("Still wrong" in a for a in result.get("assumptions", []))
