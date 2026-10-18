import logging

from src.logging_config import configure_logging


def test_configure_logging_sets_up_application_logging(caplog):
    configure_logging()

    with caplog.at_level(logging.INFO):
        logging.getLogger("src.tests").info("logging configuration test")

    assert "logging configuration test" in caplog.text
