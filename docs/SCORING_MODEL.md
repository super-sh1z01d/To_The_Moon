# Hybrid Momentum Scoring Model

Comprehensive documentation of the advanced hybrid momentum scoring system used to evaluate Solana token arbitrage potential.

## 🎯 Overview

The Hybrid Momentum Model is an advanced scoring system that evaluates token arbitrage potential using four key components combined with EWMA (Exponential Weighted Moving Average) smoothing for stability and manipulation resistance.

### Key Features
- **Multi-Component Analysis**: Four distinct scoring components
- **EWMA Smoothing**: Reduces volatility and prevents manipulation
- **Real-Time Adaptation**: Responds to market changes while maintaining stability
- **Configurable Weights**: Adjustable component importance
- **Quality Validation**: Built-in data quality checks

## 🧮 Scoring Components

### 1. Transaction Acceleration (TX_Accel)

**Purpose**: Measures if trading activity is accelerating in recent minutes compared to the hourly average.

**Formula**:
```
TX_Accel = (tx_count_5m / 5) / (tx_count_1h / 60)
```

**Interpretation**:
- `> 1.0`: Trading pace is accelerating
- `= 1.0`: Consistent trading pace
- `< 1.0`: Trading pace is slowing down

**Example**:
```
tx_count_5m = 50 transactions
tx_count_1h = 300 transactions

rate_5m = 50/5 = 10 tx/min
rate_1h = 300/60 = 5 tx/min
TX_Accel = 10/5 = 2.0 (2x acceleration)
```

### 2. Volume Momentum (Vol_Momentum)

**Purpose**: Compares recent 5-minute volume to the average 5-minute volume over the past hour.

**Formula**:
```
Vol_Momentum = volume_5m / (volume_1h / 12)
```

**Interpretation**:
- `> 1.0`: Above-average volume activity
- `= 1.0`: Average volume activity
- `< 1.0`: Below-average volume activity

**Example**:
```
volume_5m = $10,000
volume_1h = $60,000

avg_5m_volume = 60,000/12 = $5,000
Vol_Momentum = 10,000/5,000 = 2.0 (2x above average)
```

### 3. Token Freshness (Token_Freshness)

**Purpose**: Provides a bonus for recently migrated tokens, as they often have higher arbitrage potential.

**Formula**:
```
Token_Freshness = max(0, (threshold_hours - hours_since_creation) / threshold_hours)
```

**Default Parameters**:
- `threshold_hours = 6.0` (configurable)

**Interpretation**:
- `1.0`: Just migrated (0 hours old)
- `0.5`: 3 hours old (50% bonus)
- `0.0`: 6+ hours old (no bonus)

**Example**:
```
Token created 2 hours ago:
Token_Freshness = max(0, (6-2)/6) = 4/6 = 0.67
```

### 4. Orderflow Imbalance (Orderflow_Imbalance)

**Purpose**: Measures buy/sell pressure by analyzing the imbalance in trading volumes.

**Formula**:
```
Orderflow_Imbalance = (buys_volume_5m - sells_volume_5m) / (buys_volume_5m + sells_volume_5m)
```

**Interpretation**:
- `+1.0`: All buying pressure (100% buys)
- `0.0`: Balanced buying and selling
- `-1.0`: All selling pressure (100% sells)

**Example**:
```
buys_volume_5m = $7,000
sells_volume_5m = $3,000

Orderflow_Imbalance = (7000-3000)/(7000+3000) = 4000/10000 = 0.4
(40% buy pressure)
```

## 🔢 Final Score Calculation

### Weighted Sum Formula

```
Final_Score = (W_tx × TX_Accel) + (W_vol × Vol_Momentum) + 
              (W_fresh × Token_Freshness) + (W_oi × Orderflow_Imbalance)
```

### Default Component Weights

| Component | Weight | Rationale |
|-----------|--------|-----------|
| `W_tx` | 0.25 | Transaction acceleration indicates momentum |
| `W_vol` | 0.25 | Volume momentum shows market interest |
| `W_fresh` | 0.25 | Fresh tokens have higher arbitrage potential |
| `W_oi` | 0.25 | Orderflow imbalance indicates direction |

### Example Calculation

```
Given:
TX_Accel = 2.0
Vol_Momentum = 1.5
Token_Freshness = 0.67
Orderflow_Imbalance = 0.4

Final_Score = (0.25 × 2.0) + (0.25 × 1.5) + (0.25 × 0.67) + (0.25 × 0.4)
            = 0.5 + 0.375 + 0.1675 + 0.1
            = 1.1425
```

