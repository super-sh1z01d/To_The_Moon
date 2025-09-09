To The Moon — система скоринга токенов Solana
=============================================

Публичный сервис для автоматического отслеживания, анализа и скоринга токенов, мигрировавших с Pump.fun на DEX в сети Solana. Бэкенд на Python/FastAPI, фронтенд — React/Vite. Без Docker, деплой из Git.

Содержание
---------
- Возможности
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
- Подписка на миграции токенов через WebSocket Pump.fun → создание записей (status: `monitoring`).
- Валидация через DexScreener: проверка наличия WSOL/pumpfun-amm и внешнего пула → `active`.
- Сбор метрик по WSOL‑парам: ликвидность, дельты 5м/15м, транзакции 5м.
- Расчёт скоринга по формулам ТЗ (временная заглушка holders: `HD_norm=1`).
- Планировщик (APScheduler): отдельные частоты обновления для «горячих»/«остывших» токенов.
- Архивация: `active` ниже порога долгое время и `monitoring` с таймаутом.
- Публичное API: список, детали токена, пулы WSOL, пересчёт on‑demand.
- Фронтенд (SPA): дашборд, сортировка/пагинация, просмотр пулов, страница настроек, детальная карточка токена.

Архитектура
-----------
- Backend (FastAPI): `src/app`, маршруты `/health`, `/version`, `/settings`, `/tokens`, `/admin`, `/ui` (минимальный UI) и раздача SPA `/app`.
- DB (PostgreSQL/SQLite dev): ORM SQLAlchemy 2.x, миграции Alembic. Таблицы: `tokens`, `token_scores`, `app_settings`.
- Scheduler (APScheduler): фоновые задачи обновления «hot/cold» и часовая архивация.
- Worker Pump.fun (WebSocket): `src/workers/pumpfun_ws.py` — подписка `subscribeMigration` и запись `monitoring` токенов.
- Внешние API: DexScreener (pairs), Pump.fun WS (migrations). Метрика holders временно исключена.

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
5) Откройте интерфейс: http://localhost:8000/app (дашборд, настройки).

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
- `.env`:
  - `APP_ENV` (dev/stage/prod)
  - `LOG_LEVEL` (INFO/DEBUG)
  - `HOST`, `PORT` — для uvicorn (если не через systemd)
  - `DATABASE_URL` — например: `postgresql+psycopg2://user:pass@localhost:5432/tothemoon`
  - `FRONTEND_DIST_PATH=frontend/dist` — путь к собранной SPA
  - `SCHEDULER_ENABLED=true`
- `app_settings` (через API `/settings`):
  - Весовые коэффициенты: `weight_s`, `weight_l`, `weight_m`, `weight_t`
  - Порог: `min_score`
  - Тайминги: `hot_interval_sec`, `cold_interval_sec`, `archive_below_hours`, `monitoring_timeout_hours`

Миграции
--------
- Применить: `python3 -m alembic upgrade head`
- Сгенерировать (при доработках): `python3 -m alembic revision -m "msg" --autogenerate`

API
---
- Health/version: `GET /health`, `GET /version`
- Settings:
  - `GET /settings/` — все ключи (с дефолтами)
  - `GET /settings/{key}` — значение (или дефолт), `404` если ключ неизвестен
  - `PUT /settings/{key}` — обновить (строковое значение)
- Tokens:
  - `GET /tokens?min_score=&limit=&offset=&sort=score_desc|score_asc`
    - Возвращает `{ total, items: [...], meta: {total,limit,offset,page,page_size,has_prev,has_next,sort,min_score} }`
  - `GET /tokens/{mint}` — детали токена: последний `score/metrics`, `score_history`, `pools` (только WSOL), `status`, ссылка Solscan
  - `POST /tokens/{mint}/refresh` — on‑demand пересчёт (новый снапшот + score)
  - `GET /tokens/{mint}/pools` — WSOL‑пулы (адрес, dex, ссылка Solscan)
- Admin:
  - `POST /admin/recalculate` — запустить обновление «горячих» и «остывших» токенов
- UI:
  - `/app` — SPA (дашборд и настройки)
  - `/ui` — минималистичный HTML/JS UI (параллельно SPA)

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
- Unit/Integration: `pytest -q` (по мере добавления тестов).
- Smoke‑скрипты: `scripts/smoke_db.py`, `scripts/validate_monitoring.py`, `scripts/update_metrics.py`, `scripts/compute_scores.py`, `scripts/archive_tokens.py`.

Безопасность и эксплуатация
---------------------------
- Не храните секреты в Git. Используйте `/etc/tothemoon.env` или секрет‑менеджер.
- Ограничьте CORS на проде (по умолчанию в dev открыт `*`).
- Следите за лимитами DexScreener: при 429 в логах будет `rate_limited`.
- Планировщик и воркер — раздельные процессы (API + APScheduler, WS‑воркер отдельным сервисом).

Дорожная карта
--------------
- Метрика holders (Helius) и включение `HD_norm` вместо заглушки.
- Расширенная сортировка/фильтры по ликвидности, транзакциям, движению цен.
- Улучшенная пагинация (cursor‑based) и поиск по имени/символу.
- Метрики Prometheus и дашборд Grafana.

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
