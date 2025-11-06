# 🔧 Справочник по модулям проекта

Быстрый справочник по всем модулям проекта Spark Wallet Bot.

---

## 📱 Основные модули бота

### `telegram_bot.py` - Главный бот (2391 строк)
**Что делает:** Точка входа, все обработчики команд и callback'ов

**Основные команды:**
- `/start` - Приветствие и главное меню
- `/help` - Помощь
- `/buy` - Купить токен
- `/sell` - Продать токен
- `/wallets` - Мои кошельки
- `/withdraw` - Вывести средства

**Основные обработчики:**
```python
cmd_start()                    # /start
cmd_my_wallets()              # Показать кошельки
cmd_create_wallet()           # Создать кошелек
cmd_buy_new()                 # /buy
handle_buy_callbacks()        # Обработка покупки
  ├─ buy_execute              # Основная покупка
  ├─ buy_execute_flashnet     # Через Flashnet AMM
  ├─ buy_execute_spark        # Через Spark Money (NotImplemented)
  └─ buy_cancel               # Отмена
```

**Глобальные объекты:**
```python
wallet_manager                 # Менеджер кошельков
token_service                  # Сервис токенов
user_data                      # Данные пользователей
positions                      # Позиции (покупки/продажи)
```

---

### `spark_wallet.py` - Менеджер кошельков (977 строк)
**Что делает:** Управление Spark кошельками, балансами, транзакциями

**Класс:** `SparkWalletManager`

**Основные методы:**

#### Создание и управление:
```python
create_wallet(user_id, wallet_name)        # Создать кошелек
get_user_wallets(user_id)                  # Получить все кошельки
get_wallet_by_name(wallet_name)            # Получить по имени
```

#### Балансы:
```python
get_wallet_balance(wallet_address)         # Получить баланс (UTXO API)
get_transaction_history(wallet_address)    # История транзакций
```

#### Покупка токенов:
```python
buy_meme(contract_address, amount_sats, wallet_name, slippage, priority_fee_sats)
    # ✅ РЕАЛЬНАЯ ИНТЕГРАЦИЯ с Flashnet AMM
    # Возвращает: {status, txid, tokens_received, error}
    # Ошибка: 403 Forbidden - нужны API credentials

buy_meme_native(...)
    # ❌ НЕ РЕАЛИЗОВАНО - выбрасывает NotImplementedError
    # Требуется интеграция с Spark Node API
```

#### Продажа:
```python
sell_meme(contract_address, token_amount, wallet_name, slippage)
    # Продажа токена (частично реализовано)
```

#### Вывод:
```python
withdraw_to_lightning(wallet_name, invoice)        # Lightning вывод
withdraw_to_l1(wallet_name, address, amount_sats)  # L1 Bitcoin вывод
```

**Формат данных:**
```python
# Wallet object:
{
    "name": "wallet_471657882_1762366089",
    "address": "spark1pgss8...",
    "private_key": "hex...",
    "mnemonic": "word1 word2 ...",
    "created_at": 1762366089
}
```

---

## 💰 Модули покупки

### `buy_handlers.py` - Основные обработчики (20.5 KB)
**Что делает:** UI flow для покупки токенов

**Функции:**
```python
cmd_buy_new()                          # /buy - начало
handle_token_address_input()           # Ввод адреса токена
handle_buy_wallet_selection()          # Выбор кошелька
handle_buy_amount_selection()          # Выбор суммы
handle_custom_amount_input()           # Кастомная сумма
handle_buy_tip_selection()             # Выбор комиссии
handle_buy_confirmation()              # Подтверждение
```

**UI Flow:**
```
/buy → Токен → Кошелек → Сумма → Tip → Slippage → Подтверждение → Выполнение
```

---

### `buy_handlers_extended.py` - Расширенные функции (14.8 KB)
**Что делает:** Slippage, кастомные значения, финальное выполнение

**Функции:**
```python
handle_buy_set_slippage()              # Открыть меню slippage
handle_slippage_selection()            # Выбор slippage (1-15%)
handle_custom_tip_input()              # Кастомная комиссия
handle_custom_slippage_input()         # Кастомный slippage
handle_buy_confirm()                   # Финальное подтверждение
handle_buy_execute()                   # Выполнение покупки
handle_buy_cancel()                    # Отмена
```

**Важно:**
- ✅ Проверяет `result['status'] == 'success'`
- ✅ Проверяет наличие TxID
- ❌ Выбрасывает Exception при ошибке

---

### `buy_keyboards.py` - Клавиатуры UI (5.7 KB)
**Что делает:** Все клавиатуры для покупки

