#!/usr/bin/env python3
"""
Spam detection module for monitoring ComputeBudget instruction patterns
in token transactions to identify artificial trading activity.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import httpx
from sqlalchemy.orm import Session

from src.core.config import get_config
from src.adapters.db.deps import get_db
from src.adapters.repositories.tokens_repo import TokensRepository

logger = logging.getLogger(__name__)


class SpamDetector:
    """Detects spam patterns in token transactions."""
    
    # Default whitelist of wallets to ignore in spam detection (e.g., our own bots)
    DEFAULT_WHITELISTED_WALLETS = {
        "8vNwSvT1S8P99c9XmjfXfV4DSGZLfUoNFx63zngCuh54",  # NotArb bot wallet
    }
    
    def __init__(self, whitelisted_wallets: Optional[set] = None):
        config = get_config()
        self.helius_rpc_url = f"https://mainnet.helius-rpc.com/?api-key={config.helius_api_key}"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.whitelisted_wallets = whitelisted_wallets or self.DEFAULT_WHITELISTED_WALLETS
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def make_rpc_request(self, method: str, params: List) -> Dict:
        """Make async RPC request to Helius."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            response = await self.client.post(self.helius_rpc_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                logger.error(f"RPC Error: {result['error']}")
                return {}
            
            return result.get("result", {})
            
        except Exception as e:
            logger.error(f"RPC request failed: {e}")
            return {}
    
    async def get_token_signatures(self, mint_address: str, limit: int = 100) -> List[str]:
        """Get recent transaction signatures for a token."""
        try:
            result = await self.make_rpc_request("getSignaturesForAddress", [
                mint_address,
                {
                    "limit": limit,
                    "commitment": "confirmed"
                }
            ])
            
            return [sig["signature"] for sig in result] if result else []
            
        except Exception as e:
            logger.error(f"Error fetching signatures for {mint_address}: {e}")
            return []
    
    async def analyze_transaction_batch(self, signatures: List[str]) -> Dict[str, int]:
        """Analyze a batch of transactions for spam patterns."""
        instruction_counts = {
            "total_instructions": 0,
            "compute_budget_instructions": 0,
            "transfer_instructions": 0,
            "system_instructions": 0,
            "unknown_instructions": 0
        }
        
        # Process transactions in smaller batches to avoid rate limits
        batch_size = 10
        for i in range(0, len(signatures), batch_size):
            batch = signatures[i:i + batch_size]
            
            # Get transaction details for batch
            tasks = [self.get_transaction_details(sig) for sig in batch]
            transactions = await asyncio.gather(*tasks, return_exceptions=True)
            
            for tx in transactions:
                if isinstance(tx, Exception) or not tx:
                    continue
                
                try:
                    self._analyze_single_transaction(tx, instruction_counts)
                except Exception as e:
                    logger.debug(f"Error analyzing transaction: {e}")
                    continue
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        return instruction_counts
    
    async def get_transaction_details(self, signature: str) -> Optional[Dict]:
        """Get detailed transaction information."""
        try:
            result = await self.make_rpc_request("getTransaction", [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "confirmed"
                }
            ])
            
            return result if result else None
            
        except Exception as e:
            logger.debug(f"Error fetching transaction {signature}: {e}")
            return None
    
    def _analyze_single_transaction(self, tx: Dict, counts: Dict[str, int]) -> None:
        """Analyze a single transaction for instruction patterns."""
        transaction = tx.get("transaction", {})
        message = transaction.get("message", {})
        
        # Check if transaction is from whitelisted wallet
        account_keys = message.get("accountKeys", [])
        for account in account_keys:
            # Handle both string and dict formats
            pubkey = account if isinstance(account, str) else account.get("pubkey", "")
            if pubkey in self.whitelisted_wallets:
                logger.debug(f"Skipping transaction from whitelisted wallet: {pubkey[:8]}...")
                return  # Skip this transaction entirely
        
        instructions = message.get("instructions", [])
        
        for instruction in instructions:
            counts["total_instructions"] += 1
            
            program_id = instruction.get("programId", "")
            
            # Check for ComputeBudget program
            if "ComputeBudget111" in program_id:
                counts["compute_budget_instructions"] += 1
            
            # Check for other patterns
            elif "1111111111111111" in program_id:  # System Program
                counts["system_instructions"] += 1
            
            elif "parsed" in instruction:
                parsed = instruction["parsed"]
                inst_type = parsed.get("type", "")
                
                if inst_type in ["transfer", "transferChecked"]:
                    counts["transfer_instructions"] += 1
                else:
                    counts["unknown_instructions"] += 1
            else:
                counts["unknown_instructions"] += 1
    
    def calculate_spam_metrics(self, instruction_counts: Dict[str, int]) -> Dict[str, float]:
        """Calculate spam metrics from instruction counts."""
        total = instruction_counts.get("total_instructions", 0)
        compute_budget = instruction_counts.get("compute_budget_instructions", 0)
        
        if total == 0:
            return {
                "spam_percentage": 0.0,
                "risk_level": "unknown",
                "total_instructions": 0,
                "compute_budget_count": 0
            }
        
        spam_percentage = (compute_budget / total) * 100
        
        # Determine risk level (adjusted thresholds based on testing)
        if spam_percentage >= 70:
            risk_level = "high"
        elif spam_percentage >= 50:
            risk_level = "medium"
        elif spam_percentage >= 25:
            risk_level = "low"
        else:
            risk_level = "clean"
        
        return {
            "spam_percentage": round(spam_percentage, 2),
            "risk_level": risk_level,
            "total_instructions": total,
            "compute_budget_count": compute_budget,
            "transfer_count": instruction_counts.get("transfer_instructions", 0),
            "system_count": instruction_counts.get("system_instructions", 0)
        }
    
    async def analyze_token_spam(self, mint_address: str) -> Dict[str, any]:
        """Analyze spam patterns for a single token."""
        start_time = time.time()
        
        try:
            # Get recent signatures
            signatures = await self.get_token_signatures(mint_address, limit=100)
            
            if not signatures:
                logger.warning(f"No signatures found for token {mint_address}")
                return {
                    "mint_address": mint_address,
                    "error": "No transactions found",
                    "analysis_time": time.time() - start_time
                }
            
            # Analyze transactions
            instruction_counts = await self.analyze_transaction_batch(signatures[:20])  # Limit to 20 for speed
            
            # Calculate metrics
            spam_metrics = self.calculate_spam_metrics(instruction_counts)
            
            result = {
                "mint_address": mint_address,
                "timestamp": datetime.utcnow().isoformat(),
                "transactions_analyzed": len(signatures[:20]),
                "spam_metrics": spam_metrics,
                "analysis_time": round(time.time() - start_time, 2)
            }
            
            logger.info(f"Spam analysis for {mint_address[:8]}...: "
                       f"{spam_metrics['spam_percentage']:.1f}% spam "
                       f"({spam_metrics['risk_level']}) in {result['analysis_time']}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing spam for {mint_address}: {e}")
            return {
                "mint_address": mint_address,
                "error": str(e),
                "analysis_time": time.time() - start_time
            }


