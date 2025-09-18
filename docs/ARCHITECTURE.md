# System Architecture

Complete architectural overview of the To The Moon token scoring system, including hybrid momentum model, data quality validation, and monitoring capabilities.

## 🏗️ High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React Dashboard]
        API_CLIENT[API Client]
    end
    
    subgraph "Application Layer"
        FASTAPI[FastAPI Server]
        ROUTES[Route Handlers]
        MIDDLEWARE[Middleware]
    end
    
    subgraph "Domain Layer"
        SCORING[Scoring Service]
        METRICS[Metrics Aggregation]
        VALIDATION[Data Validation]
        SCHEDULER[Task Scheduler]
    end
    
    subgraph "Adapter Layer"
        DB[Database Layer]
        DEXSCREENER[DexScreener Client]
        PUMPFUN[Pump.fun WebSocket]
    end
    
    subgraph "External Services"
        DEXAPI[DexScreener API]
        PUMPWS[Pump.fun WebSocket]
        POSTGRES[(PostgreSQL)]
    end
    
    UI --> API_CLIENT
    API_CLIENT --> FASTAPI
    FASTAPI --> ROUTES
    ROUTES --> SCORING
    ROUTES --> METRICS
    SCORING --> VALIDATION
    SCHEDULER --> SCORING
    SCORING --> DB
    METRICS --> DEXSCREENER
    SCHEDULER --> PUMPFUN
    DEXSCREENER --> DEXAPI
    PUMPFUN --> PUMPWS
    DB --> POSTGRES
```

## 📁 Project Structure

### Backend Components
```
src/
├── app/                    # FastAPI Application Layer
│   ├── main.py            # Application entry point & middleware
│   ├── routes/            # API route handlers
│   │   ├── tokens.py      # Token endpoints
│   │   ├── meta.py        # Health & system endpoints
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
│   │   ├── scoring_service.py      # Unified scoring service
│   │   ├── hybrid_momentum_model.py # Advanced scoring model
│   │   ├── component_calculator.py # Component calculations
│   │   ├── ewma_service.py         # EWMA smoothing
│   │   └── scorer.py               # Legacy scoring logic
│   ├── metrics/           # Metrics aggregation
│   │   ├── dex_aggregator.py       # DEX data aggregation
│   │   └── enhanced_dex_aggregator.py # Enhanced metrics
│   ├── validation/        # Data validation
│   │   ├── data_filters.py         # Data quality validation
│   │   ├── dex_rules.py           # DEX validation rules
│   │   └── quality_settings.py    # Quality configuration
│   └── settings/          # Settings management
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
│   ├── service.py        # APScheduler tasks
│   ├── monitoring.py     # Health monitoring
│   ├── fallback_handler.py # Fallback mechanisms
│   └── tasks.py          # Background tasks
└── workers/              # Background Workers
    └── pumpfun_ws.py     # WebSocket worker
```

## 🧮 Hybrid Momentum Scoring Architecture

### Scoring Pipeline

```mermaid
flowchart TD
    A[Token Migration Event] --> B[Create Monitoring Token]
    B --> C[DexScreener Validation]
    C --> D{Activation Criteria Met?}
    D -->|Yes| E[Promote to Active]
    D -->|No| F[Keep Monitoring]
    E --> G[Collect Enhanced Metrics]
    F --> G
    G --> H[Data Quality Validation]
    H --> I{Data Quality OK?}
    I -->|Yes| J[Calculate Components]
    I -->|No| K[Apply Fallback Logic]
    K --> J
    J --> L[Apply EWMA Smoothing]
    L --> M[Compute Final Score]
    M --> N[Store Score Snapshot]
    N --> O[Update Token Status]
