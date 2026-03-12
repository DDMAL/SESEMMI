from unittest.mock import AsyncMock, MagicMock, patch

from app.graph.tools.wikidata import wikidata_qid_lookup

_WIKIDATA_RESPONSE = {
    "search": [
        {
            "id": "Q26876",
            "label": "Taylor Swift",
            "description": "American singer-songwriter",
        },
        {
            "id": "Q99671",
            "label": "Taylor Swift (album)",
            "description": "2006 album by Taylor Swift",
        },
    ]
}


async def test_happy_path_returns_top_matches():
    mock_response = MagicMock()
    mock_response.json.return_value = _WIKIDATA_RESPONSE
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.wikidata.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Taylor Swift"})

    assert len(result) == 2
    assert result[0] == {
        "qid": "Q26876",
        "label": "Taylor Swift",
        "description": "American singer-songwriter",
    }
    assert result[1]["qid"] == "Q99671"


async def test_happy_path_passes_correct_params():
    mock_response = MagicMock()
    mock_response.json.return_value = {"search": []}
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.wikidata.httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get
        await wikidata_qid_lookup.ainvoke({"entity_name": "Bach", "language": "de"})

    call_kwargs = mock_get.call_args
    params = call_kwargs[1]["params"]
    assert params["search"] == "Bach"
    assert params["language"] == "de"
    assert params["action"] == "wbsearchentities"
    assert params["type"] == "item"
    assert params["limit"] == "5"


async def test_network_error_returns_empty_list():
    with patch("app.graph.tools.wikidata.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("network failure")
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Taylor Swift"})

    assert result == []


async def test_http_error_returns_empty_list():
    import httpx as httpx_lib

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx_lib.HTTPStatusError(
        "503", request=MagicMock(), response=MagicMock()
    )

    with patch("app.graph.tools.wikidata.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Taylor Swift"})

    assert result == []


async def test_empty_search_results():
    mock_response = MagicMock()
    mock_response.json.return_value = {"search": []}
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.wikidata.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "zzznomatchxyz"})

    assert result == []


async def test_missing_description_field_defaults_to_empty_string():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "search": [
            {"id": "Q12345", "label": "Unknown Entity"},  # no 'description' key
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.wikidata.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Unknown Entity"})

    assert result == [{"qid": "Q12345", "label": "Unknown Entity", "description": ""}]


async def test_user_agent_header_is_set():
    mock_response = MagicMock()
    mock_response.json.return_value = {"search": []}
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.wikidata.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        await wikidata_qid_lookup.ainvoke({"entity_name": "Bach"})

    _, client_kwargs = mock_client.call_args
    assert "User-Agent" in client_kwargs.get("headers", {})


async def test_timeout_returns_empty_list():
    import httpx as httpx_lib

    with patch("app.graph.tools.wikidata.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx_lib.TimeoutException("timed out")
        )
        result = await wikidata_qid_lookup.ainvoke({"entity_name": "Taylor Swift"})

    assert result == []