**Функции:**
```python
create_buy_keyboard()                  # Главная клавиатура
create_wallet_selection_keyboard()     # Выбор кошелька
create_amount_keyboard()               # Выбор суммы
create_tip_keyboard()                  # Выбор комиссии
create_slippage_keyboard()             # Выбор slippage
create_confirmation_keyboard()         # Подтверждение (3 кнопки)
```

---

## 🔌 Интеграции с внешними сервисами

### `flashnet_integration.py` - Flashnet AMM
**Что делает:** Главная интеграция с Flashnet AMM

**Функция:**
```python
execute_buy(wallet_manager, wallet_name, token_address, amount_btc_sats, slippage_pct)
    # 1. Получает данные кошелька
    # 2. Создает FlashnetAMMClient
    # 3. Аутентифицируется
    # 4. Получает quote (цену)
    # 5. Выполняет swap
    
    # Возвращает: {status, txid, tokens_received, error}
    # ⚠️ Текущая ошибка: 403 Forbidden
```

**Как исправить 403:**
1. Откройте `flashnet_auth.py`
2. Обновите API credentials в `.env`
3. Или используйте `flashnet_auth_curl.py` / `flashnet_auth_playwright.py`

---

### `flashnet_amm_client.py` - HTTP клиент
**Что делает:** HTTP клиент для Flashnet API

**Класс:** `FlashnetAMMClient`

**Методы:**
```python
authenticate()                         # POST /v1/auth/challenge + /verify
get_quote(from_token, to_token, amount) # GET /v1/quote
execute_swap(...)                      # POST /v1/swap
```

**API Endpoints:**
- `https://api.amm.flashnet.xyz/v1/auth/challenge`
- `https://api.amm.flashnet.xyz/v1/auth/verify`
- `https://api.amm.flashnet.xyz/v1/quote`
- `https://api.amm.flashnet.xyz/v1/swap`

---

### `utxo_pool_api.py` - UTXO.fun API
**Что делает:** Получение данных о токенах и балансах

**Класс:** `UTXOPoolAPI`

**Методы:**
```python
get_token_pool(token_address)          # Данные пула токена
get_wallet_balance(wallet_address)     # Баланс кошелька
get_transaction_history(wallet_address) # История транзакций
```

**API:**
- `https://api.utxo.fun/pool/{token_address}`
- `https://api.utxo.fun/address/{wallet_address}/balance`

**Статус:** ✅ Работает корректно

---

### `token_info.py` - Сервис токенов
**Что делает:** Информация о токенах, расчеты

**Класс:** `TokenInfoService`

**Методы:**
```python
get_token_info(token_address)                      # Информация о токене
calculate_tokens_for_btc(token_address, btc_amount) # Расчет количества
get_token_price(token_address)                     # Цена токена
btc_to_sats(btc)                                   # BTC → sats
sats_to_btc(sats)                                  # sats → BTC
```

**Пример:**
```python
service = TokenInfoService()
info = await service.get_token_info("btkn1fa6l5xk6...")
# Возвращает: {symbol: "MIM", name: "Magic Internet Money", price_btc: 7.23e-10}

calc = await service.calculate_tokens_for_btc("btkn1...", 0.001)
# Возвращает: {token_amount: 1382430.0, price_btc: 7.23e-10}
```

---

## 🔧 Утилиты

### `generate_spark_wallet.py` - Генерация кошельков
**Что делает:** Создает новый Spark кошелек

**Функция:**
```python
generate_spark_wallet()
    # 1. Генерирует приватный ключ (32 байта)
    # 2. Вычисляет публичный ключ (secp256k1)
    # 3. Создает Spark адрес (bech32m)
    # 4. Генерирует мнемонику (12 слов)
    
    # Возвращает: {
    #   private_key: str,
    #   public_key: str,
    #   address: str,        # spark1...
    #   mnemonic: str
    # }
```

**Пример адреса:**
`spark1pgss8avx2fjx0epmnyk2d8ar5ke4jjpk0wh9e4xkz9a8tu28cdh9kw00ghypjq`

---

### `bech32m_encoder.py` - Bech32m кодирование
**Что делает:** Кодирует/декодирует bech32m адреса

**Функции:**
```python
encode_bech32m(hrp, data)              # Кодировать
decode_bech32m(address)                # Декодировать
validate_spark_address(address)        # Валидировать
```

**HRP (Human Readable Part):**
- `spark` - для кошельков
- `btkn` - для токенов

---

### `btc_price.py` - Цена Bitcoin
**Что делает:** Получает текущую цену BTC

**Функции:**
```python
get_btc_price()                        # Цена BTC в USD (CoinGecko)
format_usd(amount_btc, btc_price)      # Форматировать в USD
sats_to_usd(sats, btc_price)           # Конвертировать sats → USD
```

