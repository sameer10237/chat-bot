from src.chatbot import ChatMessage
from src.message_format import format_chat_messages


def test_format_chat_messages_preserves_order_and_roles():
    history = (
        ChatMessage(role="user", content="First question"),
        ChatMessage(role="assistant", content="First answer"),
    )

    assert format_chat_messages("Be helpful.", history, "Next question") == [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Next question"},
    ]
