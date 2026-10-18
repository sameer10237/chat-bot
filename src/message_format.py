from collections.abc import Sequence

from .chatbot import ChatMessage


def format_chat_messages(
    system_prompt: str,
    history: Sequence[ChatMessage],
    user_message: str,
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": message.role, "content": message.content} for message in history
    )
    messages.append({"role": "user", "content": user_message})
    return messages
