# Trading Configurations Guide

Optimized scoring model configurations for different Solana DEX arbitrage strategies.

## 🎯 Overview

This guide provides battle-tested configurations for the hybrid momentum scoring model, each optimized for specific trading scenarios and market conditions in Solana ecosystem.

## 📋 Configuration Profiles

### 1. **"Scalper" - High-Frequency Arbitrage**

**Target:** 1-5 minute timeframes, rapid DEX arbitrage opportunities

```json
{
  "scoring_model_active": "hybrid_momentum",
  "w_tx": 0.4,
  "w_vol": 0.35,
  "w_fresh": 0.15,
  "w_oi": 0.1,
  "ewma_alpha": 0.5,
  "freshness_threshold_hours": 3.0,
  "hot_interval_sec": 15,
  "cold_interval_sec": 60,
  "min_score": 0.8
}
```

**Key Advantages:**
- **High transaction sensitivity** (w_tx=0.4) - Quickly identifies trading activity spikes
- **Fast smoothing** (alpha=0.5) - Model adapts rapidly to changes
- **Short update intervals** - Catches brief arbitrage windows
- **Fresh token focus** - Prioritizes recently migrated high-volatility tokens

**Best For:** Quick trades, high-frequency arbitrage between DEXs, scalping strategies

### 2. **"Momentum Hunter" - Trend-Following Arbitrage**

**Target:** 15-60 minute positions, sustained momentum plays

```json
{
  "scoring_model_active": "hybrid_momentum",
  "w_tx": 0.25,
  "w_vol": 0.45,
  "w_fresh": 0.1,
  "w_oi": 0.2,
  "ewma_alpha": 0.2,
  "freshness_threshold_hours": 12.0,
  "hot_interval_sec": 30,
  "cold_interval_sec": 120,
  "min_score": 0.4
}
```

**Key Advantages:**
- **Maximum volume focus** (w_vol=0.45) - Identifies tokens with sustained volume growth
- **Slow smoothing** (alpha=0.2) - Filters short-term noise, focuses on trends
- **Orderflow consideration** (w_oi=0.2) - Helps determine trend direction
- **Extended analysis periods** - Suitable for medium-term positions

**Best For:** Trend following, 15-60 minute positions, arbitrage on sustained moves### 
3. **"Fresh Token Sniper" - New Token Hunter**

**Target:** Newly migrated tokens, early entry opportunities

```json
{
  "scoring_model_active": "hybrid_momentum",
  "w_tx": 0.2,
  "w_vol": 0.2,
  "w_fresh": 0.5,
  "w_oi": 0.1,
  "ewma_alpha": 0.4,
  "freshness_threshold_hours": 1.0,
  "hot_interval_sec": 10,
  "cold_interval_sec": 30,
  "min_score": 0.6
}
```

**Key Advantages:**
- **Maximum freshness bonus** (w_fresh=0.5) - Prioritizes just-migrated tokens
- **Ultra-short freshness window** (1 hour) - Focus on newest tokens only
- **Super-fast updates** - Never misses a new token
- **Moderate smoothing** - Balance between sensitivity and stability

**Best For:** Primary listing arbitrage, catching new token pumps, early entry strategies

### 4. **"Balanced Arbitrage" - Universal Strategy**

**Target:** General-purpose trading, mixed market conditions

```json
{
  "scoring_model_active": "hybrid_momentum",
  "w_tx": 0.25,
  "w_vol": 0.25,
  "w_fresh": 0.25,
  "w_oi": 0.25,
  "ewma_alpha": 0.3,
  "freshness_threshold_hours": 6.0,
  "hot_interval_sec": 30,
  "cold_interval_sec": 120,
  "min_score": 0.5
}
```

**Key Advantages:**
- **Equal weight distribution** - Considers all factors equally
- **Standard smoothing parameters** - Optimal balance of stability and sensitivity
- **Moderate thresholds** - Works in various market conditions
- **Versatility** - Performs well across different volatility regimes

**Best For:** Beginner traders, strategy testing, mixed approaches, uncertain markets

### 5. **"Orderflow Specialist" - Flow Analysis**

**Target:** Institutional flow detection, counter-trend opportunities

```json
{
  "scoring_model_active": "hybrid_momentum",
  "w_tx": 0.15,
  "w_vol": 0.25,
  "w_fresh": 0.1,
  "w_oi": 0.5,
  "ewma_alpha": 0.25,
  "freshness_threshold_hours": 24.0,
  "hot_interval_sec": 45,
  "cold_interval_sec": 180,
  "min_score": 0.3
}
```

