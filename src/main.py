from fastapi import FastAPI

from .config import APP_NAME

app = FastAPI(
    title=APP_NAME,
    description="API for the chatbot application.",
    version="0.1.0",
)
