from __future__ import annotations

import logging
import os
import time
from typing import Dict, Iterable, List

import httpx


class SolanaRpcClient:
    """Lightweight JSON-RPC client for Solana public endpoints."""

    def __init__(self, endpoint: str | None = None, timeout: float = 10.0):
        self.endpoint = endpoint or os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self._client = httpx.Client(timeout=timeout, headers={"User-Agent": "ToTheMoonPoolClassifier/1.0"})
        self._log = logging.getLogger("solana_rpc_client")

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # pragma: no cover - defensive
            pass

    def get_account_owners(self, addresses: Iterable[str], batch_size: int = 50, delay_sec: float = 0.2) -> Dict[str, str]:
        """Fetch owner program id for each account address."""
        owners: Dict[str, str] = {}
        address_list = [addr for addr in addresses if addr]
        if not address_list:
            return owners

        for i in range(0, len(address_list), batch_size):
            chunk = address_list[i : i + batch_size]
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getMultipleAccounts",
                "params": [
                    chunk,
                    {"encoding": "base64", "commitment": "confirmed"},
                ],
            }
            try:
                response = self._client.post(self.endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                self._log.warning("rpc_request_failed", extra={"extra": {"error": str(exc), "addresses": len(chunk)}})
                continue

            result = data.get("result", {})
            values: List[dict] = result.get("value") or []

            for addr, account in zip(chunk, values):
                if account and isinstance(account, dict):
                    owner = account.get("owner")
                    if owner:
                        owners[addr] = owner

            if i + batch_size < len(address_list):
                time.sleep(delay_sec)

        return owners
