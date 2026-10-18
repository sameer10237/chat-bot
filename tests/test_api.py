from fastapi.testclient import TestClient

from src.documents import Document
from src.main import app
from src.rag import RAGAnswer


class StubChatbot:
    async def answer(self, message, history):
        return RAGAnswer(
            reply=f"Answer to: {message}",
            sources=(
                Document(
                    "source-1",
                    "Knowledge text.",
                    {"title": "Admissions", "url": "https://example.test/admissions"},
                ),
            ),
        )


def test_health_and_chat_ui_routes():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        page = client.get("/")
        assert page.status_code == 200
        assert "chat-form" in page.text
        assert client.get("/static/app.js").status_code == 200


def test_chat_endpoint_returns_reply_and_sources():
    with TestClient(app) as client:
        app.state.chatbot = StubChatbot()
        response = client.post(
            "/api/chat",
            json={
                "message": "  How do I apply? ",
                "history": [{"role": "user", "content": "Hello"}],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Answer to: How do I apply?",
        "sources": [
            {
                "id": "source-1",
                "title": "Admissions",
                "url": "https://example.test/admissions",
                "category": None,
                "heading": None,
            }
        ],
    }


def test_chat_endpoint_rejects_blank_message():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "  "})

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Message must not be empty."
