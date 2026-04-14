from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.tools.wikidata import _parse_mcp_response, wikidata_qid_lookup


def _make_result(text: str):
    """Wrap text in a mock MCP result object with a .content list of text blocks."""
    block = MagicMock()
    block.text = text
    result = MagicMock()
    result.content = [block]
    return result


def _make_result_multi(*texts: str):
    """Wrap multiple text strings as separate blocks in a single MCP result."""
    blocks = []
    for t in texts:
        block = MagicMock()
        block.text = t
        blocks.append(block)
    result = MagicMock()
    result.content = blocks
    return result


# ---------------------------------------------------------------------------
# _parse_mcp_response unit tests
# ---------------------------------------------------------------------------


def test_parse_plain_text_qid_regex():
    result = _make_result(
        "Q1339: Johann Sebastian Bach — German composer (1685-1750)\n"
        "Q57233: Bach (crater) — crater on Mercury"
    )
    items = _parse_mcp_response(result)
    assert items[0] == {
        "qid": "Q1339",
        "label": "Johann Sebastian Bach",
        "description": "German composer (1685-1750)",
    }
    assert items[1] == {
        "qid": "Q57233",
        "label": "Bach (crater)",
        "description": "crater on Mercury",
    }


def test_parse_entry_without_description():
    result = _make_result("Q1339: Johann Sebastian Bach")
    items = _parse_mcp_response(result)
    assert items[0] == {
        "qid": "Q1339",
        "label": "Johann Sebastian Bach",
        "description": "",
    }


def test_parse_empty_content_returns_empty():
    result = MagicMock()
    result.content = []
    assert _parse_mcp_response(result) == []


def test_parse_block_with_no_text_attribute_skipped():
    block = MagicMock(spec=[])  # no .text attribute
    result = MagicMock()
    result.content = [block]
    assert _parse_mcp_response(result) == []


def test_parse_non_qid_lines_skipped():
    result = _make_result(
        "Some random text\nno match here\nQ42: Douglas Adams — author"
    )
    items = _parse_mcp_response(result)
    assert len(items) == 1
    assert items[0]["qid"] == "Q42"


def test_parse_multiple_blocks_combined():
    result = _make_result_multi(
        "Q1339: Bach — composer",
        "Q26876: Taylor Swift — singer",
    )
    items = _parse_mcp_response(result)
    assert len(items) == 2
    assert items[0]["qid"] == "Q1339"
    assert items[1]["qid"] == "Q26876"


# ---------------------------------------------------------------------------
# wikidata_qid_lookup integration tests (MCP client mocked)
# ---------------------------------------------------------------------------


async def test_successful_search_returns_parsed_results():
    raw = _make_result("Q1339: Johann Sebastian Bach — German composer")

    with patch("app.graph.tools.wikidata.MultiServerMCPClient") as mock_client_cls:
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=raw)
        mock_client_cls.return_value.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_client_cls.return_value.session.return_value.__aexit__ = AsyncMock(
            return_value=False
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Bach"})

    assert result == [
        {
            "qid": "Q1339",
            "label": "Johann Sebastian Bach",
            "description": "German composer",
        }
    ]


async def test_context_is_appended_to_query():
    raw = _make_result("")

    with patch("app.graph.tools.wikidata.MultiServerMCPClient") as mock_client_cls:
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=raw)
        mock_client_cls.return_value.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_client_cls.return_value.session.return_value.__aexit__ = AsyncMock(
            return_value=False
        )
        await wikidata_qid_lookup.ainvoke(
            {"entity_name": "Bach", "context": "Find works in RISM"}
        )

    call_args = mock_session.call_tool.call_args
    query = call_args[0][1]["query"]
    assert "Bach" in query
    assert "Find works in RISM" in query


async def test_mcp_error_returns_empty_list():
    with patch("app.graph.tools.wikidata.MultiServerMCPClient") as mock_client_cls:
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(
            side_effect=Exception("MCP server unavailable")
        )
        mock_client_cls.return_value.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_client_cls.return_value.session.return_value.__aexit__ = AsyncMock(
            return_value=False
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Bach"})

    assert result == []


async def test_empty_results_returns_empty_list():
    raw = _make_result("")

    with patch("app.graph.tools.wikidata.MultiServerMCPClient") as mock_client_cls:
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=raw)
        mock_client_cls.return_value.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_client_cls.return_value.session.return_value.__aexit__ = AsyncMock(
            return_value=False
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "zzznomatchxyz"})

    assert result == []


async def test_malformed_text_handled_gracefully():
    raw = _make_result("not valid {{{{ content")

    with patch("app.graph.tools.wikidata.MultiServerMCPClient") as mock_client_cls:
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=raw)
        mock_client_cls.return_value.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_client_cls.return_value.session.return_value.__aexit__ = AsyncMock(
            return_value=False
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Bach"})

    assert isinstance(result, list)
