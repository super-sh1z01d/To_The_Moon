# Conventions — To The Moon (Python)

Версия: 2.0 • Дата: 2025‑09‑17

Цель: единые и простые правила разработки, чтобы быстро и стабильно выпускать изменения без оверинжиниринга. Обновлено для поддержки новой архитектуры скоринга с множественными моделями.

## Стек и версии
- Python 3.10+.
- FastAPI, SQLAlchemy 2.x, Alembic, APScheduler (выбран как планировщик).
- Pydantic v2, pydantic‑settings.
- HTTP: httpx (async), WebSocket: websockets/async websockets клиент.
- Frontend: React + Vite + TypeScript.

## Структура проекта
- `src/` — исходный код приложения.
- `src/app/` — FastAPI приложение (инициализация, роуты, DI, middlewares).
- `src/domain/` — доменная логика:
  - `src/domain/scoring/` — модели скоринга (HybridMomentumModel, ComponentCalculator, EWMAService)
  - `src/domain/metrics/` — агрегаторы метрик (EnhancedDexAggregator)
  - `src/domain/settings/` — управление настройками
  - `src/domain/validation/` — валидаторы данных
- `src/adapters/` — интеграции:
  - `src/adapters/services/` — внешние API (DexScreener, Pump.fun WS)
  - `src/adapters/repositories/` — репозитории данных
  - `src/adapters/db/` — модели БД и зависимости
- `src/core/` — конфиг, логирование, утилиты, ошибки.
- `src/scheduler/` — планировщик задач и воркеры.
- `migrations/` — Alembic миграции.
- `scripts/` — служебные скрипты запуска и диагностики.
- `tests/` — тесты (unit/integration).
- `frontend/` — исходники SPA (React + Vite).

**Принципы архитектуры**:
- Чистая архитектура: Domain → Adapters → App
- Dependency Injection через FastAPI
- Единый интерфейс для множественных моделей скоринга
- Минимизируем количество слоёв, но сохраняем четкое разделение ответственности

## Код‑стайл
- PEP‑8, типизация везде (mypy совместимо).
- Имена: snake_case для функций/переменных, PascalCase для классов, UPPER_SNAKE для констант.
- Докстринги формата Google или NumPy для публичных функций/классов.
- Исключения: собственные исключения в `core.exceptions`.
- Импорты: стандартные → сторонние → локальные (isort порядок).
- Форматирование/линт: black, ruff (по умолчанию, без фанатизма в конфиге).

## Логирование
- Формат: JSON (структурные логи), уровень INFO для прод, DEBUG для тестов.
- Обязательные поля: `ts`, `level`, `msg`, `service`, `env`, `version`, `module`, `op`, `trace_id`.
- Для внешних вызовов логируем: `target`, `method`, `url`, `status`, `latency_ms`, `retries`, `error`.
- Не логируем секреты и персональные данные.
- Фронтенд в dev: подробные консольные логи запросов/ошибок.

## Конфигурация
- Значения из `.env` → pydantic‑settings → объект Config (single source of truth).
- Ключевые переменные:
  - `DATABASE_URL`
  - `APP_ENV` (dev/stage/prod)
  - `LOG_LEVEL` (INFO/DEBUG)
  - Интервалы и пороги могут храниться в БД (`app_settings`) и переопределять дефолты.
  - `FRONTEND_DIST_PATH` — путь к собранной статике фронта (если нестандартный)

## Работа с БД
- SQLAlchemy 2.x, декларативные модели.
- Сессии через зависимость FastAPI, без автокоммита; транзакции явные.
- Время: всегда UTC (`TIMESTAMPTZ`), на уровне Python — tz‑aware.
- Миграции: Alembic, одна миграция — один смысловой шаг.

## Интеграции (DexScreener, Pump.fun WS)
- httpx: таймауты (connect/read ≤ 5с), ретраи с экспоненциальной паузой (max 3–5).
- Rate limits: при 429 — respect Retry‑After или backoff со слотом 5–30с.
- Валидация ответов: pydantic‑модели с `strict=True` на критичных полях.
- WS воркер: авто‑reconnect с джиттером, «at‑least‑once» доставка через идемпотентные вставки (UNIQUE по mint).
- Метрика holders временно исключена; в расчёте используется `HD_norm = 1`.

## Домен: скоринг

