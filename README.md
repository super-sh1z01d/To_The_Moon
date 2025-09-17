To The Moon — система скоринга токенов Solana
=============================================

Публичный сервис для автоматического отслеживания, анализа и скоринга токенов, мигрировавших с Pump.fun на DEX в сети Solana. Использует продвинутую модель "Hybrid Momentum" для оценки арбитражного потенциала токенов. Бэкенд на Python/FastAPI, фронтенд — React/Vite. Без Docker, деплой из Git.

Содержание
---------
- Возможности
- Модели скоринга
- Архитектура
- Требования
- Быстрый старт (dev)
- Конфигурация
- Миграции
- API
- Продакшен‑деплой (без Docker)
- Правила разработки
- Тестирование
- Безопасность и эксплуатация
- Дорожная карта

Возможности
-----------
- **Подписка на миграции токенов** через WebSocket Pump.fun → создание записей (status: `monitoring`).
- **Валидация через DexScreener**: проверка наличия WSOL/pumpfun-amm и внешнего пула → `active`.
- **Расширенный сбор метрик** по WSOL/SOL и USDC‑парам: учитываются `pumpfun-amm`, `pumpswap` и внешние DEX; classic `pumpfun` исключён.
- **Hybrid Momentum скоринг**: продвинутая модель оценки арбитражного потенциала на основе 4 компонентов:
  - **Transaction Acceleration** — ускорение торговой активности
  - **Volume Momentum** — импульс торгового объема
  - **Token Freshness** — свежесть токена (недавно мигрировавшие получают бонус)
  - **Orderflow Imbalance** — дисбаланс покупок/продаж
- **EWMA сглаживание** всех компонентов для стабильности результатов.
- **Множественные модели скоринга**: поддержка legacy и hybrid momentum моделей с переключением через API.
- **Планировщик (APScheduler)**: отдельные частоты обновления для «горячих»/«остывших» токенов.
- **Архивация**: `active` ниже порога долгое время и `monitoring` с таймаутом.
- **Публичное API**: список, детали токена, компоненты скоринга, пулы WSOL, пересчёт on‑demand.
- **Логи**: in‑memory буфер + API для чтения и страницы просмотра с фильтрами.
- **Фронтенд (SPA)**: дашборд (автообновление каждые 5 сек), сортировка/пагинация, просмотр пулов, страница настроек, детальная карточка токена, вкладка логов.

Модели скоринга
---------------

### Hybrid Momentum Model (по умолчанию)
Продвинутая модель для оценки краткосрочного арбитражного потенциала:

**Формула**: `Score = (W_tx × Tx_Accel) + (W_vol × Vol_Momentum) + (W_fresh × Token_Freshness) + (W_oi × Orderflow_Imbalance)`

**Компоненты**:
- **Tx_Accel** = `(tx_count_5m / 5) / (tx_count_1h / 60)` — ускорение транзакций
- **Vol_Momentum** = `volume_5m / (volume_1h / 12)` — импульс объема
- **Token_Freshness** = `max(0, (6 - hours_since_creation) / 6)` — свежесть токена
- **Orderflow_Imbalance** = `(buys_volume_5m - sells_volume_5m) / (buys_volume_5m + sells_volume_5m)` — дисбаланс ордеров

**Особенности**:
- EWMA сглаживание всех компонентов (параметр `ewma_alpha`)
- Конфигурируемые веса компонентов через API
- Учет свежести токенов (недавно мигрировавшие получают бонус)

### Legacy Model
Простая модель на основе ликвидности, волатильности и активности:
- Компоненты: `l` (ликвидность), `s` (волатильность), `m` (моментум), `t` (транзакции)
- Поддерживается для обратной совместимости

Архитектура
-----------
- **Backend (FastAPI)**: `src/app`, маршруты `/health`, `/version`, `/settings`, `/tokens`, `/admin`, `/logs`, `/ui` (минимальный UI) и раздача SPA `/app`.
- **DB (PostgreSQL/SQLite dev)**: ORM SQLAlchemy 2.x, миграции Alembic. Таблицы: `tokens`, `token_scores`, `app_settings`.
  - Новые поля в `token_scores`: `raw_components`, `smoothed_components`, `scoring_model`
