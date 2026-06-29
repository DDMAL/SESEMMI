import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.graph.state import GraphState
from app.graph.model import get_structured_model
from app.graph.schema_corpus import VALID_DB_NAMES

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
    "utsi": "University of Tennessee Song Index — American folk and popular songs, anthologies",
    "cantusindex": "Cantus Index — medieval Latin chant index linking chant traditions across sources",
    "ckg-apsearch": "CKG APSearch — NFDI4Culture feed of Arab phonogram recordings (works only)",
    "ckg-detmold": "CKG Detmolder Hoftheater — NFDI4Culture feed of Detmold Court Theatre works, persons, and places",
    "ckg-musiconn": "CKG musiconn.performance — NFDI4Culture feed for music performance history (events, persons, organizations, works, places, collections)",
}

# Only offer enabled databases to the model (disabled ones are excluded from VALID_DB_NAMES).
_DB_LIST = "\n".join(
    f'  <db name="{k}">{v}</db>'
    for k, v in _DB_DESCRIPTIONS.items()
    if k in VALID_DB_NAMES
)


class EntityContext(BaseModel):
    entity: str
    description: str


class IntakeClassification(BaseModel):
    intents: list[
        Literal["lookup", "aggregation", "existence", "intersection", "comparison"]
    ]
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
            "ckg-apsearch",
            "ckg-detmold",
            "ckg-musiconn",
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
  <intent name="lookup">Find specific entities or facts (simple SELECT WHERE)</intent>
  <intent name="aggregation">Count, sum, average, or group by (GROUP BY / COUNT / AVG / SUM)</intent>
  <intent name="existence">Find entities that do or do not have a certain property or relationship (FILTER NOT EXISTS / FILTER EXISTS / OPTIONAL+FILTER)</intent>
  <intent name="intersection">Find entities that appear in or link across two or more databases, or that require Wikidata federation to join external data with LinkedMusic — joined via shared Wikidata QIDs or equivalent identifiers (JOIN across GRAPH blocks or SERVICE blocks)</intent>
  <intent name="comparison">Compare counts or values across two datasets, often requiring arithmetic between subquery results (subqueries with ABS / MINUS / value arithmetic)</intent>
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
  <rule>Include: person names (composers, performers, authors), place names (cities, countries, regions), work titles (compositions, manuscripts, albums), organization names (ensembles, labels, institutions), and music domain-specific identifiers (e.g., modal designations like "dorian mode", scale names like "blues scale", opus numbers like "Opus 40", catalogue numbers like "BWV 244", instrument names like "lute", genre/form names like "motet" or "reel").</rule>
  <rule>Exclude: overly broad descriptors that do not name a specific filterable concept (e.g., "music", "medieval", "chant", "song"), date or year constraints (e.g., "after 1950", "before 1800", "in 2015"), and numeric qualifiers that express quantity or rank (e.g., "top 10", "at least 3").</rule>
  <rule>Use canonical Wikidata forms (e.g., "Johann Sebastian Bach" not "Bach", "New York City" not "NYC").</rule>
  <rule>For each entity, infer a short disambiguation description from the query's wording (e.g., "composed by X" → X is a "composer"; "recorded in Y" → Y is a "city" or "town"; "held at Z" → Z is an "institution").</rule>
  <rule>Keep descriptions concise. For persons, use their role optionally prefixed with a single qualifying adjective (nationality, era, or style) when it can be inferred from the target database's description — e.g., if the target database is specifically American, use "American composer" rather than "composer". Never append additional nouns after the role (e.g., avoid "composer of musical compositions" or "composer of works"), as these cause Wikidata search to return related objects instead of the person.</rule>
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
    <entity_contexts>{{"Wolfgang Amadeus Mozart": "composer", "British Library": "institution"}}</entity_contexts>
  </example>
  <example>
    <query>Find all chants in Cantus DB in lydian mode</query>
    <entity_contexts>{{"lydian mode": "tonality"}}</entity_contexts>
  </example>
  <example>
    <query>Find all songs in the University of Tennessee Song Index composed by Stephen Foster</query>
    <entity_contexts>{{"Stephen Foster": "American composer"}}</entity_contexts>
    <reason>UTSI is an American folk/popular music database, so "American composer" better disambiguates the Wikidata lookup than the generic "composer".</reason>
  </example>
</entity_guidance>

<output_fields>
  <field name="intents">One or more applicable intent types. Most queries have one, but complex queries may combine several (e.g. ["intersection", "aggregation"] for "how many composers appear in both DIAMM and RISM?")</field>
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
        "- Did an inefficient query structure cause a timeout?\n"
        "- Did the previous attempt target the wrong databases?\n"
        "- Were the intents misidentified (wrong types selected, or a type missing)?\n"
        "- Was federation incorrectly set?\n"
        "- Were important entities missing or incorrectly described?\n"
        "Adjust intents, target_graphs, needs_federation, and entity_contexts "
        "to address the root cause of the failure.\n"
        "</repair_context>"
    )


async def intake_node(state: GraphState) -> dict:
    structured = get_structured_model(IntakeClassification)
    system = _SYSTEM_PROMPT.format(db_list=_DB_LIST)
    user = f"<query>\n{state['user_query']}\n</query>" + _build_repair_block(state)
    try:
        result = await structured.ainvoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        return {
            "intents": result.intents,
            # Drop any disabled database the model may still have picked.
            "target_graphs": [g for g in result.target_graphs if g in VALID_DB_NAMES],
            "needs_federation": result.needs_federation,
            "entity_contexts": {
                ec.entity: ec.description for ec in result.entity_contexts
            },
        }
    except Exception:
        logger.exception("intake_node classification failed, using broad fallback")
        return {
            "intents": ["lookup"],
            "target_graphs": VALID_DB_NAMES,
            "needs_federation": False,
            "entity_contexts": {},
        }
