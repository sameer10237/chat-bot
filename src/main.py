import logging

from fastapi import FastAPI

from .config import APP_NAME
from .logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=APP_NAME,
    description="API for the chatbot application.",
    version="0.1.0",
)