**Пример:**
```python
price = await get_btc_price()  # 98542.50
usd = sats_to_usd(8800, price)  # $95.81
```

---

## 🎨 UI модули

### `main_menu_keyboard.py` - Главное меню
**Функции:**
```python
create_main_menu()                     # Главное меню
```

**Кнопки:**
- 👛 Мои кошельки
- 💰 Купить токен
- 💸 Продать токен
- 📤 Вывести средства
- ℹ️ Помощь

---

### `back_keyboard.py` - Кнопка "Назад"
**Функции:**
```python
create_back_keyboard()                 # Кнопка "◀️ Назад"
```

---

## 📊 Модули данных

### `spark_wallets/wallets.json` - База кошельков
**Формат:**
```json
{
  "471657882": [
    {
      "name": "wallet_471657882_1762366089",
      "address": "spark1pgss8...",
      "private_key": "...",
      "mnemonic": "word1 word2 ...",
      "created_at": 1762366089
    }
  ]
}
```

**Ключ:** Telegram user_id  
**Значение:** Массив кошельков

---

## 🚫 Отключенные модули

### `lightspark_client.py` - Lightspark (не используется)
**Причина:** Требует UMA server, сложная настройка

### `luminex_scraper.py` - Luminex (не используется)
**Причина:** Scraping не надежен

---

## 📈 Потоки данных

### Покупка токена (полный flow):

```
1. Пользователь: /buy
   ↓
2. buy_handlers.py: cmd_buy_new()
   - Проверяет наличие кошельков
   - Запрашивает адрес токена
   ↓
3. Пользователь вводит: btkn1fa6l5xk6...
   ↓
4. buy_handlers.py: handle_token_address_input()
   - Валидирует адрес
   ↓
5. token_info.py: get_token_info(token_address)
   ↓
6. utxo_pool_api.py: get_token_pool(token_address)
   - Получает: symbol, name, price_btc, market_cap
   ↓
7. Показ информации о токене
   - "MIM - Magic Internet Money"
   - "Цена: $0.00007305"
   ↓
8. buy_keyboards.py: create_buy_keyboard()
   - Кнопки: Wallet, Amount, Tip, Slippage, ✅ Confirm
   ↓
9. Пользователь настраивает параметры
   ↓
10. buy_handlers_extended.py: handle_buy_confirm()
    - Показывает 3 кнопки:
      - 💰 Flashnet AMM
      - 🔸 Spark Money
      - ❌ Отмена
   ↓
11. [Пользователь: Flashnet AMM]
    ↓
12. telegram_bot.py: handle_buy_callbacks() → buy_execute_flashnet
    ↓
13. flashnet_integration.py: execute_buy()
    ↓
14. flashnet_amm_client.py: FlashnetAMMClient()
    - authenticate() → ❌ 403 Forbidden
    ↓
15. Возврат ошибки: {status: "error", error: "403 Forbidden"}
    ↓
16. telegram_bot.py: Показывает ошибку пользователю
    "❌ Ошибка при покупке!
     Client error '403 Forbidden' for url '...'"
```

---

## 🔍 Быстрый поиск проблем

### Проблема: "TxID: N/A"
**Где:** `telegram_bot.py`, `buy_handlers_extended.py`  
**Исправлено:** Добавлены проверки `result['status']` и `result['txid']`

### Проблема: "403 Forbidden" (Flashnet)
**Где:** `flashnet_integration.py`, `flashnet_amm_client.py`  
**Решение:** Обновите credentials в `.env` или `flashnet_auth.py`

### Проблема: "NotImplementedError" (Spark Money)
**Где:** `spark_wallet.py` (строки 588-629)  
**Решение:** Реализуйте подключение к Spark Node API или используйте Flashnet

### Проблема: "Баланс 0 SATS"
**Где:** `spark_wallet.py`, `utxo_pool_api.py`  
**Решение:** Проверьте `get_wallet_balance()`, убедитесь что UTXO API работает

---

## 📝 Быстрые команды

### Запуск бота:
```powershell
python telegram_bot.py
```

### Тесты:
```powershell
python test_integration.py        # Все интеграции
python test_utxo_browser.py       # UTXO API
python test_flashnet_integration.py # Flashnet
```

### Логи:
```powershell
Get-Content bot_error.log -Tail 20  # Последние 20 ошибок
```

---

## 🆘 Контакты

**GitHub:** buildonspark/spark  
**Branch:** main  
**Docs:** `docs/PROJECT_ARCHITECTURE.md` - полная документация

---

**Обновлено:** 6 ноября 2025
