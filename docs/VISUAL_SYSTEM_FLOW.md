# 🎯 To The Moon - Визуальная Схема Системы

## 📊 Основной Поток Обработки Токенов

```
                    🚀 TO THE MOON SYSTEM FLOW 🚀
    
    ┌─────────────────────────────────────────────────────────────────────┐
    │                        INPUT SOURCES                                │
    └─────────────────────────────────────────────────────────────────────┘
    
    🔄 Pump.fun          📡 DexScreener         ⏰ Scheduler
    WebSocket            API Data              Timer Events
         │                    │                     │
         │ New Migration      │ Token Pairs         │ Process Batch
         ▼                    ▼                     ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                      💾 DATABASE                                    │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
    │  │   TOKENS    │  │TOKEN_SCORES │  │APP_SETTINGS │                │
    │  │ monitoring  │  │ components  │  │   weights   │                │
    │  │   active    │  │   scores    │  │ thresholds  │                │
    │  │  archived   │  │  metadata   │  │   config    │                │
    │  └─────────────┘  └─────────────┘  └─────────────┘                │
    └─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    🔄 TOKEN PROCESSING PIPELINE                     │
    └─────────────────────────────────────────────────────────────────────┘
    
         NEW TOKEN              VALIDATION              SCORING
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ 🆕 MONITORING   │───▶│ ✅ VALIDATION   │───▶│ 📊 ACTIVE       │
    │                 │    │                 │    │                 │
    │ • From Pump.fun │    │ • Check pools   │    │ • Calculate     │
    │ • Basic data    │    │ • Verify WSOL   │    │ • Score tokens  │
    │ • Min threshold │    │ • Liquidity OK  │    │ • Update DB     │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
              │                       │                       │
              │ Timeout 12h           │ No external pools     │ Score < 0.1
              ▼                       ▼                       ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                        🗄️ ARCHIVED                                  │
    │ • Low performance tokens                                            │
    │ • Timed out monitoring tokens                                       │
    │ • Manual archive                                                    │
    └─────────────────────────────────────────────────────────────────────┘
```

## 🧮 Арбитражная Формула - Детальная Схема

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                   🔥 ARBITRAGE SCORING ENGINE                       │
    └─────────────────────────────────────────────────────────────────────┘
    
    INPUT DATA:
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ TX_COUNT_5M     │    │ TX_COUNT_1H     │    │ TOKEN_AGE       │
    │ (Transactions   │    │ (Transactions   │    │ (Hours since    │
    │  in 5 minutes)  │    │  in 1 hour)     │    │  creation)      │
    └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
              │                      │                      │
              ▼                      ▼                      ▼
    
    ┌─────────────────────────────────────────────────────────────────────┐
    │                      COMPONENT CALCULATION                          │
    └─────────────────────────────────────────────────────────────────────┘
    
    TX COMPONENT (80% weight):
    ┌─────────────────────────────────────────────────────────────────────┐
    │  ABSOLUTE ACTIVITY (70%)     │  ACCELERATION (30%)                  │
    │                              │                                      │
    │  if TX_5m < 50:             │  Rate_5m = TX_5m / 5                 │
    │    abs_score = 0.0          │  Rate_1h = TX_1h / 60                │
    │  elif TX_5m >= 200:         │                                      │
    │    abs_score = 1.0          │  if Rate_1h > 0:                     │
    │  else:                      │    ratio = Rate_5m / Rate_1h         │
    │    abs_score = (TX_5m-50)   │    if ratio >= 2.0:                  │
    │               /(200-50)     │      accel_score = 1.0               │
    │                             │    elif ratio >= 1.0:                │
    │  ┌─────────────────────────┐│      accel_score = (ratio-1.0)/1.0   │
    │  │ 🎯 OPTIMIZED FOR 700ms ││    else:                              │
    │  │    ARBITRAGE BOTS       ││      accel_score = 0.0               │
    │  │                        ││  else:                                │
    │  │ 200+ TX/5min = PERFECT ││    accel_score = 0.0                 │
    │  │ 50-200 TX/5min = SCALE ││                                      │
    │  │ <50 TX/5min = REJECT   ││                                      │
    │  └─────────────────────────┘│                                      │
    └─────────────────────────────┴──────────────────────────────────────┘
                              │                      │
                              ▼                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │           TX_SCORE = abs_score × 0.7 + accel_score × 0.3           │
    └─────────────────────────────────────────────────────────────────────┘
    
    FRESHNESS COMPONENT (20% weight):
    ┌─────────────────────────────────────────────────────────────────────┐
    │  if hours_since_creation < 6:                                       │
    │    fresh_score = (6 - hours_since_creation) / 6                     │
    │  else:                                                              │
    │    fresh_score = 0.0                                                │
    │                                                                     │
    │  🆕 NEW TOKENS GET BONUS POINTS                                     │
    └─────────────────────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────────────────────┐
    │                         FINAL CALCULATION                           │
    │                                                                     │
    │  RAW_SCORE = TX_SCORE × 0.8 + FRESH_SCORE × 0.2                   │
    │                                                                     │
    │  SMOOTHED_SCORE = RAW_SCORE × 0.3 + PREVIOUS_SCORE × 0.7          │
    │                                                                     │
    │  📊 EWMA SMOOTHING REDUCES NOISE AND STABILIZES SCORES             │
    └─────────────────────────────────────────────────────────────────────┘
