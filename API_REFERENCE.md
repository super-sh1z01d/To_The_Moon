# API Reference

## Base URL
- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

## Authentication
No authentication required for read operations. Admin operations should be protected at the network level.

## Response Format
All API responses follow a consistent JSON format with appropriate HTTP status codes.

### Success Response
```json
{
  "data": { ... },
  "meta": { ... }
}
```

### Error Response
```json
{
  "error": {
    "code": 400,
    "message": "Validation error",
    "details": { ... }
  }
}
```

## Endpoints

### Health & System

#### GET /health
System health check.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-09-17T10:00:00Z"
}
```

#### GET /version
Application version information.

**Response:**
```json
{
  "version": "2.0.0",
  "build": "2025-09-17",
  "model": "hybrid_momentum"
}
```

### Settings Management

#### GET /settings/
Get all application settings with defaults.

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
  "min_score": "0.15"
}
```

#### GET /settings/{key}
Get specific setting value.

**Parameters:**
- `key` (path): Setting key name

**Response:**
```json
{
  "key": "w_tx",
  "value": "0.25"
}
```

**Error Responses:**
- `404`: Setting key not found

#### PUT /settings/{key}
Update specific setting value.

**Parameters:**
- `key` (path): Setting key name

**Request Body:**
```json
{
  "value": "0.3"
}
```

**Response:**
```json
{
  "key": "w_tx",
  "value": "0.3",
  "updated": true
}
```

**Error Responses:**
- `400`: Invalid value or validation error
- `404`: Setting key not found

#### GET /settings/validation/errors
Get current settings validation errors.

**Response:**
```json
{
  "errors": [
    {
      "key": "w_tx",
      "error": "Value must be between 0.0 and 1.0"
    }
  ],
  "valid": false
}
```

#### GET /settings/weights
Get weights for all scoring models.

**Response:**
```json
{
  "hybrid_momentum": {
    "w_tx": 0.25,
    "w_vol": 0.25,
    "w_fresh": 0.25,
    "w_oi": 0.25
  },
  "legacy": {
    "weight_s": 0.35,
    "weight_l": 0.25,
    "weight_m": 0.20,
    "weight_t": 0.20
  }
}
```

#### POST /settings/model/switch
Switch active scoring model.

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
  "switched": true
}
```

**Error Responses:**
- `400`: Invalid model name

### Token Operations

#### GET /tokens/
List tokens with filtering and pagination.

**Query Parameters:**
- `min_score` (float, optional): Minimum score threshold (default: from settings)
- `limit` (int, optional): Number of items per page (1-100, default: 50)
- `offset` (int, optional): Number of items to skip (default: 0)
- `sort` (string, optional): Sort order - `score_desc`, `score_asc` (default: `score_desc`)
- `statuses` (string, optional): Comma-separated status list - `active`, `monitoring`, `archived` (default: `active,monitoring`)

**Response:**
```json
{
  "total": 150,
  "items": [
    {
      "mint_address": "So11111111111111111111111111111111111111112",
      "name": "Wrapped SOL",
      "symbol": "WSOL",
      "status": "active",
      "score": 0.8542,
      "liquidity_usd": 125000.50,
      "delta_p_5m": 0.0234,
      "delta_p_15m": 0.0456,
      "n_5m": 145,
      "primary_dex": "raydium",
      "fetched_at": "2025-09-17T10:00:00Z",
      "scored_at": "2025-09-17T10:01:00Z",
      "solscan_url": "https://solscan.io/token/So11111111111111111111111111111111111111112",
      "raw_components": {
        "tx_accel": 0.85,
        "vol_momentum": 0.78,
        "token_freshness": 0.92,
        "orderflow_imbalance": 0.65
      },
      "smoothed_components": {
        "tx_accel": 0.82,
        "vol_momentum": 0.75,
        "token_freshness": 0.89,
        "orderflow_imbalance": 0.62
      },
      "scoring_model": "hybrid_momentum",
      "created_at": "2025-09-17T08:00:00Z"
    }
  ],
  "meta": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "page": 1,
    "page_size": 50,
    "has_prev": false,
    "has_next": true,
    "sort": "score_desc",
    "min_score": 0.15
  }
}
```

#### GET /tokens/{mint}
Get detailed information about a specific token.

**Parameters:**
- `mint` (path): Token mint address
- `history_limit` (query, optional): Number of historical score entries (1-200, default: 20)

**Response:**
```json
{
  "mint_address": "So11111111111111111111111111111111111111112",
  "name": "Wrapped SOL",
  "symbol": "WSOL",
  "status": "active",
  "score": 0.8542,
  "metrics": {
    "L_tot": 125000.50,
    "delta_p_5m": 0.0234,
    "delta_p_15m": 0.0456,
    "n_5m": 145,
    "primary_dex": "raydium",
    "fetched_at": "2025-09-17T10:00:00Z",
    "pools": [...]
  },
  "raw_components": {
    "tx_accel": 0.85,
    "vol_momentum": 0.78,
    "token_freshness": 0.92,
    "orderflow_imbalance": 0.65
  },
  "smoothed_components": {
    "tx_accel": 0.82,
    "vol_momentum": 0.75,
    "token_freshness": 0.89,
    "orderflow_imbalance": 0.62
  },
  "scoring_model": "hybrid_momentum",
  "score_history": [
    {
      "created_at": "2025-09-17T10:01:00Z",
      "score": 0.8542,
      "metrics": { ... }
    }
  ],
  "pools": [
    {
      "address": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
      "dex": "raydium",
      "quote": "WSOL",
      "solscan_url": "https://solscan.io/address/58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
    }
  ],
  "solscan_url": "https://solscan.io/token/So11111111111111111111111111111111111111112"
}
```

**Error Responses:**
- `404`: Token not found

#### POST /tokens/{mint}/refresh
Force refresh token metrics and recalculate score.

**Parameters:**
- `mint` (path): Token mint address

**Response:**
```json
{
  "updated_snapshot_id": 12345,
  "score": 0.8542,
  "updated_at": "2025-09-17T10:05:00Z"
}
```

**Error Responses:**
- `404`: Token not found
- `503`: External API unavailable

#### GET /tokens/{mint}/pools
Get token's trading pools.

**Parameters:**
- `mint` (path): Token mint address

**Response:**
```json
[
  {
    "address": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
    "dex": "raydium",
    "quote": "WSOL",
    "solscan_url": "https://solscan.io/address/58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
  },
  {
    "address": "7XawhbbxtsRcQA8KTkHT9f9nc6d69UwqCDh6U5EEbEmX",
    "dex": "orca",
    "quote": "USDC",
    "solscan_url": "https://solscan.io/address/7XawhbbxtsRcQA8KTkHT9f9nc6d69UwqCDh6U5EEbEmX"
  }
]
```

**Error Responses:**
- `404`: Token not found

### Admin Operations

#### POST /admin/recalculate
Trigger manual recalculation of token scores.

**Response:**
```json
{
  "status": "started",
  "message": "Recalculation triggered for hot and cold token groups",
  "timestamp": "2025-09-17T10:00:00Z"
}
```

### Logging

#### GET /logs/
Get application logs from in-memory buffer.

**Query Parameters:**
- `limit` (int, optional): Number of log entries (1-500, default: 100)
- `levels` (string, optional): Comma-separated log levels - `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `loggers` (string, optional): Comma-separated logger names
- `contains` (string, optional): Filter by message content
- `since` (string, optional): ISO timestamp to filter logs after

