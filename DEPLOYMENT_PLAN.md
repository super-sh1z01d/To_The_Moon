# Deployment Plan - Version 2.0.0 (Hybrid Momentum)

**Дата**: 17 сентября 2025  
**Версия**: 2.0.0  
**Кодовое имя**: Hybrid Momentum  

## 🎯 Цель деплоя

Развертывание версии 2.0.0 с новой моделью скоринга "Hybrid Momentum" и улучшенным дашбордом.

## 📋 Предварительная проверка

### Локальная проверка
- [x] Все тесты проходят
- [x] Фронтенд собирается без ошибок
- [x] API работает корректно
- [x] База данных готова к миграции
- [x] Документация обновлена

### Подготовка к деплою
```bash
# 1. Проверка статуса
git status

# 2. Добавление всех изменений
git add .

# 3. Коммит изменений
git commit -m "feat: Hybrid Momentum v2.0.0 - Advanced scoring model with enhanced dashboard

- NEW: Hybrid Momentum scoring model with 4 components (TX, Vol, Fresh, OI)
- NEW: EWMA smoothing for score stability
- NEW: Enhanced dashboard with component visualization
- NEW: Advanced filtering and sorting capabilities
- NEW: Visual indicators and color coding
- IMPROVED: API with component breakdown support
- IMPROVED: Table optimization (removed redundant columns)
- ADDED: Comprehensive documentation suite
- ADDED: Migration guide and deployment instructions
- TESTED: 27+ unit tests with full coverage"

# 4. Пуш на сервер
git push origin main
```

## 🚀 План развертывания

### Этап 1: Подготовка сервера
```bash
# Подключение к серверу
ssh user@your-server.com

# Переход в директорию приложения
cd /srv/tothemoon

# Создание бэкапа
sudo -u tothemoon bash -c "
  # Бэкап базы данных
  pg_dump tothemoon > backup_$(date +%Y%m%d_%H%M%S).sql
  
  # Бэкап конфигурации
  cp /etc/tothemoon.env /etc/tothemoon.env.backup
  
  # Бэкап приложения
  tar -czf tothemoon_backup_$(date +%Y%m%d_%H%M%S).tar.gz .
"
```

### Этап 2: Обновление кода
```bash
# Автоматическое обновление через deploy script
sudo bash scripts/deploy.sh
```

**Что произойдет:**
1. Git pull последних изменений
2. Обновление Python зависимостей
3. Применение миграций базы данных
4. Сборка фронтенда
5. Перезапуск сервисов
6. Проверка работоспособности

### Этап 3: Проверка развертывания
```bash
# Проверка статуса сервисов
sudo systemctl status tothemoon.service
sudo systemctl status tothemoon-ws.service

# Проверка здоровья API
curl http://localhost:8000/health

# Проверка активной модели
curl http://localhost:8000/settings/scoring_model_active

# Проверка новых полей API
curl "http://localhost:8000/tokens/?limit=1" | jq '.items[0] | {score, raw_components, smoothed_components, scoring_model}'
```

## 🔧 Изменения в системе

### База данных
**Новые поля в `token_scores`:**
- `raw_components` (JSON) - Сырые значения компонентов
- `smoothed_components` (JSON) - Сглаженные значения компонентов  
- `scoring_model` (VARCHAR) - Используемая модель скоринга

**Миграция:** Автоматическая через Alembic

### API изменения
**Новые поля в ответах:**
- `raw_components` - Детализация компонентов
- `smoothed_components` - Сглаженные компоненты
- `scoring_model` - Активная модель
- `created_at` - Время создания токена

**Новые настройки:**
- `scoring_model_active` - Активная модель скоринга
- `w_tx`, `w_vol`, `w_fresh`, `w_oi` - Веса компонентов
- `ewma_alpha` - Параметр сглаживания
- `freshness_threshold_hours` - Порог свежести

### Фронтенд изменения
**Новые компоненты:**
- `ScoreCell` - Визуализация скора с компонентами
- `ComponentsCell` - Отображение отдельных компонентов
- `AgeCell` - Возраст токена с индикатором свежести

**Новая функциональность:**
- Адаптивная таблица (показывает колонки в зависимости от модели)
- Фильтр "Только свежие" токены
- Сортировка по компонентам (TX, Vol, Fresh, OI)
- Цветовое кодирование скоров
- Индикаторы свежести 🆕

