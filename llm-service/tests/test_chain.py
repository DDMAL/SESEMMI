from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.llm.chain import clean_sparql, translate_to_sparql

from app.config import settings


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
    # No SPARQL keywords — falls back to full stripped text
    assert clean_sparql(text) == text


async def test_translate_to_sparql_with_rag_examples():
    fake_llm = FakeListChatModel(responses=["SELECT ?x WHERE { }"])
    examples = [{"nl": "Find songs", "sparql": "SELECT ?s WHERE { }"}]

    with patch("app.llm.chain.ChatGoogleGenerativeAI", return_value=fake_llm):
        result = await translate_to_sparql("test query", rag_examples=examples)

    assert result["sparql"] == "SELECT ?x WHERE { }"
    # FakeListChatModel has no usage_metadata, so token counts will be 0
    assert result["usage"]["inputTokens"] == 0
    assert isinstance(result["durationMs"], int)


async def test_translate_to_sparql_returns_structure():
    fake_llm = FakeListChatModel(responses=["SELECT ?y WHERE { }"])

    with patch("app.llm.chain.ChatGoogleGenerativeAI", return_value=fake_llm):
        result = await translate_to_sparql("how many songs", rag_examples=[])

    assert "sparql" in result
    assert "usage" in result
    assert "durationMs" in result
    assert {"inputTokens", "outputTokens", "totalTokens"} == set(result["usage"])
