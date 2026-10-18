from .chatbot import ChatMessage


class ConversationMemory:
    def __init__(self, max_turns: int = 20) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.max_turns = max_turns
        self._messages: list[ChatMessage] = []

    @property
    def messages(self) -> tuple[ChatMessage, ...]:
        return tuple(self._messages)

    def add_exchange(self, user_message: str, assistant_message: str) -> None:
        self._messages.extend(
            (
                ChatMessage(role="user", content=user_message),
                ChatMessage(role="assistant", content=assistant_message),
            )
        )
        self._messages = self._messages[-self.max_turns * 2 :]

    def clear(self) -> None:
        self._messages.clear()
