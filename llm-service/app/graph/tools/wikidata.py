import logging

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_WIKIDATA_API = "https://www.wikidata.org/w/api.php"
_TIMEOUT = 10.0
_LIMIT = 5
_USER_AGENT = "sesemmi-llm/1.0 (https://github.com/sesemmi; bot) httpx"


@tool
async def wikidata_qid_lookup(entity_name: str, language: str = "en") -> list[dict]:
    """Look up a Wikidata entity QID by name. Returns top 5 matches."""
    params = {
        "action": "wbsearchentities",
        "search": entity_name,
        "language": language,
        "format": "json",
        "type": "item",
        "limit": str(_LIMIT),
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as client:
            response = await client.get(_WIKIDATA_API, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception:
        logger.exception("wikidata_qid_lookup failed for %r", entity_name)
        return []

    return [
        {
            "qid": item["id"],
            "label": item["label"],
            "description": item.get("description", ""),
        }
        for item in data.get("search", [])
    ]
