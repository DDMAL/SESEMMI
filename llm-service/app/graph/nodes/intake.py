import logging
from typing import Literal

from langchain_ollama import ChatOllama
from pydantic import BaseModel

from app.config import settings
from app.graph.state import GraphState
from app.rag.schema_corpus import VALID_DB_NAMES

logger = logging.getLogger(__name__)

_DB_DESCRIPTIONS = {
    "diamm": "Digital Image Archive of Medieval Music — compositions, manuscripts, composers",
    "thesession": "Irish traditional music — tunes, sessions, recordings, events",
    "musicbrainz": "Open music encyclopedia — artists, works, recordings, releases, labels",
    "theglobaljukebox": "Cross-cultural music dataset — songs, cultures, instruments",
    "digthatlick": "Jazz improvisation database — tracks and melodic solos",
    "cantusdb": "Medieval Latin chant archive — sources and chants",
    "rism": "Historical music manuscripts — sources, persons, institutions",
}

_DB_LIST = "\n".join(f"- {k}: {v}" for k, v in _DB_DESCRIPTIONS.items())


class IntakeClassification(BaseModel):
    intent: Literal["lookup", "aggregation", "comparison", "path", "cross_graph"]
    target_graphs: list[
        Literal[
            "diamm",
            "musicbrainz",
            "thesession",
            "theglobaljukebox",
            "digthatlick",
            "rism",
            "cantusdb",
        ]
    ]
    mentions_entities: bool
    needs_federation: bool


_PROMPT_TEMPLATE = """\
Classify this music database query for SPARQL generation.

Available databases:
{db_list}

Intent types:
- lookup: find specific entities or facts
- aggregation: count, sum, average, or group by
- comparison: compare multiple entities or order results
- path: find connections or relationships between entities
- cross_graph: query across multiple databases

Classify:
- intent: the query's primary purpose
- target_graphs: which databases are relevant (can be multiple)
- mentions_entities: true if the query references specific named entities (people, places, works)
- needs_federation: true if Wikidata federation (SERVICE clause) is likely needed

Federation guidance:
- Set needs_federation=false when the query can be answered entirely within LinkedMusic
  databases, even if it involves filtering by named entities (persons, places, works)
  that are stored as Wikidata URIs inside the graphs.
- Set needs_federation=true ONLY when information required to answer the query is
  completely absent from LinkedMusic (e.g., an artist's birth date, gender, nationality,
  or other biographical data not stored in any LinkedMusic graph).
- Example: "solos by Charlie Parker in NYC" — needs_federation=false (performer and
  recording location are Wikidata URIs stored directly in Dig That Lick).
- Example: "find artists born after 1950" — needs_federation=true (birth dates are
  only in Wikidata, not in LinkedMusic graphs).

Query: {user_query}"""


async def intake_node(state: GraphState) -> dict:
    model = ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_ctx=settings.ollama_num_ctx,
        num_thread=settings.ollama_num_thread,
        think=settings.ollama_think,
    )
    structured = model.with_structured_output(IntakeClassification)
    prompt = _PROMPT_TEMPLATE.format(db_list=_DB_LIST, user_query=state["user_query"])
    try:
        result = await structured.ainvoke(prompt)
        return {
            "intent": result.intent,
            "target_graphs": result.target_graphs,
            "mentions_entities": result.mentions_entities,
            "needs_federation": result.needs_federation,
        }
    except Exception:
        logger.exception("intake_node classification failed, using broad fallback")
        return {
            "intent": "lookup",
            "target_graphs": VALID_DB_NAMES,
            "mentions_entities": True,
            "needs_federation": False,
        }
