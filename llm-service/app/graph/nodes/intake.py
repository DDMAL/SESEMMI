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

_DB_LIST = "\n".join(f'  <db name="{k}">{v}</db>' for k, v in _DB_DESCRIPTIONS.items())


class IntakeClassification(BaseModel):
    intent: Literal["lookup", "aggregation"]
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
    needs_federation: bool
    extracted_entities: list[str]


_PROMPT_TEMPLATE = """\
<task>Classify a music database query for SPARQL generation.</task>

<databases>
{db_list}
</databases>

<intent_types>
  <intent name="lookup">Find specific entities or facts</intent>
  <intent name="aggregation">Count, sum, average, or group by</intent>
</intent_types>

<output_fields>
  <field name="intent">The query's primary purpose (one of the intent types above)</field>
  <field name="target_graphs">Which databases are relevant (can be multiple)</field>
  <field name="needs_federation">true if Wikidata federation (SERVICE clause) is likely needed</field>
  <field name="extracted_entities">List of named entities (persons, places, works, organizations) mentioned in the query that may need Wikidata QID resolution. Return an empty list if none.</field>
</output_fields>

<federation_guidance>
  <rule>Set needs_federation=false when the query can be answered entirely within LinkedMusic databases, even if it involves filtering by named entities (persons, places, works) that are stored as Wikidata URIs inside the graphs.</rule>
  <rule>Set needs_federation=true ONLY when information required to answer the query is completely absent from LinkedMusic (e.g., an artist's birth date, gender, nationality, or other biographical data not stored in any LinkedMusic graph).</rule>
  <example needs_federation="false">
    <query>solos by Charlie Parker in NYC</query>
    <reason>Performer and recording location are Wikidata URIs stored directly in Dig That Lick.</reason>
  </example>
  <example needs_federation="true">
    <query>find artists born after 1950</query>
    <reason>Birth dates are only in Wikidata, not in LinkedMusic graphs.</reason>
  </example>
</federation_guidance>

<entity_extraction_guidance>
  <rule>Extract specific named entities that may need Wikidata QID resolution for SPARQL filtering. These will be looked up against the Wikidata API to obtain QIDs (e.g., Q5765 → Charlie Parker).</rule>
  <rule>Include: person names (composers, performers, authors), place names (cities, countries, regions), work titles (compositions, manuscripts, albums), and organization names (ensembles, labels, institutions).</rule>
  <rule>Exclude: generic category terms (e.g., "jazz", "medieval", "chant"), temporal expressions (e.g., "19th century", "after 1950"), and numeric qualifiers (e.g., "top 10", "at least 3").</rule>
  <rule>Use the canonical form of each entity as it would appear in Wikidata (e.g., "Johann Sebastian Bach" not "Bach", "New York City" not "NYC").</rule>
  <example>
    <query>solos by Charlie Parker recorded in New York</query>
    <extracted_entities>["Charlie Parker", "New York City"]</extracted_entities>
  </example>
  <example>
    <query>medieval chants from the 12th century</query>
    <extracted_entities>[]</extracted_entities>
  </example>
  <example>
    <query>works by Mozart held at the British Library</query>
    <extracted_entities>["Wolfgang Amadeus Mozart", "British Library"]</extracted_entities>
  </example>
</entity_extraction_guidance>

<query>{user_query}</query>"""


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
            "needs_federation": result.needs_federation,
            "extracted_entities": result.extracted_entities,
        }
    except Exception:
        logger.exception("intake_node classification failed, using broad fallback")
        return {
            "intent": "lookup",
            "target_graphs": VALID_DB_NAMES,
            "needs_federation": False,
            "extracted_entities": [],
        }