## 📊 EWMA Smoothing System

### Purpose of Smoothing

1. **Volatility Reduction**: Prevents erratic score changes
2. **Manipulation Resistance**: Reduces impact of artificial spikes
3. **Trend Preservation**: Maintains underlying trends
4. **Stability**: Provides consistent scoring over time

### EWMA Formula

```
EWMA_new = α × current_value + (1 - α) × EWMA_previous
```

### Parameters

- **Alpha (α)**: 0.3 (default, configurable)
- **Applied To**: All components + final score
- **Initialization**: First value becomes initial EWMA

### Smoothing Behavior

| Alpha Value | Behavior |
|-------------|----------|
| `α = 0.1` | Very smooth, slow to react |
| `α = 0.3` | Balanced (default) |
| `α = 0.5` | Moderate smoothing |
| `α = 0.9` | Minimal smoothing, reactive |

### Example EWMA Calculation

```
Previous EWMA: 0.8
Current Raw Score: 1.2
Alpha: 0.3

New EWMA = 0.3 × 1.2 + 0.7 × 0.8
         = 0.36 + 0.56
         = 0.92
```

## ⚙️ Configuration Parameters

### Component Weights

```json
{
  "w_tx": 0.25,           // Transaction acceleration weight
  "w_vol": 0.25,          // Volume momentum weight  
  "w_fresh": 0.25,        // Token freshness weight
  "w_oi": 0.25            // Orderflow imbalance weight
}
```

### EWMA Parameters

```json
{
  "ewma_alpha": 0.3,                    // Smoothing factor (0.0-1.0)
  "freshness_threshold_hours": 6.0      // Freshness bonus duration
}
```

### Quality Thresholds

```json
{
  "min_liquidity_usd": 500.0,          // Minimum pool liquidity
  "min_score_change": 0.05,            // Minimum change for update
  "max_price_change": 0.5               // Maximum price change (50%)
}
```

## 🔍 Data Quality Integration

### Quality Validation Levels

1. **Critical Issues** (Block scoring):
   - Negative liquidity or transaction counts
   - Invalid data types
   - Missing required metrics

2. **Warnings** (Score with flags):
   - High liquidity but no transactions
   - Many transactions but no price movement
   - Suspicious price change ratios

3. **Fallback Mechanisms**:
   - Emergency scoring using historical medians
   - Degraded scoring with quality warnings
   - Gradual score recovery when data improves

### Quality Impact on Scoring

```python
if data_quality_critical_issues:
    # Use emergency fallback score
    score = median_of_last_10_scores * 0.5
elif data_quality_warnings:
    # Calculate score but flag quality issues
    score = calculate_normal_score()
    add_quality_warning_flag()
else:
    # Normal scoring process
    score = calculate_normal_score()
```

## 📈 Performance Characteristics

### Scoring Ranges

| Score Range | Interpretation | Typical Characteristics |
|-------------|----------------|------------------------|
| `> 2.0` | Exceptional | High momentum, fresh token, strong imbalance |
| `1.0 - 2.0` | Strong | Good momentum with some favorable factors |
| `0.5 - 1.0` | Moderate | Average activity with mixed signals |
| `0.1 - 0.5` | Weak | Low activity or unfavorable conditions |
| `< 0.1` | Minimal | Very low activity or poor conditions |

### Component Contribution Analysis

```python
# Example high-scoring token breakdown
{
  "final_score": 1.85,
  "components": {
    "tx_accel": 2.5,        # Strong acceleration (62.5% contribution)
    "vol_momentum": 1.8,    # Good volume (45% contribution)  
    "token_freshness": 0.8, # Moderately fresh (20% contribution)
    "orderflow_imbalance": 0.6  # Moderate buy pressure (15% contribution)
  },
  "weighted_contributions": {
    "tx_accel": 0.625,      # 2.5 × 0.25
    "vol_momentum": 0.45,   # 1.8 × 0.25
    "token_freshness": 0.2, # 0.8 × 0.25
    "orderflow_imbalance": 0.15  # 0.6 × 0.25
  }
}
```

## 🔧 Tuning and Optimization

### Weight Optimization

**Considerations for adjusting weights**:
- **Market Conditions**: Bull vs bear market preferences
- **Token Types**: Different weights for different token categories
- **Time Periods**: Intraday vs longer-term optimization
- **Performance Metrics**: Backtest results and live performance

### Alpha Tuning

