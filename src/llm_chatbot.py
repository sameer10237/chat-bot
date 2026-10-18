from collections.abc import Sequence

from . import config
from .chatbot import Chatbot, ChatMessage
from .context import calculate_history_budget, trim_history
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
        return await self.respond_with_prompt(
            message,
            history,
            self.system_prompt,
        )

    async def respond_with_prompt(
        self,
        message: str,
        history: Sequence[ChatMessage],
        system_prompt: str,
    ) -> str:
        user_message = validate_user_message(message)
        history_budget = calculate_history_budget(
            system_prompt,
            user_message,
            config.MAX_CONTEXT_TOKENS,
        )
        recent_history = trim_history(history, history_budget)
        messages = format_chat_messages(
            system_prompt,
            recent_history,
            user_message,
        )
        return await self.client.generate(messages)