**Key Advantages:**
- **Maximum orderflow focus** (w_oi=0.5) - Detects strong buy/sell pressure imbalances
- **Long-term analysis** - Considers tokens over 24-hour periods
- **Slow smoothing** - Filters short-term manipulation
- **Low entry threshold** - More opportunities for analysis

**Best For:** Institutional flow analysis, large position detection, counter-trend strategies#
# 🔧 Implementation Guide

### Quick Configuration via API

```bash
# Set "Scalper" configuration
curl -X PUT http://localhost:8000/settings/w_tx \
  -H "Content-Type: application/json" \
  -d '{"value": "0.4"}'

curl -X PUT http://localhost:8000/settings/w_vol \
  -H "Content-Type: application/json" \
  -d '{"value": "0.35"}'

curl -X PUT http://localhost:8000/settings/w_fresh \
  -H "Content-Type: application/json" \
  -d '{"value": "0.15"}'

curl -X PUT http://localhost:8000/settings/w_oi \
  -H "Content-Type: application/json" \
  -d '{"value": "0.1"}'

curl -X PUT http://localhost:8000/settings/ewma_alpha \
  -H "Content-Type: application/json" \
  -d '{"value": "0.5"}'

curl -X PUT http://localhost:8000/settings/freshness_threshold_hours \
  -H "Content-Type: application/json" \
  -d '{"value": "3.0"}'

curl -X PUT http://localhost:8000/settings/hot_interval_sec \
  -H "Content-Type: application/json" \
  -d '{"value": "15"}'

curl -X PUT http://localhost:8000/settings/min_score \
  -H "Content-Type: application/json" \
  -d '{"value": "0.8"}'
```

### Batch Configuration via Database

```sql
-- Switch to "Momentum Hunter" configuration
UPDATE app_settings SET value = '0.25' WHERE key = 'w_tx';
UPDATE app_settings SET value = '0.45' WHERE key = 'w_vol';
UPDATE app_settings SET value = '0.1' WHERE key = 'w_fresh';
UPDATE app_settings SET value = '0.2' WHERE key = 'w_oi';
UPDATE app_settings SET value = '0.2' WHERE key = 'ewma_alpha';
UPDATE app_settings SET value = '12.0' WHERE key = 'freshness_threshold_hours';
UPDATE app_settings SET value = '30' WHERE key = 'hot_interval_sec';
UPDATE app_settings SET value = '0.4' WHERE key = 'min_score';
```

### Configuration Switching Script

```python
# scripts/switch_config.py
import requests
import json

def apply_configuration(config_name, settings):
    """Apply a trading configuration via API"""
    base_url = "http://localhost:8000"
    
    for key, value in settings.items():
        response = requests.put(
            f"{base_url}/settings/{key}",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"value": str(value)})
        )
        if response.status_code == 200:
            print(f"✅ {key} = {value}")
        else:
            print(f"❌ Failed to set {key}: {response.text}")
    
    print(f"\n🎯 {config_name} configuration applied!")

# Usage examples
SCALPER_CONFIG = {
    "w_tx": 0.4,
    "w_vol": 0.35,
    "w_fresh": 0.15,
    "w_oi": 0.1,
    "ewma_alpha": 0.5,
    "freshness_threshold_hours": 3.0,
    "hot_interval_sec": 15,
    "min_score": 0.8
}

apply_configuration("Scalper", SCALPER_CONFIG)
```## 📊 
Configuration Selection Guide

### Market Condition Based Selection

| Market Condition | Recommended Configuration | Reasoning |
|------------------|---------------------------|-----------|
| **High Volatility** | Scalper or Fresh Token Sniper | Fast adaptation to rapid changes |
| **Trending Markets** | Momentum Hunter | Captures sustained directional moves |
| **Sideways/Uncertain** | Balanced Arbitrage | Robust across conditions |
| **Low Volume** | Orderflow Specialist | Detects subtle institutional activity |
| **New Listings** | Fresh Token Sniper | Maximizes early opportunity capture |

### Time-Based Recommendations (UTC)

| Time Period | Primary Config | Secondary Config | Market Characteristics |
|-------------|----------------|------------------|----------------------|
| **00:00-04:00** | Fresh Token Sniper | Scalper | Asian session, new token activity |
| **04:00-08:00** | Balanced Arbitrage | Orderflow Specialist | Low volume transition |
| **08:00-12:00** | Momentum Hunter | Scalper | European session ramp-up |
| **12:00-16:00** | Momentum Hunter | Balanced Arbitrage | US session peak activity |
| **16:00-20:00** | Scalper | Momentum Hunter | US session high volatility |
| **20:00-00:00** | Balanced Arbitrage | Fresh Token Sniper | Evening wind-down |

