from .errors import ChatbotError

MAX_MESSAGE_LENGTH = 1200


def validate_user_message(message: str) -> str:
    normalized = message.strip()
    if not normalized:
        raise ChatbotError("Message must not be empty.", 422)
    if len(normalized) > MAX_MESSAGE_LENGTH:
        raise ChatbotError(
            f"Message must be at most {MAX_MESSAGE_LENGTH} characters.",
            422,
        )
    return normalized
