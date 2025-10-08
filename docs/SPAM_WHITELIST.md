# Spam Detection Whitelist

## Overview

The spam detection system now supports whitelisting wallet addresses to prevent our own bots and trusted sources from inflating spam metrics.

## Problem Solved

When our NotArb bot trades a token, its transactions would be counted as spam, potentially:
- Increasing the token's spam percentage
- Causing the token to be filtered out from NotArb export
- Creating a self-defeating cycle

## Solution

Transactions from whitelisted wallets are completely ignored during spam analysis.

## Configuration

### Default Whitelist

```
8vNwSvT1S8P99c9XmjfXfV4DSGZLfUoNFx63zngCuh54  # NotArb bot wallet
```

### Admin UI

1. Open Settings page
2. Find "🤖 Whitelist кошельков" section
3. Add wallet addresses (comma-separated)
4. Save settings

### API

```bash
# Get current whitelist
curl http://67.213.119.189:8000/settings/spam_whitelist_wallets

# Update whitelist
curl -X PUT http://67.213.119.189:8000/settings/spam_whitelist_wallets \
  -H "Content-Type: application/json" \
  -d '{"value": "wallet1,wallet2,wallet3"}'
```

## How It Works

1. **Transaction Analysis**: When analyzing a token's transactions
2. **Wallet Check**: Each transaction's `accountKeys` are checked against whitelist
3. **Skip Whitelisted**: If any account matches whitelist, transaction is skipped
4. **Accurate Metrics**: Only non-whitelisted transactions count toward spam percentage

## Implementation Details

### Code Location

- `src/monitoring/spam_detector.py`: Main implementation
- `src/domain/settings/defaults.py`: Default whitelist value
- `frontend/src/pages/Settings.tsx`: Admin UI

### Key Functions

```python
class SpamDetector:
    DEFAULT_WHITELISTED_WALLETS = {
        "8vNwSvT1S8P99c9XmjfXfV4DSGZLfUoNFx63zngCuh54",
    }
    
    def __init__(self, whitelisted_wallets: Optional[set] = None):
        self.whitelisted_wallets = whitelisted_wallets or self.DEFAULT_WHITELISTED_WALLETS
    
    def _analyze_single_transaction(self, tx: Dict, counts: Dict[str, int]) -> None:
        # Check if transaction is from whitelisted wallet
        account_keys = message.get("accountKeys", [])
        for account in account_keys:
            pubkey = account if isinstance(account, str) else account.get("pubkey", "")
            if pubkey in self.whitelisted_wallets:
                return  # Skip this transaction
```

### Dynamic Loading

Whitelist is loaded from settings on each monitoring cycle:

```python
def _get_whitelisted_wallets(self, db: Session) -> set:
    whitelist_str = get_setting(db, "spam_whitelist_wallets", "")
    wallets = {w.strip() for w in whitelist_str.split(",") if w.strip()}
    return wallets
```

## Benefits

1. **Accurate Spam Detection**: Only external activity counts
2. **No Self-Sabotage**: Our bots don't disqualify good tokens
3. **Flexible**: Easy to add more trusted wallets
4. **Real-time**: Changes apply on next monitoring cycle

## Monitoring

Check logs for whitelist activity:

```bash
sudo journalctl -u tothemoon -f | grep -i whitelist
```

Expected log messages:
- `Loaded N whitelisted wallets for spam detection`
- `Skipping transaction from whitelisted wallet: XXXXXXXX...`

## Future Enhancements

- [ ] Whitelist by program ID (e.g., all Raydium transactions)
- [ ] Whitelist by transaction type
- [ ] Automatic detection of known bot wallets
- [ ] Whitelist expiration/rotation
