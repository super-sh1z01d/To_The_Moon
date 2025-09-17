# Server Deployment Instructions - Version 2.0.0

**Дата**: 17 сентября 2025  
**Версия**: 2.0.0 (Hybrid Momentum + Parameter Cleanup)  
**Статус**: ✅ Готов к развертыванию

## 🧹 Изменения в этой версии
- **УДАЛЕН**: Параметр `max_price_change_5m` из Hybrid Momentum модели
- **УПРОЩЕНЫ**: Настройки системы (меньше параметров)
- **СОХРАНЕНА**: Полная совместимость с legacy кодом
- **ОБНОВЛЕНА**: Документация и UI

## 🚀 Быстрое развертывание

### Вариант 1: Автоматическое обновление (Рекомендуется)

```bash
# Подключение к серверу
ssh user@your-server.com

# Переход в директорию приложения
cd /srv/tothemoon

# Запуск автоматического обновления
sudo bash scripts/deploy.sh
```

**Что произойдет:**
1. ✅ Git pull последних изменений
2. ✅ Обновление Python зависимостей
3. ✅ Применение миграций базы данных
4. ✅ Сборка нового фронтенда
5. ✅ Перезапуск сервисов
6. ✅ Проверка работоспособности

### Вариант 2: Пошаговое обновление

```bash
# 1. Подключение к серверу
ssh user@your-server.com

# 2. Создание бэкапа (рекомендуется)
cd /srv/tothemoon
sudo -u tothemoon pg_dump tothemoon > backup_$(date +%Y%m%d_%H%M%S).sql
sudo cp /etc/tothemoon.env /etc/tothemoon.env.backup

# 3. Обновление кода
sudo -u tothemoon git pull origin main

# 4. Обновление зависимостей
sudo -u tothemoon venv/bin/pip install -r requirements.txt

# 5. Применение миграций
sudo -u tothemoon bash -c "source venv/bin/activate && python -m alembic upgrade head"

# 6. Сборка фронтенда
cd frontend
sudo -u tothemoon npm ci
sudo -u tothemoon npm run build
cd -

# 7. Перезапуск сервисов
sudo systemctl restart tothemoon.service
sudo systemctl restart tothemoon-ws.service

# 8. Проверка работоспособности
curl http://localhost:8000/health
```

## 🔍 Проверка развертывания

### 1. Статус сервисов
```bash
# Проверка статуса основных сервисов
sudo systemctl status tothemoon.service
sudo systemctl status tothemoon-ws.service

# Должно показать: Active: active (running)
```

### 2. API работоспособность
```bash
# Проверка здоровья системы
curl http://localhost:8000/health
# Ожидаемый ответ: {"status":"ok"}

# Проверка активной модели скоринга
curl http://localhost:8000/settings/scoring_model_active
# Ожидаемый ответ: {"key":"scoring_model_active","value":"hybrid_momentum"}
```

### 3. Новая функциональность
```bash
# Проверка новых полей API
curl "http://localhost:8000/tokens/?limit=1" | jq '.items[0] | {score, raw_components, smoothed_components, scoring_model, created_at}'

# Ожидаемый ответ должен содержать:
# - raw_components: {...}
# - smoothed_components: {...}
# - scoring_model: "hybrid_momentum"
# - created_at: "2025-09-17T..."
```

### 4. Веб-интерфейс
```bash
# Откройте в браузере
http://your-server.com/app

# Проверьте:
# ✅ Таблица загружается
# ✅ Видны новые колонки: TX, Vol, Fresh, OI, Возраст (для Hybrid Momentum)
# ✅ Работают фильтры "Только свежие" и "Компактный режим"
# ✅ Цветовое кодирование скоров
# ✅ Индикаторы свежести 🆕
```

## 🎯 Ключевые изменения в системе

### База данных
- ✅ **Новые поля**: `raw_components`, `smoothed_components`, `scoring_model` в таблице `token_scores`
- ✅ **Миграция**: Автоматическая, без потери данных
- ✅ **Совместимость**: Старые записи продолжают работать

### API
- ✅ **Новые поля в ответах**: Компоненты скоринга и метаданные
- ✅ **Новые настройки**: Веса компонентов, параметры сглаживания
- ✅ **Обратная совместимость**: Все старые endpoints работают

### Фронтенд
- ✅ **Адаптивная таблица**: Показывает колонки в зависимости от модели
- ✅ **Новые фильтры**: "Только свежие", "Компактный режим"
- ✅ **Визуальные улучшения**: Цвета, прогресс-бары, индикаторы
- ✅ **Оптимизация**: Удалены избыточные колонки

## ⚙️ Настройка системы

### Проверка конфигурации
```bash
# Просмотр текущих настроек
curl http://localhost:8000/settings/ | jq

# Основные настройки Hybrid Momentum:
# - scoring_model_active: "hybrid_momentum"
# - w_tx: "0.25" (вес Transaction Acceleration)
# - w_vol: "0.25" (вес Volume Momentum)
# - w_fresh: "0.25" (вес Token Freshness)
# - w_oi: "0.25" (вес Orderflow Imbalance)
# - ewma_alpha: "0.3" (параметр сглаживания)
# - freshness_threshold_hours: "6.0" (порог свежести)
```

