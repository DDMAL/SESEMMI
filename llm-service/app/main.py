# Normalize non-standard package version strings (e.g., '3+computecanada' on HPC systems)
# before langsmith loads — it calls tuple(map(int, version.split("."))) which crashes
# on non-semver strings (langsmith/client.py _default_retry_config).
import importlib.metadata as _importlib_metadata
import re as _re

_orig_metadata_version = _importlib_metadata.version


def _safe_metadata_version(package: str) -> str:
    ver = _orig_metadata_version(package)
    return _re.split(r"[+\-]", ver)[0]


_importlib_metadata.version = _safe_metadata_version

import json
import logging
import os
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.graph.builder import build_graph, run_graph
from app.graph.clarify import ClarifyResult, clarify_query
from app.graph.model import get_chat_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.rag_enabled:
        from app.rag.store import seed_store

        await seed_store()
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    yield


app = FastAPI(title="SESEMI LLM Service", lifespan=lifespan)


class TranslateRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class TranslateResponse(BaseModel):
    sparql: str
    usage: dict
    durationMs: int
    graphs: list[str] | None = None
    confidence: str | None = None
    assumptions: list[str] | None = None
    resultCount: int | None = None
    executionError: str | None = None
    results: dict | None = None


@app.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest):
    try:
        result = await run_graph(req.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ClarifyTurn(BaseModel):
    question: str
    answer: str


class ClarifyRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    history: list[ClarifyTurn] = Field(default_factory=list)


@app.post("/clarify", response_model=ClarifyResult)
async def clarify(req: ClarifyRequest):
    if not settings.clarification_enabled:
        return ClarifyResult(ready=True, questions=[], enriched_query=req.query)
    return await clarify_query(req.query, [t.model_dump() for t in req.history])


class ExplainRequest(BaseModel):
    sparql: str = Field(min_length=1, max_length=5000)


class ExplainResponse(BaseModel):
    explanation: str


_EXPLAIN_SYSTEM = (
    "You are an expert in SPARQL and linked music databases (RISM, MusicBrainz, Cantus, DIAMM, etc.).\n"
    "Explain the SPARQL query below in 2–4 plain-English sentences for a non-technical musicologist.\n"
    "Describe what data it retrieves and what conditions or filters it applies.\n"
    "Do not mention SPARQL keywords, syntax, or variable names — describe the intent only.\n"
    "Be as brief and concise as possible."
)


@app.post("/explain", response_model=ExplainResponse)
async def explain(req: ExplainRequest):
    try:
        model = get_chat_model()
        response = await model.ainvoke(
            [
                SystemMessage(content=_EXPLAIN_SYSTEM),
                HumanMessage(content=f"Explain this SPARQL query:\n\n{req.sparql}"),
            ]
        )
        return ExplainResponse(explanation=str(response.content).strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ExplainChatMessage(BaseModel):
    role: str
    content: str


class ExplainChatRequest(BaseModel):
    sparql: str = Field(min_length=1, max_length=5000)
    messages: list[ExplainChatMessage] = Field(default_factory=list, max_length=40)


class ExplainChatResponse(BaseModel):
    reply: str
    intent: str = ""


_EXPLAIN_CHAT_SYSTEM = (
    "You are an expert in SPARQL and linked music databases (RISM, MusicBrainz, Cantus, DIAMM, etc.).\n"
    "The user is exploring a SPARQL query. Answer follow-up questions concisely in 1-3 sentences.\n"
    "Describe intent in plain English — avoid SPARQL syntax in your answers.\n"
    "If the user requests a change, describe what would be different in the new query.\n"
    "Be as brief and concise as possible.\n"
    "End your response with a line 'INTENT: <phrase>' where <phrase> is a 2-5 word imperative "
    "summary of what the user asked for (e.g. 'search all databases', 'include death dates', "
    "'limit to baroque period')."
)


@app.post("/explain/chat", response_model=ExplainChatResponse)
async def explain_chat(req: ExplainChatRequest):
    try:
        model = get_chat_model()
        context = HumanMessage(
            content=f"Here is the SPARQL query we are discussing:\n\n{req.sparql}"
        )
        history: list[HumanMessage | AIMessage] = [
            HumanMessage(content=msg.content) if msg.role == "user" else AIMessage(content=msg.content)
            for msg in req.messages
        ]
        lc_messages = [SystemMessage(content=_EXPLAIN_CHAT_SYSTEM), context, *history]
        response = await model.ainvoke(lc_messages)
        raw = str(response.content).strip()
        intent = ""
        if "\nINTENT:" in raw:
            parts = raw.rsplit("\nINTENT:", 1)
            raw = parts[0].strip()
            intent = parts[1].strip()
        return ExplainChatResponse(reply=raw, intent=intent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


_STEP_LABELS = {
    "intake": "Routing query",
    "retrieve": "Retrieving context",
    "generate": "Generating SPARQL",
    "validate": "Validating",
    "execute": "Executing",
    "judge": "Scoring confidence",
}


def _step_detail(name: str, output: dict) -> str:
    if name == "intake":
        intents = ", ".join(output.get("intents") or [])
        graphs = ", ".join(output.get("target_graphs") or [])
        return f"{intents} · {graphs}" if graphs else intents
    if name == "retrieve":
        qids = output.get("resolved_qids") or {}
        n = len(qids)
        return f"{n} QID{'s' if n != 1 else ''} resolved" if qids else ""
    if name == "validate":
        errors = output.get("validation_errors") or []
        return "✓ valid" if not errors else f"✗ {errors[0]}"
    if name == "execute":
        err = output.get("execution_error")
        if err:
            return f"✗ {err[:80]}"
        count = output.get("result_count", 0)
        return f"{count} result{'s' if count != 1 else ''}"
    if name == "judge":
        return output.get("confidence", "")
    return ""


@app.post("/translate/stream")
async def translate_stream(req: TranslateRequest):
    async def event_stream():
        try:
            graph = build_graph()
            initial_state = {
                "user_query": req.query,
                "repair_count": 0,
                "max_repairs": settings.max_repair_iterations,
            }
            sparql = ""
            confidence = "medium"
            async for event in graph.astream_events(initial_state, version="v2"):
                etype = event["event"]
                name = event.get("name", "")
                if etype == "on_chain_start" and name in _STEP_LABELS:
                    yield f"event: step_start\ndata: {json.dumps({'step': name, 'label': _STEP_LABELS[name]})}\n\n"
                elif etype == "on_chain_end" and name in _STEP_LABELS:
                    out = (event.get("data") or {}).get("output") or {}
                    if name == "generate" and "sparql" in out:
                        sparql = out["sparql"]
                    if "confidence" in out:
                        confidence = out["confidence"]
                    detail = _step_detail(name, out)
                    yield f"event: step_done\ndata: {json.dumps({'step': name, 'label': _STEP_LABELS[name], 'detail': detail})}\n\n"
                elif etype == "on_chat_model_stream":
                    if (event.get("metadata") or {}).get(
                        "langgraph_node"
                    ) == "generate":
                        chunk = (event.get("data") or {}).get("chunk")
                        if chunk:
                            raw = getattr(chunk, "content", "")
                            if isinstance(raw, list):
                                text = "".join(
                                    (
                                        part["text"]
                                        if isinstance(part, dict) and "text" in part
                                        else ""
                                    )
                                    for part in raw
                                )
                            else:
                                text = raw or ""
                        else:
                            text = ""
                        if text:
                            yield f"event: token\ndata: {json.dumps({'text': text})}\n\n"
            yield f"event: done\ndata: {json.dumps({'sparql': sparql, 'confidence': confidence})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health_check():
    return {"status": "ok"}
