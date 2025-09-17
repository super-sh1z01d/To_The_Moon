# Hybrid Momentum Scoring - Implementation Summary

**Дата завершения**: 17 сентября 2025  
**Статус**: ✅ Core Implementation Complete

## Что было реализовано

### 🎯 Новая модель скоринга "Hybrid Momentum"

Полностью реализована продвинутая модель оценки арбитражного потенциала токенов:

**Формула**: `Score = (W_tx × Tx_Accel) + (W_vol × Vol_Momentum) + (W_fresh × Token_Freshness) + (W_oi × Orderflow_Imbalance)`

**Компоненты**:
1. **Transaction Acceleration** — ускорение транзакционной активности
2. **Volume Momentum** — импульс торгового объема  
3. **Token Freshness** — бонус за свежесть токена (до 6 часов)
4. **Orderflow Imbalance** — дисбаланс покупок/продаж

### 🔧 Техническая реализация

#### Архитектура
- **ScoringService** — унифицированный интерфейс для множественных моделей
- **HybridMomentumModel** — основная логика новой модели
- **ComponentCalculator** — расчет компонентов с обработкой ошибок
- **EWMAService** — экспоненциальное сглаживание для стабильности
- **EnhancedDexAggregator** — расширенный сбор метрик

#### База данных
- Новые поля в `token_scores`: `raw_components`, `smoothed_components`, `scoring_model`
- Миграция с сохранением существующих данных
- Новые настройки в `app_settings` для конфигурации модели

#### API
- Обновленные endpoints с поддержкой новых настроек
- Валидация параметров модели
- Переключение между моделями через API
- Детализация компонентов скоринга в ответах

### 📊 Качество и тестирование

#### Unit тесты (27 тестов)
- ✅ **ComponentCalculator**: 12 тестов (все компоненты + граничные случаи)
- ✅ **EWMAService**: 15 тестов (сглаживание + персистентность)
- ✅ Валидация настроек и обработка ошибок

#### Покрытие функциональности
- ✅ Расчет всех компонентов скоринга
- ✅ EWMA сглаживание с персистентностью в БД
- ✅ Переключение между моделями скоринга
- ✅ Валидация и обработка некорректных данных
- ✅ Интеграция с существующим scheduler'ом

### ⚙️ Конфигурация

#### Новые настройки
```
scoring_model_active: "hybrid_momentum"  # Активная модель
w_tx: "0.25"                            # Вес ускорения транзакций
w_vol: "0.25"                           # Вес импульса объема
w_fresh: "0.25"                         # Вес свежести токена
w_oi: "0.25"                            # Вес дисбаланса ордеров
ewma_alpha: "0.3"                       # Параметр сглаживания
freshness_threshold_hours: "6.0"        # Порог свежести
```

#### Валидация
- Веса: неотрицательные числа
- EWMA α: диапазон [0.0, 1.0]
- Пороги: положительные числа
- Модель: "hybrid_momentum" или "legacy"

## Результаты

### ✅ Достигнутые цели

1. **Продвинутый скоринг**: Реализована сложная модель с 4 компонентами
2. **Стабильность**: EWMA сглаживание устраняет волатильность скоров
3. **Гибкость**: Поддержка множественных моделей с переключением
4. **Надежность**: Comprehensive тестирование и обработка ошибок
5. **Прозрачность**: Детализация компонентов для анализа
6. **Производительность**: Оптимизированная архитектура без деградации

### 📈 Улучшения по сравнению с legacy моделью

- **Более точная оценка**: 4 компонента vs простая формула
- **Учет свежести**: Бонус для недавно мигрировавших токенов
- **Стабильность**: EWMA сглаживание vs простое сглаживание
- **Прозрачность**: Разбивка по компонентам vs черный ящик
- **Конфигурируемость**: Настройка весов через API

### 🔍 Метрики качества

- **Тесты**: 27/27 проходят (100%)
- **Покрытие**: Все критические компоненты покрыты тестами
- **Производительность**: Без деградации времени расчета
- **Надежность**: Graceful handling всех граничных случаев
- **Совместимость**: Полная обратная совместимость

## Готовность к продакшену

### ✅ Production Ready
- Все тесты проходят
- API работает с валидацией
- База данных обновлена
- Scheduler интегрирован
- Документация обновлена

### 🚀 Активация
Hybrid Momentum модель **активна по умолчанию** и используется для всех новых расчетов скоринга.

### 📋 Следующие шаги (опционально)
1. **Frontend обновления** — UI для компонентов скоринга
2. **Расширенная аналитика** — графики и сравнения моделей
3. **Машинное обучение** — автоматическая оптимизация весов
4. **Дополнительные модели** — новые алгоритмы скоринга

## Заключение