**Guidelines for EWMA alpha selection**:
- **High Volatility Markets**: Lower alpha (0.1-0.2) for stability
- **Trending Markets**: Higher alpha (0.4-0.6) for responsiveness
- **Manipulation Concerns**: Lower alpha (0.2-0.3) for resistance
- **Real-time Trading**: Moderate alpha (0.3-0.4) for balance

### Performance Monitoring

```python
# Key metrics to monitor
{
  "scoring_latency": "< 100ms",           # Time to calculate score
  "ewma_convergence": "3-5 updates",     # Time to stabilize
  "quality_pass_rate": "> 95%",          # Data quality success
  "component_correlation": "< 0.7",      # Component independence
  "score_stability": "< 10% variance"    # Score consistency
}
```

## 🧪 Testing and Validation

### Unit Testing

```python
# Component calculation tests
def test_tx_acceleration():
    assert calculate_tx_accel(50, 300) == 2.0
    assert calculate_tx_accel(0, 300) == 0.0
    assert calculate_tx_accel(25, 0) == 0.0

def test_volume_momentum():
    assert calculate_vol_momentum(10000, 60000) == 2.0
    assert calculate_vol_momentum(5000, 60000) == 1.0

def test_token_freshness():
    assert calculate_token_freshness(0, 6) == 1.0
    assert calculate_token_freshness(3, 6) == 0.5
    assert calculate_token_freshness(6, 6) == 0.0

def test_orderflow_imbalance():
    assert calculate_orderflow_imbalance(7000, 3000) == 0.4
    assert calculate_orderflow_imbalance(5000, 5000) == 0.0
```

### Integration Testing

```python
# End-to-end scoring tests
def test_complete_scoring_pipeline():
    metrics = {
        "tx_count_5m": 50,
        "tx_count_1h": 300,
        "volume_5m": 10000,
        "volume_1h": 60000,
        "hours_since_creation": 2,
        "buys_volume_5m": 7000,
        "sells_volume_5m": 3000
    }
    
    result = hybrid_momentum_model.calculate_score(token, metrics)
    
    assert result.final_score > 0
    assert result.smoothed_score > 0
    assert len(result.raw_components) == 4
    assert len(result.smoothed_components) == 4
```

## 📚 Usage Examples

### Basic Scoring

```python
from src.domain.scoring.hybrid_momentum_model import HybridMomentumModel
from src.domain.scoring.ewma_service import EWMAService

# Initialize model
ewma_service = EWMAService(repository)
model = HybridMomentumModel(ewma_service)

# Calculate score
result = model.calculate_score(token, metrics)

print(f"Final Score: {result.final_score}")
print(f"Smoothed Score: {result.smoothed_score}")
print(f"Components: {result.raw_components}")
```

### Configuration Updates

```python
# Update component weights
weights = WeightConfig(
    w_tx=0.3,      # Increase transaction weight
    w_vol=0.3,     # Increase volume weight  
    w_fresh=0.2,   # Decrease freshness weight
    w_oi=0.2       # Decrease orderflow weight
)

model.update_weights(weights)
```

### EWMA Analysis

```python
# Get smoothing statistics
stats = ewma_service.get_smoothing_statistics(
    token_id=123,
    component="tx_accel",
    window_size=10
)

print(f"Variance Reduction: {stats['variance_reduction']:.2%}")
print(f"Raw Mean: {stats['raw_mean']:.3f}")
print(f"Smoothed Mean: {stats['smoothed_mean']:.3f}")
```

## 🔗 Related Documentation

- **[Architecture Guide](ARCHITECTURE.md)** - System architecture and data flow
- **[API Reference](API_REFERENCE.md)** - API endpoints for scoring data
- **[Development Guide](DEVELOPMENT.md)** - Development setup and testing
- **[Deployment Guide](DEPLOYMENT.md)** - Production configuration

## 📊 Appendix: Mathematical Foundations

### EWMA Mathematical Properties

1. **Convergence**: EWMA converges to the mean of the input series
2. **Memory**: Exponentially decreasing weights for historical values
3. **Stability**: Bounded output for bounded input
4. **Responsiveness**: Controlled by alpha parameter

### Component Independence

The four components are designed to be largely independent:
- **TX_Accel**: Focuses on transaction rate changes
- **Vol_Momentum**: Focuses on volume changes
- **Token_Freshness**: Time-based component
- **Orderflow_Imbalance**: Direction-based component

This independence ensures that the model captures different aspects of token behavior and reduces the risk of overfitting to a single market condition.