```

## ⚡ Scheduler Processing Flow

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                      ⏰ SCHEDULER ARCHITECTURE                       │
    └─────────────────────────────────────────────────────────────────────┘
    
    ┌─────────────────┐              ┌─────────────────┐
    │   HOT GROUP     │              │   COLD GROUP    │
    │   (Every 15s)   │              │   (Every 35s)   │
    │                 │              │                 │
    │ 🔥 High Priority│              │ ❄️ Low Priority │
    │ • Score ≥ 0.5   │              │ • Score < 0.5   │
    │ • Recent update │              │ • Older tokens  │
    │ • Active status │              │ • Monitoring    │
    │ • Batch: 30     │              │ • Batch: 70     │
    └─────────┬───────┘              └─────────┬───────┘
              │                                │
              ▼                                ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                      🔄 PROCESSING PIPELINE                         │
    │                                                                     │
    │  1. 📡 Fetch DexScreener pairs                                      │
    │  2. 🧮 Calculate enhanced metrics                                    │
    │  3. 📊 Run scoring algorithm                                         │
    │  4. 💾 Update database                                              │
    │  5. 🔄 Apply EWMA smoothing                                         │
    │  6. 📈 Update token status                                          │
    │                                                                     │
    │  ⏱️ Timeout: 2 seconds per token                                    │
    │  🛡️ Circuit breaker: Auto-recovery on API failures                 │
    │  🔄 Retry logic: 4 attempts with exponential backoff               │
    └─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                        📊 RESULT DISTRIBUTION                       │
    │                                                                     │
    │  🔥 Score ≥ 0.7: BOT READY     (~2-5 tokens)                      │
    │  🟡 Score ≥ 0.5: WATCH LIST    (~5-10 tokens)                     │
    │  🟠 Score ≥ 0.3: RISKY         (~10-20 tokens)                    │
    │  ❌ Score < 0.3: FILTERED      (~80% of tokens)                   │
    └─────────────────────────────────────────────────────────────────────┘
```## 🤖 Bo
t Integration & API Flow

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    🤖 ARBITRAGE BOT INTEGRATION                     │
    └─────────────────────────────────────────────────────────────────────┘
    
    TO THE MOON SYSTEM          NOTARB INTEGRATION         ARBITRAGE BOT
    ┌─────────────────┐         ┌─────────────────┐        ┌─────────────────┐
    │ 📊 SCORING      │────────▶│ 🔄 EXPORT       │───────▶│ ⚡ TRADING      │
    │                 │         │                 │        │                 │
    │ • Calculate     │ Tokens  │ • Filter ≥0.4   │ JSON   │ • 700ms cycles  │
    │ • Filter        │ with    │ • Pool data     │ config │ • Price monitor │
    │ • Rank          │ scores  │ • Metadata      │        │ • Profit calc   │
    │ • Update        │         │ • Addresses     │        │ • Execute       │
    └─────────────────┘         └─────────────────┘        └─────────────────┘
              │                           │                          │
              ▼                           ▼                          ▼
    ┌─────────────────┐         ┌─────────────────┐        ┌─────────────────┐
    │ SCORE TIERS:    │         │ POOL TYPES:     │        │ TRADING PAIRS:  │
    │                 │         │                 │        │                 │
    │ 🔥 ≥0.7: AUTO   │         │ • WSOL/SOL      │        │ • DEX arbitrage │
    │ 🟡 ≥0.5: MANUAL │         │ • USDC pairs    │        │ • Cross-pool    │
    │ 🟠 ≥0.3: RISKY  │         │ • High liquidity│        │ • Price diff    │
    │ ❌ <0.3: SKIP   │         │ • Volume data   │        │ • Slippage opt  │
    └─────────────────┘         └─────────────────┘        └─────────────────┘
    
    API ENDPOINTS:
    ┌─────────────────────────────────────────────────────────────────────┐
    │ GET /tokens?min_score=0.4&status=active                            │
    │ GET /tokens/{mint}/pools                                            │
    │ GET /notarb/pools                                                   │
    │ GET /health                                                         │
    └─────────────────────────────────────────────────────────────────────┘