class SpamMonitoringService:
    """Service for continuous spam monitoring of top tokens."""
    
    def __init__(self):
        self.monitoring_interval = 5  # seconds
        self.min_score_threshold = 50  # minimum score for monitoring
        self.detector = None  # Will be initialized with settings
    
    def _get_whitelisted_wallets(self, db: Session) -> set:
        """Get whitelisted wallets from settings."""
        try:
            from src.domain.settings.service import get_setting
            whitelist_str = get_setting(db, "spam_whitelist_wallets", "")
            
            if not whitelist_str:
                return SpamDetector.DEFAULT_WHITELISTED_WALLETS
            
            # Parse comma-separated list
            wallets = {w.strip() for w in whitelist_str.split(",") if w.strip()}
            logger.info(f"Loaded {len(wallets)} whitelisted wallets for spam detection")
            return wallets
            
        except Exception as e:
            logger.warning(f"Error loading whitelist, using defaults: {e}")
            return SpamDetector.DEFAULT_WHITELISTED_WALLETS
        
    async def get_tokens_to_monitor(self, db: Session) -> List[str]:
        """Get list of token mint addresses that should be monitored."""
        try:
            tokens_repo = TokensRepository(db)
            
            # Get active tokens with score above threshold
            tokens = tokens_repo.get_active_tokens_above_score(self.min_score_threshold)
            
            mint_addresses = [token.mint_address for token in tokens]
            
            logger.info(f"Found {len(mint_addresses)} tokens to monitor for spam")
            return mint_addresses
            
        except Exception as e:
            logger.error(f"Error getting tokens to monitor: {e}")
            return []
    
    async def monitor_spam_continuously(self):
        """Continuously monitor spam for top tokens."""
        logger.info("Starting continuous spam monitoring...")
        
        while True:
            try:
                # Get current database session
                db = next(get_db())
                
                try:
                    # Initialize detector with current whitelist settings
                    whitelisted_wallets = self._get_whitelisted_wallets(db)
                    
                    async with SpamDetector(whitelisted_wallets=whitelisted_wallets) as detector:
                        # Get tokens to monitor
                        mint_addresses = await self.get_tokens_to_monitor(db)
                        
                        if not mint_addresses:
                            logger.info("No tokens to monitor, waiting...")
                            await asyncio.sleep(self.monitoring_interval)
                            continue
                        
                        # Analyze spam for each token
                        spam_results = []
                        for mint_address in mint_addresses:
                            try:
                                result = await detector.analyze_token_spam(mint_address)
                                spam_results.append(result)
                                
                                # Store result in database (implement this)
                                await self._store_spam_result(db, result)
                                
                            except Exception as e:
                                logger.error(f"Error analyzing {mint_address}: {e}")
                                continue
                        
                        # Log summary
                        if spam_results:
                            high_spam_count = sum(1 for r in spam_results 
                                                if r.get("spam_metrics", {}).get("risk_level") in ["high", "medium"])
                            
                            logger.info(f"Spam monitoring cycle complete: "
                                       f"{len(spam_results)} tokens analyzed, "
                                       f"{high_spam_count} with high/medium spam risk")
                        
                finally:
                    db.close()
                
                # Wait before next cycle
                await asyncio.sleep(self.monitoring_interval)
                    
                except Exception as e:
                    logger.error(f"Error in spam monitoring cycle: {e}")
                    await asyncio.sleep(self.monitoring_interval)
    
    async def _store_spam_result(self, db: Session, result: Dict) -> None:
        """Store spam analysis result in database."""
        try:
            # TODO: Implement database storage
            # For now, just log the result
            
            mint_address = result.get("mint_address", "unknown")
            spam_metrics = result.get("spam_metrics", {})
            
            if spam_metrics:
                spam_pct = spam_metrics.get("spam_percentage", 0)
                risk_level = spam_metrics.get("risk_level", "unknown")
                
                logger.info(f"SPAM RESULT: {mint_address[:8]}... = {spam_pct:.1f}% ({risk_level})")
            
        except Exception as e:
            logger.error(f"Error storing spam result: {e}")


# Utility functions for manual testing
async def analyze_single_token(mint_address: str) -> Dict:
    """Analyze spam for a single token (for testing)."""
    async with SpamDetector() as detector:
        return await detector.analyze_token_spam(mint_address)


async def test_spam_detection():
    """Test spam detection on known tokens."""
    test_tokens = [
        "J4UBm5kvMSHeUwbNgZW4ySpCHBvS7LXknZ7rqQR9pump",  # Known spammy token
        "So11111111111111111111111111111111111111112",   # WSOL (should be clean)
    ]
    
    async with SpamDetector() as detector:
        for token in test_tokens:
            print(f"\n🔍 Analyzing {token}...")
            result = await detector.analyze_token_spam(token)
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                metrics = result.get("spam_metrics", {})
                print(f"📊 Spam: {metrics.get('spam_percentage', 0):.1f}% "
                      f"({metrics.get('risk_level', 'unknown')})")
                print(f"⏱️  Analysis time: {result.get('analysis_time', 0):.2f}s")


if __name__ == "__main__":
    # Test the spam detection
    asyncio.run(test_spam_detection())