# To The Moon - Полная Блок-Схема Системы

## 🎯 Обзор Системы

To The Moon - это система автоматического скоринга токенов Solana, которые мигрировали с Pump.fun на внешние DEX платформы. Система оптимизирована для высокочастотного арбитража с интервалами 700ms.

---

## 📊 Полная Блок-Схема Процесса

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           🚀 TO THE MOON SYSTEM                                │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   🔄 PUMP.FUN   │    │  📡 DEXSCREENER │    │  🎯 SCHEDULER   │
│   WebSocket     │    │      API        │    │   (15-45s)      │
│   Monitoring    │    │   Data Source   │    │   Processing    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ New Migration        │ Token Data           │ Batch Processing
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          💾 DATABASE LAYER                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   TOKENS    │  │TOKEN_SCORES │  │APP_SETTINGS │  │   ALEMBIC   │          │
│  │             │  │             │  │             │  │ MIGRATIONS  │          │
│  │ • mint_addr │  │ • score     │  │ • weights   │  │             │          │
│  │ • symbol    │  │ • metrics   │  │ • thresholds│  │             │          │
│  │ • status    │  │ • components│  │ • config    │  │             │          │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        🔄 TOKEN LIFECYCLE FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │ NEW TOKEN   │ ◄─── Pump.fun Migration Detected
    │ (monitoring)│
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐      ┌─────────────────────────────────────┐
    │ VALIDATION  │ ────▶│ • Check DexScreener pairs           │
    │   PHASE     │      │ • Validate WSOL/SOL pools          │
    └──────┬──────┘      │ • Exclude pumpfun-only pools       │
           │             │ • Min liquidity: $200 (monitoring) │
           ▼             └─────────────────────────────────────┘
    ┌─────────────┐
    │   ACTIVE    │ ◄─── External pools found + validation passed
    │   STATUS    │
    └──────┬──────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         📊 SCORING PIPELINE                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  📈 METRICS     │    │  🧮 COMPONENTS  │    │  ⚖️ WEIGHTED    │
│  COLLECTION     │    │  CALCULATION    │    │    SCORING      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • TX counts     │    │ TX Component    │    │ Final Score =   │
│ • Volume data   │    │ (Arbitrage)     │    │ 0.8×TX +        │
│ • Price changes │    │ ┌─────────────┐ │    │ 0.2×FRESH       │
│ • Liquidity     │    │ │70% Absolute │ │    │                 │
│ • Order flow    │    │ │30% Accel    │ │    │ EWMA Smoothing  │
│ • Pool info     │    │ └─────────────┘ │    │ α = 0.3         │
└─────────────────┘    │                 │    └─────────────────┘
                       │ VOL Component   │
                       │ (Disabled: 0%)  │
                       │                 │
                       │ FRESH Component │
                       │ (Age bonus)     │
                       │                 │
                       │ OI Component    │
                       │ (Disabled: 0%)  │
                       └─────────────────┘
## 🎯 Дет
альный Процесс Арбитражного Скоринга

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    🔥 ARBITRAGE SCORING FORMULA                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

INPUT: TX_5m, TX_1h
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ ABSOLUTE        │    │ ACCELERATION    │
│ ACTIVITY        │    │ COMPONENT       │
│                 │    │                 │
│ if TX_5m < 50:  │    │ Rate_5m = TX_5m/5│
│   score = 0.0   │    │ Rate_1h = TX_1h/60│
│ elif TX_5m≥200: │    │                 │
│   score = 1.0   │    │ if Rate_1h > 0: │
│ else:           │    │   ratio = Rate_5m/│
│   score = (TX_5m│    │          Rate_1h │
│   -50)/(200-50) │    │   if ratio ≥ 2.0:│
│                 │    │     accel = 1.0  │
│                 │    │   elif ratio≥1.0:│
│                 │    │     accel = ratio│
│                 │    │            -1.0  │
│                 │    │   else:          │
│                 │    │     accel = 0.0  │
│                 │    │ else:            │
│                 │    │   accel = 0.0    │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          │ Weight: 70%          │ Weight: 30%
          ▼                      ▼
         ┌─────────────────────────────┐
         │    TX_Score = Absolute×0.7  │
         │             + Accel×0.3     │
         └─────────────┬───────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │ FINAL_SCORE = TX_Score×0.8  │
         │             + Freshness×0.2 │
         └─────────────────────────────┘
