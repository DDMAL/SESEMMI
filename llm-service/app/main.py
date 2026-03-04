from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.llm.chain import translate_to_sparql

from contextlib import asynccontextmanager
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.rag_enabled:
        from app.rag.store import seed_store

        await seed_store()
    yield


app = FastAPI(title="SESEMI LLM Service", lifespan=lifespan)


class TranslateRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class TranslateResponse(BaseModel):
    sparql: str
    usage: dict
    durationMs: int


@app.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest):
    try:
        result = await translate_to_sparql(req.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}
