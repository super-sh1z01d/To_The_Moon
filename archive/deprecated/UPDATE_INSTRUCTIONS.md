# 🔄 Инструкции по обновлению - Parameter Cleanup

**Версия**: 2.0.0 - Parameter Cleanup  
**Дата**: $(date)  
**Для**: Работающих приложений To The Moon

## 🎯 Что изменится

- ❌ Поле "Максимальное изменение цены (%)" исчезнет из настроек
- ✅ Все поля настроек получат подробные описания с префиксом "Что это:"
- ✅ Улучшенный UX - более понятные подсказки для каждого параметра
- ✅ Все остальные функции работают как прежде
- ✅ Никаких breaking changes
- ✅ Производительность не изменится

## ⚡ Быстрое обновление (30 секунд)

**Для большинства случаев - рекомендуется:**

```bash
# На сервере, в директории приложения
bash scripts/quick_update.sh
```

**Что делает:**
- Обновляет код из Git
- Пересобирает фронтенд
- Перезапускает только работающие сервисы
- Проверяет работоспособность

## 🔧 Полное обновление (2 минуты)

**Если нужно обновить зависимости или есть проблемы:**

```bash
# На сервере, в директории приложения
sudo bash scripts/deploy_parameter_cleanup.sh
```

**Что делает:**
- Создает резервную копию
- Обновляет код и зависимости
- Применяет миграции БД
- Пересобирает фронтенд
- Перезапускает все сервисы
- Проводит полную проверку

## 📋 Пошаговая инструкция

### 1. Подключение к серверу
```bash
ssh your-user@your-server.com
```

### 2. Переход в директорию приложения
```bash
# Найдите где установлено приложение:
cd /opt/to_the_moon        # Обычное расположение
# или
cd /srv/tothemoon          # Альтернативное расположение  
# или
cd /home/ubuntu/to_the_moon # Пользовательская установка
```

### 3. Проверка текущего состояния
```bash
# Проверьте что работает
sudo systemctl status to-the-moon
sudo systemctl status to-the-moon-worker

# Проверьте версию
git log --oneline -1
```

### 4. Выполнение обновления
```bash
# Быстрое обновление (рекомендуется)
bash scripts/quick_update.sh

# ИЛИ полное обновление (если нужно)
sudo bash scripts/deploy_parameter_cleanup.sh
```

### 5. Проверка результата
```bash
# Проверьте статус сервисов
sudo systemctl status to-the-moon
sudo systemctl status to-the-moon-worker

# Проверьте здоровье приложения
curl http://localhost:8000/health

# Проверьте логи (не должно быть ошибок)
sudo journalctl -u to-the-moon --since "2 minutes ago"
```

### 6. Проверка UI
- Откройте веб-интерфейс: `http://your-server:8000`
- Перейдите в Settings
- Убедитесь что:
  - ❌ Поля "Максимальное изменение цены (%)" больше нет
  - ✅ Все поля имеют подробные описания с "Что это:"
  - ✅ При наведении на поля показываются подсказки

## 🚨 Если что-то пошло не так

### Быстрый откат (quick_update)
```bash
# Восстановите файлы из бэкапа (показан в выводе скрипта)
cp -r /tmp/to_the_moon_backup_*/src/* src/
cp -r /tmp/to_the_moon_backup_*/frontend_src/* frontend/src/
cd frontend && npm run build && cd ..
sudo systemctl restart to-the-moon
```

### Полный откат (deploy_parameter_cleanup)
```bash
# Остановите сервисы
sudo systemctl stop to-the-moon to-the-moon-worker

# Восстановите из бэкапа (путь показан в выводе скрипта)
sudo rm -rf /opt/to_the_moon
sudo mv /opt/to_the_moon_backup_* /opt/to_the_moon

# Запустите сервисы
sudo systemctl start to-the-moon
sudo systemctl start to-the-moon-worker
```

## 📊 Мониторинг после обновления

### Проверьте в течение 10 минут:
```bash
# Логи основного сервиса
sudo journalctl -u to-the-moon -f

# Логи воркера
sudo journalctl -u to-the-moon-worker -f

# Использование ресурсов
htop

# Здоровье приложения
watch -n 5 'curl -s http://localhost:8000/health'
```

### Ключевые метрики:
- ✅ Сервисы запущены и активны
- ✅ Нет ошибок в логах
- ✅ HTTP health check проходит
- ✅ Память и CPU в норме
- ✅ Settings UI загружается без поля max_price_change_5m

## 📞 Поддержка

### Если нужна помощь:
1. Проверьте логи: `sudo journalctl -u to-the-moon --since "10 minutes ago"`
2. Проверьте статус: `sudo systemctl status to-the-moon`
3. Используйте план отката выше
4. Проверьте документацию: `DEPLOYMENT_CHECKLIST.md`

### Полезные команды:
```bash
# Перезапуск сервисов
sudo systemctl restart to-the-moon
sudo systemctl restart to-the-moon-worker

# Проверка конфигурации
python3 -c "from src.domain.settings.defaults import DEFAULT_SETTINGS; print('OK')"

# Проверка фронтенда
cd frontend && npm run build
```

---

## ✅ Ожидаемый результат

После успешного обновления:
- 🔧 Поле "Максимальное изменение цены (%)" исчезнет из настроек
- 📝 Все поля получат подробные описания с "Что это:"
- 💡 Улучшенный UX - более понятные подсказки для пользователей
- 📊 Hybrid Momentum скоринг продолжит работать как прежде
- 🔄 Legacy скоринг продолжит работать как прежде
- 📈 Никаких изменений в производительности
- 🎯 Более чистый и понятный интерфейс настроек

**Время обновления**: 30 секунд - 2 минуты  
**Риск**: Минимальный (только удаление неиспользуемого параметра)  
**Откат**: Простой и быстрый