### Архитектура скоринга
- **ScoringService** — унифицированный интерфейс для всех моделей
- **HybridMomentumModel** — продвинутая модель с 4 компонентами
- **ComponentCalculator** — статические методы расчета компонентов
- **EWMAService** — экспоненциальное сглаживание с персистентностью

### Принципы реализации
- Метрики и формулы строго соответствуют ТЗ.
- Все исходные метрики сохраняем в `token_scores.metrics` для прозрачности.
- **Новое**: компоненты скоринга сохраняем в `raw_components` и `smoothed_components`.
- **Новое**: модель скоринга указывается в поле `scoring_model`.
- Весовые коэффициенты и пороги читаем из `app_settings` с кэшем в памяти (TTL ~15с).
- Поддержка множественных моделей через настройку `scoring_model_active`.

### Hybrid Momentum модель
- **4 компонента**: Transaction Acceleration, Volume Momentum, Token Freshness, Orderflow Imbalance
- **EWMA сглаживание** всех компонентов для стабильности
- **Конфигурируемые веса**: w_tx, w_vol, w_fresh, w_oi
- **Валидация входных данных** с graceful fallback
- **Детальное логирование** всех этапов расчета

### Тестирование скоринга
- Unit тесты для каждого компонента с граничными случаями
- Тесты EWMA сглаживания с различными сценариями
- Интеграционные тесты полного pipeline скоринга
- Покрытие тестами: ComponentCalculator (12 тестов), EWMAService (15 тестов)

## API (REST)
- Последовательная схема URL и именование ресурсов.
- Пагинация: `limit` (<= 100), `offset` (или `cursor` — если потребуется).
- Сортировка по умолчанию — по `score DESC`.
- Ответы: pydantic‑модели, численные поля — десятичные/float с масштабом из ТЗ.
- Ошибки: унифицированный формат `{error: {code, message}}`.
- OpenAPI/Swagger по умолчанию включен.

## Планировщики
- Для простоты — APScheduler (background, async) в том же процессе API или отдельном воркере.
- Долгие задачи/ретраи не должны блокировать event loop — выносить в фоновый scheduler/воркер.

## Тестирование

### Структура тестов
- **Unit тесты**: быстрые, изолированные тесты доменной логики
  - `tests/test_component_calculator.py` — тесты компонентов скоринга
  - `tests/test_ewma_service.py` — тесты EWMA сглаживания
- **Integration тесты**: с БД и моками внешних API
- **End-to-end тесты**: полный pipeline через API

### Принципы тестирования
- pytest с фикстурами для изоляции тестов
- Временная БД (schema per test), rollback после теста
- Моки для внешних API (DexScreener, Pump.fun)
- Тестирование граничных случаев и обработки ошибок
- «Боевые» прогонки — только вручную с отдельным конфигом (`APP_ENV=dev_live`)

### Покрытие тестами
- ✅ ComponentCalculator: 12 тестов (все компоненты + edge cases)
- ✅ EWMAService: 15 тестов (сглаживание + персистентность)
- ✅ Валидация настроек и API endpoints
- 🔄 ScoringService: интеграционные тесты (в разработке)
- 🔄 HybridMomentumModel: end-to-end тесты (в разработке)

### Запуск тестов
```bash
# Все тесты
PYTHONPATH=. python3 -m pytest -v

# Конкретные модули
PYTHONPATH=. python3 -m pytest tests/test_component_calculator.py -v
PYTHONPATH=. python3 -m pytest tests/test_ewma_service.py -v
```

## Коммиты и PR
- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- Маленькие атомарные изменения. Каждое закрытие таска — краткий ченджлог в README (или релизные заметки в Git/Release).

## Безопасность
- Секреты — только через переменные окружения/секрет‑менеджер.
- CORS — явно ограниченный список источников.
- В заголовках не светим серверные детали; убираем лишние stacktraces на проде.

## Деплой (без Docker)
- Деплой из Git: `git pull` → `pip install -r requirements.txt` → `alembic upgrade head` → `npm ci && npm run build` → рестарт `uvicorn`.
- Рекомендуемый сервис: `systemd` unit для `uvicorn`; логи приложения — в stdout (JSON), системные — journald.

## Документация и процесс
- Держим актуальным README (ключевые изменения, инструкции и roadmap).
- Если появляются вопросы/идеи — сначала фиксируем в «Открытых вопросах» в `tasklist.md`, затем уточняем.
- Предпочитаем простые решения. Если есть сомнение — берём самое понятное и измеряем.