```

### Component Architecture

```mermaid
graph LR
    subgraph "Input Metrics"
        TX[Transaction Data]
        VOL[Volume Data]
        LIQ[Liquidity Data]
        TIME[Creation Time]
    end
    
    subgraph "Component Calculator"
        CALC[ComponentCalculator]
        TX_ACCEL[TX Acceleration]
        VOL_MOM[Volume Momentum]
        FRESH[Token Freshness]
        ORDER[Orderflow Imbalance]
    end
    
    subgraph "EWMA Service"
        SMOOTH[EWMA Smoothing]
        HISTORY[Historical Data]
        ALPHA[Alpha Parameter]
    end
    
    subgraph "Scoring Model"
        WEIGHTS[Component Weights]
        FORMULA[Weighted Sum]
        FINAL[Final Score]
    end
    
    TX --> TX_ACCEL
    VOL --> VOL_MOM
    VOL --> ORDER
    TIME --> FRESH
    
    TX_ACCEL --> SMOOTH
    VOL_MOM --> SMOOTH
    FRESH --> SMOOTH
    ORDER --> SMOOTH
    
    SMOOTH --> FORMULA
    WEIGHTS --> FORMULA
    FORMULA --> FINAL
```

### Component Formulas

| Component | Formula | Purpose |
|-----------|---------|---------|
| **Transaction Acceleration** | `(tx_5m/5) / (tx_1h/60)` | Measures trading pace acceleration |
| **Volume Momentum** | `vol_5m / (vol_1h/12)` | Compares recent vs average volume |
| **Token Freshness** | `max(0, (6-hours)/6)` | Bonus for recently migrated tokens |
| **Orderflow Imbalance** | `(buys-sells)/(buys+sells)` | Buy/sell pressure analysis |

### EWMA Smoothing

```
EWMA Formula: new_value = α × current + (1-α) × previous
- α = 0.3 (configurable smoothing parameter)
- Applied to all components and final score
- Reduces volatility and prevents manipulation
- Maintains scoring stability over time
```

## 🔍 Data Quality & Validation System

### Multi-Level Validation

```mermaid
flowchart TD
    A[Raw DEX Data] --> B[Liquidity Filtering]
    B --> C[Pool Validation]
    C --> D[Metrics Consistency Check]
    D --> E{Critical Issues?}
    E -->|Yes| F[Block Update]
    E -->|No| G{Warnings Only?}
    G -->|Yes| H[Allow with Warnings]
    G -->|No| I[Full Quality Pass]
    F --> J[Log Critical Error]
    H --> K[Log Warnings]
    I --> L[Process Normally]
```

### Validation Levels

1. **Critical Issues** (Block updates):
   - Negative liquidity or transaction counts
   - Invalid data types
   - Missing required fields

2. **Warnings** (Allow with flags):
   - High liquidity but no transactions
   - Many transactions but no price movement
   - Suspicious price change ratios

3. **Quality Filters**:
   - Minimum liquidity thresholds ($500)
   - DEX exclusions (bonding curves)
   - Pool count anomaly detection

### Fallback Mechanisms

```mermaid
graph TD
    A[Data Quality Issue] --> B{Issue Type}
    B -->|Critical| C[Use Emergency Score]
    B -->|Warning| D[Use Degraded Score]
    B -->|Temporary| E[Use Fallback Score]
    
    C --> F[Median of Last 10 Scores × 0.5]
    D --> G[Current Score with Warning Flag]
    E --> H[Average of Recent Scores × 0.7]
    
    F --> I[Continue Processing]
    G --> I
    H --> I
```

## 📊 Scheduler & Monitoring Architecture

### Smart Scheduling System

```mermaid
graph TB
    subgraph "Token Classification"
        HOT[Hot Tokens<br/>smoothed_score ≥ 0.3]
        COLD[Cold Tokens<br/>smoothed_score < 0.3]
    end
    
    subgraph "Update Frequencies"
        HOT_SCHED[Every 30 seconds]
        COLD_SCHED[Every 2 minutes]
    end
    
    subgraph "Health Monitoring"
        HEALTH[Health Monitor]
        STALE[Stale Detection]
        ALERTS[Alert System]
    end
    
    HOT --> HOT_SCHED
    COLD --> COLD_SCHED
    HOT_SCHED --> HEALTH
    COLD_SCHED --> HEALTH
    HEALTH --> STALE
    STALE --> ALERTS