```

---

## 🔄 Scheduler Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ⏰ SCHEDULER CYCLES                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

Every 15 seconds (HOT GROUP):
┌─────────────────┐
│ HIGH PRIORITY   │ ──┐
│ • Score ≥ 0.5   │   │
│ • Recent updates│   │
│ • Active status │   │
└─────────────────┘   │
                      ▼
Every 35 seconds (COLD GROUP):     ┌─────────────────┐
┌─────────────────┐                │ BATCH PROCESS   │
│ LOW PRIORITY    │ ──────────────▶│ • Fetch pairs   │
│ • Score < 0.5   │                │ • Calculate     │
│ • Older tokens  │                │ • Update DB     │
│ • Monitoring    │                │ • Apply EWMA    │
└─────────────────┘                └─────────────────┘
                                           │
                                           ▼
                                   ┌─────────────────┐
                                   │ STATUS UPDATES  │
                                   │ • Archive low   │
                                   │ • Promote good  │
                                   │ • Timeout old   │
                                   └─────────────────┘
```

---

## 📊 Token Status Transitions

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        🔄 TOKEN STATUS FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │ MONITORING  │ ◄─── New token from Pump.fun
    │             │
    │ Conditions: │
    │ • Min 1 TX  │
    │ • Min $1 vol│
    │ • Basic val │
    └──────┬──────┘
           │
           │ External pools found
           │ + Validation passed
           ▼
    ┌─────────────┐
    │   ACTIVE    │
    │             │
    │ Conditions: │
    │ • Min 100 TX│
    │ • Min $500  │
    │ • Strict val│
    └──────┬──────┘
           │
           │ Score < threshold
           │ for 12+ hours
           ▼
    ┌─────────────┐
    │  ARCHIVED   │ ◄─── Also: Monitoring timeout (12h)
    │             │
    │ Reasons:    │
    │ • Low score │
    │ • Timeout   │
    │ • Manual    │
    └─────────────┘
```

---

## 🎯 API & Frontend Integration

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         🌐 API & FRONTEND FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   REACT SPA     │    │   FASTAPI       │    │   DATABASE      │
│   Frontend      │    │   Backend       │    │   SQLite/PG     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ GET /tokens          │                      │
          ├─────────────────────▶│ Query latest scores  │
          │                      ├─────────────────────▶│
          │                      │                      │
          │ Token list + scores  │ Formatted response   │
          │◄─────────────────────┤◄─────────────────────┤
          │                      │                      │
          │ Auto-refresh 30s     │                      │
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • Token table   │    │ • /tokens       │    │ • tokens        │
│ • Score sorting │    │ • /tokens/{id}  │    │ • token_scores  │
│ • Filtering     │    │ • /health       │    │ • app_settings  │
│ • Pagination    │    │ • /meta         │    │                 │
│ • Components    │    │ • /notarb       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```---


## 🤖 Bot Integration Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        🤖 ARBITRAGE BOT INTEGRATION                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  TO THE MOON    │    │  NOTARB POOLS   │    │ ARBITRAGE BOT   │
│    SYSTEM       │    │  INTEGRATION    │    │   (700ms)       │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ Tokens score ≥ 0.4   │                      │
          ├─────────────────────▶│ Export qualified     │
          │                      │ tokens to JSON       │
          │                      ├─────────────────────▶│
          │                      │                      │
          │                      │ Pool addresses       │ High-freq
          │                      │ + metadata           │ trading
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ SCORING TIERS:  │    │ • WSOL pairs    │    │ TRADING LOGIC:  │
│                 │    │ • USDC pairs    │    │                 │
│ 🔥 ≥ 0.7: BOT   │    │ • Liquidity     │    │ • 700ms cycles  │
│ 🟡 ≥ 0.5: WATCH │    │ • Volume data   │    │ • Price diff    │
│ 🟠 ≥ 0.3: RISKY │    │ • DEX info      │    │ • Slippage calc │
│ ❌ < 0.3: SKIP  │    │                 │    │ • Profit target │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🔧 Configuration & Settings

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ⚙️ SYSTEM CONFIGURATION                                │
└─────────────────────────────────────────────────────────────────────────────────┘

DATABASE SETTINGS (app_settings table):
┌─────────────────────────────────────────────────────────────────────────────────┐
│ SCORING WEIGHTS:                    │ ARBITRAGE SETTINGS:                       │
│ • w_tx: 0.8 (80%)                  │ • tx_calculation_mode: arbitrage_activity │
│ • w_vol: 0.0 (0%)                  │ • arbitrage_min_tx_5m: 50                 │
│ • w_fresh: 0.2 (20%)               │ • arbitrage_optimal_tx_5m: 200            │
│ • w_oi: 0.0 (0%)                   │ • arbitrage_acceleration_weight: 0.3      │
├─────────────────────────────────────┼───────────────────────────────────────────┤
│ THRESHOLDS:                         │ SCHEDULER SETTINGS:                       │
│ • min_score: 0.1                    │ • hot_group_interval: 15s                 │
│ • archive_below_hours: 12           │ • cold_group_interval: 35s                │
│ • monitoring_timeout_hours: 12      │ • batch_size_hot: 30                      │
│ • min_pool_liquidity_usd: 500       │ • batch_size_cold: 70                     │
└─────────────────────────────────────┴───────────────────────────────────────────┘

