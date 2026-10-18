import asyncio
import json

import httpx
import pytest

from src.errors import ChatbotError
from src.llm_client import NvidiaClient


def test_generate_sends_messages_and_returns_reply():
    def handle_request(request):
        assert request.url == "https://llm.example/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert json.loads(request.content)["messages"] == [
            {"role": "user", "content": "Hello"}
        ]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": " Hi there. "}}]},
        )

    client = NvidiaClient(
        api_key="test-key",
        base_url="https://llm.example/v1/",
        model="test-model",
        transport=httpx.MockTransport(handle_request),
    )

    assert (
        asyncio.run(client.generate([{"role": "user", "content": "Hello"}]))
        == "Hi there."
    )


def test_generate_rejects_missing_api_key():
    client = NvidiaClient(api_key="")

    with pytest.raises(ChatbotError) as error:
        asyncio.run(client.generate([]))

    assert error.value.status_code == 503


def test_generate_rejects_malformed_provider_response():
    client = NvidiaClient(
        api_key="test-key",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
    )

    with pytest.raises(ChatbotError) as error:
        asyncio.run(client.generate([]))

    assert error.value.status_code == 502


def test_generate_maps_provider_http_errors():
    client = NvidiaClient(
        api_key="test-key",
        transport=httpx.MockTransport(lambda request: httpx.Response(429)),
    )

    with pytest.raises(ChatbotError) as error:
        asyncio.run(client.generate([]))

    assert error.value.status_code == 502
