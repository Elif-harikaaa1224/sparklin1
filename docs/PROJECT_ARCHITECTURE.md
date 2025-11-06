# 📐 Архитектура проекта Spark Wallet Bot

**Версия:** 3.0  
**Дата:** 6 ноября 2025  
**Статус:** Production Ready (с реальными ошибками для отладки)

---

## 📁 Структура проекта

```
spark-wallet-bot3/
├── 🤖 Основные файлы бота
│   ├── telegram_bot.py          # Главный файл бота (2391 строк)
│   ├── spark_wallet.py          # Менеджер кошельков (977 строк)
│   └── requirements.txt         # Python зависимости
│
├── 💰 Модули покупки токенов
│   ├── buy_handlers.py          # Основные обработчики покупки (20.5 KB)
│   ├── buy_handlers_extended.py # Расширенные функции (slippage, confirm) (14.8 KB)
│   ├── buy_keyboards.py         # Клавиатуры для покупки (5.7 KB)
│   └── token_info.py            # Сервис информации о токенах
│
├── 💸 Модули продажи токенов
│   ├── sell_handlers.py         # Обработчики продажи
│   └── sell_keyboards.py        # Клавиатуры для продажи
│
├── 🏦 Модули вывода средств
│   ├── withdrawal_handlers.py   # Обработчики вывода
│   └── spark_withdrawal.py      # Логика вывода через Spark
│
├── 🔌 Интеграции с внешними сервисами
│   ├── flashnet_integration.py       # Главная интеграция Flashnet AMM
│   ├── flashnet_amm_client.py        # HTTP клиент для Flashnet
│   ├── flashnet_swap.py              # Swap функции
│   ├── flashnet_auth.py              # Аутентификация (базовая)
│   ├── flashnet_auth_curl.py         # Аутентификация через curl
│   ├── flashnet_auth_playwright.py   # Аутентификация через Playwright
│   ├── utxo_pool_api.py              # UTXO.fun Pool API (токены + баланс)
│   ├── lightspark_client.py          # Lightspark Lightning (не используется)
│   ├── lightspark_graphql_client.py  # Lightspark GraphQL (не используется)
│   └── luminex_scraper.py            # Luminex scraper (не используется)
│
├── 🔧 Утилиты и вспомогательные модули
│   ├── generate_spark_wallet.py      # Генерация Spark кошельков
│   ├── bech32m_encoder.py            # Кодирование bech32m адресов
│   ├── spark_protobuf.py             # Protobuf сериализация
│   ├── btc_price.py                  # Получение цены BTC
│   ├── back_keyboard.py              # Клавиатура "Назад"
│   └── main_menu_keyboard.py         # Главное меню
│
├── 🧪 Тесты
│   ├── test_integration.py           # Интеграционные тесты
│   ├── test_bot_flow.py              # Тесты потока бота
│   ├── test_flashnet_integration.py  # Тесты Flashnet
│   ├── test_utxo_browser.py          # Тесты UTXO API
│   └── tests/                        # Папка с дополнительными тестами
│
├── 📚 Документация
│   ├── docs/
│   │   ├── PROJECT_ARCHITECTURE.md   # Этот файл
│   │   ├── FLASHNET_RESTORE.md       # Восстановление Flashnet
│   │   └── QUICK_START_AFTER_RESTORE.md
│   ├── README.md                     # Основная документация
│   ├── CLEANUP_SUMMARY.md            # История очистки проекта
│   └── WALLET_FEATURES.md            # Документация функций кошелька
│
├── 💾 Данные
│   ├── spark_wallets/                # Кошельки пользователей
│   │   └── wallets.json              # JSON база данных кошельков
│   ├── wallets/                      # Старые кошельки (не используется)
│   └── test_wallets/                 # Тестовые кошельки
│
├── 🗄️ Резервные копии
│   └── spark-wallet-bot-backup/      # Полный бекап всех модулей
│
├── ⚙️ Конфигурация
│   ├── .env                          # Переменные окружения (API ключи)
│   ├── .env.example                  # Пример конфигурации
│   ├── start_bot.ps1                 # Скрипт запуска (PowerShell)
│   └── restart_bot.ps1               # Скрипт перезапуска
│
└── 🔨 Spark SDK (подпроект)
    └── spark-sdk/                    # Spark Protocol SDK
        ├── sdks/js/                  # JavaScript SDK
        ├── sdks/rs/                  # Rust SDK
        ├── signer/                   # FROST Signer
        └── protos/                   # Protocol Buffers
```

