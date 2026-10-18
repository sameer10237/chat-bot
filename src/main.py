import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from .api_models import ChatRequest, ChatResponse, SourceResponse
from .chatbot import ChatMessage
from .config import APP_NAME, CORS_ORIGINS, NVIDIA_MODEL
from .errors import ChatbotError
from .logging_config import configure_logging
from .rag import RAGChatbot
from .services import create_chatbot
from .validation import validate_user_message

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    chatbot = create_chatbot()
    application.state.chatbot = chatbot
    try:
        yield
    finally:
        chatbot.engine.vector_store.close()


app = FastAPI(
    title=APP_NAME,
    description="API for the chatbot application.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
    )
    return response


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
