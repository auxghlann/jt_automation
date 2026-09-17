import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = "app.log"
DEFAULT_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d]: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_dir: str | Path = DEFAULT_LOG_DIR,
    log_file: str = DEFAULT_LOG_FILE,
    log_level: str | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """Configures persistent rotating file logging for the application.
    
    Logging to a file preserves the clean interactive terminal/Rich UI
    and avoids stdio interference with FastMCP JSON-RPC communication.
    """
    target_dir = Path(log_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / log_file

    if log_level is None:
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, log_level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Check if a RotatingFileHandler targeting this log_path already exists
    abs_log_path = str(log_path.resolve())
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            if getattr(handler, "baseFilename", None) == abs_log_path:
                return root_logger

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    formatter = logging.Formatter(DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)

    # Suppress overly chatty external libraries at INFO level
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("google_auth_oauthlib").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger instance, ensuring logging is configured."""
    root_logger = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        setup_logging()
    return logging.getLogger(name)
