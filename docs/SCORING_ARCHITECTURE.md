# Архитектура системы скоринга

Версия: 2.0 • Дата: 2025-09-17

## Обзор

Система скоринга To The Moon использует модульную архитектуру с поддержкой множественных моделей оценки арбитражного потенциала токенов. Основная модель — "Hybrid Momentum" — сочетает анализ транзакционной активности, объемов торгов, свежести токенов и дисбаланса ордеров.

## Архитектурная диаграмма

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   API Routes    │  │  Admin Panel    │  │ Scheduler   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Scoring Service │  │ Hybrid Momentum │  │ EWMA Service│ │
│  │  (Orchestrator) │  │     Model       │  │             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Component     │  │   Enhanced      │  │  Settings   │ │
│  │  Calculator     │  │ DEX Aggregator  │  │  Service    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Adapter Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ DexScreener API │  │   Database      │  │  Settings   │ │
│  │     Client      │  │  Repository     │  │ Repository  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Компоненты системы

### 1. ScoringService (Orchestrator)

**Расположение**: `src/domain/scoring/scoring_service.py`

**Назначение**: Унифицированный интерфейс для работы с различными моделями скоринга.

**Ключевые методы**:
- `calculate_token_score()` — расчет скора с автоматическим выбором модели
- `get_active_model()` — получение активной модели
- `switch_model()` — переключение между моделями
- `save_score_result()` — сохранение результатов в БД

**Поддерживаемые модели**:
- `hybrid_momentum` — продвинутая модель (по умолчанию)
- `legacy` — простая модель для обратной совместимости

### 2. HybridMomentumModel

**Расположение**: `src/domain/scoring/hybrid_momentum_model.py`

**Назначение**: Реализация продвинутой модели скоринга на основе 4 компонентов.

**Формула**: 
```
Score = (W_tx × Tx_Accel) + (W_vol × Vol_Momentum) + (W_fresh × Token_Freshness) + (W_oi × Orderflow_Imbalance)
```

**Компоненты**:
1. **Transaction Acceleration** — ускорение транзакционной активности
2. **Volume Momentum** — импульс торгового объема
3. **Token Freshness** — бонус за свежесть токена
4. **Orderflow Imbalance** — дисбаланс покупок/продаж

**Особенности**:
- EWMA сглаживание всех компонентов
- Конфигурируемые веса через настройки
- Детальное логирование и обработка ошибок
- Валидация входных данных

### 3. ComponentCalculator

**Расположение**: `src/domain/scoring/component_calculator.py`

**Назначение**: Статические методы для расчета компонентов скоринга.

**Методы**:
- `calculate_tx_accel(tx_5m, tx_1h)` — ускорение транзакций
- `calculate_vol_momentum(vol_5m, vol_1h)` — импульс объема
- `calculate_token_freshness(hours, threshold)` — свежесть токена
- `calculate_orderflow_imbalance(buys, sells)` — дисбаланс ордеров
- `validate_component_inputs(metrics)` — валидация входных данных

**Формулы**:
```python
# Transaction Acceleration
tx_accel = (tx_count_5m / 5) / (tx_count_1h / 60)

# Volume Momentum  
vol_momentum = volume_5m / (volume_1h / 12)

# Token Freshness
token_freshness = max(0, (threshold_hours - hours_since_creation) / threshold_hours)

# Orderflow Imbalance
orderflow_imbalance = (buys_volume_5m - sells_volume_5m) / (buys_volume_5m + sells_volume_5m)
```

### 4. EWMAService

**Расположение**: `src/domain/scoring/ewma_service.py`

**Назначение**: Экспоненциальное сглаживание компонентов для стабильности результатов.

**Ключевые методы**:
- `apply_smoothing()` — применение EWMA ко всем компонентам
- `calculate_ewma()` — расчет одного EWMA значения
- `get_previous_values()` — получение предыдущих значений из БД

**Формула EWMA**:
```
EWMA_new = α × current_value + (1 - α) × EWMA_previous
```

**Особенности**:
- Персистентность в базе данных
- Инициализация при отсутствии истории
- Валидация параметра α (0.0-1.0)
- Статистика сглаживания для анализа

### 5. EnhancedDexAggregator

**Расположение**: `src/domain/metrics/enhanced_dex_aggregator.py`

**Назначение**: Расширенный сбор метрик из DexScreener API для новой модели скоринга.

**Собираемые метрики**:
- `tx_count_5m`, `tx_count_1h` — количество транзакций
- `volume_5m`, `volume_1h` — торговые объемы
- `buys_volume_5m`, `sells_volume_5m` — оценка объемов покупок/продаж
- `hours_since_creation` — время с момента создания токена

**Методы оценки**:
- Объемы покупок/продаж оцениваются через пропорции транзакций
- Время создания рассчитывается от `token.created_at`
- Валидация консистентности данных

