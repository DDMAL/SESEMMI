from unittest.mock import patch

from langchain_core.documents import Document

from app.graph.nodes.retrieve import _get_rag_examples


def test_rag_backfill_retains_database_matches_first():
    unrelated = Document(
        page_content="Unrelated", metadata={"sparql": "other", "databases": ["diamm"]}
    )
    related = Document(
        page_content="Jazz tracks",
        metadata={"sparql": "jazz", "databases": ["weimarjazz"]},
    )
    with (
        patch("app.rag.store.get_vector_store") as store,
        patch("app.graph.nodes.retrieve.settings") as settings,
    ):
        settings.rag_top_k = 2
        store.return_value.similarity_search.return_value = [unrelated, related]
        result = _get_rag_examples("Jazz tracks", ["weimarjazz"])
    assert [example["sparql"] for example in result] == ["jazz", "other"]
