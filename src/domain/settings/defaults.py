DEFAULT_SETTINGS: dict[str, str] = {
    # Legacy scoring weights
    "weight_s": "0.35",
    "weight_l": "0.25",
    "weight_m": "0.20",
    "weight_t": "0.20",
    
    # Hybrid momentum scoring weights
    "w_tx": "0.25",      # Transaction acceleration weight
    "w_vol": "0.25",     # Volume momentum weight
    "w_fresh": "0.25",   # Token freshness weight
    "w_oi": "0.25",      # Orderflow imbalance weight
    
    # Scoring model configuration
    "scoring_model_active": "hybrid_momentum",  # Active scoring model: "legacy" or "hybrid_momentum"
    
    # EWMA smoothing parameters
    "ewma_alpha": "0.3",                    # EWMA smoothing parameter (0.0-1.0)
    "freshness_threshold_hours": "6.0",    # Token freshness threshold in hours
    
    # Legacy smoothing (for backward compatibility)
    "score_smoothing_alpha": "0.3",
    
    # Scoring thresholds
    "min_score": "0.10",
    
    # Timing configuration
    "hot_interval_sec": "10",
    "cold_interval_sec": "45",
    
    # Token lifecycle
    "archive_below_hours": "12",
    "monitoring_timeout_hours": "12",
    
    # Activation thresholds
    "activation_min_liquidity_usd": "200",
    
    # Data filtering for stability
    "min_pool_liquidity_usd": "500",        # Minimum pool liquidity for inclusion (USD)
    # NOTE: max_price_change_5m removed - not used in Hybrid Momentum model
    "min_score_change": "0.05",             # Minimum score change for update (5%)
    "max_liquidity_change_ratio": "3.0",    # Maximum liquidity change ratio
    
    # NotArb bot integration
    "notarb_min_score": "0.5",              # Minimum score threshold for NotArb bot export
    "notarb_max_spam_percentage": "50",     # Maximum spam percentage for NotArb bot export (0-100)
    
    # Backlog monitoring
    "backlog_warning_threshold": "75",      # Warning threshold for backlog size
    "backlog_error_threshold": "100",       # Error threshold for backlog size
    "backlog_critical_threshold": "150",    # Critical threshold for backlog size
    
    # Spam detection whitelist
    "spam_whitelist_wallets": "8vNwSvT1S8P99c9XmjfXfV4DSGZLfUoNFx63zngCuh54",  # Comma-separated list of wallet addresses to ignore in spam detection
    
    # Component calculation parameters (previously hardcoded)
    "liquidity_factor_threshold": "100000.0",  # Liquidity threshold for volume momentum factor ($100k)
    "orderflow_significance_threshold": "500.0",  # Volume threshold for orderflow significance ($500)
    "manipulation_detection_ratio": "3.0",     # Size ratio threshold for manipulation detection (3x average)
    
    # Arbitrage mode settings
    "tx_calculation_mode": "acceleration",     # Transaction calculation mode: "acceleration" or "arbitrage_activity"
    "arbitrage_min_tx_5m": "50",              # Minimum transactions for arbitrage calculation
    "arbitrage_optimal_tx_5m": "200",         # Optimal transactions for arbitrage bots
    "arbitrage_acceleration_weight": "0.3",   # Weight of acceleration component in arbitrage mode
    
    # Filtering thresholds (set to 0 to disable harsh filtering)
    "min_tx_threshold_5m": "0",              # Minimum transactions per 5 minutes (0 = disabled)
    "min_tx_threshold_1h": "0",              # Minimum transactions per hour (0 = disabled)
    "min_volume_threshold_5m": "0",          # Minimum volume per 5 minutes USD (0 = disabled)
    "min_volume_threshold_1h": "0",          # Minimum volume per hour USD (0 = disabled)
    "min_orderflow_volume_5m": "0",          # Minimum orderflow volume per 5 minutes USD (0 = disabled)
}
