# API Reference

Complete API documentation for the To The Moon token scoring system.

## 🌐 Base URLs

- **Development**: `http://localhost:8000`
- **Production**: `https://tothemoon.sh1z01d.ru`
- **Interactive Docs**: `https://tothemoon.sh1z01d.ru/docs`

## 🔐 Authentication

- **Read Operations**: No authentication required
- **Admin Operations**: Protected at network level
- **Rate Limiting**: Applied to prevent abuse

## 📋 Response Format

All API responses follow consistent JSON format with appropriate HTTP status codes.

### Success Response
```json
{
  "total": 100,
  "items": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "has_next": true
  }
}
```

### Error Response
```json
{
  "error": {
    "code": 400,
    "message": "Validation error",
    "path": "/tokens/",
    "details": {
      "field": "Invalid value"
    }
  }
}
```

## 🏥 Health & System Endpoints

### GET /health
Basic system health check.

**Response:**
```json
{
  "status": "ok"
}
```

**Status Codes:**
- `200`: System healthy
- `503`: System unavailable

---

### GET /health/scheduler
Detailed scheduler health monitoring.

**Response:**
```json
{
  "scheduler": {
    "overall_healthy": true,
    "issues": [],
    "last_check": "2025-09-18T10:00:00+00:00"
  },
  "stale_tokens": {
    "stale_count": 2,
    "total_active": 10,
    "stale_percentage": 20.0,
    "stale_tokens": [
      {
        "symbol": "TOKEN1",
        "mint": "ABC123...",
        "age_minutes": 15.5,
        "last_update": "2025-09-18T09:45:00+00:00"
      }
    ],
    "max_age_minutes": 10
  },
  "timestamp": "2025-09-18T10:00:00+00:00"
}
```

**Status Codes:**
- `200`: Health check completed
- `500`: Health check failed

---

### GET /version
Application version and build information.

**Response:**
```json
{
  "version": "2.1.0",
  "build_date": "2025-09-18",
  "scoring_model": "hybrid_momentum",
  "features": [
    "scheduler_monitoring",
    "data_quality_validation",
    "fallback_mechanisms"
  ]
}
```

## 🪙 Token Endpoints

### GET /tokens/
List tokens with filtering and pagination.

**Query Parameters:**
- `limit` (int, optional): Number of tokens to return (1-100, default: 50)
- `offset` (int, optional): Number of tokens to skip (default: 0)
- `min_score` (float, optional): Minimum score threshold (default: from settings)
- `sort` (string, optional): Sort order - `score_desc` or `score_asc` (default: `score_desc`)
- `statuses` (string, optional): Comma-separated status filter - `active,monitoring,archived`

**Example Request:**
```bash
GET /tokens/?limit=10&min_score=0.5&statuses=active,monitoring&sort=score_desc
```