- **Scoring Service**: Унифицированный интерфейс для множественных моделей скоринга
  - `HybridMomentumModel` — новая продвинутая модель
  - `ComponentCalculator` — расчет компонентов скоринга
  - `EWMAService` — экспоненциальное сглаживание
- **Scheduler (APScheduler)**: фоновые задачи обновления «hot/cold», валидация `monitoring→active` и часовая архивация.
  - Автоматическое переключение между моделями скоринга
  - При активации пытаемся заполнить `name`/`symbol` из `baseToken` DexScreener, если они были пустыми.
  - Правило активации/демоции по ликвидности внешних пулов: токен становится `active`, если есть хотя бы один внешний пул WSOL/SOL/USDC (DEX не в {pumpfun, pumpfun-amm, pumpswap}) с ликвидностью ≥ `activation_min_liquidity_usd`.
- **Worker Pump.fun (WebSocket)**: `src/workers/pumpfun_ws.py` — подписка `subscribeMigration` и запись `monitoring` токенов.
- **Внешние API**: DexScreener (pairs), Pump.fun WS (migrations).
  - Расширенный сбор метрик: транзакции 5м/1ч, объемы 5м/1ч, оценка объемов покупок/продаж
  - WSOL распознаётся как `WSOL` и `SOL` (а также варианты `W_SOL`, `W-SOL`); USDC распознаётся по символу `USDC`
  - Пулы Pump.fun определяются `dexId` ∈ {`pumpfun-amm`,`pumpfun`,`pumpswap`}; из расчёта исключён только `pumpfun` (classic)

Требования
----------
- Python 3.10+ (разработка велась на 3.9.6 — совместимость обеспечена синтаксисом Optional и т.п.).
- Node.js 18+ и npm — для сборки SPA.
- PostgreSQL 14+ для продакшена (в dev по умолчанию используется `sqlite:///dev.db`).

Быстрый старт (dev)
-------------------
1) Клонируйте репозиторий и установите зависимости:
```
python3 -m pip install -r requirements.txt
cp .env.example .env
```
2) Примените миграции (по умолчанию SQLite dev.db):
```
python3 -m alembic upgrade head
```
3) Соберите фронтенд:
```
cd frontend && npm install && npm run build && cd -
```
4) Запустите сервер:
```
PYTHONPATH=. python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000
```
5) Откройте интерфейс: http://localhost:8000/app (Дашборд, Настройки, Логи).

Дополнительно (dev):
- Заполнить тестовыми данными:
```
PYTHONPATH=. python3 scripts/smoke_db.py
PYTHONPATH=. python3 scripts/dev_mark_active.py
PYTHONPATH=. python3 scripts/update_metrics.py --limit 1
PYTHONPATH=. python3 scripts/compute_scores.py --limit 1
```
- Проверить валидатор (для реальных токенов):
```
PYTHONPATH=. python3 scripts/validate_monitoring.py --limit 25
```
- Запустить WS‑воркер (нужна сеть):
```
PUMPFUN_RUN_SECONDS=120 PYTHONPATH=. python3 -m src.workers.pumpfun_ws
```

Конфигурация
------------
Все основные настройки читаются из `.env` (см. `.env.example`) и таблицы `app_settings`:

### Переменные окружения (.env):
- `APP_ENV` (dev/stage/prod)
- `LOG_LEVEL` (INFO/DEBUG)
- `HOST`, `PORT` — для uvicorn (если не через systemd)
- `DATABASE_URL` — например: `postgresql+psycopg2://user:pass@localhost:5432/tothemoon`
- `FRONTEND_DIST_PATH=frontend/dist` — путь к собранной SPA
- `SCHEDULER_ENABLED=true` — включает APScheduler (обновления, валидация, архивация)

### Настройки скоринга (через API `/settings`):

**Модель скоринга**:
- `scoring_model_active` — активная модель: `"hybrid_momentum"` или `"legacy"`

**Hybrid Momentum веса**:
- `w_tx` (0.25) — вес ускорения транзакций
- `w_vol` (0.25) — вес импульса объема
- `w_fresh` (0.25) — вес свежести токена
- `w_oi` (0.25) — вес дисбаланса ордеров

**EWMA сглаживание**:
- `ewma_alpha` (0.3) — параметр сглаживания (0.0-1.0)
- `freshness_threshold_hours` (6.0) — порог свежести токена в часах

