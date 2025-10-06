# Система детекции спама

## 📋 Обзор

Создана система мониторинга спам-активности для токенов на основе анализа ComputeBudget инструкций в транзакциях Solana.

## 🎯 Принцип работы

### Критерии детекции спама:
- **ComputeBudget инструкции** - основной индикатор ботовой активности
- **Синхронные транзакции** - все транзакции в одну секунду
- **Повторяющиеся паттерны** - одинаковые суммы, интервалы, структуры

### Формула расчета спам-процента:
```
spam_percentage = (compute_budget_instructions / total_instructions) * 100
```

### Пороги оценки:
- **0-25%** = 🟢 Чистый
- **25-50%** = 🟡 Подозрительный  
- **50-70%** = 🟠 Высокий риск
- **70%+** = 🔴 Спам

## 🏗️ Архитектура

### Основные компоненты:

1. **SpamDetector** (`src/monitoring/spam_detector.py`)
   - Анализ транзакций через Helius RPC
   - Подсчет ComputeBudget инструкций
   - Расчет спам-метрик

2. **SpamMonitoringService** 
   - Непрерывный мониторинг топовых токенов
   - Интервал: каждые 5 секунд
   - Лимит: топ-10 токенов по скору

3. **Задача scheduler** (`src/scheduler/tasks.py`)
   - `monitor_spam_once()` - разовый анализ
   - `run_spam_monitor()` - синхронная обертка

## 📊 Результаты тестирования

### Производительность:
- **Средняя скорость**: 0.76s на токен
- **Batch анализ**: 0.49s на токен (параллельно)
- **Цель достигнута**: <2s для 5-секундного цикла

### Примеры детекции:
- **J4UBm5kvMSHeUwbNgZW4ySpCHBvS7LXknZ7rqQR9pump**: 64.7% спам (HIGH)
- **WSOL**: 37.6% спам (MEDIUM) - даже системные токены показывают активность

## 🚀 Использование

### Запуск тестов:
```bash
# Тест детектора
python3 scripts/test_spam_detector.py

# Тест задачи мониторинга
python3 scripts/test_spam_monitoring.py

# Анализ конкретного токена
python3 scripts/analyze_spam_transactions.py
```

### Запуск daemon:
```bash
# Непрерывный мониторинг каждые 5 секунд
python3 scripts/run_spam_monitor_daemon.py
```

### Интеграция в scheduler:
```python
from src.scheduler.tasks import run_spam_monitor

# Добавить в APScheduler с интервалом 5 секунд
scheduler.add_job(run_spam_monitor, 'interval', seconds=5)
```

## 📈 Метрики и логирование

### Логи спам-детекции:
- `spam_monitor_start` - начало цикла мониторинга
- `high_spam_detected` - обнаружен токен с высоким спамом
- `spam_monitor_complete` - завершение цикла с метриками

### Структура спам-метрик:
```json
{
  "spam_percentage": 64.7,
  "risk_level": "high",
  "total_instructions": 85,
  "compute_budget_count": 55,
  "transfer_count": 12,
  "system_count": 4
}
```

## 🔧 Конфигурация

### Переменные окружения:
- `HELIUS_API_KEY` - ключ для Helius RPC API

### Настройки в базе:
- `min_score` - минимальный скор для мониторинга (по умолчанию: 50.0)

## 🎯 Планы развития

1. **Интеграция в основной скоринг**:
   - Добавить спам-процент как штрафной коэффициент
   - Снижать скор токенов с высоким спамом

2. **Расширение критериев**:
   - Анализ кошельков (возраст, активность)
   - Паттерны сумм транзакций
   - Временные корреляции

3. **Хранение в БД**:
   - Добавить поле `spam_metrics` в `TokenScore`
   - История изменений спам-уровня
   - API для получения спам-данных

4. **Алерты и уведомления**:
   - Telegram уведомления о высоком спаме
   - Dashboard с визуализацией спам-метрик
   - Автоматическая фильтрация спамных токенов

## 🔍 Примеры использования

### Анализ конкретного токена:
```python
from src.monitoring.spam_detector import analyze_single_token

result = await analyze_single_token("J4UBm5kvMSHeUwbNgZW4ySpCHBvS7LXknZ7rqQR9pump")
print(f"Spam level: {result['spam_metrics']['spam_percentage']:.1f}%")
```

### Получение топовых токенов для мониторинга:
```python
from src.adapters.repositories.tokens_repo import TokensRepository

repo = TokensRepository(db)
tokens = repo.get_active_tokens_above_score(min_score=50.0)
print(f"Found {len(tokens)} tokens for spam monitoring")
```

Система готова к использованию и может быть легко интегрирована в существующую архитектуру мониторинга токенов.