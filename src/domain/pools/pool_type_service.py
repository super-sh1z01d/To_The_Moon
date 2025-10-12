from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from src.adapters.repositories.pool_metadata_repo import PoolMetadataRepository
from src.integrations.solana_rpc import SolanaRpcClient

# Map Solana AMM program IDs to human-readable pool types
PROGRAM_ID_MAP: Dict[str, str] = {
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "raydium_amm",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": "raydium_cpmm",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "raydium_clmm",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "meteora_dlmm",
    "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG": "meteora_damm_v2",
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "pumpfun_amm",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "orca_whirlpool",
    "GAMMA7meSFWaBXF25oSUgmGRwaW6sCMFLmBNiMSdbHVT": "goosefx_gamma",
}

UNKNOWN_POOL_TYPE = "unknown"


class PoolTypeService:
    """Resolve accurate pool types using on-chain owner program accounts."""

    def __init__(self, db: Session, rpc_client: Optional[SolanaRpcClient] = None):
        self._log = logging.getLogger("pool_type_service")
        self.repo = PoolMetadataRepository(db)
        self.rpc_client = rpc_client or SolanaRpcClient()

    def close(self) -> None:
        try:
            self.rpc_client.close()
        except Exception:  # pragma: no cover - defensive
            pass

    def enrich_pairs(self, pairs: Iterable[dict]) -> List[dict]:
        """Filter pairs to only those with resolved pool types and enrich metadata."""
        address_to_pair: Dict[str, dict] = {}
        addresses: List[str] = []

        for pair in pairs:
            address = pair.get("pairAddress") or pair.get("address")
            if not address:
                continue
            if address in address_to_pair:
                continue
            address_to_pair[address] = dict(pair)
            addresses.append(address)

        if not addresses:
            return []

        metadata = self.repo.get_many(addresses)
        missing = [addr for addr in addresses if addr not in metadata or metadata[addr]["pool_type"] == UNKNOWN_POOL_TYPE]

        if missing:
            owner_map = self.rpc_client.get_account_owners(missing)
            upserts: List[tuple[str, str, str]] = []
            for addr in missing:
                owner = owner_map.get(addr)
                if not owner:
                    continue
                pool_type = PROGRAM_ID_MAP.get(owner, UNKNOWN_POOL_TYPE)
                metadata[addr] = {"owner_program": owner, "pool_type": pool_type}
                upserts.append((addr, owner, pool_type))

            if upserts:
                self.repo.bulk_upsert(upserts)

        enriched_pairs: List[dict] = []
        for address, pair in address_to_pair.items():
            meta = metadata.get(address)
            if not meta:
                continue
            pool_type = meta.get("pool_type")
            if not pool_type or pool_type == UNKNOWN_POOL_TYPE:
                continue
            pair["pool_type"] = pool_type
            pair["owner_program"] = meta.get("owner_program")
            enriched_pairs.append(pair)

        return enriched_pairs

    def insert_primary_pool_type(self, metrics: dict) -> Optional[str]:
        """Determine and embed primary pool type into metrics (for legacy table)."""
        pool_type_counts = Counter()
        pools = metrics.get("pools")

        if isinstance(pools, list):
            for pool in pools:
                if not isinstance(pool, dict):
                    continue
                pool_type = pool.get("pool_type")
                if isinstance(pool_type, str) and pool_type:
                    pool_type_counts[pool_type] += 1

        primary_pool_type: Optional[str] = None
        if pool_type_counts:
            max_count = max(pool_type_counts.values())
            candidates = sorted(pt for pt, cnt in pool_type_counts.items() if cnt == max_count)
            primary_pool_type = candidates[0]

        if primary_pool_type:
            metrics["primary_pool_type"] = primary_pool_type

        return primary_pool_type

    def get_pool_type(self, address: str) -> Optional[str]:
        if not address:
            return None
        metadata = self.repo.get_many([address])
        info = metadata.get(address)
        if not info:
            return None
        pool_type = info.get("pool_type")
        return pool_type if pool_type and pool_type != UNKNOWN_POOL_TYPE else None
