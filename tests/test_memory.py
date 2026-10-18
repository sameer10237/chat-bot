import pytest

from src.chatbot import ChatMessage
from src.context import calculate_history_budget, estimate_tokens, trim_history
from src.errors import ChatbotError
from src.memory import ConversationMemory


def test_memory_tracks_recent_complete_exchanges():
    memory = ConversationMemory(max_turns=2)
    memory.add_exchange("first", "reply one")
    memory.add_exchange("second", "reply two")
    memory.add_exchange("third", "reply three")

    assert memory.messages == (
        ChatMessage(role="user", content="second"),
        ChatMessage(role="assistant", content="reply two"),
        ChatMessage(role="user", content="third"),
        ChatMessage(role="assistant", content="reply three"),
    )


def test_memory_can_be_cleared():
    memory = ConversationMemory()
    memory.add_exchange("hello", "hi")

    memory.clear()

    assert memory.messages == ()


def test_memory_requires_at_least_one_turn():
    with pytest.raises(ValueError, match="max_turns must be positive"):
        ConversationMemory(max_turns=0)


def test_token_estimate_handles_empty_and_unicode_text():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("🙂") == 1


def test_history_trimming_discards_oldest_messages_first():
    history = (
        ChatMessage(role="user", content="old"),
        ChatMessage(role="assistant", content="reply"),
        ChatMessage(role="user", content="new"),
    )

    assert trim_history(history, 6) == (history[-1],)


def test_history_trimming_preserves_complete_turns():
    history = (
        ChatMessage(role="user", content="old"),
        ChatMessage(role="assistant", content="reply"),
        ChatMessage(role="user", content="new"),
        ChatMessage(role="assistant", content="answer"),
    )

    assert trim_history(history, 12) == history[-2:]


def test_history_trimming_rejects_negative_budget():
    with pytest.raises(ValueError, match="max_tokens must not be negative"):
        trim_history((), -1)


def test_context_budget_rejects_prompt_larger_than_window():
    with pytest.raises(ChatbotError, match="exceed the configured context window"):
        calculate_history_budget("system", "question", 1)
