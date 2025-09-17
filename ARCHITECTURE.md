# Architecture Overview

## System Architecture

To The Moon is a modern web application built with a clean architecture pattern, separating concerns between domain logic, adapters, and application layers.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   External      │
│   (React SPA)   │◄──►│   (FastAPI)     │◄──►│   APIs          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Database      │
                       │ (PostgreSQL)    │
                       └─────────────────┘
```

## Component Architecture

### Backend Components

```
src/
├── app/                    # FastAPI Application Layer
│   ├── main.py            # Application entry point & middleware
│   ├── routes/            # API route handlers
│   │   ├── tokens.py      # Token endpoints
│   │   ├── settings.py    # Settings management
│   │   ├── admin.py       # Admin operations
│   │   └── logs.py        # Logging endpoints
│   ├── logs_buffer.py     # In-memory log buffer
│   └── spa.py             # SPA serving logic
├── core/                  # Core Utilities
│   ├── config.py          # Application configuration
│   └── json_logging.py    # Structured logging
├── domain/                # Business Logic Layer
│   ├── scoring/           # Scoring Models & Logic
│   │   ├── service.py     # Unified scoring service
│   │   ├── hybrid_momentum_model.py  # Advanced scoring model
│   │   ├── component_calculator.py   # Component calculations
│   │   ├── ewma_service.py           # EWMA smoothing
│   │   └── scorer.py      # Legacy scoring logic
│   ├── metrics/           # Metrics aggregation
│   ├── settings/          # Settings management
│   └── validation/        # Data validation
├── adapters/              # External Integration Layer
│   ├── db/               # Database Layer
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── base.py       # Database configuration
│   │   └── deps.py       # Database dependencies
│   ├── repositories/     # Data Access Layer
│   │   └── tokens_repo.py # Token data operations
│   └── services/         # External API Clients
│       └── dexscreener_client.py # DexScreener integration
├── scheduler/            # Background Processing
│   └── service.py        # APScheduler tasks
└── workers/              # Background Workers
    └── pumpfun_ws.py     # WebSocket worker
```

### Frontend Components

```
frontend/
├── src/
│   ├── pages/            # Page Components
│   │   ├── Dashboard.tsx # Main dashboard
│   │   ├── Settings.tsx  # Settings page
│   │   ├── TokenDetail.tsx # Token details
│   │   └── Logs.tsx      # Logs viewer
│   ├── components/       # Reusable Components
│   │   ├── ScoreCell.tsx # Score visualization
│   │   ├── ComponentsCell.tsx # Component display
│   │   └── AgeCell.tsx   # Age with freshness indicator
│   ├── lib/              # Utilities & API
│   │   ├── api.ts        # API client
│   │   └── scoring-utils.ts # Scoring utilities
│   └── styles.css        # Global styles
└── dist/                 # Built assets
```

## Data Flow Architecture

### Scoring Pipeline

```
1. Token Migration (WebSocket)
   ↓
2. Token Creation (status: monitoring)
   ↓
3. Validation (DexScreener API)
   ↓
4. Metrics Collection (Multi-DEX aggregation)
   ↓
5. Component Calculation (4 components)
   ↓
6. EWMA Smoothing (Stability)
   ↓
7. Score Computation (Weighted sum)
   ↓
8. Database Storage (with components)
   ↓
9. API Response (Frontend display)
```

### Request Flow

```
Frontend Request
   ↓
FastAPI Router
   ↓
Route Handler
   ↓
Repository Layer
   ↓
Database Query
   ↓
Domain Logic Processing
   ↓
Response Serialization
   ↓
Frontend Update
```

## Scoring Model Architecture

### Hybrid Momentum Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Hybrid Momentum Model                    │
├─────────────────────────────────────────────────────────────┤
│  Input: Token Metrics (liquidity, transactions, volume)    │
│                           ↓                                 │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ ComponentCalc   │  │ EWMAService     │                  │
│  │ - TX Accel      │  │ - Smoothing     │                  │
│  │ - Vol Momentum  │  │ - Persistence   │                  │
│  │ - Token Fresh   │  │ - Stability     │                  │
│  │ - Orderflow     │  └─────────────────┘                  │
│  └─────────────────┘           ↓                           │
│           ↓                    ↓                           │
│  ┌─────────────────────────────────────────────────────────┤
│  │        Weighted Score Calculation                       │
│  │  Score = W_tx×TX + W_vol×Vol + W_fresh×Fresh + W_oi×OI │
│  └─────────────────────────────────────────────────────────┤
│                           ↓                                 │
│  Output: Final Score + Component Breakdown                 │
└─────────────────────────────────────────────────────────────┘
```

### Component Calculations

```
Transaction Acceleration:
  TX_Accel = (tx_count_5m / 5) / (tx_count_1h / 60)
  
Volume Momentum:
  Vol_Momentum = volume_5m / (volume_1h / 12)
  
Token Freshness:
  Token_Freshness = max(0, (6 - hours_since_creation) / 6)
  
Orderflow Imbalance:
  OI = (buys_volume_5m - sells_volume_5m) / total_volume_5m
```

## Database Architecture

### Schema Design