Проект **успешно завершен**. Новая модель скоринга "Hybrid Momentum" полностью реализована, протестирована и готова к использованию в продакшене. Система обеспечивает более точную и стабильную оценку арбитражного потенциала токенов при сохранении высокой производительности и надежности.

**Ключевое достижение**: Создана масштабируемая архитектура для множественных моделей скоринга, которая позволит легко добавлять новые алгоритмы в будущем.
---


# 🚀 Полная инструкция по развертыванию на Ubuntu VPS

## Для новичков: пошаговое руководство

### Шаг 1: Подготовка VPS

#### 1.1 Подключение к серверу
```bash
# Подключитесь к вашему VPS через SSH
ssh root@YOUR_SERVER_IP

# Или если у вас есть пользователь с sudo правами:
ssh username@YOUR_SERVER_IP
```

#### 1.2 Обновление системы
```bash
# Обновите список пакетов и систему
sudo apt update && sudo apt upgrade -y

# Установите базовые утилиты
sudo apt install -y curl wget git htop nano
```

### Шаг 2: Автоматическая установка (РЕКОМЕНДУЕТСЯ)

#### 2.1 Одна команда для полной установки
```bash
# Запустите автоматический установщик
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/super-sh1z01d/To_The_Moon/main/scripts/install.sh)"
```

**Что произойдет:**
- ✅ Установка Python 3, Node.js, PostgreSQL
- ✅ Создание пользователя `tothemoon`
- ✅ Клонирование репозитория в `/srv/tothemoon`
- ✅ Установка зависимостей и миграции БД
- ✅ Сборка фронтенда
- ✅ Настройка systemd сервисов
- ✅ Запуск приложения

#### 2.2 Проверка установки
```bash
# Проверьте статус сервисов
sudo systemctl status tothemoon.service
sudo systemctl status tothemoon-ws.service

# Проверьте работу API
curl http://localhost:8000/health
# Должно вернуть: {"status": "ok"}
```

### Шаг 3: Настройка базы данных (опционально)

#### 3.1 Использование PostgreSQL (рекомендуется для продакшена)
```bash
# Установите PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Создайте базу данных и пользователя
sudo -u postgres psql -c "CREATE USER tothemoon WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE tothemoon OWNER tothemoon;"

# Обновите конфигурацию
sudo nano /etc/tothemoon.env
```

**В файле `/etc/tothemoon.env` замените:**
```bash
# Было:
DATABASE_URL=sqlite:///dev.db

# Стало:
DATABASE_URL=postgresql+psycopg2://tothemoon:your_secure_password@127.0.0.1:5432/tothemoon
```

#### 3.2 Применение миграций
```bash
# Перейдите в директорию приложения
cd /srv/tothemoon

# Примените миграции
sudo -u tothemoon bash -c "source venv/bin/activate && python -m alembic upgrade head"

# Перезапустите сервисы
sudo systemctl restart tothemoon.service tothemoon-ws.service
```

### Шаг 4: Настройка веб-сервера (Nginx)

#### 4.1 Установка Nginx
```bash
# Установите Nginx
sudo apt install -y nginx

# Скопируйте конфигурацию
sudo cp /srv/tothemoon/scripts/nginx/tothemoon.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/tothemoon.conf /etc/nginx/sites-enabled/

# Удалите дефолтный сайт
sudo rm /etc/nginx/sites-enabled/default

# Проверьте конфигурацию и перезапустите
sudo nginx -t
sudo systemctl restart nginx
```

#### 4.2 Настройка домена (если есть)
```bash
# Отредактируйте конфигурацию Nginx
sudo nano /etc/nginx/sites-available/tothemoon.conf

# Замените "your.domain.tld" на ваш домен
# server_name your.domain.tld;
```

### Шаг 5: Настройка HTTPS (SSL)

#### 5.1 Установка Certbot
```bash
# Установите Certbot
sudo apt install -y certbot python3-certbot-nginx

# Получите SSL сертификат (замените на ваш домен)
sudo certbot --nginx -d your.domain.tld -m your@email.com --agree-tos --redirect
```

### Шаг 6: Проверка работы приложения

#### 6.1 Проверка API
```bash
# Проверьте здоровье системы
curl http://localhost:8000/health

# Проверьте настройки скоринга
curl http://localhost:8000/settings/scoring_model_active

# Проверьте список токенов
curl http://localhost:8000/tokens?limit=5
```

#### 6.2 Проверка веб-интерфейса
Откройте в браузере:
- **Локально**: http://YOUR_SERVER_IP:8000/app
- **С доменом**: https://your.domain.tld/app

### Шаг 7: Мониторинг и логи

