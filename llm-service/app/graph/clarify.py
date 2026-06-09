"""Conversational query clarification.

A stateless pre-processing step that runs BEFORE the LangGraph pipeline. Given a user's
natural-language query and any clarifications gathered so far, it decides whether the query is
specific enough to translate into accurate SPARQL. If not, it returns a few targeted follow-up
questions (each with suggested answer chips). When the query is clear enough it returns
``ready=True`` and a synthesized, disambiguated ``enriched_query`` that the pipeline consumes in
place of the raw query.

This lives outside the graph on purpose: the frontend owns the conversation transcript and calls
``clarify_query`` in a loop, then sends ``enriched_query`` to the unchanged ``/translate`` flow.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.config import settings
from app.graph.model import get_structured_model
from app.graph.nodes.intake import _DB_DESCRIPTIONS

logger = logging.getLogger(__name__)

_DB_LIST = "\n".join(f"  - {k}: {v}" for k, v in _DB_DESCRIPTIONS.items())


class ClarifyQuestion(BaseModel):
    question: str = Field(description="A single, concise follow-up question.")
    options: list[str] = Field(
        default_factory=list,
        description="2-4 suggested answer chips the user can click; may be empty.",
    )


class ClarifyResult(BaseModel):
    ready: bool = Field(
        description="True if the query is specific enough to translate; "
        "False if more clarification would help."
    )
    questions: list[ClarifyQuestion] = Field(
        default_factory=list,
        description="Follow-up questions to ask. Empty when ready=True.",
    )
    enriched_query: str = Field(
        description="The best precise, disambiguated rewrite of the query given everything "
        "known so far. Always populated, even when ready=False, so it can be used as a fallback."
    )


_SYSTEM_PROMPT = """\
You are a query-disambiguation assistant for a natural-language search engine over 11 linked \
music-metadata databases. The user's query will be translated into a SPARQL query that runs \
against these databases:

{db_list}

<task>
Decide whether the user's query (plus any clarifications gathered so far) is specific enough to \
produce an accurate SPARQL query.
- If it is ambiguous or under-specified, set ready=false and ask up to {max_questions} targeted \
follow-up questions. Each question should resolve a concrete ambiguity (which database/entity \
type, which named entity, which attribute, what time range, what to return, etc.). For each \
question, suggest 2-4 short clickable answer options when sensible; the user may also type a \
free-text answer.
- If it is specific enough, set ready=true and return no questions.
</task>

<rules>
- Ask ONLY about ambiguities that would materially change the generated SPARQL. Do not ask for
  information the user clearly already gave.
- Prefer fewer, higher-value questions. Never exceed {max_questions} questions.
- ALWAYS populate enriched_query with the best precise rewrite of the user's intent given
  everything known so far — fold in every answer the user has provided. This is used both when
  ready=true and as a fallback if the user skips ahead.
- Keep enriched_query a single natural-language request (not SPARQL). Be specific about the
  target database(s), named entities, attributes, and what to return.
- Do not invent facts the user did not imply.
</rules>"""


def _format_history(query: str, history: list[dict]) -> str:
    lines = [f"Original query: {query}"]
    if history:
        lines.append("\nClarifications so far:")
        for turn in history:
            lines.append(f"- Q: {turn.get('question', '')}")
            lines.append(f"  A: {turn.get('answer', '')}")
    return "\n".join(lines)


async def clarify_query(query: str, history: list[dict]) -> ClarifyResult:
    """Return clarifying questions, or a ready signal with an enriched query.

    ``history`` is a list of ``{"question": str, "answer": str}`` dicts representing the
    clarifications the user has already answered.
    """
    model = get_structured_model(ClarifyResult)
    system = _SYSTEM_PROMPT.format(
        db_list=_DB_LIST, max_questions=settings.clarification_max_questions
    )
    user = _format_history(query, history)
    try:
        result = await model.ainvoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
    except Exception:
        logger.exception("clarify_query failed, passing the query through unchanged")
        return ClarifyResult(ready=True, questions=[], enriched_query=query)

    # Guard rails: cap question count and guarantee enriched_query is never empty.
    if result.ready:
        result.questions = []
    else:
        result.questions = result.questions[: settings.clarification_max_questions]
    if not result.enriched_query.strip():
        result.enriched_query = query
    return result
