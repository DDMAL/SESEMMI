from app.rag.store import get_vector_store
from app.config import settings


def retrieve_examples(query: str, top_k: int | None = None) -> list[dict]:
    k = top_k if top_k is not None else settings.rag_top_k
    store = get_vector_store()
    results = store.similarity_search(query, k=k)
    return [
        {"nl": doc.page_content, "sparql": doc.metadata["sparql"]} for doc in results
    ]
