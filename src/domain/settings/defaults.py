DEFAULT_SETTINGS: dict[str, str] = {
    # Hybrid momentum scoring weights
    "w_tx": "0.25",      # Transaction acceleration weight
    "w_vol": "0.25",     # Volume momentum weight
    "w_fresh": "0.25",   # Token freshness weight
    "w_oi": "0.25",      # Orderflow imbalance weight
    
    # Scoring model configuration (hybrid-only)
    "scoring_model_active": "hybrid_momentum",
    
    # EWMA smoothing parameters
    "ewma_alpha": "0.3",                    # EWMA smoothing parameter (0.0-1.0)
    "freshness_threshold_hours": "6.0",    # Token freshness threshold in hours
    
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

    # Pipeline v2 rollout and auto-rollback
    "pipeline_v2_canary_percent": "100",                   # % of tokens routed to v2 queue worker (0-100)
    "pipeline_v2_auto_rollback_enabled": "true",           # Pause seeding when queue exceeds rollback thresholds
    "pipeline_v2_deadletter_rollback_threshold": "0.01",   # Deadletter ratio trigger for seed pause
    "pipeline_v2_lag_rollback_seconds": "600",             # Queue lag trigger for seed pause
    "pipeline_v2_due_rollback_threshold": "300",           # Due jobs trigger for seed pause
    "pipeline_v2_dex_error_rate_rollback_threshold": "0.25",  # Dex broker error-rate trigger for seed pause
    "pipeline_v2_dex_min_requests_for_rollback": "50",        # Min dex requests before applying error-rate rollback
    "pipeline_v2_rollback_cooldown_sec": "120",            # Pause duration after rollback trigger
    
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

    # Archived token reactivation
    "process_archived_tokens": "false",      # Enable archived token processing (disabled by default for safety)
    "archived_min_txns_5m": "300",           # Minimum transactions in last 5 minutes for archived token reactivation
    "archived_max_age_days": "7",            # Maximum age in days for archived tokens to be considered for reactivation
}
