import os
from pathlib import Path

from dotenv import load_dotenv

from .prompts import DEFAULT_SYSTEM_PROMPT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
load_dotenv(PROJECT_ROOT / ".env")

APP_NAME = os.getenv("APP_NAME", "Chatbot API").strip()
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip()
HOST = os.getenv("HOST", "127.0.0.1").strip()
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "6000"))
if MAX_CONTEXT_TOKENS < 1:
    raise ValueError("MAX_CONTEXT_TOKENS must be positive")
MIN_RETRIEVAL_SCORE = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.25"))
if not -1 <= MIN_RETRIEVAL_SCORE <= 1:
    raise ValueError("MIN_RETRIEVAL_SCORE must be between -1 and 1")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct").strip()
NVIDIA_EMBEDDING_MODEL = os.getenv(
    "NVIDIA_EMBEDDING_MODEL",
    "nvidia/nv-embedqa-e5-v5",
).strip()
NVIDIA_BASE_URL = os.getenv(
    "NVIDIA_BASE_URL",
    "https://integrate.api.nvidia.com/v1",
).rstrip("/")
CHUNKS_PATH = DATA_DIR / "sdit_chatbot_chunks.json"
VECTOR_DB_PATH = PROJECT_ROOT / "var" / "vector_store.sqlite3"
