from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Set


# Ring buffer for recent log records
MAX_LOG_RECORDS = 2000
LOG_BUFFER: Deque[Dict[str, Any]] = deque(maxlen=MAX_LOG_RECORDS)
SEEN_LOGGERS: Set[str] = set()


class BufferJsonHandler(logging.Handler):
    """Logging handler that stores JSON-like payloads in-memory."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            payload: Dict[str, Any] = {
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
                "module": record.module,
                "func": record.funcName,
                "line": record.lineno,
            }
            if hasattr(record, "extra") and isinstance(getattr(record, "extra"), dict):
                # Merge extra fields into the payload for easier filtering
                payload.update(record.extra)  # type: ignore[arg-type]
            LOG_BUFFER.append(payload)
            SEEN_LOGGERS.add(record.name)
        except Exception:
            # Avoid crashing on logging path
            pass


def attach_buffer_handler() -> None:
    """Attach BufferJsonHandler to root logger (idempotent)."""
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, BufferJsonHandler):
            return
    root.addHandler(BufferJsonHandler())

