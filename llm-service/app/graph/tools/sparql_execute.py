import logging

import httpx

from app.config import settings
from app.graph.tools.federation import classify_execution_error

logger = logging.getLogger(__name__)


async def execute_sparql(query: str, endpoint: str | None = None) -> dict:
    """POST a SPARQL query to Virtuoso and return parsed JSON results.

    On failure returns ``{"results": None, "error": <text>, "error_kind": ...}`` where
    ``error_kind`` is ``"external_service"`` (the federated SERVICE call to Wikidata failed — the
    local part may still be salvageable) or ``"query_fault"`` (a fault in the query itself). We do
    not retry: a WDQS 429/5xx/timeout is volume-driven and won't clear in seconds, so failing fast
    to graceful degradation beats making the user wait on a low-odds retry.
    """
    url = endpoint or settings.virtuoso_endpoint
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/sparql-results+json",
    }
    timeout = httpx.Timeout(settings.sparql_timeout, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, data={"query": query}, headers=headers)
            response.raise_for_status()
            return {"results": response.json(), "error": None, "error_kind": None}
    except httpx.ReadTimeout as exc:
        kind = classify_execution_error(query, "timeout")
        logger.warning("execute_sparql ReadTimeout (%s)", kind)
        return {"results": None, "error": str(exc) or "ReadTimeout", "error_kind": kind}
    except httpx.HTTPStatusError as exc:
        error_text = f"HTTP {exc.response.status_code}: {exc.response.text}"
        kind = classify_execution_error(query, error_text)
        logger.warning("Virtuoso HTTP error (%s): %s", kind, error_text)
        return {"results": None, "error": error_text, "error_kind": kind}
    except Exception as exc:
        logger.exception("execute_sparql failed")
        return {"results": None, "error": str(exc), "error_kind": "query_fault"}