### Настройка весов (опционально)
```bash
# Изменение веса Transaction Acceleration
curl -X PUT http://localhost:8000/settings/w_tx \
  -H "Content-Type: application/json" \
  -d '{"value": "0.3"}'

# Изменение параметра сглаживания
curl -X PUT http://localhost:8000/settings/ewma_alpha \
  -H "Content-Type: application/json" \
  -d '{"value": "0.2"}'
```

### Переключение модели (если нужно)
```bash
# Переключение на Legacy модель
curl -X POST http://localhost:8000/settings/model/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "legacy"}'

# Переключение обратно на Hybrid Momentum
curl -X POST http://localhost:8000/settings/model/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "hybrid_momentum"}'
```

## 🔧 Устранение неполадок

### Проблема: Сервис не запускается
```bash
# Проверка логов
sudo journalctl -u tothemoon.service -n 50

# Проверка конфигурации
sudo nano /etc/tothemoon.env

# Проверка прав доступа
sudo chown -R tothemoon:tothemoon /srv/tothemoon
```

### Проблема: Миграция не применилась
```bash
# Проверка статуса миграции
sudo -u tothemoon bash -c "source venv/bin/activate && python -m alembic current"

# Принудительное применение
sudo -u tothemoon bash -c "source venv/bin/activate && python -m alembic upgrade head"

# Проверка схемы БД
sudo -u postgres psql tothemoon -c "\d token_scores"
```

### Проблема: Фронтенд не обновился
```bash
# Пересборка фронтенда
cd /srv/tothemoon/frontend
sudo -u tothemoon rm -rf node_modules dist
sudo -u tothemoon npm install
sudo -u tothemoon npm run build

# Перезапуск сервиса
sudo systemctl restart tothemoon.service
```

### Проблема: API возвращает старый формат
```bash
# Проверка активной модели
curl http://localhost:8000/settings/scoring_model_active

# Принудительное обновление токена
curl -X POST http://localhost:8000/tokens/YOUR_TOKEN_MINT/refresh

# Проверка новых полей
curl "http://localhost:8000/tokens/?limit=1" | jq '.items[0] | keys'
```

## 📊 Мониторинг после развертывания

### Проверка производительности
```bash
# Время ответа API
time curl -s http://localhost:8000/tokens/?limit=10 > /dev/null

# Использование памяти
ps aux | grep uvicorn

# Использование диска
df -h /srv/tothemoon
```

### Проверка логов
```bash
# Логи основного сервиса
sudo journalctl -u tothemoon.service -f

# Логи WebSocket воркера
sudo journalctl -u tothemoon-ws.service -f

# Логи через API
curl "http://localhost:8000/logs/?limit=10" | jq
```

### Проверка данных
```bash
# Количество токенов с компонентами
curl "http://localhost:8000/tokens/?limit=100" | jq '[.items[] | select(.smoothed_components != null)] | length'

# Проверка свежих токенов
curl "http://localhost:8000/tokens/?limit=100" | jq '[.items[] | select(.created_at != null)] | length'
```

## 🎉 Критерии успешного развертывания

### ✅ Технические критерии
- [ ] Сервисы запущены и работают стабильно
- [ ] API возвращает код 200 на /health
- [ ] База данных содержит новые поля
- [ ] Фронтенд загружается без ошибок
- [ ] Миграции применены успешно

### ✅ Функциональные критерии
- [ ] Hybrid Momentum модель активна по умолчанию
- [ ] API возвращает компоненты скоринга
- [ ] Таблица показывает новые колонки
- [ ] Фильтры и сортировка работают
- [ ] Визуальные индикаторы отображаются

### ✅ Пользовательские критерии
- [ ] Дашборд загружается быстро (< 2 сек)
- [ ] Таблица адаптируется к модели
- [ ] Цветовое кодирование понятно
- [ ] Фильтры работают интуитивно
- [ ] Индикаторы свежести помогают

## 📞 Поддержка

### В случае проблем
1. **Проверьте логи**: `sudo journalctl -u tothemoon.service -f`
2. **Проверьте статус**: `sudo systemctl status tothemoon.service`
3. **Проверьте API**: `curl http://localhost:8000/health`
4. **Проверьте конфигурацию**: `/etc/tothemoon.env`

### Документация
- **README.md** - Основная документация
- **MIGRATION_GUIDE.md** - Подробное руководство по миграции
- **API_REFERENCE.md** - Полная документация API
- **TROUBLESHOOTING** - Раздел в README.md

### Откат (если необходимо)
```bash
# Остановка сервисов
sudo systemctl stop tothemoon.service tothemoon-ws.service

# Восстановление БД
sudo -u postgres psql tothemoon < backup_YYYYMMDD_HHMMSS.sql

# Откат кода
cd /srv/tothemoon
sudo -u tothemoon git reset --hard HEAD~1

# Восстановление зависимостей и перезапуск
sudo -u tothemoon venv/bin/pip install -r requirements.txt
cd frontend && sudo -u tothemoon npm ci && sudo -u tothemoon npm run build && cd -
sudo systemctl start tothemoon.service tothemoon-ws.service
```

---

## 🚀 Готов к развертыванию!

Версия 2.0.0 (Hybrid Momentum) готова к развертыванию на продакшен сервере. Следуйте инструкциям выше для безопасного и успешного обновления.

**Удачного деплоя!** 🎯