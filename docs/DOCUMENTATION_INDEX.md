# 📚 Документация проекта Spark Wallet Bot

Центральный индекс всей документации проекта.

---

## 🚀 Быстрый старт

**Новый пользователь?** Читайте в таком порядке:

1. **README.md** - Основная информация о проекте
2. **QUICK_START_AFTER_RESTORE.md** - Быстрый старт после восстановления
3. **PROJECT_ARCHITECTURE.md** - Полная архитектура проекта
4. **MODULE_REFERENCE.md** - Справочник по модулям

---

## 📖 Основная документация

### 🏗️ Архитектура

| Документ | Описание | Размер |
|----------|----------|--------|
| [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) | Полная архитектура проекта, все модули, потоки данных | 23 KB |
| [MODULE_REFERENCE.md](MODULE_REFERENCE.md) | Краткий справочник по всем модулям и функциям | 14 KB |

### 🔧 Интеграции

| Документ | Описание |
|----------|----------|
| [FLASHNET_RESTORE.md](FLASHNET_RESTORE.md) | Восстановление Flashnet AMM из бекапа |
| [UTXO_POOL_API_README.md](../UTXO_POOL_API_README.md) | Документация UTXO.fun API интеграции |
| [WALLET_FEATURES.md](../WALLET_FEATURES.md) | Документация функций кошелька |

### 🧪 Тестирование и отладка

| Документ | Описание |
|----------|----------|
| [QUICK_START_AFTER_RESTORE.md](QUICK_START_AFTER_RESTORE.md) | Быстрый старт, тестирование, отладка ошибок |
| [TESTING_GUIDE.md](../TESTING_GUIDE.md) | Руководство по тестированию |

### 📜 История изменений

| Документ | Описание |
|----------|----------|
| [CLEANUP_SUMMARY.md](../CLEANUP_SUMMARY.md) | История очистки проекта (удалено 90 файлов) |
| [MIGRATION_COMPLETE.md](../MIGRATION_COMPLETE.md) | История миграции функций |

---

## 🔍 Поиск по темам

### Я хочу...

#### ...понять структуру проекта
→ [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) - Раздел "Структура проекта"

#### ...найти конкретную функцию
→ [MODULE_REFERENCE.md](MODULE_REFERENCE.md) - Используйте Ctrl+F

#### ...исправить ошибку
→ [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) - Раздел "Известные проблемы"  
→ [QUICK_START_AFTER_RESTORE.md](QUICK_START_AFTER_RESTORE.md) - Раздел "Ожидаемые ошибки"

#### ...добавить новую функцию
1. [MODULE_REFERENCE.md](MODULE_REFERENCE.md) - Найдите похожий модуль
2. [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) - Изучите поток данных
3. Используйте существующий модуль как шаблон

#### ...настроить Flashnet AMM
→ [FLASHNET_RESTORE.md](FLASHNET_RESTORE.md) - Полное руководство  
→ [QUICK_START_AFTER_RESTORE.md](QUICK_START_AFTER_RESTORE.md) - Раздел "Ошибка 1: Connection Error"

#### ...работать с кошельками
→ [WALLET_FEATURES.md](../WALLET_FEATURES.md) - Все функции кошельков  
→ [MODULE_REFERENCE.md](MODULE_REFERENCE.md) - Раздел "spark_wallet.py"

#### ...интегрировать токены
→ [MODULE_REFERENCE.md](MODULE_REFERENCE.md) - Раздел "token_info.py"  
→ [UTXO_POOL_API_README.md](../UTXO_POOL_API_README.md) - UTXO.fun API

---

## 📊 Документация по модулям

### Основные модули:

