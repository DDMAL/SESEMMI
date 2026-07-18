from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.graph.tools.sparql_execute import execute_sparql

_SPARQL_QUERY = "SELECT * WHERE { GRAPH <https://linkedmusic.ca/graphs/diamm/> { ?s ?p ?o } } LIMIT 10"
_SPARQL_RESULTS = {
    "results": {
        "bindings": [
            {"s": {"type": "uri", "value": "https://example.org/1"}},
        ]
    }
}


async def test_success_returns_results():
    mock_response = MagicMock()
    mock_response.json.return_value = _SPARQL_RESULTS
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        result = await execute_sparql(_SPARQL_QUERY)

    assert result == {"results": _SPARQL_RESULTS, "error": None, "error_kind": None}


async def test_uses_settings_endpoint_by_default():
    from app.config import settings

    mock_response = MagicMock()
    mock_response.json.return_value = _SPARQL_RESULTS
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post
        await execute_sparql(_SPARQL_QUERY)

    call_args = mock_post.call_args
    assert call_args[0][0] == settings.virtuoso_endpoint


async def test_custom_endpoint_overrides_settings():
    custom_endpoint = "http://custom-host:9999/sparql"
    mock_response = MagicMock()
    mock_response.json.return_value = _SPARQL_RESULTS
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post
        await execute_sparql(_SPARQL_QUERY, endpoint=custom_endpoint)

    call_args = mock_post.call_args
    assert call_args[0][0] == custom_endpoint


async def test_sends_correct_headers():
    mock_response = MagicMock()
    mock_response.json.return_value = _SPARQL_RESULTS
    mock_response.raise_for_status.return_value = None

    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post
        await execute_sparql(_SPARQL_QUERY)

    call_kwargs = mock_post.call_args[1]
    headers = call_kwargs["headers"]
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert headers["Accept"] == "application/sparql-results+json"
    assert call_kwargs["data"] == {"query": _SPARQL_QUERY}


async def test_http_error_returns_error_string():
    mock_inner_response = MagicMock()
    mock_inner_response.status_code = 500
    mock_inner_response.text = "Internal Server Error"

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=mock_inner_response
    )

    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        result = await execute_sparql(_SPARQL_QUERY)

    assert result["results"] is None
    assert "HTTP 500" in result["error"]
    assert "Internal Server Error" in result["error"]


async def test_network_exception_returns_error_string():
    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=Exception("network failure")
        )
        result = await execute_sparql(_SPARQL_QUERY)

    assert result["results"] is None
    assert result["error"] == "network failure"


async def test_timeout_returns_error_string():
    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("timed out")
        )
        result = await execute_sparql(_SPARQL_QUERY)

    assert result["results"] is None
    assert result["error"] is not None


async def test_http_error_classified_query_fault():
    """A local Virtuoso fault (SP031-style 500) → error_kind='query_fault', no retry."""
    mock_inner_response = MagicMock()
    mock_inner_response.status_code = 500
    mock_inner_response.text = "Virtuoso 37000 Error SP031: SPARQL compiler"

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=mock_inner_response
    )

    mock_post = AsyncMock(return_value=mock_response)
    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = mock_post
        result = await execute_sparql(_SPARQL_QUERY)

    assert result["error_kind"] == "query_fault"
    assert mock_post.call_count == 1  # not retried


async def test_external_service_429_classified_not_retried():
    """A WDQS 429 (wrapped as a Virtuoso 500) → error_kind='external_service', failed fast.

    We don't retry: a volume-driven 429 won't clear in seconds, so we degrade immediately rather
    than make the user wait."""
    mock_inner_response = MagicMock()
    mock_inner_response.status_code = 500
    mock_inner_response.text = (
        "Virtuoso 42000 Error SPARQL_REXEC: remote endpoint "
        "<https://query.wikidata.org/sparql> returned HTTP/1.1 429 Too Many Requests"
    )

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=mock_inner_response
    )

    mock_post = AsyncMock(return_value=mock_response)
    with patch("app.graph.tools.sparql_execute.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = mock_post
        result = await execute_sparql(_SPARQL_QUERY)

    assert result["results"] is None
    assert result["error_kind"] == "external_service"
    assert "429" in result["error"]
    assert mock_post.call_count == 1  # no retry
