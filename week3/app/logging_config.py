# Week 3 Day 5: logging configuration
# OutreachOS - AI sales outreach tool
# Sets up console + rotating file logging with a request id on every line.

import logging
import logging.handlers
import os
import uuid
import sys


# A simple request-id holder. In production you would use a middleware
# to set this per request. Here we generate one per log call for clarity.
_request_id_var: str | None = None


def set_request_id(request_id: str) -> None:
    """Set the request id for the current logging context."""
    global _request_id_var
    _request_id_var = request_id


def get_request_id() -> str:
    """Get the current request id, generating one if none is set."""
    global _request_id_var
    if _request_id_var is None:
        _request_id_var = str(uuid.uuid4())[:8]
    return _request_id_var


class RequestIdFormatter(logging.Formatter):
    """Adds a request id field to every log record."""

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = get_request_id()
        return super().format(record)


def setup_logging(log_file: str = "logs/app.log") -> None:
    """Configure console and rotating file logging.

    - Console: INFO and above.
    - File: DEBUG and above, rotates at 1 MB, keeps 3 backups.
    - Each line: timestamp | level | request_id | message
    Never log request bodies or secrets.
    """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = RequestIdFormatter(
        fmt="%(asctime)s | %(levelname)-8s | req=%(request_id)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)