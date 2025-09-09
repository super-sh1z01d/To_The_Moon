from __future__ import annotations

import logging
from typing import Any, Optional

import httpx


class DexScreenerClient:
    BASE_URL = "https://api.dexscreener.com/token-pairs/v1/solana/"

    def __init__(self, timeout: float = 5.0):
        self._timeout = timeout
        self._log = logging.getLogger("dexscreener")

    def _build_url(self, mint: str) -> str:
        return f"{self.BASE_URL}{mint}"

    def get_pairs(self, mint: str) -> Optional[list[dict[str, Any]]]:
        url = self._build_url(mint)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url)
        except Exception as e:  # noqa: BLE001
            self._log.warning("http_error", extra={"extra": {"mint": mint, "error": type(e).__name__}})
            return None
        if resp.status_code == 429:
            self._log.warning("rate_limited", extra={"extra": {"mint": mint, "status": resp.status_code}})
            return None
        if resp.status_code != 200:
            self._log.info("unexpected_status", extra={"extra": {"mint": mint, "status": resp.status_code}})
            return None
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            self._log.warning("non_json_response", extra={"extra": {"mint": mint}})
            return None
        pairs = data if isinstance(data, list) else data.get("pairs") if isinstance(data, dict) else None
        if not isinstance(pairs, list):
            self._log.info("no_pairs", extra={"extra": {"mint": mint}})
            return []
        return pairs

