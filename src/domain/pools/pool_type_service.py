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

    def _resolve_metadata(self, addresses: List[str]) -> Dict[str, Dict[str, str]]:
        """Fetch or populate pool metadata for the provided addresses."""
        if not addresses:
            return {}

        metadata = self.repo.get_many(addresses)
        missing = [
            addr
            for addr in addresses
            if addr not in metadata or metadata[addr].get("pool_type") in (None, UNKNOWN_POOL_TYPE)
        ]

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

        return {addr: metadata.get(addr, {}) for addr in addresses}

    def annotate_metrics_pools(self, metrics: dict) -> List[dict]:
        """Ensure metrics['pools'] contains classified pools and strip unknown ones."""
        pools = metrics.get("pools")
        if not isinstance(pools, list):
            self._log.debug("No pools list found in metrics")
            return []

        self._log.debug(f"Processing {len(pools)} pools for classification")

        addresses = [
            str(pool.get("address"))
            for pool in pools
            if isinstance(pool, dict) and pool.get("address")
        ]

        if not addresses:
            self._log.warning("No pool addresses found to classify")
            return []

        metadata = self._resolve_metadata(addresses)
        self._log.debug(f"Resolved metadata for {len(metadata)} addresses")

        classified: List[dict] = []
        unknown_count = 0
        for pool in pools:
            if not isinstance(pool, dict):
                continue
            addr = pool.get("address")
            info = metadata.get(str(addr)) if addr else None
            pool_type = pool.get("pool_type")
            owner_program = pool.get("owner_program")

            if info:
                resolved_type = info.get("pool_type")
                resolved_owner = info.get("owner_program")
            else:
                # If there is no RPC-derived info, the type is unknown.
                # Do not fall back to the dexscreener type.
                resolved_type = UNKNOWN_POOL_TYPE
                resolved_owner = None

            if not resolved_type or resolved_type == UNKNOWN_POOL_TYPE:
                unknown_count += 1
                self._log.debug(f"Pool {addr} has unknown type, skipping")
                continue

            pool["pool_type"] = resolved_type
            if resolved_owner:
                pool["owner_program"] = resolved_owner
            classified.append(pool)

        self._log.info(f"Classified {len(classified)} pools, {unknown_count} unknown")
        metrics["pools"] = classified
        return classified

    def insert_primary_pool_type(self, metrics: dict) -> Optional[str]:
        """Determine and embed primary pool type into metrics (for legacy table)."""
        pools = self.annotate_metrics_pools(metrics)
        pool_type_counts = Counter(
            pool.get("pool_type")
            for pool in pools
            if isinstance(pool, dict) and isinstance(pool.get("pool_type"), str)
        )

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
