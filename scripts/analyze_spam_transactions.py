#!/usr/bin/env python3
"""
Analyze spam transactions for a specific token using Helius RPC.

This script fetches the last 100 transactions for a token and analyzes them
for spam patterns including repetitive amounts, timing patterns, and wallet behavior.
"""

import json
import requests
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional
import statistics

# Configuration
HELIUS_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=e515761d-a0d4-4c02-ba17-7bc73ebe08b0"
TOKEN_MINT = "J4UBm5kvMSHeUwbNgZW4ySpCHBvS7LXknZ7rqQR9pump"


def make_rpc_request(method: str, params: List[Any]) -> Dict[str, Any]:
    """Make RPC request to Helius."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    
    response = requests.post(HELIUS_RPC_URL, json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    if "error" in result:
        raise Exception(f"RPC Error: {result['error']}")
    
    return result.get("result", {})


def get_token_transactions(mint_address: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent transactions for a token using Solana RPC."""
    try:
        # First get signatures for the token mint address
        signatures = get_signatures_for_address(mint_address, limit)
        
        if not signatures:
            print("No signatures found for this token")
            return []
        
        print(f"Found {len(signatures)} signatures, fetching transaction details...")
        
        transactions = []
        for i, signature in enumerate(signatures[:20]):  # Limit to first 20 for analysis
            if i % 5 == 0:
                print(f"Processing transaction {i+1}/{min(20, len(signatures))}...")
            
            tx_detail = get_transaction_details(signature)
            if tx_detail:
                transactions.append(tx_detail)
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        return transactions
        
    except Exception as e:
        print(f"Error fetching token transactions: {e}")
        return []


def get_signatures_for_address(address: str, limit: int = 100) -> List[str]:
    """Get transaction signatures for an address."""
    try:
        result = make_rpc_request("getSignaturesForAddress", [
            address,
            {
                "limit": limit,
                "commitment": "confirmed"
            }
        ])
        
        return [sig["signature"] for sig in result]
        
    except Exception as e:
        print(f"Error fetching signatures: {e}")
        return []


def get_transaction_details(signature: str) -> Optional[Dict[str, Any]]:
    """Get detailed transaction information."""
    try:
        result = make_rpc_request("getTransaction", [
            signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0,
                "commitment": "confirmed"
            }
        ])
        
        return result
        
    except Exception as e:
        print(f"Error fetching transaction {signature}: {e}")
        return None


