from langchain_postgres import PGVector
from langchain_core.documents import Document
from app.rag.embeddings import embeddings
from app.rag.corpus import RAG_CORPUS
from app.config import settings

_store: PGVector | None = None


def get_vector_store() -> PGVector:
    global _store
    if _store is None:
        _store = PGVector(
            embeddings=embeddings,
            collection_name="sparql_examples",
            connection=settings.database_url,
            use_jsonb=True,
        )
    return _store


async def seed_store() -> None:
    store = get_vector_store()
    docs = [
        Document(page_content=ex["nl"], metadata={"sparql": ex["sparql"]})
        for ex in RAG_CORPUS
    ]
    store.add_documents(docs)
