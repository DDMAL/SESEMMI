import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.graph.state import GraphState
from app.llm.model import get_chat_model
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
    "weimarjazz": "Weimar Jazz Database — jazz compositions, records, tracks, solo transcriptions",
    "simssadb": "SIMSSA DB — symbolic music scores, works, sections, sources, persons",
    "utsi": "University of Tennessee Song Index — folk and popular songs, anthologies",
    "cantusindex": "Cantus Index — medieval Latin chant index linking chant traditions across sources",
}

_DB_LIST = "\n".join(f'  <db name="{k}">{v}</db>' for k, v in _DB_DESCRIPTIONS.items())


class EntityContext(BaseModel):
    entity: str
    description: str


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
            "weimarjazz",
            "simssadb",
            "utsi",
            "cantusindex",
        ]
    ]
    needs_federation: bool
    entity_contexts: list[EntityContext]


_SYSTEM_PROMPT = """\
<task>Classify a music database query for SPARQL generation.</task>

<databases>
{db_list}
</databases>

<intent_types>
  <intent name="lookup">Find specific entities or facts</intent>
  <intent name="aggregation">Count, sum, average, or group by</intent>
</intent_types>

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

<entity_guidance>
  <rule>Extract specific named entities that may need Wikidata QID resolution for SPARQL filtering. These will be looked up against the Wikidata API to obtain QIDs (e.g., Q5765 → Charlie Parker).</rule>
  <rule>Include: person names (composers, performers, authors), place names (cities, countries, regions), work titles (compositions, manuscripts, albums), organization names (ensembles, labels, institutions), and music domain-specific identifiers (e.g., modal designations like "mode 1", scale names like "blues scale", opus numbers like "Opus 40", catalogue numbers like "BWV 244", instrument names like "lute", genre/form names like "motet" or "reel").</rule>
  <rule>Exclude: overly broad descriptors that do not name a specific filterable concept (e.g., "music", "medieval", "chant", "song"), date or year constraints (e.g., "after 1950", "before 1800", "in 2015"), and numeric qualifiers that express quantity or rank (e.g., "top 10", "at least 3").</rule>
  <rule>Use canonical Wikidata forms (e.g., "Johann Sebastian Bach" not "Bach", "New York City" not "NYC").</rule>
  <rule>For each entity, infer a short disambiguation description from the query's wording (e.g., "composed by X" → X is a "composer"; "recorded in Y" → Y is a "city" or "town"; "held at Z" → Z is an "institution").</rule>
  <rule>Keep descriptions concise: use a single noun or role word. For persons, use only their role (e.g., "composer", "musician", "performer") — never append additional nouns like "of musical compositions" or "of works", as these cause Wikidata search to return related objects instead of the person.</rule>
  <rule>Return a dict mapping each entity name to its description. Return an empty dict if no entities apply.</rule>
  <example>
    <query>solos by Charlie Parker recorded in New York</query>
    <entity_contexts>{{"Charlie Parker": "musician", "New York City": "city"}}</entity_contexts>
  </example>
  <example>
    <query>medieval chants from the 12th century</query>
    <entity_contexts>{{}}</entity_contexts>
  </example>
  <example>
    <query>works by Mozart held at the British Library</query>
    <entity_contexts>{{"Wolfgang Amadeus Mozart": "composer", "British Library": "library that holds works"}}</entity_contexts>
  </example>
  <example>
    <query>Find all chants in Cantus DB in mode 5</query>
    <entity_contexts>{{"mode 5": "Lydian chant mode"}}</entity_contexts>
  </example>
</entity_guidance>

<output_fields>
  <field name="intent">The query's primary purpose (one of the intent types above)</field>
  <field name="target_graphs">Which databases are relevant (can be multiple)</field>
  <field name="needs_federation">true if Wikidata federation (SERVICE clause) is likely needed</field>
  <field name="entity_contexts">A dict mapping each extracted entity name to a short disambiguation description inferred from the query. Return an empty dict if no entities.</field>
</output_fields>"""


def _build_repair_block(state: GraphState) -> str:
    previous_sparql = state.get("sparql", "")
    if not previous_sparql:
        return ""
    reasons: list[str] = []
    for err in state.get("validation_errors") or []:
        reasons.append(err)
    if exec_err := state.get("execution_error"):
        reasons.append(f"Execution error: {exec_err}")
    if feedback := state.get("judge_feedback"):
        reasons.append(f"Semantic feedback: {feedback}")
    failure_text = (
        "\n".join(f"- {r}" for r in reasons)
        if reasons
        else "(no specific errors recorded)"
    )
    return (
        "\n\n<repair_context>\n"
        "A previous SPARQL generation attempt for this query failed. "
        "Analyze what went wrong and update your classification accordingly.\n\n"
        f"<previous_query>\n{previous_sparql}\n</previous_query>\n\n"
        f"<failure_reason>\n{failure_text}\n</failure_reason>\n\n"
        "Think through:\n"
        "- Did the previous attempt target the wrong databases?\n"
        "- Was the intent (lookup vs aggregation) misidentified?\n"
        "- Was federation incorrectly set?\n"
        "- Were important entities missing or incorrectly described?\n"
        "Adjust intent, target_graphs, needs_federation, and entity_contexts "
        "to address the root cause of the failure.\n"
        "</repair_context>"
    )


async def intake_node(state: GraphState) -> dict:
    model = get_chat_model()
    structured = model.with_structured_output(IntakeClassification)
    system = _SYSTEM_PROMPT.format(db_list=_DB_LIST)
    user = f"<query>\n{state['user_query']}\n</query>" + _build_repair_block(state)
    try:
        result = await structured.ainvoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        return {
            "intent": result.intent,
            "target_graphs": result.target_graphs,
            "needs_federation": result.needs_federation,
            "entity_contexts": {
                ec.entity: ec.description for ec in result.entity_contexts
            },
        }
    except Exception:
        logger.exception("intake_node classification failed, using broad fallback")
        return {
            "intent": "lookup",
            "target_graphs": VALID_DB_NAMES,
            "needs_federation": False,
            "entity_contexts": {},
        }
