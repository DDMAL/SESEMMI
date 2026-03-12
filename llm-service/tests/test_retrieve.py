from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.rag.retrieve import retrieve_examples


def test_retrieve_examples_returns_correct_format():
    mock_docs = [
        Document(
            page_content="Find all songs", metadata={"sparql": "SELECT ?s WHERE { }"}
        ),
        Document(
            page_content="Find all artists", metadata={"sparql": "SELECT ?a WHERE { }"}
        ),
    ]
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = mock_docs

    with patch("app.rag.retrieve.get_vector_store", return_value=mock_store):
        results = retrieve_examples("Find music")

    assert len(results) == 2
    assert results[0] == {"nl": "Find all songs", "sparql": "SELECT ?s WHERE { }"}
    assert results[1] == {"nl": "Find all artists", "sparql": "SELECT ?a WHERE { }"}


def test_retrieve_examples_uses_default_top_k():
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = []

    with (
        patch("app.rag.retrieve.get_vector_store", return_value=mock_store),
        patch("app.rag.retrieve.settings") as mock_settings,
    ):
        mock_settings.rag_top_k = 5
        retrieve_examples("test query")

    mock_store.similarity_search.assert_called_once_with("test query", k=5)


def test_retrieve_examples_custom_top_k():
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = []

    with patch("app.rag.retrieve.get_vector_store", return_value=mock_store):
        retrieve_examples("test query", top_k=3)

    mock_store.similarity_search.assert_called_once_with("test query", k=3)
