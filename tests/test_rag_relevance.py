import asyncio

from src.documents import Document
from src.rag import RAGEngine
from src.vector_store import SearchResult


class StubEmbeddingClient:
    async def embed(self, text):
        return [1.0]


class StubVectorStore:
    def search(self, embedding, limit):
        return [
            SearchResult(Document("relevant", "Relevant.", {}), 0.8),
            SearchResult(Document("noise", "Unrelated.", {}), 0.1),
        ]


def test_retrieval_discards_low_relevance_results():
    engine = RAGEngine(
        embedding_client=StubEmbeddingClient(),
        vector_store=StubVectorStore(),
        min_retrieval_score=0.25,
    )

    results = asyncio.run(engine.retrieve("question"))

    assert [result.document.id for result in results] == ["relevant"]
