import asyncio
from collections.abc import Callable

from .chatbot import Chatbot
from .memory import ConversationMemory


async def run_cli(
    chatbot: Chatbot,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    memory = ConversationMemory()
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

        reply = await chatbot.respond(message, memory.messages)
        output_fn(f"Assistant: {reply}")
        memory.add_exchange(message, reply)


def main(chatbot: Chatbot) -> None:
    asyncio.run(run_cli(chatbot))
