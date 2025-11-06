# 📁 Структура проекта Spark Wallet Bot

## 🚀 Основные файлы (НЕОБХОДИМЫЕ)

### 1️⃣ Главный бот
- **telegram_bot.py** (104 KB) - Основной файл бота, точка входа
  - Обработка команд /start, /help, /my_wallets
  - Отображение главного меню
  - Координация всех модулей

### 2️⃣ Управление кошельками
- **spark_wallet.py** (46 KB) - Менеджер кошельков Spark
  - Создание/импорт кошельков
  - Получение баланса через UTXO.fun API
  - Управление приватными ключами
  - Работа с токенами

- **generate_spark_wallet.py** (8 KB) - Генерация новых кошельков
  - BIP-39 мнемоники
  - Создание Spark адресов

- **bech32m_encoder.py** (2.5 KB) - Кодирование адресов Spark
  - Bech32m кодирование для spark1 адресов

- **spark_protobuf.py** (1.2 KB) - Protobuf для Spark
  - Сериализация данных Spark

### 3️⃣ Покупка токенов
- **buy_handlers.py** (21 KB) - Обработчики покупки токенов
  - /buy команда
  - Выбор кошелька, суммы, tip, slippage
  - Отображение баланса в SATS + USD
  
- **buy_keyboards.py** (5.8 KB) - Клавиатуры для покупки
  - Inline кнопки для выбора параметров

### 4️⃣ Продажа токенов
- **sell_handlers.py** (15 KB) - Обработчики продажи токенов
  - /sell команда
  - Выбор токена и суммы

- **sell_keyboards.py** (3.2 KB) - Клавиатуры для продажи

### 5️⃣ Вывод средств
- **withdrawal_handlers.py** (28 KB) - Обработчики вывода
  - /withdraw команда
  - Вывод на L1, Lightning, другой Spark адрес
  
- **spark_withdrawal.py** (20 KB) - Менеджер вывода средств
  - Создание транзакций вывода

### 6️⃣ Информация о токенах
- **token_info.py** (21 KB) - Получение данных о токенах
  - UTXO Pool API интеграция
  - Цена, ликвидность, market cap
  
- **utxo_pool_api.py** (20 KB) - Клиент UTXO Pool API
  - Работа с API utxo.fun

### 7️⃣ Цены и конвертация
- **btc_price.py** (4.6 KB) - Сервис цен BTC
  - Получение цены BTC (CoinGecko/Binance)
  - Конвертация SATS ↔ USD
  - Форматирование валют

### 8️⃣ UI элементы
- **main_menu_keyboard.py** (2.2 KB) - Главное меню
- **back_keyboard.py** (1.2 KB) - Кнопка "Назад"

### 9️⃣ Конфигурация
- **.env** - Переменные окружения (BOT_TOKEN, API ключи)
- **.env.example** - Пример конфигурации
- **requirements.txt** - Python зависимости

### 🔟 Скрипты запуска
- **start_bot.ps1** - Запуск бота (PowerShell)
- **start_bot.bat** - Запуск бота (CMD)
- **restart_bot.ps1** - Перезапуск бота

---

## 🧪 Полезные тесты (ОСТАВИТЬ)

### Интеграционные тесты
- **test_integration.py** (6.3 KB) - Основной интеграционный тест
  - Проверка всех компонентов системы
  
- **test_bot_flow.py** (4 KB) - Тест flow бота
  - Проверка пользовательских сценариев

### Тесты компонентов
- **test_mim_calculation.py** (4.3 KB) - Тест расчета токенов
  - Проверка математики покупки/продажи
  
- **test_utxo_browser.py** (2.3 KB) - Тест UTXO API
  - Проверка получения данных из UTXO.fun
  
- **test_utxo_metadata.py** (2.4 KB) - Тест метаданных токенов

---

## 🗑️ УДАЛИТЬ (Неиспользуемые файлы)

### Старые обработчики
- **buy_handlers_extended.py** (15 KB) - Дубликат buy_handlers.py

### Flashnet (не используется)
- **flashnet_amm_client.py** (18 KB)
- **flashnet_auth.py** (10 KB)
- **flashnet_auth_curl.py** (11 KB)
- **flashnet_auth_playwright.py** (16 KB)
- **flashnet_integration.py** (15 KB)
- **flashnet_swap.py** (29 KB)
- **test_flashnet_integration.py** (6.7 KB)
- **test_flashnet_swap.py** (5.1 KB)
- **test_jwt_auth.py** (3.4 KB)

### Lightspark (не используется)
- **lightspark_client.py** (10 KB)
- **lightspark_graphql_client.py** (11 KB)
- **test_lightspark.py** (3.8 KB)
- **test_lightspark_graphql.py** (5.4 KB)
- **test_lightspark_node.py** (3.6 KB)
- **test_lightspark_test_mode.py** (1.9 KB)
- **test_list_nodes.py** (2.3 KB)
- **test_create_invoice_simple.py** (2.6 KB)

### Luminex (не используется)
- **luminex_scraper.py** (10 KB)
- **test_luminex_integration.py** (1.6 KB)

