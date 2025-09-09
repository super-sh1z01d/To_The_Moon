import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Attach extra dict if provided
        if hasattr(record, "extra") and isinstance(record.extra, Mapping):
            payload.update(record.extra)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO", service: Optional[str] = None, version: Optional[str] = None, env: Optional[str] = None) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    # Reset handlers to avoid duplication on reload
    root.handlers = [handler]

    # Propagate uvicorn access logs through root as JSON
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

    # Emit initial line
    logging.getLogger("startup").info(
        "service_started",
        extra={
            "extra": {"service": service or "to-the-moon", "version": version or "unknown", "env": env or "dev"}
        },
    )
