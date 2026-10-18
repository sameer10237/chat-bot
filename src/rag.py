from collections.abc import Sequence
from dataclasses import dataclass

from . import config
from .chatbot import Chatbot, ChatMessage
from .documents import Document, load_documents
from .embeddings import NvidiaEmbeddingClient
from .llm_chatbot import LLMChatbot
from .llm_client import NvidiaClient
from .validation import validate_user_message
from .vector_store import SearchResult, SQLiteVectorStore


@dataclass(frozen=True)
class RAGAnswer:
    reply: str
    sources: tuple[Document, ...]


class RAGEngine:
    def __init__(
        self,
        embedding_client: NvidiaEmbeddingClient,
        vector_store: SQLiteVectorStore,
        min_retrieval_score: float = config.MIN_RETRIEVAL_SCORE,
    ) -> None:
        if not -1 <= min_retrieval_score <= 1:
            raise ValueError("min_retrieval_score must be between -1 and 1")
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.min_retrieval_score = min_retrieval_score

    async def index_documents(self, documents: Sequence[Document]) -> None:
        for document in documents:
            embedding = await self.embedding_client.embed(document.content)
            self.vector_store.upsert(document, embedding)

    async def index_knowledge_base(self) -> int:
        documents = load_documents()
        await self.index_documents(documents)
        return len(documents)

    async def retrieve(self, query: str, limit: int = 4) -> list[SearchResult]:
        embedding = await self.embedding_client.embed(query)
        results = self.vector_store.search(embedding, limit=limit)
        return [
            result for result in results if result.score >= self.min_retrieval_score
        ]


class RAGChatbot(Chatbot):
    def __init__(
        self,
        engine: RAGEngine,
        client: NvidiaClient | None = None,
        system_prompt: str = config.SYSTEM_PROMPT,
    ) -> None:
        self.engine = engine
        self.llm = LLMChatbot(
            client=client or NvidiaClient(), system_prompt=system_prompt
        )

    async def respond(
        self,
        message: str,
        history: Sequence[ChatMessage] = (),
    ) -> str:
        return (await self.answer(message, history)).reply

    async def answer(
        self,
        message: str,
        history: Sequence[ChatMessage] = (),
    ) -> RAGAnswer:
        user_message = validate_user_message(message)
        results = await self.engine.retrieve(user_message)
        context = self._format_context(results)
        system_prompt = self.llm.system_prompt
        if context:
            system_prompt = f"{system_prompt}\n\nKnowledge base context:\n{context}"

        reply = await self.llm.respond_with_prompt(
            user_message,
            history,
            system_prompt,
        )
        return RAGAnswer(
            reply=reply,
            sources=tuple(result.document for result in results),
        )

    @staticmethod
    def _format_context(results: Sequence[SearchResult]) -> str:
        entries = []
        for index, result in enumerate(results, start=1):
            title = result.document.metadata.get("title", "Untitled document")
            url = result.document.metadata.get("url", "Unknown source")
            entries.append(f"[{index}] {title} ({url})\n{result.document.content}")
        return "\n\n".join(entries)
