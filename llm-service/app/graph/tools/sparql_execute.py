import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def execute_sparql(query: str, endpoint: str | None = None) -> dict:
    """POST a SPARQL query to Virtuoso and return parsed JSON results."""
    url = endpoint or settings.virtuoso_endpoint
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/sparql-results+json",
    }
    timeout = httpx.Timeout(settings.sparql_timeout, connect=10.0)
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url, data={"query": query}, headers=headers
                )
                response.raise_for_status()
                return {"results": response.json(), "error": None}
        except httpx.ReadTimeout as exc:
            last_exc = exc
            logger.warning("execute_sparql ReadTimeout (attempt %d/2)", attempt + 1)
            if attempt == 0:
                await asyncio.sleep(2)
        except httpx.HTTPStatusError as exc:
            error_text = f"HTTP {exc.response.status_code}: {exc.response.text}"
            logger.warning("Virtuoso HTTP error: %s", error_text)
            return {"results": None, "error": error_text}
        except Exception as exc:
            logger.exception("execute_sparql failed")
            return {"results": None, "error": str(exc)}
    logger.error("execute_sparql timed out after 2 attempts")
    return {"results": None, "error": str(last_exc)}
