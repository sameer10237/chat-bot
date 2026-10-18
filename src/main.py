import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api_models import ChatRequest, ChatResponse, SourceResponse
from .chatbot import ChatMessage
from .config import APP_NAME, NVIDIA_MODEL
from .errors import ChatbotError
from .logging_config import configure_logging
from .rag import RAGChatbot
from .validation import validate_user_message

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=APP_NAME,
    description="API for the chatbot application.",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "model": NVIDIA_MODEL}


def get_chatbot(request: Request) -> RAGChatbot:
    chatbot = getattr(request.app.state, "chatbot", None)
    if chatbot is None:
        raise ChatbotError("The chatbot service is not initialized.", 503)
    return chatbot


@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(payload: ChatRequest, request: Request) -> ChatResponse:
    chatbot = get_chatbot(request)
    message = validate_user_message(payload.message)
    history = tuple(
        ChatMessage(role=item.role, content=item.content.strip())
        for item in payload.history
        if item.content.strip()
    )
    answer = await chatbot.answer(message, history)
    sources = [
        SourceResponse(
            id=document.id,
            title=_metadata_text(document.metadata.get("title")),
            url=_metadata_text(document.metadata.get("url")),
            category=_metadata_text(document.metadata.get("category")),
            heading=_metadata_text(document.metadata.get("heading")),
        )
        for document in answer.sources
    ]
    return ChatResponse(reply=answer.reply, sources=sources)


@app.exception_handler(ChatbotError)
async def handle_chatbot_error(request: Request, exc: ChatbotError) -> JSONResponse:
    logger.error("Chatbot request failed at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.message}},
    )


def _metadata_text(value: str | int | None) -> str | None:
    return value if isinstance(value, str) else None
