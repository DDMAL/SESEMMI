"""Unit tests for the conversational clarification step."""

from unittest.mock import AsyncMock, patch

from app.graph.clarify import ClarifyQuestion, ClarifyResult, clarify_query
from app.main import ClarifyRequest, clarify


def _mock_chain(result: ClarifyResult):
    """Return a mock structured chain (what get_structured_model returns) yielding ``result``."""
    chain = AsyncMock()
    chain.ainvoke.return_value = result
    return chain


# ---------------------------------------------------------------------------
# clarify_query
# ---------------------------------------------------------------------------


async def test_ambiguous_query_returns_questions():
    """A vague query yields ready=False with follow-up questions."""
    llm_result = ClarifyResult(
        ready=False,
        questions=[
            ClarifyQuestion(question="Which database?", options=["DIAMM", "RISM"]),
            ClarifyQuestion(question="Which composer?", options=[]),
        ],
        enriched_query="songs by Bach (database and composer unclear)",
    )
    chain = _mock_chain(llm_result)

    with patch("app.graph.clarify.get_structured_model", return_value=chain):
        result = await clarify_query("songs by Bach", [])

    assert result.ready is False
    assert len(result.questions) == 2
    assert result.questions[0].options == ["DIAMM", "RISM"]


async def test_ready_query_clears_questions_and_enriches():
    """A specific query (with answers) is ready and has a non-empty enriched query."""
    llm_result = ClarifyResult(
        ready=True,
        questions=[ClarifyQuestion(question="stale", options=[])],
        enriched_query="Find all chants in Cantus DB composed by J.S. Bach",
    )
    chain = _mock_chain(llm_result)
    history = [{"question": "Which database?", "answer": "Cantus DB"}]

    with patch("app.graph.clarify.get_structured_model", return_value=chain):
        result = await clarify_query("songs by Bach", history)

    assert result.ready is True
    # ready=True must clear any questions the model returned
    assert result.questions == []
    assert result.enriched_query.strip()


async def test_questions_capped_to_max(monkeypatch):
    """More questions than the configured max are truncated."""
    monkeypatch.setattr(
        "app.graph.clarify.settings.clarification_max_questions", 2, raising=False
    )
    llm_result = ClarifyResult(
        ready=False,
        questions=[ClarifyQuestion(question=f"q{i}", options=[]) for i in range(5)],
        enriched_query="still ambiguous",
    )
    chain = _mock_chain(llm_result)

    with patch("app.graph.clarify.get_structured_model", return_value=chain):
        result = await clarify_query("vague", [])

    assert len(result.questions) == 2


async def test_empty_enriched_query_falls_back_to_original():
    """A blank enriched_query is replaced with the original query."""
    llm_result = ClarifyResult(ready=True, questions=[], enriched_query="   ")
    chain = _mock_chain(llm_result)

    with patch("app.graph.clarify.get_structured_model", return_value=chain):
        result = await clarify_query("my original query", [])

    assert result.enriched_query == "my original query"


async def test_llm_failure_passes_query_through():
    """If the LLM call raises, clarify_query degrades to ready pass-through."""
    chain = AsyncMock()
    chain.ainvoke.side_effect = RuntimeError("LLM down")

    with patch("app.graph.clarify.get_structured_model", return_value=chain):
        result = await clarify_query("anything", [])

    assert result.ready is True
    assert result.questions == []
    assert result.enriched_query == "anything"


# ---------------------------------------------------------------------------
# /clarify endpoint feature flag
# ---------------------------------------------------------------------------


async def test_endpoint_passthrough_when_flag_disabled():
    """With clarification disabled, the endpoint returns ready without calling the LLM."""
    with patch("app.main.settings") as mock_settings:
        mock_settings.clarification_enabled = False
        with patch("app.main.clarify_query") as mock_clarify:
            result = await clarify(ClarifyRequest(query="hello", history=[]))

    assert result.ready is True
    assert result.enriched_query == "hello"
    mock_clarify.assert_not_called()
