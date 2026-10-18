from . import config
from .embeddings import NvidiaEmbeddingClient
from .llm_client import NvidiaClient
from .rag import RAGChatbot, RAGEngine
from .vector_store import SQLiteVectorStore


def create_chatbot() -> RAGChatbot:
    vector_store = SQLiteVectorStore(config.VECTOR_DB_PATH)
    engine = RAGEngine(
        embedding_client=NvidiaEmbeddingClient(),
        vector_store=vector_store,
    )
    return RAGChatbot(engine=engine, client=NvidiaClient())
