# План интеграции Lightspark SDK в Spark Wallet Bot

**Дата:** 2025-11-04  
**Статус:** План / В ожидании credentials

---

## Зачем нужен Lightspark SDK?

### Проблемы с текущим подходом:

❌ **Flashnet AMM API:**
- Cloudflare блокирует все запросы (HTTP 403)
- Даже с браузерными заголовками не работает
- Нет официального Python SDK
- Невозможно протестировать

✅ **Lightspark SDK:**
- Официальный SDK от разработчиков
- Нет Cloudflare блокировок
- Полная документация
- Test mode (REGTEST) для разработки
- Python SDK доступен
- Автоматическое управление узлами

---

## Этап 1: Регистрация и настройка

### 1.1 Создать Lightspark аккаунт

1. ✅ Перейти на: https://app.lightspark.com/signup
2. ✅ Зарегистрироваться
3. ✅ Подтвердить email
4. ✅ Войти в dashboard

### 1.2 Сгенерировать API credentials

1. ✅ Перейти в **Developers > API Config**
2. ✅ Нажать **"New Token"**
3. ✅ Настроить:
   - Name: `spark-wallet-bot-test`
   - Environment: **Test** (REGTEST)
   - Permissions: **Write**
4. ✅ Сохранить:
   - Client ID
   - Client Secret (ВАЖНО: больше не покажут!)
   - Node ID
   - Node Password (для test: `1234!@#$`)

### 1.3 Добавить в .env

```bash
# Lightspark API Credentials (Test Mode)
LIGHTSPARK_API_TOKEN_CLIENT_ID=<your_client_id>
LIGHTSPARK_API_TOKEN_CLIENT_SECRET=<your_client_secret>
LIGHTSPARK_NODE_ID=<your_node_id>
LIGHTSPARK_NODE_PASSWORD=1234!@#$

# Lightspark API Credentials (Live Mode) - для будущего
# LIGHTSPARK_LIVE_CLIENT_ID=
# LIGHTSPARK_LIVE_CLIENT_SECRET=
# LIGHTSPARK_LIVE_NODE_ID=
# LIGHTSPARK_LIVE_NODE_PASSWORD=
```

---

## Этап 2: Установка SDK

### 2.1 Установить Lightspark Python SDK

```bash
pip install lightspark
```

### 2.2 Проверить установку

```python
import lightspark
print(lightspark.__version__)
```

---

## Этап 3: Создание Lightspark клиента

### 3.1 Создать файл: `lightspark_client.py`