**Response:**
```json
{
  "total": 25,
  "items": [
    {
      "mint_address": "ABC123...",
      "name": "Example Token",
      "symbol": "EXT",
      "status": "active",
      "score": 1.25,
      "raw_components": {
        "tx_accel": 1.5,
        "vol_momentum": 1.2,
        "token_freshness": 0.8,
        "orderflow_imbalance": 0.3,
        "final_score": 1.25
      },
      "smoothed_components": {
        "tx_accel": 1.4,
        "vol_momentum": 1.15,
        "token_freshness": 0.75,
        "orderflow_imbalance": 0.28,
        "final_score": 1.20
      },
      "scoring_model": "hybrid_momentum",
      "liquidity_usd": 50000.0,
      "delta_p_5m": 0.025,
      "delta_p_15m": 0.045,
      "n_5m": 25,
      "primary_dex": "raydium",
      "created_at": "2025-09-18T08:00:00+00:00",
      "scored_at": "2025-09-18T10:00:00+00:00",
      "solscan_url": "https://solscan.io/token/ABC123..."
    }
  ],
  "meta": {
    "page": 1,
    "limit": 10,
    "has_next": true,
    "total_pages": 3
  }
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid parameters
- `422`: Validation error

---

### GET /tokens/{mint}
Get detailed information for a specific token.

**Path Parameters:**
- `mint` (string): Token mint address

**Response:**
```json
{
  "mint_address": "ABC123...",
  "name": "Example Token",
  "symbol": "EXT",
  "status": "active",
  "score": 1.25,
  "raw_components": {
    "tx_accel": 1.5,
    "vol_momentum": 1.2,
    "token_freshness": 0.8,
    "orderflow_imbalance": 0.3,
    "final_score": 1.25
  },
  "smoothed_components": {
    "tx_accel": 1.4,
    "vol_momentum": 1.15,
    "token_freshness": 0.75,
    "orderflow_imbalance": 0.28,
    "final_score": 1.20
  },
  "scoring_model": "hybrid_momentum",
  "metrics": {
    "L_tot": 50000.0,
    "tx_count_5m": 25,
    "tx_count_1h": 180,
    "volume_5m": 5000.0,
    "volume_1h": 45000.0,
    "buys_volume_5m": 3000.0,
    "sells_volume_5m": 2000.0,
    "hours_since_creation": 2.5,
    "data_quality_ok": true,
    "data_quality_issues": [],
    "fetched_at": "2025-09-18T10:00:00+00:00"
  },
  "pools": [
    {
      "address": "DEF456...",
      "dex": "raydium",
      "quote": "SOL",
      "solscan_url": "https://solscan.io/address/DEF456..."
    }
  ],
  "score_history": [
    {
      "score": 1.25,
      "smoothed_score": 1.20,
      "scoring_model": "hybrid_momentum",
      "created_at": "2025-09-18T10:00:00+00:00"
    }
  ],
  "created_at": "2025-09-18T08:00:00+00:00",
  "solscan_url": "https://solscan.io/token/ABC123..."
}
```

**Status Codes:**
- `200`: Token found
- `404`: Token not found

---

### POST /tokens/{mint}/refresh
Force recalculation of token score and metrics.

**Path Parameters:**
- `mint` (string): Token mint address

**Response:**
```json
{
  "message": "Token refresh initiated",
  "mint_address": "ABC123...",
  "previous_score": 1.20,
  "new_score": 1.25,
  "updated_at": "2025-09-18T10:05:00+00:00"
}
```

**Status Codes:**
- `200`: Refresh completed
- `404`: Token not found
- `503`: External API unavailable

---

### GET /tokens/{mint}/pools
Get trading pools for a specific token.

**Path Parameters:**
- `mint` (string): Token mint address

**Response:**
```json
[
  {
    "address": "DEF456...",
    "dex": "raydium",
    "quote": "SOL",
    "solscan_url": "https://solscan.io/address/DEF456..."
  },
  {
    "address": "GHI789...",
    "dex": "meteora",
    "quote": "USDC",
    "solscan_url": "https://solscan.io/address/GHI789..."
  }
]
```

**Status Codes:**
- `200`: Pools retrieved
- `404`: Token not found

## ⚙️ Settings Endpoints

### GET /settings
Get all application settings.

**Response:**
```json
{
  "scoring_model_active": "hybrid_momentum",
  "w_tx": "0.25",
  "w_vol": "0.25", 
  "w_fresh": "0.25",
  "w_oi": "0.25",
  "ewma_alpha": "0.3",
  "freshness_threshold_hours": "6.0",
  "min_score": "0.3",
  "hot_interval_sec": "30",
  "cold_interval_sec": "120",
  "min_liquidity_usd_for_activation": "500",
  "strict_data_validation": "false"
}
```

**Status Codes:**
- `200`: Settings retrieved

---

### GET /settings/{key}
Get specific setting value.

**Path Parameters:**
- `key` (string): Setting key name

**Response:**
```json
{
  "key": "w_tx",
  "value": "0.25",
  "description": "Weight for transaction acceleration component in hybrid momentum model"
}
```

**Status Codes:**
- `200`: Setting found
- `404`: Setting key not found

---

### PUT /settings/{key}
Update specific setting value.

**Path Parameters:**
- `key` (string): Setting key name

**Request Body:**
```json
{
  "value": "0.30"
}
```

**Response:**
```json
{
  "key": "w_tx",
  "old_value": "0.25",
  "new_value": "0.30",
  "updated_at": "2025-09-18T10:00:00+00:00"
}
```

**Status Codes:**
- `200`: Setting updated
- `400`: Invalid value
- `404`: Setting key not found

---

### POST /settings/model/switch
Switch between scoring models.

**Request Body:**
```json
{
  "model": "hybrid_momentum"
}
```

**Response:**
```json
{
  "previous_model": "legacy",
  "new_model": "hybrid_momentum",
  "switched_at": "2025-09-18T10:00:00+00:00",
  "affected_tokens": 25
}
```

**Status Codes:**
- `200`: Model switched successfully
- `400`: Invalid model name
- `422`: Model switch failed

## 🔧 Admin Endpoints

### POST /admin/recalculate
Trigger recalculation of all active tokens.

**Request Body (optional):**
```json
{
  "model": "hybrid_momentum",
  "limit": 50
}
```

**Response:**
```json
{
  "message": "Recalculation initiated",
  "tokens_processed": 25,
  "model_used": "hybrid_momentum",
  "started_at": "2025-09-18T10:00:00+00:00"
}
```

**Status Codes:**
- `200`: Recalculation started
- `503`: System busy

## 📋 Logs Endpoints

### GET /logs
Get application logs with filtering.

**Query Parameters:**
- `limit` (int, optional): Number of log entries (1-1000, default: 100)
- `level` (string, optional): Log level filter - `DEBUG,INFO,WARNING,ERROR`
- `logger` (string, optional): Logger name filter
- `since` (string, optional): ISO timestamp to filter logs since

**Example Request:**
```bash
GET /logs?limit=50&level=ERROR,WARNING&since=2025-09-18T09:00:00Z
```

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2025-09-18T10:00:00+00:00",
      "level": "ERROR",
      "logger": "dex_aggregator",
      "message": "Metrics consistency check failed",
      "extra": {
        "mint": "ABC123...",
        "error_type": "high_liquidity_no_transactions"
      }
    }
  ],
  "meta": {
    "total": 150,
    "limit": 50,
    "has_more": true
  }
}
```

