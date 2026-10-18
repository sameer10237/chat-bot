import asyncio

from src.documents import Document
from src.rag import RAGChatbot, RAGEngine
from src.vector_store import SearchResult


class StubEmbeddingClient:
    async def embed(self, text):
        return [1.0]


class StubVectorStore:
    def search(self, embedding, limit):
        return [
            SearchResult(
                Document("doc-1", "Admission details.", {"title": "Admissions"}), 0.9
            )
        ]


class StubChatClient:
    def __init__(self):
        self.messages = None

    async def generate(self, messages):
        self.messages = messages
        return "The answer."


def test_rag_answer_injects_retrieved_context_and_returns_sources():
    client = StubChatClient()
    chatbot = RAGChatbot(
        engine=RAGEngine(StubEmbeddingClient(), StubVectorStore()),
        client=client,
        system_prompt="Use relevant facts.",
    )

    answer = asyncio.run(chatbot.answer("How do admissions work?"))

    assert answer.reply == "The answer."
    assert [source.id for source in answer.sources] == ["doc-1"]
    assert "Admission details." in client.messages[0]["content"]
    assert "Admissions" in client.messages[0]["content"]
    assert client.messages[-1] == {
        "role": "user",
        "content": "How do admissions work?",
    }
