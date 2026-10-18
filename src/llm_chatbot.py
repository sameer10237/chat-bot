from collections.abc import Sequence

from . import config
from .chatbot import Chatbot, ChatMessage
from .llm_client import NvidiaClient
from .validation import validate_user_message


class LLMChatbot(Chatbot):
    def __init__(
        self,
        client: NvidiaClient | None = None,
        system_prompt: str = config.SYSTEM_PROMPT,
    ) -> None:
        self.client = client or NvidiaClient()
        self.system_prompt = system_prompt

    async def respond(
        self,
        message: str,
        history: Sequence[ChatMessage] = (),
    ) -> str:
        user_message = validate_user_message(message)
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(
            {"role": item.role, "content": item.content} for item in history
        )
        messages.append({"role": "user", "content": user_message})
        return await self.client.generate(messages)
