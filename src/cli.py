import asyncio
from collections.abc import Callable

from .chatbot import Chatbot, ChatMessage


async def run_cli(
    chatbot: Chatbot,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    history: list[ChatMessage] = []
    output_fn("Chatbot ready. Type 'quit' or 'exit' to stop.")

    while True:
        try:
            message = input_fn("You: ").strip()
        except EOFError:
            output_fn("")
            return

        if message.lower() in {"quit", "exit"}:
            return
        if not message:
            continue

        reply = await chatbot.respond(message, history)
        output_fn(f"Assistant: {reply}")
        history.extend(
            (
                ChatMessage(role="user", content=message),
                ChatMessage(role="assistant", content=reply),
            )
        )


def main(chatbot: Chatbot) -> None:
    asyncio.run(run_cli(chatbot))
