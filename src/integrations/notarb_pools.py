"""
NotArb Pool URLs Generator

Generates pool URLs for top-scoring tokens compatible with NotArb onchain-bot
URL-based markets format: https://github.com/NotArb/Release/tree/main/onchain-bot#url-based-markets
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.adapters.db.deps import get_db
from src.adapters.db.models import Token, TokenScore
from src.domain.settings.service import SettingsService

logger = logging.getLogger(__name__)


class NotArbPoolsGenerator:
    """Generates pool URLs for NotArb onchain-bot"""
    
    def __init__(self, output_path: str = "notarb_pools.json"):
        self.output_path = Path(output_path)
        self.db = next(get_db())
        self.settings = SettingsService(self.db)
        
    def get_notarb_min_score(self) -> float:
        """Get minimum score threshold for NotArb from settings"""
        try:
            min_score = self.settings.get("notarb_min_score")
            return float(min_score) if min_score else 0.5
        except Exception:
            return 0.5
    
    def get_top_tokens_with_pools(self, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get top tokens with their pool information
        
        Args:
            limit: Maximum number of tokens to return
            
        Returns:
            List of token data with pools
        """
        try:
            min_score = self.get_notarb_min_score()
            
            # Get top tokens above threshold with latest scores
            from sqlalchemy.orm import aliased
            
            # Subquery for latest score per token
            from sqlalchemy import func
            latest_score_subq = (
                self.db.query(
                    TokenScore.token_id,
                    func.max(TokenScore.created_at).label('max_created_at')
                )
                .group_by(TokenScore.token_id)
                .subquery()
            )
            
            latest_score = (
                self.db.query(
                    TokenScore.token_id,
                    TokenScore.score.label('latest_score'),
                    TokenScore.smoothed_score.label('smoothed_score')
                )
                .join(
                    latest_score_subq,
                    (TokenScore.token_id == latest_score_subq.c.token_id) &
                    (TokenScore.created_at == latest_score_subq.c.max_created_at)
                )
                .subquery()
            )
            
            tokens = (
                self.db.query(Token, latest_score.c.latest_score, latest_score.c.smoothed_score)
                .join(latest_score, Token.id == latest_score.c.token_id)
                .filter(
                    Token.status == "active",
                    latest_score.c.smoothed_score >= min_score  # Use smoothed score
                )
                .order_by(desc(latest_score.c.smoothed_score))
                .limit(limit)
                .all()
            )
            
            result = []
            for token, latest_score, smoothed_score in tokens:
                # Get pools for this token from latest snapshot
                from src.adapters.repositories.tokens_repo import TokensRepository
                from src.adapters.services.dexscreener_client import DexScreenerClient
                
                repo = TokensRepository(self.db)
                snap = repo.get_latest_snapshot(token.id)
                pools = []
                
                if snap and snap.metrics and isinstance(snap.metrics, dict) and "pools" in snap.metrics:
                    exclude = {"pumpfun"}
                    pools = [
                        p for p in (snap.metrics.get("pools") or [])
                        if isinstance(p, dict) and str(p.get("dex") or "") not in exclude and (p.get("is_wsol") or p.get("is_usdc"))
                    ]
                else:
                    # Fallback: get current pairs directly
                    pairs = DexScreenerClient(timeout=5.0).get_pairs(token.mint_address)
                    if pairs:
                        _WSOL = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
                        _USDC = {"USDC", "usdc"}
                        exclude = {"pumpfun"}
                        for p in pairs:
                            try:
                                base = (p.get("baseToken") or {})
                                quote = (p.get("quoteToken") or {})
                                dex_id = str(p.get("dexId") or "")
                                if str(base.get("address")) == token.mint_address and str(quote.get("symbol", "")).upper() in (_WSOL | _USDC) and dex_id not in exclude:
                                    pools.append({
                                        "address": p.get("pairAddress") or p.get("address"),
                                        "dex": dex_id,
                                        "quote": quote.get("symbol"),
                                    })
                            except Exception:
                                continue
                
                if pools:
                    token_data = {
                        "mint_address": token.mint_address,
                        "symbol": token.symbol or "UNKNOWN",
                        "name": token.name or "Unknown Token",
                        "score": float(smoothed_score or latest_score or 0),
                        "liquidity_usd": 0,  # Will be calculated from pools
                        "pools": []
                    }
                    
                    # Import pool type classification
                    from src.domain.pools.pool_types import get_pool_type, get_pool_type_stats
                    
                    for pool in pools:
                        pool_type = get_pool_type(pool.get("dex", ""))
                        token_data["pools"].append({
                            "address": pool.get("address"),
                            "dex": pool.get("dex"),
                            "quote": pool.get("quote"),
                            "type": pool_type.value
                        })
                    
                    # Add pool type statistics to token data
                    pool_stats = get_pool_type_stats(pools)
                    token_data["pool_types"] = pool_stats
                    
                    result.append(token_data)
            
            logger.info(f"Retrieved {len(result)} tokens with pools for NotArb")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving tokens with pools: {e}")
            return []
    
    def generate_token_pools_with_metadata(self, tokens_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate token pools with metadata for NotArb bot
        
        Args:
            tokens_data: List of token data with pools
            
        Returns:
            Dictionary with metadata and token pool groups
        """
        result = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generator": "ToTheMoon Scoring System",
                "min_score_threshold": self.get_notarb_min_score(),
                "total_tokens": len(tokens_data)
            },
            "tokens": []
        }
        
        for token in tokens_data:
            # Get all pool addresses for this specific token mint
            pool_addresses = [pool["address"] for pool in token["pools"]]
            if pool_addresses:  # Only add if token has pools
                token_info = {
                    "mint_address": token["mint_address"],
                    "symbol": token["symbol"] or "UNKNOWN",
                    "name": token["name"] or "Unknown Token",
                    "score": token["score"],
                    "pools": pool_addresses
                }
                result["tokens"].append(token_info)
                
                # Log which token mint this group belongs to
                logger.info(
                    f"Added pool group for token {token['symbol']} "
                    f"(mint: {token['mint_address'][:8]}...) "
                    f"with {len(pool_addresses)} pools"
                )
        
        return result
    
    def export_pools_config(self) -> bool:
        """
        Export pool URLs to JSON file for NotArb bot (simple array format)
        
        Returns:
            True if export successful, False otherwise
        """
        try:
            # Get top tokens with pools
            tokens_data = self.get_top_tokens_with_pools(limit=3)
            
            if not tokens_data:
                logger.warning("No tokens with pools found for export")
                # Export empty array for NotArb compatibility
                pool_urls = []
            else:
                # Generate token pools with metadata
                pool_urls = self.generate_token_pools_with_metadata(tokens_data)
            
            # Ensure output directory exists
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if file exists
            if self.output_path.exists():
                backup_path = self.output_path.with_suffix('.json.backup')
                self.output_path.rename(backup_path)
                logger.info(f"Created backup: {backup_path}")
            
            # Atomic write: write to temp file first, then rename
            temp_path = self.output_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(pool_urls, f, indent=2, ensure_ascii=False)
            
            # Atomic rename (prevents partial reads)
            temp_path.rename(self.output_path)
            
            total_tokens = len(pool_urls.get("tokens", [])) if isinstance(pool_urls, dict) else 0
            logger.info(f"Successfully exported {total_tokens} token pool groups to {self.output_path}")
            
            # Log exported tokens
            if tokens_data:
                for i, token in enumerate(tokens_data, 1):
                    logger.info(
                        f"#{i} {token['symbol']} ({token['mint_address'][:8]}...) "
                        f"Score: {token['score']:.3f}, Pools: {len(token['pools'])}"
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting pools config: {e}")
            return False
    
    def get_token_pools_list(self) -> List[List[str]]:
        """
        Get just the list of token pools (for backward compatibility)
        
        Returns:
            List where each inner list contains all pool addresses for one token
        """
        tokens_data = self.get_top_tokens_with_pools(limit=3)
        result = self.generate_token_pools_with_metadata(tokens_data)
        
        # Extract just the pools for backward compatibility
        return [token["pools"] for token in result.get("tokens", [])]
    
    def get_token_pools_with_metadata(self) -> Dict[str, Any]:
        """
        Get token pools with full metadata
        
        Returns:
            Dictionary with metadata and token information
        """
        tokens_data = self.get_top_tokens_with_pools(limit=3)
        return self.generate_token_pools_with_metadata(tokens_data)


def export_notarb_pools(output_path: str = "notarb_pools.json") -> bool:
    """
    Convenience function to export token pools for NotArb bot
    
    Args:
        output_path: Path to output JSON file
        
    Returns:
        True if export successful, False otherwise
    """
    generator = NotArbPoolsGenerator(output_path)
    return generator.export_pools_config()


if __name__ == "__main__":
    # CLI usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Export pool URLs for NotArb onchain-bot")
    parser.add_argument("--output", "-o", default="notarb_pools.json", 
                       help="Output JSON file path")
    parser.add_argument("--list-only", "-l", action="store_true",
                       help="Only print URLs to stdout")
    
    args = parser.parse_args()
    
    generator = NotArbPoolsGenerator(args.output)
    
    if args.list_only:
        token_pools = generator.get_token_pools_list()
        for pools in token_pools:
            print(pools)
    else:
        success = generator.export_pools_config()
        if success:
            print(f"✅ Successfully exported to {args.output}")
        else:
            print("❌ Export failed")