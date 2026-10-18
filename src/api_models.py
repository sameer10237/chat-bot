from typing import Literal

from pydantic import BaseModel, Field

from .validation import MAX_MESSAGE_LENGTH


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=50)


class SourceResponse(BaseModel):
    id: str
    title: str | None = None
    url: str | None = None
    category: str | None = None
    heading: str | None = None


class ChatResponse(BaseModel):
    reply: str
    sources: list[SourceResponse]
