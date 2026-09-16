"""Structured logging configuration for PillSync."""

import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configure standardized application logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("pillsync")
    logger.setLevel(log_level)
    logger.info("Logging initialized with level: %s", settings.LOG_LEVEL)
    return logger


logger = setup_logging()
