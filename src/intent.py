import re
from dataclasses import dataclass
from enum import StrEnum


class Intent(StrEnum):
    GREETING = "greeting"
    KNOWLEDGE = "knowledge"
    EMPTY = "empty"


_GREETINGS = {"hello", "hi", "hey", "good morning", "good afternoon", "good evening"}


@dataclass(frozen=True)
class ParsedPrompt:
    text: str
    intent: Intent


def parse_prompt(message: str) -> ParsedPrompt:
    text = re.sub(r"\s+", " ", message).strip()
    if not text:
        return ParsedPrompt(text="", intent=Intent.EMPTY)

    normalized = text.casefold().strip(" .,!?")
    intent = Intent.GREETING if normalized in _GREETINGS else Intent.KNOWLEDGE
    return ParsedPrompt(text=text, intent=intent)
