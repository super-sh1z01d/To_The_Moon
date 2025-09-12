#!/usr/bin/env python3
"""
Диагностика задержек обновления данных токенов.
"""

from __future__ import annotations
import sys
import logging
from datetime import datetime, timezone, timedelta

from src.core.json_logging import configure_logging
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService


def main():
    configure_logging(level="INFO")
    
    print("🔍 ДИАГНОСТИКА: Почему данные не обновляются 20 минут?")
    print("=" * 60)
    
    with SessionLocal() as sess:
        repo = TokensRepository(sess)
        settings = SettingsService(sess)
        
        # Получаем настройки
        min_score = float(settings.get("min_score") or 0.1)
        hot_interval = int(settings.get("hot_interval_sec") or 10)
        cold_interval = int(settings.get("cold_interval_sec") or 45)
        min_score_change = float(settings.get("min_score_change") or 0.05)
        
        print("\n⚙️ Текущие настройки:")
        print(f"   min_score (граница hot/cold): {min_score}")
        print(f"   hot_interval: {hot_interval} сек")
        print(f"   cold_interval: {cold_interval} сек")
        print(f"   min_score_change: {min_score_change:.1%} (фильтр незначительных изменений)")
        
        # Анализируем статусы токенов
        active_tokens = repo.list_by_status("active", limit=1000)
        monitoring_tokens = repo.list_by_status("monitoring", limit=100)
        archived_tokens = repo.list_by_status("archived", limit=100)
        
        print(f"\n📊 Распределение токенов:")
        print(f"   ✅ active: {len(active_tokens)} (должны обновляться)")
        print(f"   ⏳ monitoring: {len(monitoring_tokens)} (НЕ обновляются)")
        print(f"   📦 archived: {len(archived_tokens)} (НЕ обновляются)")
        
        if len(active_tokens) == 0:
            print("\n❌ ПРОБЛЕМА: Нет активных токенов!")
            print("   Все токены могли быть переведены в статус 'archived' или 'monitoring'")
            return
        
        # Анализируем активные токены
        now = datetime.now(tz=timezone.utc)
        hot_count = 0
        cold_count = 0
        stale_count = 0
        very_stale_count = 0
        
        print(f"\n🎯 Анализ активных токенов (первые 10):")
        print("Символ | Скор | Группа | Минут назад | Статус")
        print("-" * 55)
        
        for token in active_tokens[:10]:
            snap = repo.get_latest_snapshot(token.id)
            symbol = (token.symbol or "UNK")[:6]
            
            if snap:
                # Исправляем timezone
                snap_time = snap.created_at
                if snap_time.tzinfo is None:
                    snap_time = snap_time.replace(tzinfo=timezone.utc)
                
                score = snap.smoothed_score if snap.smoothed_score is not None else snap.score
                is_hot = score is not None and score >= min_score
                group = "hot" if is_hot else "cold"
                expected_interval = hot_interval if is_hot else cold_interval
                
                minutes_ago = (now - snap_time).total_seconds() / 60
                
                # Определяем статус
                if minutes_ago > 20:  # Больше 20 минут - очень плохо
                    status = "❌ Критично"
                    very_stale_count += 1
                elif minutes_ago > (expected_interval / 60) * 3:  # Больше 3x ожидаемого
                    status = "⚠️ Устарел"
                    stale_count += 1
                elif minutes_ago > (expected_interval / 60) * 1.5:  # Больше 1.5x ожидаемого
                    status = "⏳ Задержка"
                else:
                    status = "✅ Свежий"
                
                score_str = f"{score:.3f}" if score is not None else "None"
                print(f"{symbol:6} | {score_str:>4} | {group:4} | {minutes_ago:9.1f} | {status}")
                
                if is_hot:
                    hot_count += 1
                else:
                    cold_count += 1
            else:
                print(f"{symbol:6} | None | cold | Нет данных | ❌ Критично")
                cold_count += 1
                very_stale_count += 1
        
        print(f"\n📈 Итоги:")
        print(f"   Hot токены: {hot_count} (обновляются каждые {hot_interval}с)")
        print(f"   Cold токены: {cold_count} (обновляются каждые {cold_interval}с)")
        print(f"   Устаревшие: {stale_count}")
        print(f"   Критичные (>20 мин): {very_stale_count}")
        
        # Диагностика причин
        print(f"\n🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ ЗАДЕРЖЕК:")
        
        if very_stale_count > 0:
            print(f"❌ {very_stale_count} токенов не обновлялись >20 минут!")
        
        print("\n1. 🤖 Планировщик (scheduler):")
        print("   • Не запущен при старте приложения")
        print("   • Завис или упал с ошибкой")
        print("   • Проверьте логи: journalctl -u tothemoon.service")
        
        print("\n2. 🌐 Внешние API:")
        print("   • DexScreener недоступен или лимитирует")
        print("   • Таймауты при запросах")
        print("   • Ошибки 429 (rate limit exceeded)")
        
        print("\n3. 📊 Фильтрация данных:")
        print(f"   • Изменения скора <{min_score_change:.1%} игнорируются")
        print("   • Токены могли 'застрять' без значимых изменений")
        
        print("\n4. 🏷️ Статусы токенов:")
        print("   • Токены переведены в 'monitoring' или 'archived'")
        print("   • Только 'active' токены обновляются автоматически")
        
        print("\n5. ⚡ Системные ресурсы:")
        print("   • Высокая нагрузка на сервер")
        print("   • Проблемы с базой данных")
        print("   • Недостаток памяти или CPU")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ:")
        print("1. Проверьте статус сервиса: systemctl status tothemoon.service")
        print("2. Проверьте логи: journalctl -u tothemoon.service -f")
        print("3. Перезапустите сервис: systemctl restart tothemoon.service")
        print("4. Проверьте доступность DexScreener API")
        print("5. Рассмотрите снижение min_score_change с 5% до 2%")
        
        if very_stale_count > 0:
            print(f"\n🚨 ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ВМЕШАТЕЛЬСТВО!")
            print(f"   {very_stale_count} токенов не обновлялись >20 минут")


if __name__ == "__main__":
    main()
