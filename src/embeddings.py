import math

import httpx

from . import config
from .errors import ChatbotError


class NvidiaEmbeddingClient:
    def __init__(
        self,
        api_key: str = config.NVIDIA_API_KEY,
        base_url: str = config.NVIDIA_BASE_URL,
        model: str = config.NVIDIA_EMBEDDING_MODEL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    async def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise ChatbotError("Text to embed must not be empty.", 422)
        if not self.api_key:
            raise ChatbotError("The embedding API key is not configured.", 503)

        try:
            async with httpx.AsyncClient(
                timeout=60.0,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": text},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ChatbotError("The embedding request failed.", 502) from exc
        except httpx.RequestError as exc:
            raise ChatbotError("The embedding service is unavailable.", 502) from exc

        try:
            vector = response.json()["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ChatbotError(
                "The embedding service returned invalid data.", 502
            ) from exc

        if (
            not isinstance(vector, list)
            or not vector
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in vector
            )
        ):
            raise ChatbotError("The embedding service returned an invalid vector.", 502)
        return [float(value) for value in vector]
