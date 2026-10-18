import asyncio

import pytest

from src import config
from src.errors import ChatbotError
from src.index_knowledge import index_knowledge_base


def test_indexing_requires_a_real_api_key(monkeypatch):
    monkeypatch.setattr(config, "NVIDIA_API_KEY", "your_nvidia_api_key_here")

    with pytest.raises(ChatbotError, match="Configure NVIDIA_API_KEY"):
        asyncio.run(index_knowledge_base())