```

## 🌐 Frontend Dashboard Flow

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                      🌐 REACT SPA DASHBOARD                         │
    └─────────────────────────────────────────────────────────────────────┘
    
    USER INTERFACE                API BACKEND               DATABASE
    ┌─────────────────┐          ┌─────────────────┐       ┌─────────────────┐
    │ 📱 DASHBOARD    │─────────▶│ 🚀 FASTAPI      │──────▶│ 💾 SQLITE/PG    │
    │                 │          │                 │       │                 │
    │ • Token table   │ HTTP     │ • /tokens       │ SQL   │ • tokens        │
    │ • Score display │ requests │ • /health       │ query │ • token_scores  │
    │ • Filtering     │          │ • /meta         │       │ • app_settings  │
    │ • Sorting       │          │ • CORS enabled  │       │                 │
    │ • Auto-refresh  │          │ • JSON response │       │                 │
    └─────────┬───────┘          └─────────────────┘       └─────────────────┘
              │                            │                         │
              ▼                            ▼                         ▼
    ┌─────────────────┐          ┌─────────────────┐       ┌─────────────────┐
    │ FEATURES:       │          │ RESPONSE DATA:  │       │ STORED DATA:    │
    │                 │          │                 │       │                 │
    │ • Real-time     │          │ • Token list    │       │ • Raw scores    │
    │ • Pagination    │          │ • Components    │       │ • Smoothed      │
    │ • Component     │          │ • Metadata      │       │ • Components    │
    │   breakdown     │          │ • Timestamps    │       │ • Metrics       │
    │ • Status filter │          │ • Pool data     │       │ • History       │
    │ • Score sorting │          │ • Health status │       │ • Settings      │
    └─────────────────┘          └─────────────────┘       └─────────────────┘
    
    AUTO-REFRESH CYCLE (30 seconds):
    ┌─────────────────────────────────────────────────────────────────────┐
    │  Frontend ──fetch──▶ API ──query──▶ DB ──results──▶ API ──JSON──▶ UI │
    │     ▲                                                            │    │
    │     └────────────────── 30s timer ──────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration & Control Flow

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    ⚙️ CONFIGURATION MANAGEMENT                      │
    └─────────────────────────────────────────────────────────────────────┘
    
    SETTINGS HIERARCHY:
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ 🌍 ENVIRONMENT  │    │ 💾 DATABASE     │    │ 🔄 RUNTIME      │
    │ VARIABLES       │    │ SETTINGS        │    │ CHANGES         │
    │                 │    │                 │    │                 │
    │ • APP_ENV       │    │ • Weights       │    │ • Live updates  │
    │ • LOG_LEVEL     │    │ • Thresholds    │    │ • No restart    │
    │ • DATABASE_URL  │    │ • Intervals     │    │ • 15-45s delay  │
    │ • Static config │    │ • Dynamic vals  │    │ • Hot reload    │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
              │                      │                      │
              ▼                      ▼                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                        CONFIGURATION FLOW                           │
    │                                                                     │
    │  1. 🚀 App starts with .env defaults                                │
    │  2. 💾 Load database settings (weights, thresholds)                 │
    │  3. 🔄 Runtime updates via settings.set()                          │
    │  4. ⚡ Changes propagate to scheduler (15-45s)                      │
    │  5. 📊 New calculations use updated values                          │
    │                                                                     │
    │  🎯 KEY SETTINGS:                                                   │
    │  • tx_calculation_mode: 'arbitrage_activity'                       │
    │  • w_tx: 0.8, w_vol: 0.0, w_fresh: 0.2, w_oi: 0.0                │
    │  • arbitrage_min_tx_5m: 50, arbitrage_optimal_tx_5m: 200          │
    │  • min_score: 0.1, archive_below_hours: 12                        │
    └─────────────────────────────────────────────────────────────────────┘
    
    ROLLBACK CAPABILITY:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  CURRENT STATE           ──rollback──▶         PREVIOUS STATE        │
    │                                                                     │
    │  Arbitrage Formula                             Classic Formula      │
    │  • 80% TX, 20% FRESH                         • 25% each component  │
    │  • Arbitrage activity                        • Acceleration only    │
    │  • 200+ TX optimal                           • No TX thresholds     │
    │                                                                     │
    │  🔄 Instant switch via settings.set() - No code deployment needed  │
    └─────────────────────────────────────────────────────────────────────┘
```

