import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.tools.wikidata import _parse_mcp_response, wikidata_qid_lookup


def _make_text_block(text: str):
    block = MagicMock()
    block.text = text
    return block


def _make_search_tool(return_value):
    tool = MagicMock()
    tool.ainvoke = AsyncMock(return_value=return_value)
    return tool


# ---------------------------------------------------------------------------
# _parse_mcp_response unit tests
# ---------------------------------------------------------------------------


def test_parse_json_list_response():
    items = [
        {"id": "Q1339", "label": "Johann Sebastian Bach", "description": "German composer"},
        {"id": "Q57233", "label": "Bach (crater)", "description": "crater on Mercury"},
    ]
    blocks = [_make_text_block(json.dumps(items))]
    result = _parse_mcp_response(blocks)
    assert result == [
        {"qid": "Q1339", "label": "Johann Sebastian Bach", "description": "German composer"},
        {"qid": "Q57233", "label": "Bach (crater)", "description": "crater on Mercury"},
    ]


def test_parse_json_wrapped_search_key():
    data = {
        "search": [
            {"id": "Q26876", "label": "Taylor Swift", "description": "American singer-songwriter"},
        ]
    }
    blocks = [_make_text_block(json.dumps(data))]
    result = _parse_mcp_response(blocks)
    assert result[0]["qid"] == "Q26876"


def test_parse_concepturi_fallback():
    items = [{"concepturi": "http://www.wikidata.org/entity/Q42", "label": "Douglas Adams", "description": ""}]
    blocks = [_make_text_block(json.dumps(items))]
    result = _parse_mcp_response(blocks)
    assert result[0]["qid"] == "Q42"


def test_parse_plain_text_qid_regex():
    text = "Q1339: Johann Sebastian Bach — German composer (1685-1750)\nQ57233: Bach (crater) — crater on Mercury"
    result = _parse_mcp_response([_make_text_block(text)])
    assert result[0] == {"qid": "Q1339", "label": "Johann Sebastian Bach", "description": "German composer (1685-1750)"}
    assert result[1] == {"qid": "Q57233", "label": "Bach (crater)", "description": "crater on Mercury"}


def test_parse_empty_blocks_returns_empty():
    assert _parse_mcp_response([]) == []


def test_parse_block_with_no_text_skipped():
    block = MagicMock()
    block.text = None
    assert _parse_mcp_response([block]) == []


def test_parse_content_attribute_unwrapped():
    items = [{"id": "Q1339", "label": "Bach", "description": ""}]
    wrapper = MagicMock()
    wrapper.content = [_make_text_block(json.dumps(items))]
    result = _parse_mcp_response(wrapper)
    assert result[0]["qid"] == "Q1339"


# ---------------------------------------------------------------------------
# wikidata_qid_lookup integration tests (MCP tool mocked)
# ---------------------------------------------------------------------------


async def test_successful_search_returns_parsed_results():
    items = [
        {"id": "Q1339", "label": "Johann Sebastian Bach", "description": "German composer"},
    ]
    fake_tool = _make_search_tool([_make_text_block(json.dumps(items))])

    with patch("app.graph.tools.wikidata._get_search_tool", AsyncMock(return_value=fake_tool)):
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Bach"})

    assert result == [{"qid": "Q1339", "label": "Johann Sebastian Bach", "description": "German composer"}]


async def test_context_is_appended_to_query():
    fake_tool = _make_search_tool([_make_text_block("[]")])

    with patch("app.graph.tools.wikidata._get_search_tool", AsyncMock(return_value=fake_tool)):
        await wikidata_qid_lookup.ainvoke({"entity_name": "Bach", "context": "Find works in RISM"})

    call_args = fake_tool.ainvoke.call_args
    query = call_args[0][0]["query"]
    assert "Bach" in query
    assert "Find works in RISM" in query


async def test_mcp_error_returns_empty_list():
    fake_tool = MagicMock()
    fake_tool.ainvoke = AsyncMock(side_effect=Exception("MCP server unavailable"))

    with patch("app.graph.tools.wikidata._get_search_tool", AsyncMock(return_value=fake_tool)):
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Bach"})

    assert result == []


async def test_empty_results_returns_empty_list():
    fake_tool = _make_search_tool([_make_text_block("[]")])

    with patch("app.graph.tools.wikidata._get_search_tool", AsyncMock(return_value=fake_tool)):
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "zzznomatchxyz"})

    assert result == []


async def test_malformed_mcp_response_handled_gracefully():
    fake_tool = _make_search_tool([_make_text_block("not valid json {{")])

    with patch("app.graph.tools.wikidata._get_search_tool", AsyncMock(return_value=fake_tool)):
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Bach"})

    # Should not raise; may return empty or regex-matched items
    assert isinstance(result, list)


async def test_get_search_tool_failure_returns_empty_list():
    with patch(
        "app.graph.tools.wikidata._get_search_tool",
        AsyncMock(side_effect=Exception("connection refused")),
    ):
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Bach"})

    assert result == []