---

## 🤖 Основные компоненты

### 1. **telegram_bot.py** (2391 строк)

**Главный файл бота** - точка входа и центральный координатор.

#### Структура:
- **Строки 1-100:** Импорты и инициализация
- **Строки 101-500:** Обработчики команд (/start, /help, /wallets, /buy, /sell)
- **Строки 501-1000:** Обработчики создания кошельков
- **Строки 1001-1500:** Обработчики депозитов
- **Строки 1501-2000:** Обработчики покупки токенов
- **Строки 2001-2200:** Обработчики Flashnet и Spark Money
- **Строки 2201-2391:** Главная функция main() и запуск

#### Ключевые функции:

```python
# Команды
async def cmd_start(message: types.Message)           # /start
async def cmd_help(message: types.Message)            # /help
async def cmd_my_wallets(message: types.Message)      # Мои кошельки
async def cmd_buy_new(message: types.Message)         # /buy

# Обработчики создания кошелька
async def cmd_create_wallet(callback: types.CallbackQuery)
async def handle_wallet_name(message: types.Message, state: FSMContext)

# Обработчики покупки
async def handle_buy_callbacks(callback: types.CallbackQuery, state: FSMContext)
# - buy_execute: Основная покупка (через buy_meme)
# - buy_execute_flashnet: Покупка через Flashnet AMM
# - buy_execute_spark: Покупка через Spark Money (NotImplementedError)
# - buy_cancel: Отмена покупки

# Обработчики вывода
async def cmd_withdraw(message: types.Message)
```

#### Глобальные объекты:
```python
wallet_manager = SparkWalletManager()      # Менеджер кошельков
token_service = TokenInfoService()         # Сервис токенов
user_data = {}                             # Данные пользователей
positions = {}                             # Позиции (покупки/продажи)
```

---

### 2. **spark_wallet.py** (977 строк)

**Менеджер кошельков** - управление Spark кошельками, балансами, транзакциями.

#### Класс: `SparkWalletManager`

##### Основные методы:

**Создание и управление:**
```python
async def create_wallet(self, user_id: int, wallet_name: str = None) -> Dict
    # Создает новый Spark кошелек с приватным ключом
    # Возвращает: {address, mnemonic, wallet_name}

async def get_user_wallets(self, user_id: int) -> List[Dict]
    # Получает все кошельки пользователя
    # Возвращает список: [{name, address, balance_sats}]

async def get_wallet_by_name(self, wallet_name: str) -> Dict
    # Получает кошелек по имени
```

**Балансы и транзакции:**
```python
async def get_wallet_balance(self, wallet_address: str) -> Dict
    # Получает реальный баланс через UTXO Pool API
    # Возвращает: {balance_sats, balance_btc, transactions}

async def get_transaction_history(self, wallet_address: str) -> List[Dict]
    # История транзакций из UTXO API
```

**Покупка токенов:**
```python
async def buy_meme(self, contract_address: str, amount_sats: int, 
                   wallet_name: str, slippage: float, priority_fee_sats: int) -> Dict
    # Покупка токена через Flashnet AMM
    # Возвращает: {status, txid, tokens_received, error}
    # ⚠️ РЕАЛЬНАЯ ИНТЕГРАЦИЯ - показывает настоящие ошибки

async def buy_meme_native(self, ...) -> Dict
    # Покупка через Spark Native SDK
    # ❌ НЕ РЕАЛИЗОВАНО - выбрасывает NotImplementedError
```