```

### Monitoring Capabilities

- **Scheduler Health**: `/health/scheduler` endpoint
- **Token Freshness**: Automatic stale token detection
- **Group Execution**: Hot/cold group processing monitoring
- **Performance Metrics**: Update frequencies and success rates
- **Data Quality**: Validation success/failure tracking

## 🗄️ Database Architecture

### Enhanced Schema Design

```sql
-- Core token information
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    mint_address TEXT UNIQUE NOT NULL,
    name TEXT,
    symbol TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'monitoring',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated_at TIMESTAMP WITH TIME ZONE
);

-- Enhanced scoring snapshots
CREATE TABLE token_scores (
    id SERIAL PRIMARY KEY,
    token_id INTEGER REFERENCES tokens(id) ON DELETE CASCADE,
    score NUMERIC(10,4),
    smoothed_score NUMERIC(10,4),
    raw_components JSONB,           -- Raw component values
    smoothed_components JSONB,      -- EWMA smoothed components
    scoring_model VARCHAR(50) DEFAULT 'hybrid_momentum',
    metrics JSONB,                  -- Market data with quality flags
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Application settings
CREATE TABLE app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Indexes for performance
CREATE INDEX idx_tokens_status ON tokens(status);
CREATE INDEX idx_tokens_mint ON tokens(mint_address);
CREATE INDEX idx_scores_token_created ON token_scores(token_id, created_at DESC);
CREATE INDEX idx_scores_model ON token_scores(scoring_model);
```

### Data Relationships

```mermaid
erDiagram
    TOKENS ||--o{ TOKEN_SCORES : has
    TOKENS {
        int id PK
        string mint_address UK
        string name
        string symbol
        string status
        timestamp created_at
        timestamp last_updated_at
    }
    TOKEN_SCORES {
        int id PK
        int token_id FK
        decimal score
        decimal smoothed_score
        jsonb raw_components
        jsonb smoothed_components
        string scoring_model
        jsonb metrics
        timestamp created_at
    }
    APP_SETTINGS {
        string key PK
        string value
    }
```

## 🌐 API Architecture

### RESTful Endpoint Design

```mermaid
graph LR
    subgraph "Health & System"
        H1[GET /health]
        H2[GET /health/scheduler]
        H3[GET /version]
    end
    
    subgraph "Token Operations"
        T1[GET /tokens/]
        T2[GET /tokens/{mint}]
        T3[POST /tokens/{mint}/refresh]
        T4[GET /tokens/{mint}/pools]
    end
    
    subgraph "System Management"
        S1[GET /settings]
        S2[POST /settings]
        S3[GET /logs]
        S4[POST /admin/recalculate]
    end
```

### Enhanced Response Models

```json
{
  "mint_address": "ABC123...",
  "name": "Token Name",
  "symbol": "TKN",
  "status": "active",
  "score": 0.75,
  "raw_components": {
    "tx_accel": 0.8,
    "vol_momentum": 0.7,
    "token_freshness": 0.9,
    "orderflow_imbalance": 0.6,
    "final_score": 0.75
  },
  "smoothed_components": {
    "tx_accel": 0.75,
    "vol_momentum": 0.68,
    "token_freshness": 0.85,
    "orderflow_imbalance": 0.58,
    "final_score": 0.72
  },
  "scoring_model": "hybrid_momentum",
  "metrics": {
    "L_tot": 50000.0,
    "tx_count_5m": 25,
    "volume_5m": 1000.0,
    "data_quality_ok": true,
    "data_quality_issues": []
  },
  "created_at": "2025-09-18T10:00:00+00:00",
  "scored_at": "2025-09-18T10:05:00+00:00"
}
```

## 🔒 Security Architecture

### Security Layers

1. **Input Validation**
   - Pydantic model validation
   - SQL injection prevention via ORM
   - XSS protection via proper encoding

2. **Network Security**
   - Rate limiting on API endpoints
   - CORS configuration
   - Reverse proxy (Nginx) protection

3. **Data Protection**
   - Environment-based secrets
   - Database connection encryption
   - Structured logging (no sensitive data)

4. **Access Control**
   - Read-only public API
   - Network-level admin protection
   - Service isolation

## 🚀 Deployment Architecture

### Production Infrastructure

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx<br/>SSL Termination<br/>Static Files]
    end
    
    subgraph "Application Tier"
        APP1[FastAPI Server<br/>uvicorn]
        SCHED[APScheduler<br/>Background Tasks]
        WS[WebSocket Worker<br/>Pump.fun Monitor]
    end
    
    subgraph "Data Tier"
        DB[(PostgreSQL<br/>Primary Database)]
        LOGS[Log Storage<br/>journald]
    end
    
    subgraph "External Services"
        DEX[DexScreener API]
        PUMP[Pump.fun WebSocket]
    end
    
    LB --> APP1
    APP1 --> SCHED
    APP1 --> DB
    SCHED --> DB
    WS --> PUMP
    SCHED --> DEX
    APP1 --> LOGS
```

### Service Management

```bash
# systemd services
tothemoon.service          # Main API server
tothemoon-worker.service   # WebSocket worker

# Process architecture
├── uvicorn (ASGI server)
├── APScheduler (background tasks)
├── WebSocket worker (token monitoring)
└── Database connections (pooled)
```

## 📈 Performance & Scalability

### Performance Optimizations

1. **Database Optimizations**
   - Strategic indexing on query patterns
   - Connection pooling
   - Efficient JOIN operations
   - JSONB for flexible component storage

2. **API Performance**
   - Async request handling
   - Response caching where appropriate
   - Pagination for large datasets
   - Efficient serialization

3. **Background Processing**
   - Smart scheduling (hot/cold groups)
   - Batch processing where possible
   - Rate limiting for external APIs
   - Graceful error handling

### Scalability Considerations

- **Horizontal Scaling**: Stateless API design
- **Database Scaling**: Read replicas for reporting
- **Caching Layer**: Redis for frequently accessed data
- **Load Balancing**: Multiple API instances

## 🔧 Configuration Management

### Environment-Based Configuration

```python
# Core settings
APP_ENV: dev/stage/prod
LOG_LEVEL: INFO/DEBUG
DATABASE_URL: Connection string
SCHEDULER_ENABLED: true/false

# Scoring configuration (runtime via API)
scoring_model_active: hybrid_momentum
w_tx, w_vol, w_fresh, w_oi: Component weights
ewma_alpha: Smoothing parameter
min_score: Threshold for hot/cold classification
```

### Runtime Configuration

- **API-based settings**: `/settings` endpoint
- **Database persistence**: `app_settings` table
- **Hot reloading**: No restart required
- **Validation**: Pydantic model validation

## 🔍 Observability & Monitoring

### Logging Architecture

```mermaid
graph LR
    subgraph "Application Logs"
        APP[FastAPI App]
        SCHED[Scheduler]
        WS[WebSocket Worker]
    end
    
    subgraph "Log Processing"
        JSON[JSON Formatter]
        BUFFER[In-Memory Buffer]
        JOURNAL[systemd journal]
    end
    
    subgraph "Log Consumption"
        API[Logs API]
        UI[Web Interface]
        CLI[journalctl]
    end
    
    APP --> JSON
    SCHED --> JSON
    WS --> JSON
    JSON --> BUFFER
    JSON --> JOURNAL
    BUFFER --> API
    API --> UI
    JOURNAL --> CLI
```

### Health Monitoring

- **System Health**: `/health` endpoint
- **Scheduler Health**: `/health/scheduler` with detailed metrics
- **Token Freshness**: Automatic stale detection
- **Data Quality**: Validation success rates
- **Performance Metrics**: Response times and throughput

This architecture provides a robust, scalable, and maintainable foundation for the To The Moon token scoring system, with modern development practices and production-ready deployment strategies.