```python
"""
Lightspark SDK Client для Spark Wallet Bot
Обеспечивает Lightning Network операции через Lightspark API
"""

import os
from typing import Optional, Dict, Any
from lightspark import LightsparkClient, AccountTokenAuthProvider
from dotenv import load_dotenv

load_dotenv()


class SparkLightsparkClient:
    """Клиент для работы с Lightspark API"""
    
    def __init__(self, test_mode: bool = True):
        """
        Инициализация клиента
        
        Args:
            test_mode: True для REGTEST, False для MAINNET
        """
        self.test_mode = test_mode
        
        # Загрузить credentials
        if test_mode:
            self.client_id = os.getenv("LIGHTSPARK_API_TOKEN_CLIENT_ID")
            self.client_secret = os.getenv("LIGHTSPARK_API_TOKEN_CLIENT_SECRET")
            self.node_id = os.getenv("LIGHTSPARK_NODE_ID")
            self.node_password = os.getenv("LIGHTSPARK_NODE_PASSWORD", "1234!@#$")
        else:
            self.client_id = os.getenv("LIGHTSPARK_LIVE_CLIENT_ID")
            self.client_secret = os.getenv("LIGHTSPARK_LIVE_CLIENT_SECRET")
            self.node_id = os.getenv("LIGHTSPARK_LIVE_NODE_ID")
            self.node_password = os.getenv("LIGHTSPARK_LIVE_NODE_PASSWORD")
        
        # Проверить credentials
        if not all([self.client_id, self.client_secret, self.node_id]):
            raise ValueError("Missing Lightspark API credentials in .env")
        
        # Создать клиент
        auth_provider = AccountTokenAuthProvider(
            self.client_id, 
            self.client_secret
        )
        self.client = LightsparkClient(auth_provider)
        
        # Клиент готов
        print(f"[LIGHTSPARK] Client initialized (test_mode={test_mode})")
    
    async def initialize(self):
        """Инициализировать node signing key"""
        await self.client.load_node_signing_key(
            self.node_id, 
            password=self.node_password
        )
        print(f"[LIGHTSPARK] Node signing key loaded for {self.node_id}")
    
    async def create_funding_address(self) -> str:
        """Создать L1 адрес для пополнения узла"""
        address = await self.client.create_node_wallet_address(self.node_id)
        print(f"[LIGHTSPARK] Funding address: {address}")
        return address
    
    async def fund_node_test(self, amount_sats: int) -> Dict[str, Any]:
        """
        Пополнить узел в test mode (симуляция)
        
        Args:
            amount_sats: Сумма в satoshi
            
        Returns:
            Результат пополнения
        """
        if not self.test_mode:
            raise ValueError("fund_node_test() только для test mode")
        
        result = await self.client.fund_node(self.node_id, amount_sats)
        if not result:
            raise Exception("Unable to fund node")
        
        print(f"[LIGHTSPARK] Node funded: {result.originalValue} sats")
        return result
    
    async def create_invoice(
        self, 
        amount_sats: int, 
        memo: str = "Spark Wallet Bot"
    ) -> str:
        """
        Создать Lightning invoice
        
        Args:
            amount_sats: Сумма в satoshi
            memo: Описание платежа
            
        Returns:
            Invoice (bolt11 string)
        """
        if self.test_mode:
            invoice = await self.client.create_test_mode_invoice(
                self.node_id,
                amount_sats,
                memo
            )
        else:
            invoice = await self.client.create_invoice(
                self.node_id,
                amount_sats,
                memo
            )
        
        if not invoice:
            raise Exception("Unable to create invoice")
        
        print(f"[LIGHTSPARK] Invoice created: {invoice[:50]}...")
        return invoice
    
    async def pay_invoice(
        self, 
        invoice: str, 
        max_fees_sats: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Оплатить Lightning invoice
        
        Args:
            invoice: bolt11 invoice string
            max_fees_sats: Максимальная комиссия (если None, авто расчёт)
            
        Returns:
            Результат платежа
        """
        # Автоматический расчёт комиссии если не указано
        if max_fees_sats is None:
            # Рекомендация: max(5 sats, 17 bps * amount)
            # TODO: извлечь amount из invoice
            max_fees_sats = 1000  # Временно фиксированная
        
        result = await self.client.pay_invoice(
            self.node_id,
            invoice,
            max_fees_sats
        )
        
        if not result:
            raise Exception("Payment failed")
        
        print(f"[LIGHTSPARK] Payment successful: {result}")
        return result
    
    async def get_node_balance(self) -> int:
        """
        Получить баланс узла
        
        Returns:
            Баланс в satoshi
        """
        # TODO: реализовать через GraphQL query
        pass
    
    async def close(self):
        """Закрыть клиент"""
        # TODO: если есть cleanup метод
        pass


# Singleton instance
_lightspark_client: Optional[SparkLightsparkClient] = None


async def get_lightspark_client(test_mode: bool = True) -> SparkLightsparkClient:
    """
    Получить singleton instance клиента
    
    Args:
        test_mode: True для REGTEST, False для MAINNET
        
    Returns:
        Инициализированный клиент
    """
    global _lightspark_client
    
    if _lightspark_client is None:
        _lightspark_client = SparkLightsparkClient(test_mode=test_mode)
        await _lightspark_client.initialize()
    
    return _lightspark_client
```

---

## Этап 4: Интеграция в SparkWalletManager

### 4.1 Обновить `spark_wallet.py`

Заменить Flashnet AMM логику на Lightspark:

```python
async def buy_meme(
    self, 
    wallet_name: str, 
    token_address: str, 
    amount_btc: float
) -> dict:
    """Купить мем токен через Lightspark Lightning"""
    
    from lightspark_client import get_lightspark_client
    
    try:
        # Получить Lightspark клиент
        ls_client = await get_lightspark_client(test_mode=True)
        
        # TODO: Узнать как создать invoice для покупки токена
        # Возможно нужно интегрироваться с Flashnet через Lightning
        
        # Вариант 1: Flashnet принимает Lightning платежи?
        # Вариант 2: Нужен промежуточный сервис?
        
        return {
            "status": "success",
            "message": "Purchase via Lightspark",
            "txid": "...",
            "tokens_received": 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### 4.2 Вопросы для выяснения:

❓ **Как Flashnet интегрируется с Lightning?**
- Принимает ли Flashnet AMM Lightning invoices?
- Или нужно сначала deposit через Spark, потом swap?

❓ **Workflow покупки токена:**
1. User хочет купить токен
2. ???
3. Profit

---

## Этап 5: Тестирование

### 5.1 Создать тестовый скрипт

```python
"""test_lightspark.py - Тест Lightspark интеграции"""

