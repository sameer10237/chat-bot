from collections.abc import Sequence

from .chatbot import ChatMessage
from .errors import ChatbotError

MESSAGE_TOKEN_OVERHEAD = 4


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return (len(text.encode("utf-8")) + 3) // 4


def trim_history(
    history: Sequence[ChatMessage],
    max_tokens: int,
) -> tuple[ChatMessage, ...]:
    if max_tokens < 0:
        raise ValueError("max_tokens must not be negative")

    recent = list(history)
    token_count = sum(
        estimate_tokens(message.content) + MESSAGE_TOKEN_OVERHEAD for message in recent
    )
    while recent and token_count > max_tokens:
        remove_count = (
            2
            if len(recent) > 1
            and recent[0].role == "user"
            and recent[1].role == "assistant"
            else 1
        )
        removed = recent[:remove_count]
        del recent[:remove_count]
        token_count -= sum(
            estimate_tokens(message.content) + MESSAGE_TOKEN_OVERHEAD
            for message in removed
        )
    return tuple(recent)


def calculate_history_budget(
    system_prompt: str,
    user_message: str,
    max_tokens: int,
) -> int:
    reserved_tokens = (
        estimate_tokens(system_prompt)
        + estimate_tokens(user_message)
        + MESSAGE_TOKEN_OVERHEAD * 2
    )
    if reserved_tokens > max_tokens:
        raise ChatbotError(
            "The message and system prompt exceed the configured context window.",
            422,
        )
    return max_tokens - reserved_tokens