**Legacy веса** (для обратной совместимости):
- `weight_s`, `weight_l`, `weight_m`, `weight_t`

**Общие настройки**:
- `min_score` — минимальный порог скора
- `hot_interval_sec`, `cold_interval_sec` — интервалы обновления
- `archive_below_hours`, `monitoring_timeout_hours` — настройки архивации
- `activation_min_liquidity_usd` — минимальная ликвидность для активации

**Фильтрация данных**:
- `min_pool_liquidity_usd` (500) — минимальная ликвидность пула для учета
- `max_price_change_5m` (0.5) — максимальное изменение цены за 5м (50%)
- `min_score_change` (0.05) — минимальное изменение скора для обновления

Миграции
--------
- Применить: `python3 -m alembic upgrade head`
- Сгенерировать (при доработках): `python3 -m alembic revision -m "msg" --autogenerate`

API
---

### Health/Version
- `GET /health` — статус системы
- `GET /version` — версия приложения

### Settings
- `GET /settings/` — все настройки (с дефолтами)
- `GET /settings/{key}` — значение настройки (или дефолт), `404` если ключ неизвестен
- `PUT /settings/{key}` — обновить настройку (с валидацией)
- `GET /settings/validation/errors` — список ошибок валидации настроек
- `GET /settings/weights` — веса всех моделей скоринга
- `POST /settings/model/switch` — переключить активную модель скоринга

### Tokens
- `GET /tokens?min_score=&limit=&offset=&sort=score_desc|score_asc&statuses=active,monitoring,archived`
  - Параметры: `limit` (1–100, по умолчанию 50), `offset` (>=0), `statuses` (список через запятую)
  - По умолчанию архив исключён; чтобы видеть архив — добавьте `statuses=archived`
  - Возвращает `{ total, items: [...], meta: {...} }`
  - Поля `items[]`: `mint_address`, `name`, `symbol`, `status`, `score`, `smoothed_score`, компоненты скоринга, метрики
- `GET /tokens/{mint}` — детали токена: 
  - Последний `score/metrics`, `score_history`, `pools` (только WSOL)
  - **Новое**: разбивка компонентов скоринга (`raw_components`, `smoothed_components`)
  - **Новое**: информация о модели скоринга (`scoring_model`)
- `POST /tokens/{mint}/refresh` — on‑demand пересчёт (новый снапшот + score)
- `GET /tokens/{mint}/pools` — WSOL/SOL‑пулы (адрес, dex, ссылка Solscan)

### Admin
- `POST /admin/recalculate` — запустить обновление «горячих» и «остывших» токенов

### Logs
- `GET /logs?limit=&levels=&loggers=&contains=&since=` — последние записи in‑memory буфера
  - `limit` (1–500), `levels` (CSV уровней), `loggers` (CSV имён логгеров), `contains` (подстрока), `since` (ISO‑время)
- `GET /logs/meta` — метаданные (список доступных `logger`)

### UI
- `/app` — SPA (дашборд и настройки)
- `/ui` — минималистичный HTML/JS UI (параллельно SPA)

### Примеры использования

**Переключение модели скоринга:**
```bash
curl -X POST http://localhost:8000/settings/model/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "hybrid_momentum"}'
```

**Настройка весов Hybrid Momentum:**
```bash
curl -X PUT http://localhost:8000/settings/w_tx \
  -H "Content-Type: application/json" \
  -d '{"value": "0.3"}'
```

**Получение детализации скоринга:**
```bash
curl http://localhost:8000/tokens/So11111111111111111111111111111111111111112
# Ответ включает raw_components и smoothed_components
```

Логи — JSON, содержат поля `path`, `method`, `status`, `latency_ms`, а также ключевые события (подключение WS, вставка/дубликаты токенов, обновления метрик/скора, архивация и т.д.).

Продакшен‑деплой (без Docker)
-----------------------------
Ниже — краткая инструкция для Ubuntu 22.04+ (аналогично на других системах).

1) Зависимости на сервере
```
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx
# Node.js: установите LTS (18+) удобным для вас способом (nvm/apt)
```

2) Пользователь и директория
```
sudo useradd -r -m -d /srv/tothemoon -s /bin/bash tothemoon || true
sudo mkdir -p /srv/tothemoon
sudo chown -R tothemoon:tothemoon /srv/tothemoon
cd /srv/tothemoon
sudo -u tothemoon git clone <repo_url> .
```

