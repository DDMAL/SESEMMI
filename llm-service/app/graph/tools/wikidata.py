import json
import logging

from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import settings

logger = logging.getLogger(__name__)

_client: MultiServerMCPClient | None = None
_search_tool = None


async def _get_search_tool():
    global _client, _search_tool
    if _search_tool is None:
        _client = MultiServerMCPClient(
            {
                "wikidata": {
                    "transport": "streamable_http",
                    "url": settings.wikidata_mcp_url,
                }
            }
        )
        tools = await _client.get_tools()
        logger.debug("MCP tools available: %s", [t.name for t in tools])
        _search_tool = next(t for t in tools if "search" in t.name.lower())
        logger.info("Using MCP search tool: %s", _search_tool.name)
    return _search_tool


def _parse_mcp_response(result) -> list[dict]:
    """Parse MCP search_items response into [{qid, label, description}]."""
    # Log raw response on first call to aid format discovery
    logger.debug("MCP raw response: %r", result)

    items = []

    # Result may be a list of content blocks or a single value
    if isinstance(result, list):
        blocks = result
    elif hasattr(result, "content"):
        blocks = result.content
    else:
        blocks = [result]

    for block in blocks:
        text = None
        if hasattr(block, "text"):
            text = block.text
        elif isinstance(block, str):
            text = block

        if not text:
            continue

        # Try JSON parse first
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                for entry in parsed:
                    qid = entry.get("id") or entry.get("qid") or entry.get("concepturi", "").split("/")[-1]
                    if qid:
                        items.append(
                            {
                                "qid": qid,
                                "label": entry.get("label", ""),
                                "description": entry.get("description", ""),
                            }
                        )
                return items
            elif isinstance(parsed, dict):
                # May be wrapped: {"search": [...]} or {"results": [...]}
                entries = parsed.get("search") or parsed.get("results") or []
                for entry in entries:
                    qid = entry.get("id") or entry.get("qid") or entry.get("concepturi", "").split("/")[-1]
                    if qid:
                        items.append(
                            {
                                "qid": qid,
                                "label": entry.get("label", ""),
                                "description": entry.get("description", ""),
                            }
                        )
                return items
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: look for Q-number patterns in plain text
        import re
        for line in text.splitlines():
            m = re.search(r'\b(Q\d+)\b', line)
            if m:
                items.append({"qid": m.group(1), "label": line.strip(), "description": ""})

    return items


@tool
async def wikidata_qid_lookup(entity_name: str, context: str = "") -> list[dict]:
    """Look up a Wikidata entity QID by name via MCP semantic search.
    Pass context (e.g. the user query) to improve disambiguation."""
    try:
        query = f"{entity_name} — {context}" if context else entity_name
        search = await _get_search_tool()
        result = await search.ainvoke({"query": query})
        items = _parse_mcp_response(result)
        logger.debug("wikidata_qid_lookup %r -> %d results", entity_name, len(items))
        return items
    except Exception:
        logger.exception("wikidata_qid_lookup failed for %r", entity_name)
        return []