import asyncio
from lightspark_client import get_lightspark_client


async def test_lightspark():
    print("=== Testing Lightspark SDK ===\n")
    
    # 1. Инициализация
    print("[1/5] Initializing client...")
    client = await get_lightspark_client(test_mode=True)
    print("✅ Client initialized\n")
    
    # 2. Создать funding address
    print("[2/5] Creating funding address...")
    address = await client.create_funding_address()
    print(f"✅ Address: {address}\n")
    
    # 3. Пополнить узел (test mode)
    print("[3/5] Funding node (test mode)...")
    fund_result = await client.fund_node_test(100000)  # 100k sats
    print(f"✅ Funded: {fund_result}\n")
    
    # 4. Создать invoice
    print("[4/5] Creating invoice...")
    invoice = await client.create_invoice(10000, "Test payment")
    print(f"✅ Invoice: {invoice[:50]}...\n")
    
    # 5. Оплатить invoice
    print("[5/5] Paying invoice...")
    payment = await client.pay_invoice(invoice, max_fees_sats=100)
    print(f"✅ Payment: {payment}\n")
    
    print("=== Test completed ===")


if __name__ == "__main__":
    asyncio.run(test_lightspark())
```

### 5.2 Запустить тест

```bash
python test_lightspark.py
```

---

## Этап 6: Production deployment

### 6.1 Получить Live Mode credentials

1. Активировать Live Mode в Lightspark dashboard
2. Сгенерировать production API token
3. Установить node password
4. Добавить в `.env`:
   ```bash
   LIGHTSPARK_LIVE_CLIENT_ID=...
   LIGHTSPARK_LIVE_CLIENT_SECRET=...
   LIGHTSPARK_LIVE_NODE_ID=...
   LIGHTSPARK_LIVE_NODE_PASSWORD=...
   ```

### 6.2 Переключить на MAINNET

```python
# В production коде
client = await get_lightspark_client(test_mode=False)
```

---

## Открытые вопросы

### ❓ Вопрос 1: Flashnet + Lightning integration

**Вопрос:** Как Flashnet AMM работает с Lightning Network?

**Возможные сценарии:**
1. Flashnet принимает Lightning invoices напрямую
2. Нужно сначала deposit BTC в Spark, потом swap
3. Есть промежуточный сервис

**Где искать ответ:**
- Flashnet документация про Lightning
- Lightspark examples с AMM
- Community форумы / Discord

### ❓ Вопрос 2: Workflow покупки токена

**Текущее понимание:**
```
User → Buy token
  ↓
  ? Lightning invoice to Flashnet ?
  ? или Spark deposit + swap ?
  ↓
Token received
```

**Нужно выяснить:**
- Полный workflow покупки
- Какие API использовать
- Как связать Lightspark + Flashnet

### ❓ Вопрос 3: Python SDK методы

**Вопрос:** Точные названия методов в Python SDK?

**Что проверить:**
```bash
pip show lightspark
# Посмотреть установленную версию

python
>>> import lightspark
>>> dir(lightspark)
# Посмотреть доступные классы/функции
```

---

## Следующие шаги

### Сейчас (требуется от пользователя):

1. ✅ **Зарегистрироваться в Lightspark**
   - https://app.lightspark.com/signup
   - Получить API credentials
   - Добавить в `.env`

2. ✅ **Установить SDK**
   ```bash
   pip install lightspark
   ```

3. ✅ **Предоставить credentials**
   - Client ID
   - Client Secret
   - Node ID
   - Node Password

### После получения credentials:

4. ⏳ Создать `lightspark_client.py`
5. ⏳ Протестировать базовые операции
6. ⏳ Выяснить Flashnet + Lightning integration
7. ⏳ Интегрировать в бота
8. ⏳ Протестировать покупку/продажу
9. ⏳ Deploy в production

---

## Ресурсы

- **Lightspark Dashboard:** https://app.lightspark.com/
- **Документация:** https://docs.lightspark.com/
- **SDK Getting Started:** https://docs.lightspark.com/lightspark-sdk/getting-started
- **Quickstart:** https://docs.lightspark.com/lightspark-sdk/quickstart
- **GitHub:** https://github.com/lightsparkdev

---

**Статус:** ⏸️ Ожидание регистрации в Lightspark  
**Блокер:** Нужны API credentials  
**ETA:** После получения credentials - 1-2 дня интеграции
