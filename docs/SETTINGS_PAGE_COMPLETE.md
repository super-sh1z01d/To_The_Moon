# Settings Page - Complete Implementation

## Overview

Comprehensive settings page with ALL system parameters grouped by category for easy configuration.

## Settings Groups

### 1. Scoring Model Selection
- **Active Model**: Choose between Hybrid Momentum (recommended) and Legacy model
- **TX Calculation Mode**: Acceleration (default) or Arbitrage Activity

### 2. Hybrid Momentum Weights
Component weights for Hybrid Momentum model (must sum to 1.0):
- **w_tx** (0.25): Transaction acceleration/activity component weight
- **w_vol** (0.25): Volume momentum component weight
- **w_fresh** (0.25): Token freshness component weight
- **w_oi** (0.25): Order flow imbalance component weight
- **ewma_alpha** (0.3): Exponential smoothing factor
- **freshness_threshold_hours** (6.0): Age threshold for freshness calculation

### 3. Legacy Model Weights
Component weights for Legacy model (must sum to 1.0):
- **weight_s** (0.35): Spread component weight
- **weight_l** (0.25): Liquidity component weight
- **weight_m** (0.20): Momentum component weight
- **weight_t** (0.20): Transaction component weight
- **score_smoothing_alpha** (0.3): Smoothing factor for score changes
- **max_price_change_5m** (0.5): Maximum allowed 5-minute price change

### 4. Token Lifecycle
Activation, archival, and monitoring parameters:
- **min_score** (0.1): Minimum score threshold for active tokens
- **min_score_change** (0.05): Minimum score change to trigger update
- **activation_min_liquidity_usd** (200): Minimum liquidity to activate monitoring token
- **archive_below_hours** (12): Archive active tokens below min_score after this time
- **monitoring_timeout_hours** (12): Archive monitoring tokens after this timeout

### 5. Data Filtering - Active Tokens
Strict filtering thresholds for active tokens:
- **min_pool_liquidity_usd** (500): Minimum liquidity per pool
- **min_tx_threshold_5m** (0): Minimum 5-minute transaction count
- **min_tx_threshold_1h** (0): Minimum 1-hour transaction count
- **min_volume_threshold_5m** (0): Minimum 5-minute volume (USD)
- **min_volume_threshold_1h** (0): Minimum 1-hour volume (USD)
- **min_orderflow_volume_5m** (0): Minimum 5-minute order flow volume (USD)

### 6. Data Filtering - Monitoring Tokens
Relaxed filtering for tokens in monitoring status:
- **arbitrage_min_tx_5m** (100): Minimum 5-minute transactions for arbitrage mode
- **arbitrage_optimal_tx_5m** (200): Optimal 5-minute transactions for arbitrage mode
- **arbitrage_acceleration_weight** (0.1): Weight for acceleration in arbitrage mode

### 7. Component Calculation
Advanced parameters for score component calculations:
- **liquidity_factor_threshold** (100000): Liquidity threshold for sigmoid boost calculation (USD)
- **orderflow_significance_threshold** (500): Volume threshold for order flow significance (USD)
- **manipulation_detection_ratio** (3.0): Size ratio threshold for manipulation detection

### 8. System Performance
Update intervals and processing parameters:
- **hot_interval_sec** (10): Update interval for hot (high-activity) tokens
- **cold_interval_sec** (45): Update interval for cold (low-activity) tokens

### 9. Data Quality Validation
Configure data quality checks and warnings:
- **strict_data_validation**: Enable/disable strict validation mode
- **min_liquidity_for_warnings** (10000): Minimum liquidity to trigger zero-transaction warnings (USD)
- **min_transactions_for_warnings** (200): Minimum transactions to trigger zero-price-change warnings
- **max_stale_minutes** (10): Maximum age of data before considered stale

### 10. NotArb Integration
Configure NotArb bot export parameters:
- **notarb_min_score** (0.5): Minimum score for NotArb config export
- **notarb_max_spam_percentage** (50): Maximum spam percentage for NotArb export (%)

## Features

### Batch Save
- All changes are saved in a single batch operation
- Shows "Saving..." state during save
- Success/error toast notifications

### Reset Functionality
- Reset button to discard all unsaved changes
- Disabled when no changes pending

### Input Types
- **Number inputs**: With step control for decimal precision
- **Select dropdowns**: For model selection and boolean options
- **Units display**: Shows units (USD, hours, seconds, %) next to relevant fields

### Search (Future Enhancement)
- Search bar ready for filtering settings by name/description

## Technical Implementation

### Frontend
- **React Query**: For data fetching and mutations
- **Batch Updates**: All settings saved in parallel
- **Optimistic Updates**: UI updates immediately, then syncs with server
- **Type Safety**: Full TypeScript support

### Backend
- Settings stored in `app_settings` table
- Individual PUT endpoints for each setting
- Automatic invalidation of caches after updates

## Usage

1. Navigate to Settings page
2. Modify any settings as needed
3. Click "Save Changes" to apply all modifications
4. Click "Reset" to discard changes

## Notes

- All weights must sum to 1.0 for proper scoring
- Changes take effect immediately after save
- Some settings require scheduler restart for full effect
- Default values are shown for all settings
