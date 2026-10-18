from collections.abc import Sequence

from . import config
from .chatbot import Chatbot, ChatMessage
from .llm_client import NvidiaClient
from .message_format import format_chat_messages
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
        messages = format_chat_messages(self.system_prompt, history, user_message)
        return await self.client.generate(messages)