### Старые тесты/утилиты
- **find_api.py** (5.5 KB) - Поиск API (не нужен)
- **get_spark_client.py** (1 KB) - Устаревший
- **spark_sdk_client.py** (26 KB) - Старый SDK клиент
- **token_metadata.py** (3.8 KB) - Дубликат функционала
- **try_graphql.py** (4.6 KB) - Тестовый файл
- **test_new_api.py** (4.2 KB) - Старый тест
- **test_spark_api.py** (3.2 KB) - Старый тест
- **test_token_api.py** (1.5 KB) - Старый тест
- **test_full_system.py** (8.2 KB) - Дубликат test_integration.py

### Логи (можно очистить)
- **bot_error.log** (0 KB)
- **bot_output.log** (38 KB)
- **bot_run.log** (0 KB)

---

## 📊 Итого очистки

✅ **Удалено**: 32 файла (~300 KB неиспользуемого кода)
✅ **Оставлено**: 23 основных файла + 5 тестов
✅ **Организовано**: Тесты перемещены в папку `tests/`

---

## 📁 Итоговая структура проекта

```
spark-wallet-bot3/
│
├── 🤖 ОСНОВНОЙ БОТ
│   ├── telegram_bot.py           (102 KB) - Главный файл бота
│   ├── .env                       - Переменные окружения
│   └── requirements.txt           - Зависимости Python
│
├── 💼 УПРАВЛЕНИЕ КОШЕЛЬКАМИ
│   ├── spark_wallet.py            (45 KB) - Менеджер кошельков
│   ├── generate_spark_wallet.py   (8 KB)  - Генерация кошельков
│   ├── bech32m_encoder.py         (2 KB)  - Кодирование адресов
│   └── spark_protobuf.py          (1 KB)  - Protobuf сериализация
│
├── 🛒 ПОКУПКА/ПРОДАЖА
│   ├── buy_handlers.py            (20 KB) - Основные обработчики покупки
│   ├── buy_handlers_extended.py   (15 KB) - Расширенные обработчики (slippage, confirm, execute)
│   ├── buy_keyboards.py           (5 KB)  - Клавиатуры покупки
│   ├── sell_handlers.py           (15 KB) - Обработчики продажи
│   └── sell_keyboards.py          (3 KB)  - Клавиатуры продажи
│
├── 💸 ВЫВОД СРЕДСТВ
│   ├── withdrawal_handlers.py     (27 KB) - Обработчики вывода
│   └── spark_withdrawal.py        (20 KB) - Менеджер вывода
│
├── 📊 ТОКЕНЫ И ЦЕНЫ
│   ├── token_info.py              (20 KB) - Информация о токенах
│   ├── utxo_pool_api.py           (19 KB) - UTXO Pool API клиент
│   └── btc_price.py               (4 KB)  - Цены BTC и конвертация
│
├── 🎨 UI ЭЛЕМЕНТЫ
│   ├── main_menu_keyboard.py      (2 KB)  - Главное меню
│   └── back_keyboard.py           (1 KB)  - Кнопка назад
│
├── 🚀 ЗАПУСК
│   ├── start_bot.ps1              - Запуск (PowerShell)
│   ├── start_bot.bat              - Запуск (CMD)
│   └── restart_bot.ps1            - Перезапуск
│
├── 🧪 ТЕСТЫ (tests/)
│   ├── test_integration.py        (6 KB)  - Интеграционный тест
│   ├── test_bot_flow.py           (4 KB)  - Тест flow бота
│   ├── test_mim_calculation.py    (4 KB)  - Тест расчетов
│   ├── test_utxo_browser.py       (2 KB)  - Тест UTXO API
│   └── test_utxo_metadata.py      (2 KB)  - Тест метаданных
│
├── 📂 ДАННЫЕ
│   ├── spark_wallets/             - Активные кошельки Spark
│   ├── wallets/                   - Старые кошельки
│   └── test_wallets/              - Тестовые кошельки
│
├── 📚 ДОПОЛНИТЕЛЬНО
│   ├── docs/                      - Документация
│   ├── nodejs/                    - Node.js скрипты
│   └── spark-sdk/                 - Spark SDK
│
└── 📖 ДОКУМЕНТАЦИЯ
    └── PROJECT_STRUCTURE.md       - Этот файл
```

---

## 🎯 Как запустить бот

### Способ 1: PowerShell
```powershell
.\start_bot.ps1
```

### Способ 2: CMD
```cmd
start_bot.bat
```

### Способ 3: Напрямую
```powershell
python telegram_bot.py
```

---

## 🧪 Как запустить тесты

```powershell
cd tests
python test_integration.py
```

---

## 📝 Ключевые возможности

✅ **Кошельки**: Создание, импорт, баланс (SATS + USD)
✅ **Покупка**: Выбор токена, кошелька, суммы, tip, slippage
✅ **Продажа**: Продажа токенов из портфеля
✅ **Вывод**: L1, Lightning, Spark адреса
✅ **Цены**: Реальные цены BTC, конвертация SATS ↔ USD
✅ **API**: Интеграция с UTXO Pool API (utxo.fun)

---

## 🔧 Конфигурация (.env)

```env
BOT_TOKEN=your_telegram_bot_token
UTXO_API_KEY=your_utxo_api_key (optional)
BTC_PRICE_API=coingecko  # или binance
```