**Status Codes:**
- `200`: Logs retrieved
- `400`: Invalid parameters

---

### GET /logs/meta
Get log metadata and statistics.

**Response:**
```json
{
  "total_logs": 1500,
  "log_levels": {
    "DEBUG": 800,
    "INFO": 600,
    "WARNING": 80,
    "ERROR": 20
  },
  "loggers": [
    "scheduler",
    "dex_aggregator", 
    "scoring_service",
    "tokens_repo"
  ],
  "oldest_log": "2025-09-18T08:00:00+00:00",
  "newest_log": "2025-09-18T10:00:00+00:00"
}
```

**Status Codes:**
- `200`: Metadata retrieved

## 📊 Data Models

### Token Model
```typescript
interface Token {
  mint_address: string;
  name?: string;
  symbol?: string;
  status: 'monitoring' | 'active' | 'archived';
  score: number;
  raw_components?: ComponentBreakdown;
  smoothed_components?: ComponentBreakdown;
  scoring_model: string;
  liquidity_usd: number;
  delta_p_5m: number;
  delta_p_15m: number;
  n_5m: number;
  primary_dex?: string;
  created_at: string;
  scored_at?: string;
  solscan_url: string;
}
```

### Component Breakdown Model
```typescript
interface ComponentBreakdown {
  tx_accel: number;
  vol_momentum: number;
  token_freshness: number;
  orderflow_imbalance: number;
  final_score: number;
}
```

### Pool Model
```typescript
interface Pool {
  address: string;
  dex: string;
  quote: string;
  solscan_url: string;
}
```

### Metrics Model
```typescript
interface Metrics {
  L_tot: number;
  tx_count_5m: number;
  tx_count_1h: number;
  volume_5m: number;
  volume_1h: number;
  buys_volume_5m: number;
  sells_volume_5m: number;
  hours_since_creation: number;
  data_quality_ok: boolean;
  data_quality_issues: string[];
  fetched_at: string;
}
```

