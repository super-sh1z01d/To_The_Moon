DEFAULT_SETTINGS: dict[str, str] = {
    # Веса скоринга
    "weight_s": "0.35",
    "weight_l": "0.25",
    "weight_m": "0.20",
    "weight_t": "0.20",
    # Пороги
    "min_score": "0.10",
    # Тайминги
    "hot_interval_sec": "10",
    "cold_interval_sec": "45",
    # Жизненный цикл
    "archive_below_hours": "12",
    "monitoring_timeout_hours": "12",
    # Порог ликвидности внешнего пула для активации/демоции (USD)
    "activation_min_liquidity_usd": "200",
}
