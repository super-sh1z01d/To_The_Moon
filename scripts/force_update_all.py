#!/usr/bin/env python3
"""
Принудительное обновление всех активных токенов.
Используется для восстановления после сбоев планировщика.
"""

from __future__ import annotations
import logging

from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.scoring.scoring_service import ScoringService, NoClassifiedPoolsError


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
        scoring_service = ScoringService(repo, settings)
        
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

                try:
                    score, smoothed_score, metrics, raw_components, smoothed_components = scoring_service.calculate_token_score(
                        token,
                        pairs,
                    )
                except NoClassifiedPoolsError:
                    print("❌ нет пригодных пулов")
                    errors += 1
                    continue

                scoring_service.save_score_result(
                    token=token,
                    score=score,
                    smoothed_score=smoothed_score,
                    metrics=metrics,
                    raw_components=raw_components,
                    smoothed_components=smoothed_components,
                )
                
                shown_score = smoothed_score if smoothed_score is not None else score
                print(f"✅ Скор: {shown_score:.3f}")
                updated += 1
                
            except Exception as e:
                print(f"❌ Ошибка: {str(e)[:30]}")
                errors += 1
                log.error("token_update_failed", extra={"extra": {"mint": token.mint_address, "error": str(e)}})
        
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
