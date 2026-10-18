from collections.abc import Sequence

from . import config
from .chatbot import Chatbot, ChatMessage
from .context import MESSAGE_TOKEN_OVERHEAD, estimate_tokens, trim_history
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
        reserved_tokens = (
            estimate_tokens(self.system_prompt)
            + estimate_tokens(user_message)
            + MESSAGE_TOKEN_OVERHEAD * 2
        )
        history_budget = max(0, config.MAX_CONTEXT_TOKENS - reserved_tokens)
        recent_history = trim_history(history, history_budget)
        messages = format_chat_messages(
            self.system_prompt,
            recent_history,
            user_message,
        )
        return await self.client.generate(messages)
