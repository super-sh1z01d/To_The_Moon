# NotArb Pool URLs Integration

Simple integration for exporting pool URLs of top-scoring tokens to [NotArb onchain-bot](https://github.com/NotArb/Release/tree/main/onchain-bot).

## 🎯 Overview

This module generates pool groups for the top 3 highest-scoring tokens (by mint address) that meet the minimum score threshold. Each group contains all pools for one specific token mint, regardless of quote currency (SOL/USDC). The groups can be used directly with NotArb's arbitrage markets configuration.

**File is automatically updated by scheduler:**
- **Update frequency**: Every 5 seconds
- **File location**: `markets.json` (configurable via `NOTARB_CONFIG_PATH`)

## ⚙️ Configuration

### Minimum Score Setting

Configure the minimum score threshold via API:

```bash
# Set minimum score for NotArb export (default: 0.5)
curl -X PUT http://localhost:8000/settings/notarb_min_score \
  -H "Content-Type: application/json" \
  -d '{"value": "0.6"}'

# Get current setting
curl http://localhost:8000/settings/notarb_min_score
```

## 🔌 API Endpoints

### Get Token Pool Groups

```bash
# Get list of token pool groups (same as /notarb/markets)
curl http://localhost:8000/notarb/pools

# Response: [["token1_pool1", "token1_pool2"], ["token2_pool1", "token2_pool2", "token2_pool3"]]
```

### Get Markets JSON (NotArb Compatible)

```bash
# Get full markets.json with metadata
curl http://localhost:8000/notarb/markets

# Response: complete data with token info and pools
```

### Get Full Configuration (Debug)

```bash
# Get complete config with metadata (for debugging)
curl http://localhost:8000/notarb/config

# Response includes tokens, pools, and metadata
```

### Get File Information

```bash
# Get file status and metadata
curl http://localhost:8000/notarb/file-info

# Response includes file size, last modified, pool counts
```

### Force File Update

```bash
# Force immediate file update
curl -X POST http://localhost:8000/notarb/export

# Response includes success status and metadata
```

### Export to File

```bash
# Export to JSON file
curl -X POST "http://localhost:8000/notarb/export?output_path=pools.json"
```

## 🖥️ CLI Usage

```bash
# Show current top tokens and their pool URLs
python scripts/notarb_pools.py

# Example output:
# 🎯 NotArb minimum score threshold: 0.5
# 
# 📊 Found 3 tokens:
# ------------------------------------------------------------
# #1 WSOL     Score: 1.250 Pools: 2
# #2 USDC     Score: 0.950 Pools: 2  
# #3 mSOL     Score: 0.780 Pools: 2
# ------------------------------------------------------------
# Total pools: 6
# 
# 🔗 Pool URLs for NotArb bot:
#  1. https://dexscreener.com/solana/58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2
#  2. https://dexscreener.com/solana/7XawhbbxtsRcQA8KTkHT9f9nc6d69UwqCDh6U5EEbEmX
#  ...
```

## 📊 Output Format

The generated JSON includes token metadata and pool information:

```json
{
  "metadata": {
    "generated_at": "2025-09-18T10:00:00+00:00",
    "generator": "ToTheMoon Scoring System",
    "min_score_threshold": 0.5,
    "total_tokens": 2
  },
  "tokens": [
    {
      "mint_address": "ABC123def456ghi789jkl012mno345pqr678stu901vwx234yz",
      "symbol": "EXAMPLE1",
      "name": "Example Token 1", 
      "score": 1.25,
      "pools": [
        "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
        "7XawhbbxtsRcQA8KTkHT9f9nc6d69UwqCDh6U5EEbEmX"
      ]
    }
  ]
}
```

**Benefits for NotArb bot:**
- **Token metadata included**: No need to fetch symbol/name separately
- **Score information**: Current scoring for prioritization
- **Pool arrays**: All pools for each token mint
- **Backward compatibility**: Old format available via `/notarb/markets/pools-only`

## 🔄 Usage with NotArb Bot

1. **Get pool URLs**: Use API or CLI to get current pool URLs
2. **Configure NotArb**: Add URLs to NotArb bot's URL-based markets configuration
3. **Monitor**: URLs are updated as token scores change

### Example NotArb Integration

```bash
# Get pool addresses and save to file for NotArb bot
curl http://localhost:8000/notarb/pools > markets.json

# Or use the export endpoint
curl -X POST "http://localhost:8000/notarb/export?output_path=markets.json"
```

## 🎛️ Advanced Usage

### Programmatic Access

```python
from src.integrations.notarb_pools import NotArbPoolsGenerator

# Create generator
generator = NotArbPoolsGenerator()

# Get current minimum score
min_score = generator.get_notarb_min_score()

# Get pool URLs
urls = generator.get_pool_urls_list()

# Export to file
success = generator.export_pools_config()
```

### Custom Filtering

The module automatically filters tokens by:
- Status: `active` only
- Score: Above `notarb_min_score` setting
- Liquidity: Minimum $1,000 USD
- Limit: Top 3 tokens maximum

## 🔗 Related Documentation

- **[NotArb Onchain Bot](https://github.com/NotArb/Release/tree/main/onchain-bot)** - Target bot repository
- **[URL-based Markets](https://github.com/NotArb/Release/tree/main/onchain-bot#url-based-markets)** - NotArb URL configuration
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Scoring Model](SCORING_MODEL.md)** - Token scoring details

---

**💡 Tip**: Adjust `notarb_min_score` setting based on market conditions to control the quality threshold for exported tokens.