```sql
-- Core token information
tokens:
  - id (PK)
  - mint_address (unique)
  - name, symbol
  - status (monitoring/active/archived)
  - created_at

-- Scoring snapshots with components
token_scores:
  - id (PK)
  - token_id (FK)
  - score, smoothed_score
  - raw_components (JSON)      -- Raw component values
  - smoothed_components (JSON) -- EWMA smoothed components
  - scoring_model             -- Model used for calculation
  - metrics (JSON)            -- Market data
  - created_at

-- Application settings
app_settings:
  - key (PK)
  - value
```

### Data Relationships

```
tokens (1) ──── (N) token_scores
   │
   └── Latest score via query optimization
   └── Score history for analysis
   └── Component breakdown for transparency
```

## API Architecture

### RESTful Design

```
GET    /health                    # System health
GET    /version                   # Application version

GET    /settings/                 # All settings
GET    /settings/{key}            # Specific setting
PUT    /settings/{key}            # Update setting
POST   /settings/model/switch     # Switch scoring model

GET    /tokens/                   # Token list with pagination
GET    /tokens/{mint}             # Token details
POST   /tokens/{mint}/refresh     # Force refresh
GET    /tokens/{mint}/pools       # Token pools

POST   /admin/recalculate         # Trigger recalculation

GET    /logs/                     # Application logs
GET    /logs/meta                 # Log metadata
```

### Response Format

```json
{
  "total": 100,
  "items": [
    {
      "mint_address": "...",
      "name": "Token Name",
      "symbol": "TKN",
      "score": 0.75,
      "raw_components": {
        "tx_accel": 0.8,
        "vol_momentum": 0.7,
        "token_freshness": 0.9,
        "orderflow_imbalance": 0.6
      },
      "smoothed_components": {
        "tx_accel": 0.75,
        "vol_momentum": 0.68,
        "token_freshness": 0.85,
        "orderflow_imbalance": 0.58
      },
      "scoring_model": "hybrid_momentum",
      "created_at": "2025-09-17T10:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "has_next": true
  }
}
```

## Security Architecture

### Authentication & Authorization
- No authentication required for read operations
- Admin operations protected by network-level security
- Rate limiting on API endpoints
- Input validation and sanitization

### Data Protection
- SQL injection prevention via SQLAlchemy ORM
- XSS protection via proper output encoding
- CORS configuration for production
- Environment-based secrets management

## Deployment Architecture

### Production Setup

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Application   │    │   Database      │
│  (Reverse Proxy)│◄──►│   (uvicorn)     │◄──►│ (PostgreSQL)    │
│  - SSL/TLS      │    │  - API Server   │    │  - Persistent   │
│  - Static Files │    │  - WebSocket    │    │  - Backups      │
│  - Load Balance │    │  - Scheduler    │    │  - Monitoring   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Service Architecture

```
systemd services:
├── tothemoon.service          # Main API server
├── tothemoon-ws.service       # WebSocket worker
└── nginx.service              # Reverse proxy

Process management:
├── uvicorn (API server)
├── APScheduler (background tasks)
├── WebSocket worker (token monitoring)
└── Database connections (pooled)
```

## Monitoring & Observability

### Logging Architecture

```
Application Logs
   ↓
JSON Structured Format
   ↓
┌─────────────────┐    ┌─────────────────┐
│  In-Memory      │    │   System Logs   │
│  Buffer         │    │   (journald)    │
│  (Real-time UI) │    │   (Persistent)  │
└─────────────────┘    └─────────────────┘
```

### Health Monitoring

```
Health Checks:
├── /health endpoint          # Application health
├── Database connectivity     # DB health
├── External API status       # DexScreener availability
└── WebSocket connection      # Pump.fun connectivity

Metrics:
├── Request latency          # API performance
├── Error rates             # System reliability
├── Token processing rates  # Business metrics
└── Component calculations  # Scoring performance
```

## Scalability Considerations

### Horizontal Scaling
- Stateless API design enables multiple instances
- Database connection pooling
- Shared state via database
- Load balancing via Nginx

### Performance Optimization
- Database indexing on frequently queried fields
- API response caching where appropriate
- Efficient SQL queries with proper joins
- Frontend bundle optimization

### Resource Management
- Memory-efficient data structures
- Connection pooling for external APIs
- Background task scheduling optimization
- Garbage collection tuning

## Technology Stack

### Backend
- **Python 3.10+**: Modern Python with type hints
- **FastAPI**: High-performance async web framework
- **SQLAlchemy 2.x**: Modern ORM with async support
- **Alembic**: Database migration management
- **Pydantic v2**: Data validation and serialization
- **APScheduler**: Background task scheduling
- **uvicorn**: ASGI server implementation

### Frontend
- **React 18**: Modern UI framework with hooks
- **TypeScript**: Type-safe JavaScript development
- **Vite**: Fast build tool and dev server
- **React Router**: Client-side routing

### Database
- **PostgreSQL 14+**: Production database
- **SQLite**: Development database

### Infrastructure
- **Nginx**: Reverse proxy and static file serving
- **systemd**: Service management
- **Git**: Version control and deployment
- **Ubuntu 22.04+**: Target deployment platform

This architecture provides a solid foundation for scalable, maintainable, and performant token scoring system with modern development practices and production-ready deployment strategies.