| Модуль | Документация | Строк | Статус |
|--------|--------------|-------|--------|
| `telegram_bot.py` | [MODULE_REFERENCE.md](MODULE_REFERENCE.md#telegram_botpy) | 2391 | ✅ Работает |
| `spark_wallet.py` | [MODULE_REFERENCE.md](MODULE_REFERENCE.md#spark_walletpy) | 977 | ✅ Работает |
| `buy_handlers.py` | [MODULE_REFERENCE.md](MODULE_REFERENCE.md#buy_handlerspy) | 20.5 KB | ✅ Работает |
| `buy_handlers_extended.py` | [MODULE_REFERENCE.md](MODULE_REFERENCE.md#buy_handlers_extendedpy) | 14.8 KB | ✅ Работает |
| `flashnet_integration.py` | [FLASHNET_RESTORE.md](FLASHNET_RESTORE.md) | - | ⚠️ Требует настройки |
| `utxo_pool_api.py` | [UTXO_POOL_API_README.md](../UTXO_POOL_API_README.md) | - | ✅ Работает |

---

## 🔗 Быстрые ссылки

### Частые задачи:

**Запуск бота:**
```powershell
python telegram_bot.py
```
→ [README.md](../README.md) - Инструкции по запуску

**Тестирование:**
```powershell
python test_integration.py
python test_utxo_browser.py
```
→ [TESTING_GUIDE.md](../TESTING_GUIDE.md)

**Конфигурация:**
- `.env` файл - API ключи и токены
- `wallets.json` - База данных кошельков

→ [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md#конфигурация)

**Ошибки:**
- 403 Forbidden (Flashnet) → [FLASHNET_RESTORE.md](FLASHNET_RESTORE.md)
- NotImplementedError (Spark Money) → [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md#2-spark-money-notimplementederror)
- TxID = N/A → Исправлено ✅

---

## 📝 Структура документов

### PROJECT_ARCHITECTURE.md (Полная архитектура)
- 📁 Структура проекта (дерево файлов)
- 🤖 Основные компоненты (13 модулей)
  - telegram_bot.py
  - spark_wallet.py
  - buy_handlers.py
  - buy_handlers_extended.py
  - buy_keyboards.py
  - flashnet_integration.py
  - flashnet_amm_client.py
  - utxo_pool_api.py
  - token_info.py
  - generate_spark_wallet.py
  - bech32m_encoder.py
  - btc_price.py
  - wallets.json
- 🎯 Потоки данных
  - Поток покупки токена (16 шагов)
  - Поток получения баланса
- ⚙️ Конфигурация (.env)
- 🚀 Запуск и тестирование
- 🔍 Текущий статус модулей
- 🐛 Известные проблемы и решения

### MODULE_REFERENCE.md (Справочник)
- 📱 Основные модули бота
  - telegram_bot.py - команды и обработчики
  - spark_wallet.py - менеджер кошельков
- 💰 Модули покупки
  - buy_handlers.py - UI flow
  - buy_handlers_extended.py - расширенные функции
  - buy_keyboards.py - клавиатуры
- 🔌 Интеграции
  - flashnet_integration.py
  - flashnet_amm_client.py
  - utxo_pool_api.py
  - token_info.py
- 🔧 Утилиты
  - generate_spark_wallet.py
  - bech32m_encoder.py
  - btc_price.py
- 📈 Потоки данных (с примерами)
- 🔍 Быстрый поиск проблем
- 📝 Быстрые команды

### FLASHNET_RESTORE.md (Восстановление Flashnet)
- 📋 Что было сделано
  - Восстановлено 6 модулей
  - Изменения в spark_wallet.py
  - Изменения в telegram_bot.py
  - Изменения в buy_handlers_extended.py
- ⚠️ Реальные ошибки
  - Примеры с решениями
- 💡 Как исправлять
  - Flashnet 403 Forbidden
  - Pool not found
  - NotImplementedError
- 📝 Следующие шаги
  - 3 опции включения реальных транзакций

### QUICK_START_AFTER_RESTORE.md (Быстрый старт)
- ✅ Что сделано
- 🧪 Как протестировать (5 шагов)
- ⚠️ Ожидаемые ошибки (4 типа)
- 📝 Где смотреть ошибки
- 🔧 Файлы для настройки
- 💡 Советы по отладке
- 🆘 Если ничего не работает (План Б и В)

---

## 🎓 Обучающие материалы

### Для новичков:

1. **День 1:** Прочитайте README.md
2. **День 2:** Изучите PROJECT_ARCHITECTURE.md (раздел "Структура проекта")
3. **День 3:** Запустите бота, попробуйте создать кошелек
4. **День 4:** Попробуйте /buy, изучите ошибки
5. **День 5:** Читайте MODULE_REFERENCE.md по мере необходимости

### Для разработчиков:

1. **PROJECT_ARCHITECTURE.md** - Понимание архитектуры
2. **MODULE_REFERENCE.md** - Справочник API
3. **Исходный код** - Изучите реализацию
4. **Тесты** - Примеры использования

---

## 🆘 Получение помощи

### Последовательность действий:

1. **Проверьте документацию:**
   - [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) - "Известные проблемы"
   - [QUICK_START_AFTER_RESTORE.md](QUICK_START_AFTER_RESTORE.md) - "Ожидаемые ошибки"

2. **Найдите модуль:**
   - [MODULE_REFERENCE.md](MODULE_REFERENCE.md) - Используйте поиск (Ctrl+F)

3. **Изучите поток данных:**
   - [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) - "Потоки данных"

4. **Проверьте логи:**
   ```powershell
   Get-Content bot_error.log -Tail 20
   ```

5. **Проверьте терминал:**
   - Смотрите вывод при запуске `python telegram_bot.py`

---

## 📅 История обновлений

- **6 ноября 2025** - Создана полная документация
  - PROJECT_ARCHITECTURE.md
  - MODULE_REFERENCE.md
  - DOCUMENTATION_INDEX.md (этот файл)

- **6 ноября 2025** - Восстановлен Flashnet AMM
  - FLASHNET_RESTORE.md
  - QUICK_START_AFTER_RESTORE.md

- **5 ноября 2025** - Удалены моковые данные
  - Все исправлено для показа реальных ошибок

---

## 🔖 Полезные команды

### Навигация по документации:

```powershell
# Открыть документацию в VS Code
code docs/PROJECT_ARCHITECTURE.md
code docs/MODULE_REFERENCE.md

# Поиск в документации
Select-String -Path "docs/*.md" -Pattern "your_search_term"
```

### Работа с ботом:

```powershell
# Запуск
python telegram_bot.py

# Тесты
python test_integration.py
python test_utxo_browser.py

# Логи
Get-Content bot_error.log -Tail 20
Get-Content bot_output.log -Tail 20
```

---

**Последнее обновление:** 6 ноября 2025  
**Версия:** 1.0  
**Статус:** Production Ready (с реальными ошибками для отладки)
