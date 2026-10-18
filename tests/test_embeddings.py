import asyncio

import httpx
import pytest

from src.embeddings import NvidiaEmbeddingClient
from src.errors import ChatbotError


def test_embedding_client_returns_numeric_vector():
    client = NvidiaEmbeddingClient(
        api_key="test-key",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"data": [{"embedding": [0.25, -0.5]}]},
            )
        ),
    )

    assert asyncio.run(client.embed("campus facilities")) == [0.25, -0.5]


def test_embedding_client_rejects_non_json_response():
    client = NvidiaEmbeddingClient(
        api_key="test-key",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="not-json")
        ),
    )

    with pytest.raises(ChatbotError, match="invalid data"):
        asyncio.run(client.embed("campus facilities"))


def test_embedding_client_rejects_non_finite_values():
    client = NvidiaEmbeddingClient(
        api_key="test-key",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                text='{"data":[{"embedding":[NaN]}]}',
            )
        ),
    )

    with pytest.raises(ChatbotError, match="invalid vector"):
        asyncio.run(client.embed("campus facilities"))