**Response:**
```json
[
  {
    "ts": "2025-09-17T10:00:00.123456+00:00",
    "level": "INFO",
    "logger": "access",
    "msg": "request_completed",
    "module": "main",
    "func": "access_logger",
    "line": 54,
    "path": "/tokens/",
    "method": "GET",
    "status": 200,
    "latency_ms": 15
  }
]
```

#### GET /logs/meta
Get logging metadata.

**Response:**
```json
{
  "loggers": [
    "access",
    "scheduler",
    "scoring",
    "ewma",
    "component_calc",
    "uvicorn.access"
  ]
}
```

#### DELETE /logs/
Clear in-memory log buffer.

**Response:**
```json
{
  "cleared": 1247,
  "timestamp": "2025-09-17T10:00:00Z"
}
```

## Data Models

### Token Item
```typescript
interface TokenItem {
  mint_address: string
  name?: string
  symbol?: string
  status: 'monitoring' | 'active' | archived'
  score?: number
  liquidity_usd?: number
  delta_p_5m?: number
  delta_p_15m?: number
  n_5m?: number
  primary_dex?: string
  fetched_at?: string
  scored_at?: string
  solscan_url: string
  raw_components?: ComponentBreakdown
  smoothed_components?: ComponentBreakdown
  scoring_model?: string
  created_at?: string
}
```

### Component Breakdown
```typescript
interface ComponentBreakdown {
  tx_accel: number          // Transaction Acceleration (0.0-1.0)
  vol_momentum: number      // Volume Momentum (0.0-1.0)
  token_freshness: number   // Token Freshness (0.0-1.0)
  orderflow_imbalance: number // Orderflow Imbalance (-1.0-1.0)
}
```

### Pool Item
```typescript
interface PoolItem {
  address?: string
  dex?: string
  quote?: string
  solscan_url?: string
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters or validation error |
| 404 | Not Found - Resource not found |
| 422 | Unprocessable Entity - Invalid request body |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - External API unavailable |

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- General endpoints: 100 requests per minute per IP
- Admin endpoints: 10 requests per minute per IP
- Refresh endpoints: 5 requests per minute per IP

## Examples

### Get tokens with Hybrid Momentum components
```bash
curl "http://localhost:8000/tokens/?limit=5" | jq '.items[0].smoothed_components'
```

### Switch to Hybrid Momentum model
```bash
curl -X POST "http://localhost:8000/settings/model/switch" \
  -H "Content-Type: application/json" \
  -d '{"model": "hybrid_momentum"}'
```

### Update component weight
```bash
curl -X PUT "http://localhost:8000/settings/w_tx" \
  -H "Content-Type: application/json" \
  -d '{"value": "0.3"}'
```

### Get fresh tokens only (client-side filtering)
```bash
curl "http://localhost:8000/tokens/?limit=50" | \
  jq '.items[] | select(.created_at and (now - (.created_at | fromdateiso8601)) < 21600)'
```

### Force refresh specific token
```bash
curl -X POST "http://localhost:8000/tokens/So11111111111111111111111111111111111111112/refresh"
```

## WebSocket (Future)

WebSocket endpoints for real-time updates are planned for future releases:

```javascript
// Future WebSocket API
const ws = new WebSocket('ws://localhost:8000/ws/tokens');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  // Handle real-time token updates
};
```

## SDK (Future)

Official SDKs for popular languages are planned:

```python
# Future Python SDK
from tothemoon import Client

client = Client('http://localhost:8000')
tokens = client.tokens.list(min_score=0.5, limit=10)
```

```javascript
// Future JavaScript SDK
import { ToTheMoonClient } from '@tothemoon/sdk';

const client = new ToTheMoonClient('http://localhost:8000');
const tokens = await client.tokens.list({ minScore: 0.5, limit: 10 });
```