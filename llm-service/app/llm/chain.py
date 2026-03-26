import re
import time

from langchain_ollama import ChatOllama

from app.config import settings
from app.llm.examples import FEW_SHOT_EXAMPLES
from app.llm.prompt import build_prompt_template, format_examples


def clean_sparql(text: str) -> str:
    """Extract and clean SPARQL query from LLM output.

    Applies a cascade of strategies:
    1. Extract from ```sparql ... ``` fenced code block
    2. Extract from any ``` ... ``` code block that looks like SPARQL
    3. Extract starting from the first SPARQL keyword (PREFIX, SELECT, etc.)
    4. Return stripped text as fallback
    """
    text = text.strip()

    # Strategy 1: extract from ```sparql ... ``` block
    m = re.search(r"```sparql\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Strategy 2: extract from any ``` ... ``` block if it contains SPARQL keywords
    m = re.search(r"```(?:\w+)?\s*([\s\S]*?)\s*```", text)
    if m:
        candidate = m.group(1).strip()
        if re.search(r"\b(SELECT|CONSTRUCT|ASK|DESCRIBE)\b", candidate, re.IGNORECASE):
            return candidate

    # Strategy 3: extract from first SPARQL keyword onwards (handles prose before the query)
    m = re.search(
        r"((?:PREFIX\s+\w|SELECT\b|CONSTRUCT\b|ASK\b|DESCRIBE\b)[\s\S]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    # Fallback: return the whole text stripped
    return text


async def translate_to_sparql(
    user_query: str,
    rag_examples: (
        list[dict] | None
    ) = None,  # For testing: directly pass examples to test chain without hitting RAG store
) -> dict:
    if rag_examples is not None:
        examples = rag_examples
    elif settings.rag_enabled:
        from app.rag.retrieve import retrieve_examples

        examples = retrieve_examples(user_query)
    elif settings.few_shot_enabled:
        examples = FEW_SHOT_EXAMPLES
    else:
        examples = []

    prompt = build_prompt_template()
    model = ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_ctx=settings.ollama_num_ctx,  # context length
        num_thread=settings.ollama_num_thread,
        think=settings.ollama_think,
    )
    chain = prompt | model

    start = time.time()
    response = await chain.ainvoke(
        {
            "query": user_query,
            "examples": format_examples(examples),
        }
    )
    duration_ms = round((time.time() - start) * 1000)
    usage = response.usage_metadata or {}

    return {
        "sparql": clean_sparql(response.content),
        "usage": {
            "inputTokens": usage.get("input_tokens", 0),
            "outputTokens": usage.get("output_tokens", 0),
            "totalTokens": usage.get("total_tokens", 0),
        },
        "durationMs": duration_ms,
    }