**Продажа токенов:**
```python
async def sell_meme(self, contract_address: str, token_amount: int, 
                    wallet_name: str, slippage: float) -> Dict
    # Продажа токена (не реализовано полностью)
```

**Вывод средств:**
```python
async def withdraw_to_lightning(self, wallet_name: str, invoice: str) -> Dict
    # Вывод через Lightning Network

async def withdraw_to_l1(self, wallet_name: str, address: str, 
                        amount_sats: int) -> Dict
    # Вывод на L1 Bitcoin адрес
```

##### Внутренние методы:
```python
def ensure_valid_btkn(self, address: str)     # Валидация btkn1 адреса
def _save_wallets(self)                       # Сохранение в wallets.json
def _load_wallets(self)                       # Загрузка из wallets.json
```

---

### 3. **buy_handlers.py** (20.5 KB)

**Основные обработчики покупки токенов** - UI flow для покупки.

#### Функции:

```python
async def cmd_buy_new(message: types.Message, state: FSMContext)
    # Команда /buy - начало процесса покупки
    # Проверяет наличие кошельков, запрашивает адрес токена

async def handle_token_address_input(message: types.Message, state: FSMContext)
    # Обработка введенного адреса токена
    # 1. Валидация адреса (btkn1...)
    # 2. Получение информации через UTXO Pool API
    # 3. Расчет количества токенов
    # 4. Показ клавиатуры с вариантами покупки

async def handle_buy_wallet_selection(callback: types.CallbackQuery, state: FSMContext)
    # Выбор кошелька для покупки
    # Показывает список кошельков с балансами

async def handle_buy_amount_selection(callback: types.CallbackQuery, state: FSMContext)
    # Выбор суммы покупки
    # Варианты: 0.0001, 0.001, 0.01, 0.1 BTC или custom

async def handle_custom_amount_input(message: types.Message, state: FSMContext)
    # Ввод кастомной суммы
    # Валидация и конвертация в sats

async def handle_buy_tip_selection(callback: types.CallbackQuery, state: FSMContext)
    # Выбор комиссии (priority fee)
    # Варианты: 0.0000001 - 0.001 BTC

async def handle_buy_confirmation(callback: types.CallbackQuery, state: FSMContext)
    # Подтверждение покупки
    # Показывает итоговую информацию и кнопки подтверждения
```

#### UI Flow:
```
/buy → Введите токен → Выберите кошелек → Выберите сумму → 
→ Выберите tip → Slippage → Подтверждение → Выполнение
```

---

### 4. **buy_handlers_extended.py** (14.8 KB, 397 строк)

**Расширенные функции покупки** - slippage, кастомные значения, выполнение.

#### Функции:

```python
async def handle_buy_set_slippage(callback: types.CallbackQuery, state: FSMContext)
    # Открывает меню настройки slippage
    # Показывает варианты: 1%, 3%, 5%, 10%, 15%, custom

async def handle_slippage_selection(callback: types.CallbackQuery, state: FSMContext)
    # Обработка выбора slippage
    # Сохраняет в state и возвращает к подтверждению

async def handle_custom_tip_input(message: types.Message, state: FSMContext)
    # Ввод кастомной комиссии
    # Валидация: 0.00000001 - 0.01 BTC

async def handle_custom_slippage_input(message: types.Message, state: FSMContext)
    # Ввод кастомного slippage
    # Валидация: 0.1% - 50%

async def handle_buy_confirm(callback: types.CallbackQuery, state: FSMContext)
    # Финальное подтверждение
    # Показывает 3 кнопки: Flashnet AMM, Spark Money, Отмена

async def handle_buy_execute(callback: types.CallbackQuery, state: FSMContext)
    # Выполнение покупки (не используется напрямую в telegram_bot.py)
    # Вызывает wallet_manager.buy_meme()
    # ✅ Проверяет result['status'] == 'success'
    # ✅ Проверяет наличие TxID
    # ❌ Выбрасывает Exception при ошибке

async def handle_buy_cancel(callback: types.CallbackQuery, state: FSMContext)
    # Отмена покупки
```

