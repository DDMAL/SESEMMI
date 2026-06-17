"""Tests for app/rag/store.py — seeding and ID generation."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app.rag.store import _example_id, seed_store


@contextmanager
def _noop_lock():
    """Bypass the Postgres advisory lock so seed_store needs no real DB."""
    yield


def test_example_id_is_deterministic():
    """Same nl+sparql always produces the same ID."""
    ex = {"nl": "Find all DIAMM composers", "sparql": "SELECT ?p WHERE { }"}
    assert _example_id(ex) == _example_id(ex)


def test_example_id_differs_for_different_examples():
    """Different examples produce different IDs."""
    ex1 = {"nl": "Find composers", "sparql": "SELECT ?p WHERE { }"}
    ex2 = {"nl": "Find manuscripts", "sparql": "SELECT ?m WHERE { }"}
    assert _example_id(ex1) != _example_id(ex2)


async def test_seed_store_passes_deterministic_ids():
    """seed_store calls add_documents with stable IDs so re-seeding is idempotent."""
    mock_store = MagicMock()

    with (
        patch("app.rag.store.PGVector", return_value=mock_store),
        patch("app.rag.store._seed_lock", _noop_lock),
    ):
        await seed_store()
        first_ids = mock_store.add_documents.call_args[1]["ids"]

        await seed_store()
        second_ids = mock_store.add_documents.call_args[1]["ids"]

    assert first_ids == second_ids


async def test_seed_store_id_count_matches_corpus():
    """Number of IDs passed equals the number of corpus examples."""
    from app.rag.corpus import RAG_CORPUS

    mock_store = MagicMock()

    with (
        patch("app.rag.store.PGVector", return_value=mock_store),
        patch("app.rag.store._seed_lock", _noop_lock),
    ):
        await seed_store()

    ids = mock_store.add_documents.call_args[1]["ids"]
    assert len(ids) == len(RAG_CORPUS)
    assert len(ids) == len(set(ids))  # all IDs are unique
