import asyncio

from . import config
from .embeddings import NvidiaEmbeddingClient
from .errors import ChatbotError
from .rag import RAGEngine
from .vector_store import SQLiteVectorStore


async def index_knowledge_base() -> int:
    if (
        not config.NVIDIA_API_KEY
        or "your_nvidia_api_key_here" in config.NVIDIA_API_KEY.lower()
    ):
        raise ChatbotError(
            "Configure NVIDIA_API_KEY before indexing the knowledge base.",
            503,
        )

    vector_store = SQLiteVectorStore(config.VECTOR_DB_PATH)
    try:
        engine = RAGEngine(
            embedding_client=NvidiaEmbeddingClient(),
            vector_store=vector_store,
        )
        return await engine.index_knowledge_base()
    finally:
        vector_store.close()


def main() -> None:
    count = asyncio.run(index_knowledge_base())
    print(f"Indexed {count} knowledge documents.")


if __name__ == "__main__":
    main()