**Удаленные колонки:**
- "Δ 5м / 15м" - изменения цены
- "Транз. 5м" - количество транзакций

## ⚠️ Критические моменты

### Обратная совместимость
- ✅ **API**: Полная обратная совместимость
- ✅ **База данных**: Существующие данные сохраняются
- ✅ **Конфигурация**: Старые настройки работают
- ✅ **Legacy модель**: Поддерживается параллельно

### Потенциальные проблемы
1. **Миграция БД**: Может занять время на больших объемах данных
2. **Сборка фронтенда**: Требует Node.js и npm
3. **Новые зависимости**: Все уже в requirements.txt
4. **Настройки**: Новые настройки имеют разумные дефолты

### План отката (если нужен)
```bash
# 1. Остановка сервисов
sudo systemctl stop tothemoon.service tothemoon-ws.service

# 2. Восстановление базы данных
psql tothemoon < backup_YYYYMMDD_HHMMSS.sql

# 3. Восстановление конфигурации
sudo cp /etc/tothemoon.env.backup /etc/tothemoon.env

# 4. Откат кода
cd /srv/tothemoon
sudo -u tothemoon git reset --hard HEAD~1

# 5. Восстановление зависимостей
sudo -u tothemoon venv/bin/pip install -r requirements.txt

# 6. Пересборка фронтенда
cd frontend && sudo -u tothemoon npm ci && sudo -u tothemoon npm run build && cd -

# 7. Запуск сервисов
sudo systemctl start tothemoon.service tothemoon-ws.service
```

## 📊 Ожидаемые результаты

### Производительность
- **API**: Без деградации производительности
- **Фронтенд**: Улучшение за счет оптимизации таблицы
- **База данных**: Минимальное увеличение размера (~200 байт на запись)

### Функциональность
- **Скоринг**: Более точная оценка с 4 компонентами
- **Стабильность**: EWMA сглаживание уменьшает волатильность
- **Аналитика**: Детализация компонентов для анализа
- **UX**: Улучшенный интерфейс с визуальными индикаторами

### Мониторинг
- **Логи**: Новые события компонентного скоринга
- **Метрики**: Время расчета компонентов
- **Ошибки**: Улучшенная обработка граничных случаев

## 🎯 Критерии успеха

### Технические
- [ ] Сервисы запускаются без ошибок
- [ ] API возвращает новые поля
- [ ] Фронтенд отображает компоненты
- [ ] Миграция БД завершена успешно
- [ ] Все тесты проходят

### Функциональные
- [ ] Hybrid Momentum модель активна по умолчанию
- [ ] Компоненты рассчитываются корректно
- [ ] Фильтрация и сортировка работают
- [ ] Визуальные индикаторы отображаются
- [ ] Переключение моделей через API

### Пользовательские
- [ ] Дашборд загружается быстро
- [ ] Таблица адаптируется к модели
- [ ] Фильтры работают интуитивно
- [ ] Цветовое кодирование понятно
- [ ] Индикаторы свежести помогают

## 📞 Контакты и поддержка

### В случае проблем
1. **Проверить логи**: `sudo journalctl -u tothemoon.service -f`
2. **Проверить статус**: `sudo systemctl status tothemoon.service`
3. **Проверить API**: `curl http://localhost:8000/health`
4. **Проверить БД**: Подключение и миграции

### Документация
- **README.md** - Основная документация
- **MIGRATION_GUIDE.md** - Руководство по миграции
- **API_REFERENCE.md** - Документация API
- **TROUBLESHOOTING** - В README.md

## ✅ Чек-лист деплоя

### Перед деплоем
- [ ] Код протестирован локально
- [ ] Документация обновлена
- [ ] Бэкапы созданы
- [ ] План отката готов

### Во время деплоя
- [ ] Git push выполнен
- [ ] Deploy script запущен
- [ ] Миграции применены
- [ ] Сервисы перезапущены

### После деплоя
- [ ] Health check прошел
- [ ] API работает корректно
- [ ] Фронтенд загружается
- [ ] Новая функциональность доступна
- [ ] Логи не показывают ошибок

---

**Готов к развертыванию!** 🚀

Этот план обеспечивает безопасное и контролируемое обновление до версии 2.0.0 с минимальным риском и максимальной функциональностью.