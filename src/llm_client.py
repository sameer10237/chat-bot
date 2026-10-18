from collections.abc import Sequence

import httpx

from . import config
from .errors import ChatbotError


class NvidiaClient:
    def __init__(
        self,
        api_key: str = config.NVIDIA_API_KEY,
        base_url: str = config.NVIDIA_BASE_URL,
        model: str = config.NVIDIA_MODEL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    async def generate(self, messages: Sequence[dict[str, str]]) -> str:
        if not self.api_key:
            raise ChatbotError("The language model API key is not configured.", 503)

        try:
            async with httpx.AsyncClient(
                timeout=60.0, transport=self.transport
            ) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": list(messages)},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ChatbotError("The language model request failed.", 502) from exc
        except httpx.RequestError as exc:
            raise ChatbotError("The language model is unavailable.", 502) from exc

        try:
            reply = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ChatbotError(
                "The language model returned an invalid response.", 502
            ) from exc

        if not isinstance(reply, str) or not reply.strip():
            raise ChatbotError("The language model returned an empty response.", 502)
        return reply.strip()