## Поток данных

### 1. Сбор метрик
```
DexScreener API → EnhancedDexAggregator → Enhanced Metrics
```

### 2. Расчет компонентов
```
Enhanced Metrics → ComponentCalculator → Raw Components
```

### 3. Сглаживание
```
Raw Components → EWMAService → Smoothed Components
```

### 4. Финальный скор
```
Smoothed Components → HybridMomentumModel → Final Score
```

### 5. Сохранение
```
Score + Components → ScoringService → Database
```

## Конфигурация

### Настройки модели (app_settings)

```python
# Активная модель
"scoring_model_active": "hybrid_momentum"

# Веса компонентов
"w_tx": "0.25"      # Transaction Acceleration
"w_vol": "0.25"     # Volume Momentum  
"w_fresh": "0.25"   # Token Freshness
"w_oi": "0.25"      # Orderflow Imbalance

# EWMA параметры
"ewma_alpha": "0.3"                    # Сглаживание (0.0-1.0)
"freshness_threshold_hours": "6.0"     # Порог свежести
```

### Валидация настроек

- Веса: неотрицательные числа
- EWMA α: диапазон [0.0, 1.0]  
- Пороги: положительные числа
- Модель: "hybrid_momentum" или "legacy"

## База данных

### Обновления схемы

**Новые поля в `token_scores`**:
```sql
raw_components JSON,           -- Сырые значения компонентов
smoothed_components JSON,      -- Сглаженные значения EWMA
scoring_model VARCHAR(50)      -- Используемая модель
```

**Структура компонентов**:
```json
{
  "tx_accel": 1.2,
  "vol_momentum": 0.8,
  "token_freshness": 0.6,
  "orderflow_imbalance": 0.1,
  "final_score": 0.675
}
```

## API интерфейс

### Новые endpoints

```http
# Получение весов всех моделей
GET /settings/weights

# Переключение модели скоринга  
POST /settings/model/switch
Content-Type: application/json
{"model": "hybrid_momentum"}

# Валидация настроек
GET /settings/validation/errors
```

### Расширенные ответы

**Детали токена** теперь включают:
```json
{
  "mint_address": "...",
  "score": 0.675,
  "smoothed_score": 0.650,
  "scoring_model": "hybrid_momentum",
  "raw_components": {
    "tx_accel": 1.2,
    "vol_momentum": 0.8,
    "token_freshness": 0.6,
    "orderflow_imbalance": 0.1
  },
  "smoothed_components": {
    "tx_accel": 1.1,
    "vol_momentum": 0.75,
    "token_freshness": 0.58,
    "orderflow_imbalance": 0.08
  }
}
```

## Тестирование

### Unit тесты

**ComponentCalculator** (12 тестов):
- Нормальные случаи для всех компонентов
- Граничные случаи (деление на ноль, отрицательные значения)
- Обработка экстремальных значений
- Валидация входных данных

**EWMAService** (15 тестов):
- Инициализация без истории
- Сглаживание с предыдущими значениями
- Персистентность в БД
- Валидация параметров
- Обработка ошибок

### Интеграционные тесты

- Полный pipeline скоринга
- Переключение между моделями
- Сохранение и восстановление EWMA
- API endpoints с валидацией

## Мониторинг и логирование

### Ключевые метрики для мониторинга

- Время расчета скора на токен
- Частота ошибок в компонентах
- Распределение значений компонентов
- Эффективность EWMA сглаживания

### Структурированные логи

```json
{
  "event": "hybrid_momentum_score_calculated",
  "token_id": 123,
  "mint_address": "...",
  "raw_score": 0.675,
  "smoothed_score": 0.650,
  "components": {
    "tx_accel": 1.2,
    "vol_momentum": 0.8,
    "token_freshness": 0.6,
    "orderflow_imbalance": 0.1
  },
  "model": "hybrid_momentum",
  "calculation_time_ms": 15
}
```

## Производительность

### Оптимизации

- Кэширование настроек (TTL 15 сек)
- Batch обработка токенов в scheduler
- Переиспользование DexScreener клиента
- Оптимизированные SQL запросы для EWMA

### Масштабирование

- Горизонтальное масштабирование scheduler'а
- Разделение hot/cold токенов
- Асинхронная обработка
- Мониторинг производительности

## Миграция и развертывание

### Стратегия миграции

1. **Подготовка**: развертывание кода с feature flag
2. **Миграция БД**: добавление новых полей
3. **Тестирование**: параллельная работа моделей
4. **Переключение**: активация hybrid_momentum
5. **Мониторинг**: контроль качества скоринга

### Rollback план

- Переключение `scoring_model_active` на `legacy`
- Откат миграций БД при необходимости
- Восстановление предыдущей версии кода

Система спроектирована для надежной работы и легкого расширения новыми моделями скоринга в будущем.