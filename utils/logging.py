import logging
from logging.handlers import RotatingFileHandler
import structlog
from typing import Any

from config.settings import settings
import os


def configure_logging() -> None:
    """Configure structlog with a rotating file handler and console output."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # ensure log directory exists
    os.makedirs(os.path.dirname(settings.logs_path), exist_ok=True)
    handler = RotatingFileHandler(
        settings.logs_path, maxBytes=100 * 1024 * 1024, backupCount=3
    )
    fmt = logging.Formatter("%(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


configure_logging()


def get_logger(name: str = "nova") -> Any:
    return structlog.get_logger(name)