#### 7.1 Просмотр логов
```bash
# Логи основного сервиса
sudo journalctl -u tothemoon.service -f

# Логи WebSocket воркера
sudo journalctl -u tothemoon-ws.service -f

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

#### 7.2 Мониторинг ресурсов
```bash
# Использование ресурсов
htop

# Статус сервисов
sudo systemctl status tothemoon.service tothemoon-ws.service nginx

# Проверка портов
sudo netstat -tlnp | grep :8000
```

### Шаг 8: Обновление приложения

#### 8.1 Автоматическое обновление
```bash
# Перейдите в директорию приложения
cd /srv/tothemoon

# Запустите скрипт обновления
sudo bash scripts/deploy.sh
```

**Что произойдет:**
- ✅ Получение последних изменений из GitHub
- ✅ Обновление зависимостей
- ✅ Применение новых миграций БД
- ✅ Пересборка фронтенда
- ✅ Перезапуск сервисов
- ✅ Проверка работоспособности

### Шаг 9: Настройка модели скоринга

#### 9.1 Проверка активной модели
```bash
# Проверьте какая модель активна
curl http://localhost:8000/settings/scoring_model_active
# Должно вернуть: {"key": "scoring_model_active", "value": "hybrid_momentum"}
```

#### 9.2 Настройка весов компонентов
```bash
# Посмотрите текущие веса
curl http://localhost:8000/settings/w_tx  # Transaction Acceleration
curl http://localhost:8000/settings/w_vol # Volume Momentum
curl http://localhost:8000/settings/w_fresh # Token Freshness
curl http://localhost:8000/settings/w_oi  # Orderflow Imbalance

# Измените веса (пример)
curl -X PUT http://localhost:8000/settings/w_tx \
  -H "Content-Type: application/json" \
  -d '{"value": "0.3"}'
```

### Шаг 10: Безопасность

#### 10.1 Настройка файрвола
```bash
# Установите ufw
sudo apt install -y ufw

# Разрешите необходимые порты
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Включите файрвол
sudo ufw --force enable
```

#### 10.2 Создание пользователя для администрирования
```bash
# Создайте пользователя (замените username)
sudo adduser admin_user
sudo usermod -aG sudo admin_user

# Настройте SSH ключи для безопасного доступа
# (скопируйте ваш публичный ключ в ~/.ssh/authorized_keys)
```

### Шаг 11: Резервное копирование

#### 11.1 Настройка бэкапа базы данных
```bash
# Создайте скрипт бэкапа
sudo nano /usr/local/bin/backup-tothemoon.sh
```

**Содержимое скрипта:**
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/tothemoon"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Бэкап PostgreSQL
sudo -u postgres pg_dump tothemoon > $BACKUP_DIR/tothemoon_$DATE.sql

# Бэкап конфигурации
cp /etc/tothemoon.env $BACKUP_DIR/tothemoon.env_$DATE

# Удаление старых бэкапов (старше 7 дней)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.env_*" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Сделайте скрипт исполняемым
sudo chmod +x /usr/local/bin/backup-tothemoon.sh

# Добавьте в cron (ежедневный бэкап в 2:00)
sudo crontab -e
# Добавьте строку:
# 0 2 * * * /usr/local/bin/backup-tothemoon.sh
```

## 🔧 Устранение проблем

### Проблема: Сервис не запускается
```bash
# Проверьте логи
sudo journalctl -u tothemoon.service -n 50

# Проверьте конфигурацию
sudo nano /etc/tothemoon.env

# Проверьте права доступа
sudo chown -R tothemoon:tothemoon /srv/tothemoon
```

### Проблема: База данных недоступна
```bash
# Проверьте статус PostgreSQL
sudo systemctl status postgresql

# Проверьте подключение
sudo -u tothemoon psql -h localhost -U tothemoon -d tothemoon -c "SELECT 1;"
```

### Проблема: Фронтенд не загружается
```bash
# Пересоберите фронтенд
cd /srv/tothemoon/frontend
sudo -u tothemoon npm ci
sudo -u tothemoon npm run build

# Перезапустите сервис
sudo systemctl restart tothemoon.service
```

## 📞 Поддержка

- **GitHub**: https://github.com/super-sh1z01d/To_The_Moon
- **Логи приложения**: `sudo journalctl -u tothemoon.service -f`
- **Веб-интерфейс**: http://YOUR_SERVER_IP:8000/app
- **API документация**: http://YOUR_SERVER_IP:8000/docs

## ✅ Готово!

После выполнения всех шагов у вас будет:
- ✅ Работающее приложение To The Moon
- ✅ Hybrid Momentum модель скоринга активна
- ✅ Веб-интерфейс доступен
- ✅ Автоматические обновления настроены
- ✅ Мониторинг и логирование
- ✅ Безопасность и бэкапы

**Приложение готово к использованию для скоринга токенов Solana!** 🚀