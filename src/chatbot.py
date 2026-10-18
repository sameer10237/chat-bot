from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Sequence

ChatRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str


class Chatbot(ABC):
    @abstractmethod
    async def respond(
        self,
        message: str,
        history: Sequence[ChatMessage] = (),
    ) -> str:
        raise NotImplementedError
