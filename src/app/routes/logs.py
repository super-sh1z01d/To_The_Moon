from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from src.app.logs_buffer import LOG_BUFFER, SEEN_LOGGERS


router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=list[dict])
def get_logs(
    limit: int = Query(200, ge=1, le=500),
    levels: Optional[str] = Query(None, description="Comma-separated levels: DEBUG,INFO,WARNING,ERROR,CRITICAL"),
    loggers: Optional[str] = Query(None, description="Comma-separated logger names to include"),
    contains: Optional[str] = Query(None, description="Substring to search in message/payload"),
    since: Optional[str] = Query(None, description="ISO timestamp; return logs with ts >= since"),
) -> List[Dict[str, Any]]:
    items = list(LOG_BUFFER)

    # Parse filters
    level_set = None
    if levels:
        level_set = {s.strip().upper() for s in levels.split(",") if s.strip()}
    logger_set = None
    if loggers:
        logger_set = {s.strip() for s in loggers.split(",") if s.strip()}
    contains_l = (contains or "").lower() if contains else None
    since_dt = None
    if since:
        try:
            # Support timezone-aware ISO; fallback best-effort
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except Exception:
            since_dt = None

    def _match(entry: Dict[str, Any]) -> bool:
        if level_set and str(entry.get("level", "")).upper() not in level_set:
            return False
        if logger_set and str(entry.get("logger", "")) not in logger_set:
            return False
        if contains_l:
            blob = str(entry.get("msg", "")) + " " + str(entry)
            if contains_l not in blob.lower():
                return False
        if since_dt:
            try:
                ets = str(entry.get("ts"))
                edt = datetime.fromisoformat(ets.replace("Z", "+00:00"))
                if edt < since_dt:
                    return False
            except Exception:
                # If timestamp parse fails, do not include
                return False
        return True

    filtered = [e for e in items if _match(e)]
    # Return tail-most entries up to limit
    if len(filtered) > limit:
        filtered = filtered[-limit:]
    return filtered


@router.get("/meta", response_model=dict)
def get_logs_meta() -> Dict[str, Any]:
    return {
        "loggers": sorted(SEEN_LOGGERS),
        "hint": "Use /logs?levels=INFO,ERROR&loggers=scheduler,validator&contains=foo&limit=200",
    }


@router.delete("/", response_model=dict)
def clear_logs() -> Dict[str, Any]:
    count = len(LOG_BUFFER)
    LOG_BUFFER.clear()
    return {"cleared": count}
