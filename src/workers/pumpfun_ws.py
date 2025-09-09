from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import signal
import sys
import time
from contextlib import suppress
from typing import Any, Optional

import websockets

from src.core.json_logging import configure_logging
from src.core.config import get_config
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository


WS_URL = "wss://pumpportal.fun/api/data"


def _extract_payload(message: dict[str, Any]) -> Optional[dict[str, Any]]:
    # Возможные расположения полезной нагрузки
    for key in ("message", "payload", "data"):
        if isinstance(message.get(key), dict):
            return message[key]
    return message


def _extract_migration(data: dict[str, Any]) -> Optional[dict[str, Optional[str]]]:
    payload = _extract_payload(data) or {}
    # Heuristic: наличие ключа mint
    mint = payload.get("mint") or payload.get("token")
    if not mint:
        return None
    name = payload.get("name")
    symbol = payload.get("symbol") or payload.get("ticker")
    return {"mint": str(mint), "name": name, "symbol": symbol}


async def run_worker(run_seconds: Optional[int] = None) -> None:
    cfg = get_config()
    configure_logging(level=cfg.log_level, service=cfg.app_name + "-ws", version=cfg.app_version, env=cfg.app_env)
    log = logging.getLogger("pump_ws")
    end_at = time.monotonic() + run_seconds if run_seconds else None

    async def _connect_once() -> None:
        async with websockets.connect(
            WS_URL,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            open_timeout=5,
            max_size=2**20,
        ) as ws:
            log.info("connected", extra={"extra": {"url": WS_URL}})
            # subscribe
            sub_msg = {"method": "subscribeMigration"}
            await ws.send(json.dumps(sub_msg))
            log.info("subscribed", extra={"extra": {"method": "subscribeMigration"}})
            while True:
                if end_at and time.monotonic() >= end_at:
                    log.info("time_window_exceeded", extra={"extra": {"seconds": run_seconds}})
                    break
                raw = await ws.recv()
                try:
                    data = json.loads(raw)
                except Exception:  # noqa: BLE001
                    log.warning("non_json_message", extra={"extra": {"raw_len": len(raw) if isinstance(raw, (str, bytes)) else None}})
                    continue
                mig = _extract_migration(data)
                if not mig:
                    log.debug("message_ignored", extra={"extra": {"keys": list(data)[:5]}})
                    continue
                mint = mig["mint"]
                name = mig.get("name")
                symbol = mig.get("symbol")
                with SessionLocal() as sess:
                    repo = TokensRepository(sess)
                    inserted = repo.insert_monitoring(mint=mint, name=name, symbol=symbol)
                log.info(
                    "migration_processed",
                    extra={"extra": {"mint": mint, "name": name, "symbol": symbol, "inserted": inserted}},
                )

    # reconnect loop
    backoff = 1.0
    while True:
        try:
            await _connect_once()
            break
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log = logging.getLogger("pump_ws")
            log.warning("ws_error", extra={"extra": {"error": type(e).__name__}})
            if end_at and time.monotonic() >= end_at:
                log.info("time_window_exceeded_on_error", extra={"extra": {"seconds": run_seconds}})
                break
            await asyncio.sleep(backoff + random.uniform(0, 0.5))
            backoff = min(backoff * 2, 10)


def _main() -> int:
    # Получить желаемое время работы из env
    run_seconds_env = os.getenv("PUMPFUN_RUN_SECONDS")
    run_seconds: Optional[int] = None
    if run_seconds_env is not None:
        try:
            v = int(run_seconds_env)
            if v > 0:
                run_seconds = v
            else:
                run_seconds = None
        except Exception:
            run_seconds = None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop = asyncio.Event()

    def _handle_sig(*_args):
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(Exception):
            loop.add_signal_handler(sig, _handle_sig)

    async def _runner():
        task = asyncio.create_task(run_worker(run_seconds=run_seconds))
        await asyncio.wait({task}, return_when=asyncio.FIRST_COMPLETED)

    try:
        loop.run_until_complete(_runner())
        return 0
    finally:
        loop.stop()
        loop.close()


if __name__ == "__main__":
    sys.exit(_main())
