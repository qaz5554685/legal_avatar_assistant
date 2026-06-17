import logging
import os
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

from globalVars import BASE_DIR

load_dotenv()

LOGGER_NAME = os.getenv("LOGGER_NAME") or "LegalAvatarAssistant"
LOGGER_SEVERITY = os.getenv("LOGGER_SEVERITY") or "INFO"

LOGGER_DIR = BASE_DIR / "log"
LOGGER_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = logging.Formatter("%(levelname)s | %(asctime)s | %(name)s | %(message)s")


def set_log_handler(logger_name: str = LOGGER_NAME) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        LOGGER_DIR / f"{logger_name}.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=9,
        encoding="utf-8",
    )
    handler.setFormatter(LOG_FORMAT)
    return handler


logging.basicConfig(
    level=logging.ERROR,
    handlers=[set_log_handler()],
)

PROJECT_LOGGER = logging.getLogger(LOGGER_NAME)
PROJECT_LOGGER.setLevel(getattr(logging, LOGGER_SEVERITY.upper(), logging.INFO))
