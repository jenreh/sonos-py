"""Structured JSON logging setup."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(
    level: str = "WARNING",
    log_path: Path | None = None,
    json_logs: bool = False,
) -> None:
    """Configure root logger with optional JSON file handler."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    if not root.handlers:
        handler: logging.Handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(fmt)
        root.addHandler(handler)

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        if json_logs:
            file_handler.setFormatter(_JsonFormatter())
        else:
            file_handler.setFormatter(fmt)
        root.addHandler(file_handler)


class _JsonFormatter(logging.Formatter):
    """Minimal single-line JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
