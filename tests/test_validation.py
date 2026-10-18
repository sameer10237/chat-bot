import pytest

from src.errors import ChatbotError
from src.validation import MAX_MESSAGE_LENGTH, validate_user_message


def test_validate_user_message_trims_surrounding_whitespace():
    assert validate_user_message("  hello  ") == "hello"


@pytest.mark.parametrize("message", ["", " ", "\t\n"])
def test_validate_user_message_rejects_blank_input(message):
    with pytest.raises(ChatbotError) as error:
        validate_user_message(message)

    assert error.value.status_code == 422


def test_validate_user_message_rejects_oversized_input():
    with pytest.raises(ChatbotError) as error:
        validate_user_message("x" * (MAX_MESSAGE_LENGTH + 1))

    assert error.value.status_code == 422