## 🚨 Error Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| `400` | Bad Request | Invalid parameters, malformed JSON |
| `404` | Not Found | Token not found, invalid endpoint |
| `422` | Validation Error | Invalid data types, constraint violations |
| `429` | Rate Limited | Too many requests |
| `500` | Internal Error | Database error, unexpected exception |
| `503` | Service Unavailable | External API down, system maintenance |

## 📝 Usage Examples

### Get Top Scoring Tokens
```bash
curl "http://localhost:8000/tokens/?limit=10&min_score=1.0&sort=score_desc"
```

### Check System Health
```bash
curl "http://localhost:8000/health/scheduler"
```

### Update Scoring Weight
```bash
curl -X PUT "http://localhost:8000/settings/w_tx" \
  -H "Content-Type: application/json" \
  -d '{"value": "0.30"}'
```

### Force Token Refresh
```bash
curl -X POST "http://localhost:8000/tokens/ABC123.../refresh"
```

### Get Recent Error Logs
```bash
curl "http://localhost:8000/logs?level=ERROR&limit=20"
```

## 🔗 Related Documentation

- **[Architecture Guide](ARCHITECTURE.md)** - System design and data flow
- **[Scoring Model](SCORING_MODEL.md)** - Hybrid momentum scoring details
- **[Development Guide](DEVELOPMENT.md)** - API development and testing
- **[Deployment Guide](DEPLOYMENT.md)** - Production API configuration
## 
🤖 NotArb Integration Endpoints

Specialized endpoints for NotArb onchain-bot integration providing pool addresses for top-scoring tokens.

### GET /notarb/pools

Get token pools in simple array format (for NotArb bot compatibility).

**Response**: Array of pool address arrays
```json
[
  ["pool1", "pool2"],
  ["pool3", "pool4", "pool5"]
]
```

**Example**:
```bash
curl "https://tothemoon.sh1z01d.ru/notarb/pools"
```

**Response Codes**:
- `200`: Pools retrieved successfully
- `500`: File read error or generation failed

----

### GET /notarb/markets

Get complete token data with metadata (full format).

**Response**: Object with metadata and token information
```json
{
  "metadata": {
    "generated_at": "2025-09-18T16:00:00+00:00",
    "generator": "ToTheMoon Scoring System",
    "min_score_threshold": 0.5,
    "total_tokens": 3
  },
  "tokens": [
    {
      "mint_address": "F9Lc3HzBUhif6e3fEpB5c5QxArKnaZRbq94gqmnyH579",
      "symbol": "TOKEN",
      "name": "Token Name",
      "score": 7.0688,
      "pools": ["pool1", "pool2"]
    }
  ]
}
```

**Example**:
```bash
curl "https://tothemoon.sh1z01d.ru/notarb/markets"
```

**Response Codes**:
- `200`: Markets data retrieved successfully
- `500`: File read error or generation failed

----

### GET /notarb/file-info

Get information about the NotArb pools file.

**Response**: File status and metadata
```json
{
  "file_exists": true,
  "file_path": "markets.json",
  "file_size": 1078,
  "last_modified": "2025-09-18T16:01:04+00:00",
  "total_pool_groups": 3,
  "total_pools": 6
}
```

**Example**:
```bash
curl "https://tothemoon.sh1z01d.ru/notarb/file-info"
```

**Response Codes**:
- `200`: File info retrieved successfully
- `500`: File system error

----

### POST /notarb/export

Force update of NotArb pools file.

**Parameters**:
- `output_path` (optional): Custom output file path (default: "markets.json")

**Response**: Export status and metadata
```json
{
  "success": true,
  "output_path": "markets.json",
  "metadata": {
    "min_score_threshold": 0.5,
    "total_tokens": 3,
    "total_pool_groups": 3
  }
}
```

**Example**:
```bash
curl -X POST "https://tothemoon.sh1z01d.ru/notarb/export"
```

**Response Codes**:
- `200`: Export completed successfully
- `500`: Export failed

**Notes**:
- File is automatically updated every 5 seconds by scheduler
- Uses atomic writing to prevent corruption
- Creates backup files automatically
- Supports retry mechanism for corrupted reads