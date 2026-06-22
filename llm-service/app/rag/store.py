import hashlib
import re
import uuid
from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from langchain_postgres import PGVector
from langchain_core.documents import Document
from app.rag.embeddings import get_embeddings
from app.rag.corpus import RAG_CORPUS
from app.config import settings

_store: PGVector | None = None

# Arbitrary fixed key for the Postgres advisory lock that serializes seeding.
_SEED_LOCK_KEY = 5253553105  # "SESEMMI" → digits, fits in bigint


@contextmanager
def _seed_lock() -> Iterator[None]:
    """Hold a session-level Postgres advisory lock for the duration of seeding.

    Concurrent PGVector table creation (multiple uvicorn workers / replicas all
    running the startup lifespan) otherwise races on the internal pg_type index
    — ``UniqueViolation: "langchain_pg_collection" already exists``. Serializing
    the create+seed behind one cluster-wide lock removes the race.
    """
    engine = create_engine(settings.database_url)
    conn = engine.connect()
    try:
        conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _SEED_LOCK_KEY})
        conn.commit()
        yield
    finally:
        try:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _SEED_LOCK_KEY})
            conn.commit()
        finally:
            conn.close()
            engine.dispose()


_IRI_TO_DB = {
    "graphs/diamm/": "diamm",
    "graphs/thesession/": "thesession",
    "graphs/musicbrainz/": "musicbrainz",
    "graphs/theglobaljukebox/": "theglobaljukebox",
    "graphs/dig-that-lick/": "digthatlick",
    "graphs/cantusdb/": "cantusdb",
    "graphs/rism/": "rism",
    "graphs/wjazzd/": "wjazzd",
    "graphs/simssadb/": "simssadb",
    "graphs/utsi/": "utsi",
    "graphs/cantusindex/": "cantusindex",
    "graphs/ckg-apsearch/": "ckg-apsearch",
    "graphs/ckg-detmold/": "ckg-detmold",
    "graphs/ckg-musiconn/": "ckg-musiconn",
}


def enrich_example(example: dict) -> dict:
    sparql = example.get("sparql", "")

    databases = [db for iri, db in _IRI_TO_DB.items() if iri in sparql]
    has_federation = bool(re.search(r"\bSERVICE\b", sparql, re.IGNORECASE))
    has_aggregation = bool(
        re.search(r"\b(COUNT|AVG|SUM|GROUP\s+BY)\b", sparql, re.IGNORECASE)
    )

    graph_count = len(re.findall(r"\bGRAPH\b", sparql, re.IGNORECASE))
    service_count = len(re.findall(r"\bSERVICE\b", sparql, re.IGNORECASE))
    challenge_level = 1 if (graph_count + service_count) <= 1 else 2

    patterns: list[str] = []
    if len(databases) == 1:
        patterns.append("single_graph")
    if len(databases) > 1:
        patterns.append("multi_graph")
        patterns.append("cross_database")
    if has_federation:
        patterns.append("federated")
    if has_aggregation:
        patterns.append("aggregation")
    if re.search(r"\b(CONTAINS|REGEX)\b", sparql, re.IGNORECASE):
        patterns.append("string_match")

    return {
        "databases": databases,
        "challenge_level": challenge_level,
        "patterns": patterns,
        "has_federation": has_federation,
        "has_aggregation": has_aggregation,
    }


def _example_id(ex: dict) -> str:
    digest = hashlib.sha256((ex["nl"] + ex["sparql"]).encode()).digest()[:16]
    return str(uuid.UUID(bytes=digest))


def get_vector_store() -> PGVector:
    global _store
    if _store is None:
        _store = PGVector(
            embeddings=get_embeddings(),
            collection_name="sparql_examples",
            connection=settings.database_url,
            use_jsonb=True,
        )
    return _store


async def seed_store() -> None:
    global _store
    # Drop and recreate the collection on every startup to handle embedding
    # model changes (e.g., dimension shifts between Gemini and Ollama).
    # Safe because the corpus is static (24 hardcoded examples).
    with _seed_lock():
        _store = PGVector(
            embeddings=get_embeddings(),
            collection_name="sparql_examples",
            connection=settings.database_url,
            use_jsonb=True,
            pre_delete_collection=True,
        )
        docs = [
            Document(
                page_content=ex["nl"],
                metadata={"sparql": ex["sparql"], **enrich_example(ex)},
            )
            for ex in RAG_CORPUS
        ]
        ids = [_example_id(ex) for ex in RAG_CORPUS]
        _store.add_documents(docs, ids=ids)