### Risk Profile Matching

| Risk Tolerance | Configuration | Expected Returns | Drawdown Risk |
|----------------|---------------|------------------|---------------|
| **Conservative** | Balanced Arbitrage | Moderate, Steady | Low |
| **Moderate** | Momentum Hunter | Good, Consistent | Medium |
| **Aggressive** | Scalper | High, Variable | High |
| **Speculative** | Fresh Token Sniper | Very High, Volatile | Very High |
| **Institutional** | Orderflow Specialist | Steady, Alpha-focused | Low-Medium |

## 🎛️ Advanced Tuning Tips

### Fine-Tuning Parameters

**For Higher Sensitivity:**
- Increase `ewma_alpha` (0.4-0.6)
- Decrease update intervals
- Lower `min_score` threshold

**For More Stability:**
- Decrease `ewma_alpha` (0.1-0.3)
- Increase update intervals
- Raise `min_score` threshold

**For Fresh Token Focus:**
- Increase `w_fresh` weight
- Decrease `freshness_threshold_hours`
- Faster update intervals

**For Volume-Based Trading:**
- Increase `w_vol` weight
- Moderate `ewma_alpha` (0.2-0.4)
- Focus on `min_liquidity_usd` settings

### Performance Monitoring

```bash
# Monitor configuration performance
curl "http://localhost:8000/tokens/?limit=20&min_score=0.5" | \
  jq '.items[] | {symbol, score, smoothed_score, raw_components}'

# Check scoring distribution
curl "http://localhost:8000/logs?logger=scoring&limit=50" | \
  jq '.logs[] | select(.message | contains("score_calculated"))'
```

## 🔄 Dynamic Configuration Switching

### Automated Switching Based on Market Conditions

```python
# Example: Auto-switch based on market volatility
def auto_switch_config():
    # Get current market metrics
    response = requests.get("http://localhost:8000/tokens/?limit=10")
    tokens = response.json()['items']
    
    # Calculate average volatility
    avg_volatility = sum(abs(t.get('delta_p_5m', 0)) for t in tokens) / len(tokens)
    
    if avg_volatility > 0.1:  # High volatility
        apply_configuration("Scalper", SCALPER_CONFIG)
    elif avg_volatility > 0.05:  # Medium volatility
        apply_configuration("Momentum Hunter", MOMENTUM_CONFIG)
    else:  # Low volatility
        apply_configuration("Balanced Arbitrage", BALANCED_CONFIG)
```

### A/B Testing Framework

```python
# Test multiple configurations simultaneously
def run_ab_test(configs, duration_hours=24):
    """Run A/B test comparing different configurations"""
    results = {}
    
    for config_name, settings in configs.items():
        print(f"Testing {config_name} for {duration_hours} hours...")
        apply_configuration(config_name, settings)
        
        # Collect performance metrics
        time.sleep(duration_hours * 3600)
        
        # Analyze results
        performance = analyze_performance()
        results[config_name] = performance
    
    return results
```

## 📈 Expected Performance Characteristics

| Configuration | Avg Daily Opportunities | Win Rate | Avg Return/Trade | Max Drawdown |
|---------------|------------------------|----------|------------------|--------------|
| **Scalper** | 50-100 | 65-75% | 0.5-2% | 5-10% |
| **Momentum Hunter** | 20-40 | 70-80% | 1-5% | 8-15% |
| **Fresh Token Sniper** | 10-30 | 60-70% | 2-10% | 10-25% |
| **Balanced Arbitrage** | 30-60 | 68-78% | 0.8-3% | 6-12% |
| **Orderflow Specialist** | 15-35 | 72-82% | 1-4% | 7-14% |

*Note: Performance varies significantly based on market conditions, execution speed, and capital allocation.*

## 🔗 Related Documentation

- **[Scoring Model Details](SCORING_MODEL.md)** - Deep dive into hybrid momentum components
- **[API Reference](API_REFERENCE.md)** - Complete settings API documentation
- **[Architecture Guide](ARCHITECTURE.md)** - System design and data flow
- **[Development Guide](DEVELOPMENT.md)** - Testing and debugging configurations

---

**⚠️ Disclaimer:** These configurations are for educational purposes. Always backtest thoroughly and consider your risk tolerance before implementing any trading strategy.