## 📊 Monitoring & Health Checks

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                      📊 SYSTEM MONITORING                           │
    └─────────────────────────────────────────────────────────────────────┘
    
    HEALTH ENDPOINTS:
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ 🏥 /health      │    │ 📊 /meta        │    │ 📈 METRICS      │
    │                 │    │                 │    │                 │
    │ • API status    │    │ • Token counts  │    │ • Process rate  │
    │ • DB connection │    │ • Score stats   │    │ • Success rate  │
    │ • Scheduler     │    │ • Update times  │    │ • Response time │
    │ • External APIs │    │ • System info   │    │ • Error rate    │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
              │                      │                      │
              ▼                      ▼                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                         MONITORING FLOW                             │
    │                                                                     │
    │  🔍 CONTINUOUS MONITORING:                                          │
    │  • Circuit breaker for DexScreener API                             │
    │  • Retry logic with exponential backoff                            │
    │  • Fallback data on API failures                                   │
    │  • Health checks every 30 seconds                                  │
    │  • Automatic recovery mechanisms                                    │
    │                                                                     │
    │  📊 KEY METRICS:                                                    │
    │  • ~200 tokens processed per minute                                │
    │  • ~1,200 API calls per hour                                       │
    │  • <2s average response time                                       │
    │  • >95% success rate                                               │
    │  • 2-5 bot-ready tokens simultaneously                             │
    └─────────────────────────────────────────────────────────────────────┘
    
    ERROR HANDLING:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  API FAILURE ──▶ CIRCUIT BREAKER ──▶ FALLBACK DATA ──▶ CONTINUE    │
    │                                                                     │
    │  DB ERROR ────▶ RETRY LOGIC ──────▶ GRACEFUL FAIL ──▶ LOG & ALERT  │
    │                                                                     │
    │  TIMEOUT ─────▶ SKIP TOKEN ───────▶ NEXT IN QUEUE ──▶ PROCESS      │
    └─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Итоговая Схема Всей Системы

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           🚀 TO THE MOON - COMPLETE SYSTEM                     │
└─────────────────────────────────────────────────────────────────────────────────┘

INPUT ──▶ PROCESSING ──▶ SCORING ──▶ OUTPUT ──▶ INTEGRATION
  │           │            │          │            │
  ▼           ▼            ▼          ▼            ▼

🔄 Pump.fun  ⚡ Scheduler  🧮 Arbitrage 📊 Dashboard 🤖 Trading Bot
WebSocket    (15-45s)     Formula     (React SPA)  (700ms cycles)
             
📡 DexScreener 🔄 Batch    📈 EWMA     📱 Mobile    💰 Profit
API Data      Processing   Smoothing   Responsive   Optimization

💾 Database   🛡️ Circuit   🎯 Scoring  🌐 API       📊 Analytics
SQLite/PG     Breaker     Tiers       Endpoints    & Reporting

⚙️ Settings   📊 Health    🔄 Status   📈 Real-time 🔄 Continuous
Management    Monitoring   Updates     Updates      Improvement

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              KEY ACHIEVEMENTS                                   │
│                                                                                 │
│ ✅ Unified arbitrage formula for all tokens                                     │
│ ✅ 700ms bot optimization (200+ TX/5min focus)                                 │
│ ✅ Real-time processing (15-45s cycles)                                        │
│ ✅ Instant configuration changes (no restart)                                  │
│ ✅ Complete rollback capability                                                │
│ ✅ High-performance batch processing                                           │
│ ✅ Robust error handling & recovery                                            │
│ ✅ Full transparency & monitoring                                              │
│ ✅ Ready for production arbitrage trading                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Quick Reference

**🎯 For Arbitrage Bots:**
- Use tokens with score ≥ 0.4
- Focus on 200+ TX/5min tokens  
- Check `/notarb/pools` endpoint
- Monitor every 30 seconds

**⚙️ For Configuration:**
- All settings in database
- Changes via `settings.set()`
- No restart required
- 15-45s propagation time

**📊 For Monitoring:**
- Check `/health` endpoint
- Monitor processing rate
- Watch error rates
- Track bot-ready tokens

**🔄 For Rollback:**
- Switch formula mode instantly
- Restore previous weights
- Full backward compatibility
- Zero downtime changes

**System is production-ready for high-frequency arbitrage trading! 🚀**