import asyncio

from src.chatbot import Chatbot, ChatMessage
from src.cli import run_cli


class RecordingChatbot(Chatbot):
    def __init__(self):
        self.histories = []

    async def respond(self, message, history=()):
        self.histories.append(tuple(history))
        return f"reply: {message}"


def test_cli_keeps_history_bounded_and_exits_cleanly():
    messages = iter([f"message {index}" for index in range(22)] + ["exit"])
    chatbot = RecordingChatbot()
    output = []

    asyncio.run(
        run_cli(
            chatbot,
            input_fn=lambda prompt: next(messages),
            output_fn=output.append,
        )
    )

    assert len(chatbot.histories[-1]) == 40
    assert chatbot.histories[-1][0] == ChatMessage(
        role="user",
        content="message 1",
    )
    assert output[-1] == "Assistant: reply: message 21"