def analyze_transaction_patterns(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze transactions for spam patterns."""
    if not transactions:
        return {"error": "No transactions to analyze"}
    
    analysis = {
        "total_transactions": len(transactions),
        "time_range": {},
        "wallet_patterns": {},
        "amount_patterns": {},
        "timing_patterns": {},
        "spam_indicators": {},
        "spam_score": 0.0
    }
    
    # Extract transaction data
    tx_data = []
    wallet_activity = defaultdict(list)
    amounts = []
    timestamps = []
    
    for tx in transactions:
        try:
            # Extract basic info from RPC response
            block_time = tx.get("blockTime", 0)
            if block_time:
                timestamps.append(block_time)
            
            # Extract transaction details from RPC format
            transaction = tx.get("transaction", {})
            message = transaction.get("message", {})
            
            # Get account keys (wallet addresses)
            account_keys = message.get("accountKeys", [])
            
            # Extract instructions to find token transfers
            instructions = message.get("instructions", [])
            
            for instruction in instructions:
                try:
                    # Look for token transfer instructions
                    if "parsed" in instruction:
                        parsed = instruction["parsed"]
                        if parsed.get("type") in ["transfer", "transferChecked"]:
                            info = parsed.get("info", {})
                            
                            # Extract transfer data
                            swap_data = {
                                "timestamp": block_time,
                                "wallet": info.get("source", "unknown"),
                                "destination": info.get("destination", "unknown"),
                                "amount": info.get("amount", "0"),
                                "mint": info.get("mint", ""),
                                "signature": tx.get("transaction", {}).get("signatures", [""])[0]
                            }
                            
                            tx_data.append(swap_data)
                            
                            wallet = swap_data["wallet"]
                            if wallet != "unknown":
                                wallet_activity[wallet].append(swap_data)
                            
                            # Collect amounts for pattern analysis
                            try:
                                amount = float(swap_data["amount"])
                                if amount > 0:
                                    amounts.append(amount)
                            except (ValueError, TypeError):
                                pass
                
                except Exception as e:
                    continue
            
            # Also check pre/post token balances for more data
            meta = tx.get("meta", {})
            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])
            
            # Compare pre/post balances to find transfers
            for pre_bal, post_bal in zip(pre_balances, post_balances):
                if pre_bal.get("mint") == TOKEN_MINT or post_bal.get("mint") == TOKEN_MINT:
                    try:
                        pre_amount = float(pre_bal.get("uiTokenAmount", {}).get("uiAmount", 0))
                        post_amount = float(post_bal.get("uiTokenAmount", {}).get("uiAmount", 0))
                        
                        if pre_amount != post_amount:
                            transfer_amount = abs(post_amount - pre_amount)
                            amounts.append(transfer_amount)
                            
                            # Add to wallet activity
                            owner = pre_bal.get("owner", "unknown")
                            if owner != "unknown":
                                wallet_activity[owner].append({
                                    "timestamp": block_time,
                                    "amount": transfer_amount,
                                    "type": "balance_change"
                                })
                    except (ValueError, TypeError):
                        pass
            
        except Exception as e:
            print(f"Error processing transaction: {e}")
            continue
    
    # Analyze time range
    if timestamps:
        analysis["time_range"] = {
            "earliest": datetime.fromtimestamp(min(timestamps)).isoformat(),
            "latest": datetime.fromtimestamp(max(timestamps)).isoformat(),
            "span_hours": (max(timestamps) - min(timestamps)) / 3600
        }
    
    # Analyze wallet patterns
    analysis["wallet_patterns"] = analyze_wallet_patterns(wallet_activity)
    
    # Analyze amount patterns
    analysis["amount_patterns"] = analyze_amount_patterns(amounts)
    
    # Analyze timing patterns
    analysis["timing_patterns"] = analyze_timing_patterns(timestamps)
    
    # Calculate spam indicators
    analysis["spam_indicators"] = calculate_spam_indicators(analysis)
    
    # Calculate overall spam score
    analysis["spam_score"] = calculate_spam_score(analysis["spam_indicators"])
    
    return analysis


def analyze_wallet_patterns(wallet_activity: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """Analyze wallet behavior patterns."""
    patterns = {
        "total_unique_wallets": len(wallet_activity),
        "high_frequency_wallets": [],
        "repetitive_wallets": [],
        "new_wallet_activity": 0,
        "wallet_frequency_distribution": {}
    }
    
    frequency_counts = []
    
    for wallet, txs in wallet_activity.items():
        tx_count = len(txs)
        frequency_counts.append(tx_count)
        
        # High frequency wallets (>5 transactions)
        if tx_count > 5:
            patterns["high_frequency_wallets"].append({
                "wallet": wallet[:8] + "...",
                "transaction_count": tx_count,
                "time_span_minutes": (max(tx["timestamp"] for tx in txs) - min(tx["timestamp"] for tx in txs)) / 60 if len(txs) > 1 else 0
            })
        
        # Check for repetitive amounts
        amounts = [tx.get("amount_in", 0) for tx in txs if tx.get("amount_in")]
        if len(amounts) > 2:
            unique_amounts = len(set(amounts))
            if unique_amounts < len(amounts) * 0.5:  # Less than 50% unique amounts
                patterns["repetitive_wallets"].append({
                    "wallet": wallet[:8] + "...",
                    "total_txs": len(amounts),
                    "unique_amounts": unique_amounts,
                    "repetition_rate": (len(amounts) - unique_amounts) / len(amounts)
                })
    
    # Frequency distribution
    if frequency_counts:
        patterns["wallet_frequency_distribution"] = {
            "mean": statistics.mean(frequency_counts),
            "median": statistics.median(frequency_counts),
            "max": max(frequency_counts),
            "wallets_with_1_tx": frequency_counts.count(1),
            "wallets_with_5plus_tx": len([c for c in frequency_counts if c >= 5])
        }
    
    return patterns


def analyze_amount_patterns(amounts: List[float]) -> Dict[str, Any]:
    """Analyze transaction amount patterns."""
    if not amounts:
        return {"error": "No amounts to analyze"}
    
    patterns = {
        "total_amounts": len(amounts),
        "unique_amounts": len(set(amounts)),
        "repetition_rate": 0.0,
        "round_number_rate": 0.0,
        "amount_distribution": {},
        "suspicious_patterns": []
    }
    
    # Calculate repetition rate
    patterns["repetition_rate"] = 1.0 - (patterns["unique_amounts"] / patterns["total_amounts"])
    
    # Check for round numbers
    round_amounts = [a for a in amounts if a == round(a, 1)]  # Round to 1 decimal
    patterns["round_number_rate"] = len(round_amounts) / len(amounts)
    
    # Amount distribution
    if amounts:
        patterns["amount_distribution"] = {
            "min": min(amounts),
            "max": max(amounts),
            "mean": statistics.mean(amounts),
            "median": statistics.median(amounts),
            "std_dev": statistics.stdev(amounts) if len(amounts) > 1 else 0
        }
    
    # Find most common amounts
    amount_counter = Counter(amounts)
    most_common = amount_counter.most_common(5)
    
    for amount, count in most_common:
        if count > 2:  # Amount appears more than twice
            patterns["suspicious_patterns"].append({
                "amount": amount,
                "occurrences": count,
                "percentage": (count / len(amounts)) * 100
            })
    
    return patterns


def analyze_timing_patterns(timestamps: List[int]) -> Dict[str, Any]:
    """Analyze transaction timing patterns."""
    if len(timestamps) < 2:
        return {"error": "Not enough timestamps to analyze"}
    
    # Sort timestamps
    timestamps.sort()
    
    # Calculate intervals between transactions
    intervals = []
    for i in range(1, len(timestamps)):
        interval = timestamps[i] - timestamps[i-1]
        intervals.append(interval)
    
    patterns = {
        "total_intervals": len(intervals),
        "interval_distribution": {},
        "regular_intervals": [],
        "burst_periods": [],
        "suspicious_timing": False
    }
    
    if intervals:
        patterns["interval_distribution"] = {
            "min_seconds": min(intervals),
            "max_seconds": max(intervals),
            "mean_seconds": statistics.mean(intervals),
            "median_seconds": statistics.median(intervals),
            "std_dev": statistics.stdev(intervals) if len(intervals) > 1 else 0
        }
        
        # Check for regular intervals (bot-like behavior)
        interval_counter = Counter([round(interval, 0) for interval in intervals])
        for interval, count in interval_counter.most_common(3):
            if count > 3:  # Same interval appears more than 3 times
                patterns["regular_intervals"].append({
                    "interval_seconds": interval,
                    "occurrences": count,
                    "percentage": (count / len(intervals)) * 100
                })
        
        # Check for burst periods (many transactions in short time)
        burst_threshold = 60  # 1 minute
        burst_count = len([i for i in intervals if i < burst_threshold])
        if burst_count > len(intervals) * 0.3:  # More than 30% are bursts
            patterns["burst_periods"].append({
                "burst_transactions": burst_count,
                "total_transactions": len(intervals),
                "burst_rate": (burst_count / len(intervals)) * 100
            })
        
        # Determine if timing is suspicious
        mean_interval = statistics.mean(intervals)
        std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
        
        # Low standard deviation indicates regular timing (bot-like)
        if std_dev < mean_interval * 0.2 and mean_interval < 300:  # Very regular and frequent
            patterns["suspicious_timing"] = True
    
    return patterns


def calculate_spam_indicators(analysis: Dict[str, Any]) -> Dict[str, float]:
    """Calculate spam indicator scores (0-1 scale)."""
    indicators = {
        "repetitive_amounts": 0.0,
        "high_frequency_wallets": 0.0,
        "regular_timing": 0.0,
        "round_numbers": 0.0,
        "wallet_clustering": 0.0,
        "compute_budget_spam": 0.0,
        "program_patterns": 0.0,
        "synchronous_activity": 0.0
    }
    
    # Repetitive amounts indicator
    amount_patterns = analysis.get("amount_patterns", {})
    repetition_rate = amount_patterns.get("repetition_rate", 0)
    indicators["repetitive_amounts"] = min(repetition_rate * 2, 1.0)  # Scale to 0-1
    
    # High frequency wallets indicator
    wallet_patterns = analysis.get("wallet_patterns", {})
    high_freq_wallets = len(wallet_patterns.get("high_frequency_wallets", []))
    total_wallets = wallet_patterns.get("total_unique_wallets", 1)
    if total_wallets > 0:
        indicators["high_frequency_wallets"] = min(high_freq_wallets / total_wallets, 1.0)
    else:
        indicators["high_frequency_wallets"] = 0.0
    
    # Regular timing indicator
    timing_patterns = analysis.get("timing_patterns", {})
    if timing_patterns.get("suspicious_timing", False):
        indicators["regular_timing"] = 0.8
    elif timing_patterns.get("regular_intervals"):
        indicators["regular_timing"] = 0.5
    
    # Round numbers indicator
    round_rate = amount_patterns.get("round_number_rate", 0)
    indicators["round_numbers"] = min(round_rate * 1.5, 1.0)
    
    # Wallet clustering (many wallets with few transactions each)
    freq_dist = wallet_patterns.get("wallet_frequency_distribution", {})
    single_tx_wallets = freq_dist.get("wallets_with_1_tx", 0)
    if total_wallets > 0:
        clustering_rate = single_tx_wallets / total_wallets
        indicators["wallet_clustering"] = min(clustering_rate * 1.2, 1.0)
    else:
        indicators["wallet_clustering"] = 0.0
    
    # ComputeBudget spam indicator
    content_analysis = analysis.get("content_analysis", {})
    program_usage = content_analysis.get("program_usage", {})
    
    # Check for excessive ComputeBudget usage
    compute_budget_count = 0
    total_instructions = 0
    
    for program, count in program_usage.items():
        total_instructions += count
        if "ComputeBudget111" in program:
            compute_budget_count = count
    
    if total_instructions > 0:
        compute_budget_ratio = compute_budget_count / total_instructions
        # High ratio of ComputeBudget instructions is suspicious
        indicators["compute_budget_spam"] = min(compute_budget_ratio * 2.5, 1.0)
    
    # Program pattern analysis
    suspicious_programs = 0
    known_spam_programs = [
        "ComputeBudget111",  # Often used in spam
        "1111111111111111",  # System program overuse
    ]
    
    for program in program_usage.keys():
        for spam_program in known_spam_programs:
            if spam_program in program:
                suspicious_programs += 1
                break
    
    if len(program_usage) > 0:
        indicators["program_patterns"] = min(suspicious_programs / len(program_usage), 1.0)
    
    # Synchronous activity (all transactions in same second)
    time_range = analysis.get("time_range", {})
    span_hours = time_range.get("span_hours", 1)
    
    if span_hours < 0.001:  # Less than ~3 seconds
        indicators["synchronous_activity"] = 0.9
    elif span_hours < 0.01:  # Less than ~36 seconds
        indicators["synchronous_activity"] = 0.6
    elif span_hours < 0.1:  # Less than 6 minutes
        indicators["synchronous_activity"] = 0.3
    
    return indicators


def calculate_spam_score(indicators: Dict[str, float]) -> float:
    """Calculate overall spam score (0-100)."""
    weights = {
        "repetitive_amounts": 0.2,
        "high_frequency_wallets": 0.15,
        "regular_timing": 0.15,
        "round_numbers": 0.1,
        "wallet_clustering": 0.1,
        "compute_budget_spam": 0.15,  # High weight for ComputeBudget spam
        "program_patterns": 0.1,
        "synchronous_activity": 0.05
    }
    
    weighted_score = sum(indicators.get(key, 0) * weight for key, weight in weights.items())
    return round(weighted_score * 100, 2)


def analyze_transaction_content(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze detailed transaction content."""
    content_analysis = {
        "instruction_patterns": {},
        "program_usage": {},
        "account_patterns": {},
        "transaction_details": []
    }
    
    instruction_types = defaultdict(int)
    programs_used = defaultdict(int)
    account_frequency = defaultdict(int)
    
    for i, tx in enumerate(transactions):
        try:
            transaction = tx.get("transaction", {})
            message = transaction.get("message", {})
            meta = tx.get("meta", {})
            
            # Analyze instructions
            instructions = message.get("instructions", [])
            tx_detail = {
                "index": i,
                "signature": transaction.get("signatures", [""])[0][:16] + "...",
                "block_time": datetime.fromtimestamp(tx.get("blockTime", 0)).strftime("%H:%M:%S") if tx.get("blockTime") else "unknown",
                "instructions": [],
                "token_transfers": [],
                "accounts_involved": len(message.get("accountKeys", [])),
                "compute_units": meta.get("computeUnitsConsumed", 0),
                "fee": meta.get("fee", 0)
            }
            
            for inst in instructions:
                program_id = inst.get("programId", "unknown")
                programs_used[program_id] += 1
                
                inst_detail = {
                    "program": program_id[:8] + "..." if len(program_id) > 8 else program_id,
                    "type": "unknown"
                }
                
                if "parsed" in inst:
                    parsed = inst["parsed"]
                    inst_type = parsed.get("type", "unknown")
                    instruction_types[inst_type] += 1
                    inst_detail["type"] = inst_type
                    
                    # Extract transfer details
                    if inst_type in ["transfer", "transferChecked"]:
                        info = parsed.get("info", {})
                        inst_detail.update({
                            "source": info.get("source", "")[:8] + "..." if info.get("source") else "unknown",
                            "destination": info.get("destination", "")[:8] + "..." if info.get("destination") else "unknown",
                            "amount": info.get("amount", "0"),
                            "mint": info.get("mint", "")[:8] + "..." if info.get("mint") else "unknown"
                        })
                
                tx_detail["instructions"].append(inst_detail)
            
            # Analyze token transfers from meta
            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])
            
            for pre_bal in pre_balances:
                mint = pre_bal.get("mint", "")
                if mint:
                    account_frequency[mint] += 1
            
            # Find actual token transfers
            for j, (pre_bal, post_bal) in enumerate(zip(pre_balances, post_balances)):
                if pre_bal.get("mint") == post_bal.get("mint"):
                    pre_amount = float(pre_bal.get("uiTokenAmount", {}).get("uiAmount", 0))
                    post_amount = float(post_bal.get("uiTokenAmount", {}).get("uiAmount", 0))
                    
                    if pre_amount != post_amount:
                        transfer_detail = {
                            "mint": pre_bal.get("mint", "")[:8] + "...",
                            "owner": pre_bal.get("owner", "")[:8] + "...",
                            "change": post_amount - pre_amount,
                            "pre_balance": pre_amount,
                            "post_balance": post_amount
                        }
                        tx_detail["token_transfers"].append(transfer_detail)
            
            content_analysis["transaction_details"].append(tx_detail)
            
        except Exception as e:
            print(f"Error analyzing transaction {i}: {e}")
            continue
    
    content_analysis["instruction_patterns"] = dict(instruction_types)
    content_analysis["program_usage"] = dict(programs_used)
    content_analysis["account_patterns"] = dict(sorted(account_frequency.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return content_analysis


def print_transaction_content_report(content_analysis: Dict[str, Any]):
    """Print detailed transaction content analysis."""
    print("\n" + "=" * 60)
    print("📋 DETAILED TRANSACTION CONTENT ANALYSIS")
    print("=" * 60)
    
    # Instruction patterns
    instruction_patterns = content_analysis.get("instruction_patterns", {})
    print(f"\n🔧 INSTRUCTION PATTERNS:")
    for inst_type, count in sorted(instruction_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"   {inst_type}: {count} times")
    
    # Program usage with spam detection
    program_usage = content_analysis.get("program_usage", {})
    print(f"\n💻 PROGRAMS USED:")
    
    spam_programs = {
        "ComputeBudget111": "🚨 SPAM INDICATOR - Often used in bot transactions",
        "1111111111111111": "⚠️  System Program - High usage may indicate spam"
    }
    
    for program, count in sorted(program_usage.items(), key=lambda x: x[1], reverse=True)[:8]:
        program_short = program[:16] + "..." if len(program) > 16 else program
        
        # Check if it's a known spam program
        spam_indicator = ""
        for spam_prog, description in spam_programs.items():
            if spam_prog in program:
                spam_indicator = f" {description}"
                break
        
        print(f"   {program_short}: {count} times{spam_indicator}")
    
    # Calculate ComputeBudget ratio
    total_instructions = sum(program_usage.values())
    compute_budget_count = sum(count for prog, count in program_usage.items() if "ComputeBudget111" in prog)
    
    if total_instructions > 0:
        cb_ratio = (compute_budget_count / total_instructions) * 100
        if cb_ratio > 30:
            print(f"\n   🚨 HIGH COMPUTE BUDGET USAGE: {cb_ratio:.1f}% of all instructions")
        elif cb_ratio > 15:
            print(f"\n   ⚠️  MODERATE COMPUTE BUDGET USAGE: {cb_ratio:.1f}% of all instructions")
    
    # Account patterns
    account_patterns = content_analysis.get("account_patterns", {})
    print(f"\n🏦 TOP ACCOUNTS/MINTS:")
    for account, count in list(account_patterns.items())[:5]:
        account_short = account[:16] + "..." if len(account) > 16 else account
        print(f"   {account_short}: {count} appearances")
    
    # Transaction details
    tx_details = content_analysis.get("transaction_details", [])
    print(f"\n📊 TRANSACTION BREAKDOWN (showing first 10):")
    
    for tx in tx_details[:10]:
        print(f"\n   🔸 TX #{tx['index']} ({tx['signature']}) at {tx['block_time']}")
        print(f"     Accounts: {tx['accounts_involved']}, Compute: {tx['compute_units']}, Fee: {tx['fee']} lamports")
        
        if tx['instructions']:
            print(f"     Instructions ({len(tx['instructions'])}):")
            for inst in tx['instructions']:
                if inst['type'] in ['transfer', 'transferChecked']:
                    print(f"       - {inst['type']}: {inst.get('amount', '?')} from {inst.get('source', '?')} to {inst.get('destination', '?')}")
                else:
                    print(f"       - {inst['type']} via {inst['program']}")
        
        if tx['token_transfers']:
            print(f"     Token Transfers ({len(tx['token_transfers'])}):")
            for transfer in tx['token_transfers']:
                change_sign = "+" if transfer['change'] > 0 else ""
                print(f"       - {transfer['mint']}: {change_sign}{transfer['change']:.6f} (owner: {transfer['owner']})")


def print_analysis_report(analysis: Dict[str, Any]):
    """Print formatted analysis report."""
    print("🔍 SPAM TRANSACTION ANALYSIS REPORT")
    print("=" * 60)
    
    print(f"\n📊 OVERVIEW:")
    print(f"   Token: {TOKEN_MINT}")
    print(f"   Total Transactions: {analysis.get('total_transactions', 0)}")
    
    time_range = analysis.get("time_range", {})
    if time_range:
        print(f"   Time Range: {time_range.get('span_hours', 0):.1f} hours")
        print(f"   From: {time_range.get('earliest', 'unknown')}")
        print(f"   To: {time_range.get('latest', 'unknown')}")
    
    print(f"\n🎯 SPAM SCORE: {analysis.get('spam_score', 0):.1f}%")
    
    # Spam indicators
    indicators = analysis.get("spam_indicators", {})
    print(f"\n🚨 SPAM INDICATORS:")
    for indicator, score in indicators.items():
        status = "🔴 HIGH" if score > 0.7 else "🟡 MEDIUM" if score > 0.3 else "🟢 LOW"
        print(f"   {indicator.replace('_', ' ').title()}: {score:.2f} {status}")
    
    # Wallet patterns
    wallet_patterns = analysis.get("wallet_patterns", {})
    print(f"\n👛 WALLET PATTERNS:")
    print(f"   Unique Wallets: {wallet_patterns.get('total_unique_wallets', 0)}")
    
    high_freq = wallet_patterns.get("high_frequency_wallets", [])
    if high_freq:
        print(f"   High Frequency Wallets ({len(high_freq)}):")
        for wallet in high_freq[:5]:  # Show top 5
            print(f"     - {wallet['wallet']}: {wallet['transaction_count']} txs in {wallet['time_span_minutes']:.1f} min")
    
    repetitive = wallet_patterns.get("repetitive_wallets", [])
    if repetitive:
        print(f"   Repetitive Amount Wallets ({len(repetitive)}):")
        for wallet in repetitive[:3]:  # Show top 3
            print(f"     - {wallet['wallet']}: {wallet['repetition_rate']:.1%} repetition rate")
    
    # Amount patterns
    amount_patterns = analysis.get("amount_patterns", {})
    print(f"\n💰 AMOUNT PATTERNS:")
    print(f"   Total Amounts: {amount_patterns.get('total_amounts', 0)}")
    print(f"   Unique Amounts: {amount_patterns.get('unique_amounts', 0)}")
    print(f"   Repetition Rate: {amount_patterns.get('repetition_rate', 0):.1%}")
    print(f"   Round Numbers Rate: {amount_patterns.get('round_number_rate', 0):.1%}")
    
    suspicious = amount_patterns.get("suspicious_patterns", [])
    if suspicious:
        print(f"   Suspicious Amount Patterns:")
        for pattern in suspicious[:5]:
            print(f"     - {pattern['amount']}: {pattern['occurrences']} times ({pattern['percentage']:.1f}%)")
    
    # Timing patterns
    timing_patterns = analysis.get("timing_patterns", {})
    print(f"\n⏰ TIMING PATTERNS:")
    
    interval_dist = timing_patterns.get("interval_distribution", {})
    if interval_dist:
        print(f"   Mean Interval: {interval_dist.get('mean_seconds', 0):.1f} seconds")
        print(f"   Median Interval: {interval_dist.get('median_seconds', 0):.1f} seconds")
        print(f"   Std Deviation: {interval_dist.get('std_dev', 0):.1f} seconds")
    
    regular = timing_patterns.get("regular_intervals", [])
    if regular:
        print(f"   Regular Intervals (Bot-like):")
        for interval in regular:
            print(f"     - Every {interval['interval_seconds']:.0f}s: {interval['occurrences']} times ({interval['percentage']:.1f}%)")
    
    if timing_patterns.get("suspicious_timing", False):
        print(f"   🚨 SUSPICIOUS: Very regular timing detected (likely bot activity)")
    
    # Overall assessment
    spam_score = analysis.get("spam_score", 0)
    print(f"\n🎯 ASSESSMENT:")
    if spam_score > 70:
        print(f"   🔴 HIGH SPAM RISK: This token shows strong indicators of artificial activity")
    elif spam_score > 40:
        print(f"   🟡 MEDIUM SPAM RISK: Some suspicious patterns detected")
    elif spam_score > 15:
        print(f"   🟠 LOW SPAM RISK: Minor suspicious activity")
    else:
        print(f"   🟢 CLEAN: No significant spam indicators detected")


def main():
    """Main analysis function."""
    print(f"🚀 Starting spam analysis for token: {TOKEN_MINT}")
    print(f"🔗 Using Helius RPC: {HELIUS_RPC_URL.split('?')[0]}")
    
    try:
        # Fetch transactions
        print(f"\n📥 Fetching last 100 transactions...")
        transactions = get_token_transactions(TOKEN_MINT, limit=100)
        
        if not transactions:
            print("❌ No transactions found or API error")
            return 1
        
        print(f"✅ Fetched {len(transactions)} transactions")
        
        # Analyze patterns
        print(f"\n🔍 Analyzing transaction patterns...")
        analysis = analyze_transaction_patterns(transactions)
        
        # Analyze transaction content
        print(f"\n🔍 Analyzing transaction content...")
        content_analysis = analyze_transaction_content(transactions)
        
        # Print reports
        print_analysis_report(analysis)
        print_transaction_content_report(content_analysis)
        
        # Combine results
        analysis["content_analysis"] = content_analysis
        
        # Save detailed results
        with open("spam_analysis_results.json", "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: spam_analysis_results.json")
        
        return 0
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())