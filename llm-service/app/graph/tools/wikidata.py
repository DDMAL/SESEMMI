import logging
import re

from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import settings

logger = logging.getLogger(__name__)


def _parse_mcp_response(result) -> list[dict]:
    """Parse search_items response (newline-separated 'QID: label — desc') into dicts."""
    text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
    logger.info("MCP raw response: %r", text)
    items = []
    for line in text.splitlines():
        m = re.match(r"^(Q\d+):\s*(.+?)(?:\s*—\s*(.+))?$", line.strip())
        if m:
            items.append(
                {
                    "qid": m.group(1),
                    "label": m.group(2).strip(),
                    "description": (m.group(3) or "").strip(),
                }
            )
    return items


@tool
async def wikidata_qid_lookup(entity_name: str, context: str = "") -> list[dict]:
    """Look up a Wikidata entity QID by name via MCP semantic search.

    Args:
        entity_name: The entity name to search for (e.g. "John Ward").
        context: Short disambiguation description of the entity
                 (e.g. "English Renaissance composer", "city in Austria").
    """
    try:
        query = f"{entity_name} {context}" if context else entity_name
        client = MultiServerMCPClient(
            {
                "wikidata": {
                    "transport": "streamable_http",
                    "url": settings.wikidata_mcp_url,
                }
            }
        )
        async with client.session("wikidata") as session:
            result = await session.call_tool("search_items", {"query": query})
        items = _parse_mcp_response(result)
        logger.debug("wikidata_qid_lookup %r -> %d results", entity_name, len(items))
        return items
    except Exception:
        logger.exception("wikidata_qid_lookup failed for %r", entity_name)
        return []
