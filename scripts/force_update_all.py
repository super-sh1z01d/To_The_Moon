#!/usr/bin/env python3
"""
Принудительное обновление всех активных токенов.
Используется для восстановления после сбоев планировщика.
"""

from __future__ import annotations
import sys
import logging
from datetime import datetime, timezone

from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.metrics.dex_aggregator import aggregate_wsol_metrics
from src.domain.scoring.scorer import compute_score, compute_smoothed_score
from src.domain.pools.pool_type_service import PoolTypeService


def main():
    configure_logging(level="INFO")
    log = logging.getLogger("force_update")
    
    print("🚀 ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ ВСЕХ ТОКЕНОВ")
    print("=" * 50)
    print("Используется для восстановления после сбоев планировщика")
    print()
    
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        pool_service = PoolTypeService(sess)
        
        # Получаем настройки
        smoothing_alpha = float(settings.get("score_smoothing_alpha") or 0.3)
        min_pool_liquidity = float(settings.get("min_pool_liquidity_usd") or 500)
        max_price_change = 0.5  # Fixed value for legacy compatibility
        
        weights = {
            "weight_s": float(settings.get("weight_s") or 0.35),
            "weight_l": float(settings.get("weight_l") or 0.25),
            "weight_m": float(settings.get("weight_m") or 0.20),
            "weight_t": float(settings.get("weight_t") or 0.20),
        }
        
        # Получаем все активные токены
        tokens = repo.list_by_status("active", limit=1000)
        
        if not tokens:
            print("❌ Нет активных токенов для обновления")
            return
        
        print(f"📊 Найдено {len(tokens)} активных токенов")
        print("🌐 Подключаемся к DexScreener...")
        
        client = DexScreenerClient(timeout=10.0)  # Увеличенный таймаут
        updated = 0
        errors = 0
        
        for i, token in enumerate(tokens, 1):
            symbol = (token.symbol or "UNK")[:6]
            print(f"{i:3}/{len(tokens)} {symbol:6} ", end="", flush=True)
            
            try:
                # Получаем данные от DexScreener
                pairs = client.get_pairs(token.mint_address)
                if pairs is None:
                    print("❌ API недоступен")
                    errors += 1
                    continue
                
                enriched_pairs = pool_service.enrich_pairs(pairs)
                if not enriched_pairs:
                    print("❌ нет классифицированных пулов")
                    errors += 1
                    continue

                # Агрегируем метрики с фильтрацией
                metrics = aggregate_wsol_metrics(
                    token.mint_address,
                    enriched_pairs,
                    min_liquidity_usd=min_pool_liquidity,
                    max_price_change=max_price_change
                )
                pool_service.insert_primary_pool_type(metrics)
                
                # Вычисляем скоры
                score, _ = compute_score(metrics, weights)
                
                # Получаем предыдущий сглаженный скор
                previous_smoothed_score = repo.get_previous_smoothed_score(token.id)
                smoothed_score = compute_smoothed_score(score, previous_smoothed_score, smoothing_alpha)
                
                # Сохраняем снапшот (ПРИНУДИТЕЛЬНО, без фильтрации незначительных изменений)
                snap_id = repo.insert_score_snapshot(
                    token_id=token.id,
                    metrics=metrics,
                    score=score,
                    smoothed_score=smoothed_score
                )
                
                print(f"✅ Скор: {smoothed_score:.3f}")
                updated += 1
                
            except Exception as e:
                print(f"❌ Ошибка: {str(e)[:30]}")
                errors += 1
                log.error("token_update_failed", extra={"extra": {"mint": token.mint_address, "error": str(e)}})
        
        pool_service.close()

        print()
        print(f"📈 ИТОГИ ПРИНУДИТЕЛЬНОГО ОБНОВЛЕНИЯ:")
        print(f"   ✅ Обновлено: {updated} токенов")
        print(f"   ❌ Ошибок: {errors}")
        print(f"   📊 Успешность: {updated/(updated+errors)*100:.1f}%" if (updated+errors) > 0 else "   📊 Успешность: 0%")
        
        if updated > 0:
            print(f"\n🎉 Данные обновлены принудительно!")
            print(f"   Теперь проверьте, что планировщик работает корректно")
        else:
            print(f"\n⚠️ Не удалось обновить ни одного токена")
            print(f"   Проверьте доступность DexScreener API")


if __name__ == "__main__":
    main()