---

### 5. **buy_keyboards.py** (5.7 KB)

**Клавиатуры для UI покупки.**

#### Функции:

```python
def create_buy_keyboard(wallet_balance_sats: int, selected_amount: float) -> InlineKeyboardMarkup
    # Главная клавиатура покупки
    # Кнопки: Wallet, Amount, Tip, Slippage, ✅ Confirm

def create_wallet_selection_keyboard(wallets: List[Dict]) -> InlineKeyboardMarkup
    # Выбор кошелька
    # Показывает: {name} - {balance} SATS

def create_amount_keyboard() -> InlineKeyboardMarkup
    # Выбор суммы
    # Варианты: 0.0001, 0.001, 0.01, 0.1 BTC, Custom

def create_tip_keyboard() -> InlineKeyboardMarkup
    # Выбор комиссии
    # Варианты: 0.0000001 - 0.001 BTC, Custom

def create_slippage_keyboard() -> InlineKeyboardMarkup
    # Выбор slippage
    # Варианты: 1%, 3%, 5%, 10%, 15%, Custom

def create_confirmation_keyboard() -> InlineKeyboardMarkup
    # Финальное подтверждение
    # Кнопки: 💰 Flashnet AMM, 🔸 Spark Money, ❌ Отмена
```

---

## 🔌 Интеграции

### 6. **flashnet_integration.py**

**Главная интеграция с Flashnet AMM.**

#### Функции:

```python
async def execute_buy(wallet_manager: SparkWalletManager, wallet_name: str,
                     token_address: str, amount_btc_sats: int, 
                     slippage_pct: float) -> Dict
    # Выполняет покупку через Flashnet AMM
    # 1. Получает данные кошелька
    # 2. Создает FlashnetAMMClient
    # 3. Аутентифицируется
    # 4. Получает quote (цену)
    # 5. Выполняет swap
    # Возвращает: {status, txid, tokens_received, error}
    
    # ⚠️ РЕАЛЬНАЯ ИНТЕГРАЦИЯ
    # Текущая ошибка: 403 Forbidden (нужны API credentials)

async def buy_token(wallet_manager, wallet_data, token_address, 
                   amount_sats, slippage_pct) -> Dict
    # Внутренняя функция покупки
```

---

### 7. **flashnet_amm_client.py**

**HTTP клиент для Flashnet AMM API.**

#### Класс: `FlashnetAMMClient`

```python
class FlashnetAMMClient:
    def __init__(self, base_url: str, wallet_address: str, private_key: str)
    
    async def authenticate(self) -> None
        # Аутентификация с API
        # POST /v1/auth/challenge
        # POST /v1/auth/verify
        # ❌ Текущая ошибка: 403 Forbidden
    
    async def get_quote(self, from_token: str, to_token: str, amount: int) -> Dict
        # Получение цены обмена
        # GET /v1/quote?from={from_token}&to={to_token}&amount={amount}
    
    async def execute_swap(self, from_token: str, to_token: str, 
                          amount: int, slippage: float) -> Dict
        # Выполнение обмена
        # POST /v1/swap
        # Body: {from_token, to_token, amount, slippage, signature}
```

**Endpoints:**
- `https://api.amm.flashnet.xyz/v1/auth/challenge`
- `https://api.amm.flashnet.xyz/v1/auth/verify`
- `https://api.amm.flashnet.xyz/v1/quote`
- `https://api.amm.flashnet.xyz/v1/swap`

---

