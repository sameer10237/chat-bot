import logging

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from .config import APP_NAME, NVIDIA_MODEL
from .errors import ChatbotError
from .logging_config import configure_logging

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


@app.exception_handler(ChatbotError)
async def handle_chatbot_error(request: Request, exc: ChatbotError) -> JSONResponse:
    logger.error("Chatbot request failed at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.message}},
    )