3) Виртуальное окружение и зависимости
```
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

4) Настроить окружение
```
sudo tee /etc/tothemoon.env >/dev/null <<'ENV'
APP_ENV=prod
LOG_LEVEL=INFO
DATABASE_URL=postgresql+psycopg2://user:pass@127.0.0.1:5432/tothemoon
FRONTEND_DIST_PATH=/srv/tothemoon/frontend/dist
SCHEDULER_ENABLED=true
ENV
```

5) Миграции и сборка фронтенда
```
source venv/bin/activate
python -m alembic upgrade head
cd frontend && npm ci && npm run build && cd -
```

6) systemd сервисы
```
sudo cp scripts/systemd/tothemoon.service /etc/systemd/system/
sudo cp scripts/systemd/tothemoon-ws.service /etc/systemd/system/
# Проверьте пути WorkingDirectory/ExecStart под вашу установку
sudo systemctl daemon-reload
sudo systemctl enable tothemoon.service tothemoon-ws.service
sudo systemctl start tothemoon.service tothemoon-ws.service
```

7) Nginx (опционально)
```
sudo cp scripts/nginx/tothemoon.conf /etc/nginx/sites-available/tothemoon.conf
sudo ln -s /etc/nginx/sites-available/tothemoon.conf /etc/nginx/sites-enabled/tothemoon.conf
sudo nginx -t && sudo systemctl reload nginx
```
Подключите HTTPS (например, `certbot --nginx`) и включите редирект HTTP→HTTPS.

8) Деплой из Git
- Быстрый скрипт: `bash scripts/deploy.sh` (выполняет `git pull`, `pip install`, `alembic upgrade`, сборку фронта и `systemctl restart`).

Самый простой способ установки на сервере (1 команда)
----------------------------------------------------
Скрипт `scripts/install.sh` автоматизирует подготовку сервера: создаёт пользователя, клонирует репозиторий в `/srv/tothemoon`, готовит `venv`, применяет миграции, собирает фронтенд (если есть Node), устанавливает/запускает systemd сервисы и проверяет `/health`.

Вариант А: запустить из уже клонированного репозитория
```
sudo bash scripts/install.sh
```

Вариант Б: запустить напрямую по ссылке (без предварительного клонирования)
```
sudo bash -c "REPO_URL=https://github.com/super-sh1z01d/To_The_Moon.git bash -s" < <(curl -fsSL https://raw.githubusercontent.com/super-sh1z01d/To_The_Moon/main/scripts/install.sh)
```

Параметры (через переменные окружения):
- `REPO_URL` — URL репозитория (по умолчанию текущий GitHub).
- `APP_DIR` — путь установки (по умолчанию `/srv/tothemoon`).
- `APP_USER` — системный пользователь (по умолчанию `tothemoon`).
- `ENV_FILE` — файл окружения (по умолчанию `/etc/tothemoon.env`).

Автоматическая установка зависимостей (опционально)
- `INSTALL_NODE` (true|false, по умолчанию true) — установить Node.js 18 через NodeSource.
- `INSTALL_NGINX` (true|false, по умолчанию false) — установить Nginx и развернуть reverse proxy.
  - Укажите `SERVER_NAME=your.domain.tld` для подстановки в конфиг Nginx (иначе `_`).
- `INSTALL_POSTGRES` (true|false, по умолчанию false) — установить PostgreSQL.
- `CREATE_PG_DB` (true|false, по умолчанию false) — создать БД и пользователя.
  - `PG_DB` (tothemoon), `PG_USER` (tothemoon), `PG_PASS` (если не задан — сгенерируется).
  - Скрипт обновит `DATABASE_URL` в `$ENV_FILE`.

После установки
- Отредактируйте `/etc/tothemoon.env` для подключения к PostgreSQL (по умолчанию стоит SQLite dev.db):
  `DATABASE_URL=postgresql+psycopg2://user:pass@127.0.0.1:5432/tothemoon`
- Перезапустите сервисы: `sudo systemctl restart tothemoon.service tothemoon-ws.service`
- Проверка: `curl -fsS http://127.0.0.1:8000/health` должно вернуть `{ "status": "ok" }`.


Правила разработки
------------------
См. `conventions.md`: стек, структура, стиль, логирование, конфигурация, интеграции, тестирование, деплой из Git.

Тестирование
------------

### Unit тесты
```bash
# Запуск всех тестов
PYTHONPATH=. python3 -m pytest -v

# Тесты компонентов скоринга
PYTHONPATH=. python3 -m pytest tests/test_component_calculator.py -v

# Тесты EWMA сглаживания
PYTHONPATH=. python3 -m pytest tests/test_ewma_service.py -v
```

### Покрытие тестами
- ✅ `ComponentCalculator` — 12 тестов (все компоненты + граничные случаи)
- ✅ `EWMAService` — 15 тестов (сглаживание + персистентность)
- ✅ Валидация настроек и API endpoints
- ✅ Обработка ошибок и граничных случаев

### Utility скрипты
- `scripts/smoke_db.py` — заполнение тестовыми данными
- `scripts/validate_monitoring.py` — проверка валидатора токенов
- `scripts/update_metrics.py` — обновление метрик
- `scripts/compute_scores.py` — расчет скоров
- `scripts/archive_tokens.py` — архивация токенов

### Тестирование моделей скоринга
```bash
# Тестирование hybrid momentum модели
PYTHONPATH=. python3 -c "
from src.domain.scoring.component_calculator import ComponentCalculator
print('Tx Accel:', ComponentCalculator.calculate_tx_accel(100, 1200))
print('Vol Momentum:', ComponentCalculator.calculate_vol_momentum(1000, 12000))
print('Token Freshness:', ComponentCalculator.calculate_token_freshness(2.0, 6.0))
print('Orderflow Imbalance:', ComponentCalculator.calculate_orderflow_imbalance(600, 400))
"
```

Безопасность и эксплуатация
---------------------------
- Не храните секреты в Git. Используйте `/etc/tothemoon.env` или секрет‑менеджер.
- Ограничьте CORS на проде (по умолчанию в dev открыт `*`).
- Следите за лимитами DexScreener: при 429 в логах будет `rate_limited`.
- Планировщик и воркер — раздельные процессы (API + APScheduler, WS‑воркер отдельным сервисом).
- Логи в UI читаются из in‑memory буфера (последние ~2000 записей, обновляются в реальном времени). Для долгосрочного хранения используйте внешние решения (journald/ELK и т.п.).

Дорожная карта
--------------

### Ближайшие планы
- ✅ **Hybrid Momentum модель скоринга** — реализована
- ✅ **EWMA сглаживание компонентов** — реализовано
- ✅ **Множественные модели скоринга** — реализовано
- ✅ **Расширенный API для компонентов** — реализован

### Следующие этапы
- **Метрика holders** (Helius API) для более точного расчета Holder_Growth
- **Машинное обучение**: обучение весов модели на исторических данных
- **Дополнительные модели скоринга**: 
  - Momentum + Mean Reversion
  - Technical Analysis based
  - Social Sentiment integration
- **Расширенная аналитика**:
  - Корреляционный анализ компонентов
  - Бэктестинг моделей скоринга
  - A/B тестирование моделей

### Улучшения UI/UX
- **Интерактивные графики** компонентов скоринга
- **Настройка весов** через веб-интерфейс
- **Сравнение моделей** в реальном времени
- **Алерты** на основе скоринга

### Техническая оптимизация
- **Cursor-based пагинация** для больших объемов данных
- **Поиск по имени/символу** токенов
- **Кэширование** расчетов скоринга
- **Метрики Prometheus** и дашборд Grafana
- **Горизонтальное масштабирование** scheduler'а

Ansible деплой (опционально)
----------------------------
Подготовлен Ansible‑плейбук для автоматического развёртывания:

- inventory: `ansible/inventory.example` (настройте `ansible_host`, `ansible_user` и переменные).
- запуск: `ansible-playbook -i ansible/inventory.example ansible/playbook.yml`

Переменные (пример в inventory.example):
- `repo_url`, `app_dir`, `app_user`, `server_name`, `database_url`
- `install_node` (true), `install_nginx` (false)
- `install_postgres` (false), `create_pg_db` (false), `pg_db`, `pg_user`, `pg_pass`
- `install_certbot` (false), `certbot_email`

Роль выполнит установку зависимостей, клонирование репо, создание venv, миграции, сборку фронта, установку systemd юнитов, (опционально) nginx и certbot, перезапуск сервисов и health‑check.