### 8. **utxo_pool_api.py**

**Интеграция с UTXO.fun Pool API** - получение данных о токенах и балансах.

#### Класс: `UTXOPoolAPI`

```python
class UTXOPoolAPI:
    def __init__(self)
        # Base URL: https://api.utxo.fun
    
    async def get_token_pool(self, token_address: str) -> Dict
        # Получает данные пула токена
        # GET /pool/{token_address}
        # Возвращает: {
        #   symbol, name, price_btc, price_usd, 
        #   market_cap, holders, liquidity
        # }
    
    async def get_wallet_balance(self, wallet_address: str) -> Dict
        # Получает баланс кошелька
        # GET /address/{wallet_address}/balance
        # Возвращает: {balance_sats, transactions}
    
    async def get_transaction_history(self, wallet_address: str) -> List[Dict]
        # История транзакций кошелька
        # GET /address/{wallet_address}/transactions
```

**Статус:** ✅ Работает корректно

---

### 9. **token_info.py**

**Сервис информации о токенах.**

#### Класс: `TokenInfoService`

```python
class TokenInfoService:
    async def get_token_info(self, token_address: str) -> Dict
        # Получает информацию о токене из UTXO Pool API
        # Возвращает: {
        #   address, symbol, name, 
        #   price_btc, price_usd, 
        #   market_cap, holders
        # }
    
    async def calculate_tokens_for_btc(self, token_address: str, 
                                       btc_amount: float) -> Dict
        # Рассчитывает количество токенов для суммы BTC
        # Возвращает: {token_amount, price_btc, total_cost}
    
    async def get_token_price(self, token_address: str) -> float
        # Получает текущую цену токена в BTC
    
    def btc_to_sats(self, btc: float) -> int
        # Конвертирует BTC в satoshis
        # 1 BTC = 100,000,000 sats
    
    def sats_to_btc(self, sats: int) -> float
        # Конвертирует satoshis в BTC
```

---

## 🔧 Утилиты

### 10. **generate_spark_wallet.py**

**Генерация Spark кошельков.**

```python
def generate_spark_wallet() -> Dict
    # Создает новый Spark кошелек
    # 1. Генерирует случайный приватный ключ (32 байта)
    # 2. Вычисляет публичный ключ (secp256k1)
    # 3. Создает Spark адрес (bech32m, spark1...)
    # 4. Генерирует мнемоническую фразу (12 слов)
    
    # Возвращает: {
    #   private_key: str,      # hex
    #   public_key: str,       # hex
    #   address: str,          # spark1...
    #   mnemonic: str          # 12 слов
    # }
```

**Формат адреса:** `spark1{bech32m_encoded_pubkey}`  
**Пример:** `spark1pgss8avx2fjx0epmnyk2d8ar5ke4jjpk0wh9e4xkz9a8tu28cdh9kw00ghypjq`

---

### 11. **bech32m_encoder.py**

**Кодирование bech32m адресов.**

```python
def encode_bech32m(hrp: str, data: bytes) -> str
    # Кодирует данные в bech32m формат
    # hrp = "spark" для Spark адресов
    # hrp = "btkn" для токенов

def decode_bech32m(address: str) -> Tuple[str, bytes]
    # Декодирует bech32m адрес
    # Возвращает: (hrp, data)

def validate_spark_address(address: str) -> bool
    # Проверяет валидность Spark адреса
    # Должен начинаться с "spark1"
```

---

### 12. **btc_price.py**

**Получение цены Bitcoin.**

```python
async def get_btc_price() -> float
    # Получает текущую цену BTC в USD
    # Источник: CoinGecko API
    # Возвращает: float (например, 98542.50)

def format_usd(amount_btc: float, btc_price: float) -> str
    # Форматирует BTC сумму в USD
    # Возвращает: "$1,234.56"

def sats_to_usd(sats: int, btc_price: float) -> float
    # Конвертирует satoshis в USD
```

