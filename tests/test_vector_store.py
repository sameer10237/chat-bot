import pytest

from src.documents import Document
from src.vector_store import SQLiteVectorStore


def test_vector_store_persists_and_ranks_by_cosine_similarity(tmp_path):
    path = tmp_path / "vectors.sqlite3"
    store = SQLiteVectorStore(path)
    store.upsert(Document("x", "along x", {"title": "X"}), [1.0, 0.0])
    store.upsert(Document("y", "along y", {"title": "Y"}), [0.0, 1.0])
    store.close()

    reopened = SQLiteVectorStore(path)
    try:
        results = reopened.search([0.9, 0.1], limit=1)
    finally:
        reopened.close()

    assert len(results) == 1
    assert results[0].document.id == "x"
    assert results[0].document.metadata["title"] == "X"
    assert results[0].score > 0.9


def test_vector_store_rejects_invalid_vectors(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    try:
        with pytest.raises(ValueError, match="finite numeric"):
            store.upsert(Document("bad", "bad", {}), [float("nan")])
    finally:
        store.close()


def test_vector_store_rejects_nonpositive_result_limit(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    try:
        with pytest.raises(ValueError, match="limit must be positive"):
            store.search([1.0], limit=0)
    finally:
        store.close()