ENVIRONMENT VARIABLES (.env):
┌─────────────────────────────────────────────────────────────────────────────────┐
│ • APP_ENV: prod/stage/dev           │ • SCHEDULER_ENABLED: true                 │
│ • LOG_LEVEL: INFO/DEBUG             │ • FRONTEND_DIST_PATH: ./frontend/dist     │
│ • DATABASE_URL: sqlite:///dev.db    │ • PUMPFUN_RUN_SECONDS: 120               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📈 Performance Optimizations

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        🚀 PERFORMANCE FEATURES                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ BATCH PROCESSING│    │ EWMA SMOOTHING  │    │ CIRCUIT BREAKER │
│                 │    │                 │    │                 │
│ • 70 tokens/    │    │ • Reduces noise │    │ • API failures  │
│   cold cycle    │    │ • Stable scores │    │ • Auto recovery │
│ • 30 tokens/    │    │ • α = 0.3       │    │ • Fallback data │
│   hot cycle     │    │ • Trend follow  │    │ • Rate limiting │
│ • 2s timeout    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ PRIORITY QUEUE  │    │ DATA CACHING    │    │ ERROR HANDLING  │
│                 │    │                 │    │                 │
│ • High score    │    │ • 60s API cache │    │ • Graceful fail │
│   first         │    │ • DB connection │    │ • Retry logic   │
│ • Recent update │    │   pooling       │    │ • Fallback vals │
│ • Status based  │    │ • Memory cache  │    │ • Health checks │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🎯 Key Metrics & Monitoring

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         📊 SYSTEM METRICS                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

PROCESSING METRICS:
• Tokens processed per minute: ~200
• API calls per hour: ~1,200
• Average response time: <2s
• Success rate: >95%

SCORING DISTRIBUTION:
• Score ≥ 0.7 (Bot ready): ~2-5 tokens
• Score ≥ 0.5 (Watch list): ~5-10 tokens  
• Score ≥ 0.3 (Risky): ~10-20 tokens
• Score < 0.3 (Filtered): ~80% tokens

TOKEN LIFECYCLE:
• New tokens/day: ~50-100
• Monitoring → Active: ~20%
• Active → Archived: ~80% (12h)
• Average token lifespan: 6-24 hours

ARBITRAGE READINESS:
• 200+ TX/5min tokens: ~1-3 active
• High liquidity (>$10k): ~5-10 tokens
• Bot-ready tokens: ~2-5 simultaneously
```

---

## 🔄 Rollback & Recovery

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        🔄 ROLLBACK CAPABILITIES                                │
└─────────────────────────────────────────────────────────────────────────────────┘

FORMULA ROLLBACK:
┌─────────────────┐    ┌─────────────────┐
│ Current:        │    │ Rollback to:    │
│ Arbitrage Mode  │    │ Classic Mode    │
│                 │    │                 │
│ settings.set(   │    │ settings.set(   │
│ 'tx_calculation │    │ 'tx_calculation │
│ _mode',         │    │ _mode',         │
│ 'arbitrage_     │    │ 'acceleration') │
│ activity')      │    │                 │
└─────────────────┘    └─────────────────┘

WEIGHT ROLLBACK:
┌─────────────────┐    ┌─────────────────┐
│ Current:        │    │ Rollback to:    │
│ 80/0/20/0       │    │ 25/25/25/25     │
│                 │    │                 │
│ w_tx: 0.8       │    │ w_tx: 0.25      │
│ w_vol: 0.0      │    │ w_vol: 0.25     │
│ w_fresh: 0.2    │    │ w_fresh: 0.25   │
│ w_oi: 0.0       │    │ w_oi: 0.25      │
└─────────────────┘    └─────────────────┘

Changes take effect in 15-45 seconds without restart!
```

---

## 🎯 Summary

**To The Moon** - это комплексная система для автоматического скоринга токенов Solana, оптимизированная для высокочастотного арбитража. Система обрабатывает ~200 токенов в минуту, используя арбитражную формулу для выявления токенов с активностью 200+ транзакций за 5 минут, подходящих для ботов с интервалом 700ms.

**Ключевые особенности:**
- 🔥 Арбитражная формула (70% активность + 30% ускорение)
- ⚡ Быстрая обработка (15-45s циклы)
- 🎯 Точная селекция (скор ≥ 0.4 для ботов)
- 🔄 Мгновенное переключение режимов
- 📊 Полная прозрачность расчетов
- 🤖 Готовая интеграция с арбитражными ботами