---

## 📊 Модули данных

### 13. **spark_wallets/wallets.json**

**База данных кошельков** (JSON формат).

#### Структура:

```json
{
  "471657882": [
    {
      "name": "wallet_471657882_1762366089",
      "address": "spark1pgss8avx2fjx0epmnyk2d8ar5ke4jjpk0wh9e4xkz9a8tu28cdh9kw00ghypjq",
      "private_key": "...",
      "mnemonic": "word1 word2 ... word12",
      "created_at": 1762366089
    },
    {
      "name": "MyWallet",
      "address": "spark1...",
      "private_key": "...",
      "mnemonic": "...",
      "created_at": 1762452678
    }
  ]
}
```

**Ключ:** `user_id` (Telegram ID)  
**Значение:** Массив кошельков пользователя

---

## 🎯 Потоки данных

### Поток покупки токена:

```
Пользователь вводит btkn1... адрес
    ↓
buy_handlers.py: handle_token_address_input()
    ↓
token_info.py: get_token_info(token_address)
    ↓
utxo_pool_api.py: get_token_pool(token_address)
    ↓ [Успех]
Показ информации о токене
    ↓
Пользователь выбирает: Wallet, Amount, Tip, Slippage
    ↓
buy_handlers_extended.py: handle_buy_confirm()
    ↓
Показ 3 кнопок: Flashnet AMM | Spark Money | Cancel
    ↓
[Пользователь выбирает "Flashnet AMM"]
    ↓
telegram_bot.py: handle_buy_callbacks() → buy_execute_flashnet
    ↓
flashnet_integration.py: execute_buy()
    ↓
flashnet_amm_client.py: FlashnetAMMClient()
    ├─→ authenticate()       → ❌ 403 Forbidden (нужны credentials)
    ├─→ get_quote()
    └─→ execute_swap()
    ↓
Возврат результата: {status: "error", error: "403 Forbidden"}
    ↓
telegram_bot.py: Показывает ошибку пользователю
```

### Поток получения баланса:

```
Пользователь: "Мои кошельки"
    ↓
telegram_bot.py: cmd_my_wallets()
    ↓
spark_wallet.py: get_user_wallets(user_id)
    ↓
Для каждого кошелька:
    spark_wallet.py: get_wallet_balance(address)
        ↓
    utxo_pool_api.py: get_wallet_balance(address)
        ↓
    Парсинг транзакций, расчет баланса
        ↓
    Возврат: {balance_sats, transactions}
    ↓
Форматирование: "8,800 SATS ($95.81)"
    ↓
Показ списка кошельков с балансами
```

---

## ⚙️ Конфигурация

### .env файл

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=8499197026:AAH...
ADMIN_USER_ID=7935768100

# Flashnet AMM (требуется настройка)
FLASHNET_API_KEY=your_api_key_here
FLASHNET_API_URL=https://api.amm.flashnet.xyz

# Lightspark (не используется)
LIGHTSPARK_API_TOKEN_CLIENT_ID=...
LIGHTSPARK_API_TOKEN_CLIENT_SECRET=...

# Node URLs (опционально)
SPARK_NODE_URL=https://node.spark.network
```

---

## 🚀 Запуск бота

### Через PowerShell:

```powershell
# Запуск
.\start_bot.ps1

# Или напрямую
python telegram_bot.py
```

### Через командную строку:

```bash
python telegram_bot.py
```

---

## 🧪 Тестирование

### Интеграционные тесты:

```powershell
# Тест всей системы
python test_integration.py

# Тест UTXO API
python test_utxo_browser.py

# Тест Flashnet
python test_flashnet_integration.py

