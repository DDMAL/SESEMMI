import asyncio
import logging

import httpx

from app.config import settings
from app.graph.tools.federation import classify_execution_error

logger = logging.getLogger(__name__)


async def execute_sparql(query: str, endpoint: str | None = None) -> dict:
    """POST a SPARQL query to Virtuoso and return parsed JSON results.

    On failure returns ``{"results": None, "error": <text>, "error_kind": ...}`` where
    ``error_kind`` is ``"external_service"`` (a transient failure of a federated SERVICE call —
    rewriting the query won't help) or ``"query_fault"`` (a fault in the query itself). Transient
    timeouts and external-SERVICE 429/5xx are retried with backoff, honoring WDQS's ≤1 RPS.
    """
    url = endpoint or settings.virtuoso_endpoint
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/sparql-results+json",
    }
    timeout = httpx.Timeout(settings.sparql_timeout, connect=10.0)
    attempts = max(1, settings.sparql_max_attempts)
    for attempt in range(attempts):
        is_last = attempt + 1 >= attempts
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url, data={"query": query}, headers=headers
                )
                response.raise_for_status()
                return {"results": response.json(), "error": None, "error_kind": None}
        except httpx.ReadTimeout as exc:
            kind = classify_execution_error(query, "timeout")
            logger.warning(
                "execute_sparql ReadTimeout (attempt %d/%d, %s)",
                attempt + 1,
                attempts,
                kind,
            )
            if is_last:
                return {
                    "results": None,
                    "error": str(exc) or "ReadTimeout",
                    "error_kind": kind,
                }
            await asyncio.sleep(settings.sparql_retry_backoff)
        except httpx.HTTPStatusError as exc:
            error_text = f"HTTP {exc.response.status_code}: {exc.response.text}"
            kind = classify_execution_error(query, error_text)
            logger.warning("Virtuoso HTTP error (%s): %s", kind, error_text)
            if kind == "external_service" and not is_last:
                await asyncio.sleep(settings.sparql_retry_backoff)  # honor WDQS ≤1 RPS
                continue
            return {"results": None, "error": error_text, "error_kind": kind}
        except Exception as exc:
            logger.exception("execute_sparql failed")
            return {"results": None, "error": str(exc), "error_kind": "query_fault"}
    # Loop exits only after exhausting retries on a transient failure.
    return {
        "results": None,
        "error": "execute_sparql exhausted retries",
        "error_kind": "external_service",
    }
