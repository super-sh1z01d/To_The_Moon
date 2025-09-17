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
    "max_price_change_5m": "0.5",           # Maximum 5m price change (50%)
    "min_score_change": "0.05",             # Minimum score change for update (5%)
    "max_liquidity_change_ratio": "3.0",    # Maximum liquidity change ratio
}