# Тест потока бота
python test_bot_flow.py
```

---

## 🔍 Текущий статус модулей

| Модуль | Статус | Описание |
|--------|--------|----------|
| `telegram_bot.py` | ✅ Работает | Основной бот запущен |
| `spark_wallet.py` | ✅ Работает | Создание кошельков, балансы |
| `buy_handlers.py` | ✅ Работает | UI потоки покупки |
| `buy_handlers_extended.py` | ✅ Работает | Расширенные функции |
| `token_info.py` | ✅ Работает | Информация о токенах |
| `utxo_pool_api.py` | ✅ Работает | UTXO.fun API интеграция |
| `flashnet_integration.py` | ⚠️ Требует настройки | 403 Forbidden - нужны credentials |
| `flashnet_amm_client.py` | ⚠️ Требует настройки | Нужны API ключи |
| `lightspark_client.py` | ❌ Не используется | Lightning интеграция отключена |
| `luminex_scraper.py` | ❌ Не используется | Scraper отключен |

---

## 🐛 Известные проблемы и их решения

### 1. **Flashnet 403 Forbidden**

**Ошибка:**
```
Client error '403 Forbidden' for url 'https://api.amm.flashnet.xyz/v1/auth/challenge'
```

**Решение:**
1. Откройте `flashnet_auth.py`
2. Проверьте API credentials
3. Обновите `.env` файл с правильными ключами
4. Или используйте альтернативную аутентификацию: `flashnet_auth_curl.py` или `flashnet_auth_playwright.py`

**Файлы для изменения:**
- `flashnet_auth.py` (строки 20-50)
- `flashnet_amm_client.py` (строки 80-120)
- `.env` (добавьте `FLASHNET_API_KEY`)

---

### 2. **Spark Money NotImplementedError**

**Ошибка:**
```
NotImplementedError: buy_meme_native() не реализован!
```

**Это ожидаемое поведение!**

**Объяснение:**
- `buy_meme_native()` - заглушка для будущей интеграции с Spark Node
- Используйте **Flashnet AMM** вместо Spark Money
- Или реализуйте подключение к Spark Node API

**Файл для реализации:**
- `spark_wallet.py` (строки 588-629)

**Что нужно реализовать:**
1. Подключение к Spark Node API
2. Создание транзакции покупки
3. Подпись транзакции приватным ключом
4. Broadcast в сеть Spark

---

### 3. **TxID = N/A (исправлено)**

**Было:**
```
✅ Покупка выполнена!
📋 TxID: N/A
```

**Исправлено:**
- Теперь проверяется `result['status'] == 'success'`
- Проверяется наличие `result['txid']`
- Если TxID отсутствует → выбрасывается Exception

**Файлы изменены:**
- `telegram_bot.py` (строки 2000-2050, 2129-2200)
- `buy_handlers_extended.py` (строки 268-350)

---

## 📈 Планы развития

### Ближайшие задачи:

1. **Настроить Flashnet AMM**
   - Получить API credentials
   - Настроить аутентификацию
   - Протестировать реальные покупки

2. **Реализовать Spark Native**
   - Интеграция с Spark Node API
   - Создание и подпись транзакций
   - Broadcast в сеть

3. **Добавить продажу токенов**
   - Завершить `sell_handlers.py`
   - Интеграция с DEX для продажи
   - UI поток продажи

4. **Улучшить вывод средств**
   - Lightning Network интеграция
   - L1 Bitcoin вывод
   - Проверка комиссий

---

## 📚 Дополнительная документация

- **FLASHNET_RESTORE.md** - История восстановления Flashnet
- **QUICK_START_AFTER_RESTORE.md** - Быстрый старт
- **CLEANUP_SUMMARY.md** - История очистки проекта
- **WALLET_FEATURES.md** - Документация функций кошелька
- **UTXO_POOL_API_README.md** - Документация UTXO API

---

## 🤝 Контакты и поддержка

**Проект:** Spark Wallet Bot  
**GitHub:** buildonspark/spark  
**Ветка:** main  

---

**Последнее обновление:** 6 ноября 2025  
**Версия документации:** 1.0
