from collections.abc import Sequence

from .chatbot import ChatMessage

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
    while recent and sum(
        estimate_tokens(message.content) + MESSAGE_TOKEN_OVERHEAD
        for message in recent
    ) > max_tokens:
        recent.pop(0)
    return tuple(recent)
