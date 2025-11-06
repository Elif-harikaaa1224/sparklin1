# Lightspark SDK Documentation

**Источники:**
- https://docs.lightspark.com/lightspark-sdk/getting-started
- https://docs.lightspark.com/lightspark-sdk/quickstart

**Дата изучения:** 2025-11-04

---

## Что такое Lightspark Connect?

Lightspark Connect - это платформа для работы с Lightning Network без сложностей управления узлами, каналами, ликвидностью и маршрутизацией.

### Что Lightspark делает за нас:

✅ **Обслуживание узлов:**
- Поддержка и обновление узлов
- Безопасность узлов и watchtowers
- Резервное копирование

✅ **Управление ликвидностью:**
- Управление inbound/outbound ликвидностью
- Ребалансировка каналов
- Открытие/закрытие каналов

✅ **Маршрутизация:**
- Оптимизация маршрутов для успешных платежей
- Минимальные комиссии

---

## 1. Регистрация и получение API credentials

### Шаг 1: Создать аккаунт
1. Зарегистрироваться: https://app.lightspark.com/signup
2. Перейти в **Developers > API Config**
3. Нажать **"New Token"**
4. Выбрать:
   - Имя токена
   - **Test environment** (для тестирования)
   - **Write Permissions**

### Шаг 2: Сохранить credentials

**Требуемые данные:**
```bash
LIGHTSPARK_API_TOKEN_CLIENT_ID=<your_client_id>
LIGHTSPARK_API_TOKEN_CLIENT_SECRET=<your_client_secret>
LIGHTSPARK_NODE_ID=<your_node_id>
LIGHTSPARK_NODE_PASSWORD=<password>
```

**Для Test Mode:**
- Node Password: `1234!@#$` (дефолтный)

**Для Live Mode:**
- Node Password: устанавливается при активации live mode

⚠️ **ВАЖНО:**
- Никогда не делиться Client Secret
- Не коммитить credentials в git
- Использовать `.env` файл или secret management систему

---

## 2. Установка SDK

### Python
```bash
pip install lightspark
```

### JavaScript/TypeScript
```bash
npm install @lightsparkdev/lightspark-sdk
```

### Другие языки
- Go
- Kotlin
- Flutter
- React Native

---

## 3. Инициализация клиента

### TypeScript Example

```typescript
import {
  AccountTokenAuthProvider,
  LightsparkClient,
} from "@lightsparkdev/lightspark-sdk";

// Credentials из .env
const API_TOKEN_CLIENT_ID = process.env.LIGHTSPARK_API_TOKEN_CLIENT_ID;
const API_TOKEN_CLIENT_SECRET = process.env.LIGHTSPARK_API_TOKEN_CLIENT_SECRET;
const NODE_ID = process.env.LIGHTSPARK_NODE_ID;
const NODE_PASSWORD = "1234!@#$"; // Test mode default

// Создать клиент
const client = new LightsparkClient(
  new AccountTokenAuthProvider(
    API_TOKEN_CLIENT_ID, 
    API_TOKEN_CLIENT_SECRET
  )
);

// Загрузить ключ подписи узла
await client.loadNodeSigningKey(NODE_ID, { 
  password: NODE_PASSWORD 
});
```

### Python Example (предполагаемый)

```python
from lightspark import LightsparkClient, AccountTokenAuthProvider
import os

# Credentials
client_id = os.getenv("LIGHTSPARK_API_TOKEN_CLIENT_ID")
client_secret = os.getenv("LIGHTSPARK_API_TOKEN_CLIENT_SECRET")
node_id = os.getenv("LIGHTSPARK_NODE_ID")
node_password = "1234!@#$"  # Test mode

# Создать клиент
client = LightsparkClient(
    AccountTokenAuthProvider(client_id, client_secret)
)

# Загрузить ключ подписи
await client.load_node_signing_key(node_id, password=node_password)
```

---

## 4. Отправка Lightning платежа

### Шаг 1: Создать funding address

```typescript
const fundingAddress = await client.createNodeWalletAddress(NODE_ID);
console.log(`Funding address: ${fundingAddress}`);
```

### Шаг 2: Пополнить узел (Test Mode)

**В Test Mode** используется симуляция:
```typescript
const fundNodeOutput = await client.fundNode(NODE_ID, 200000); // 200k sats
if (!fundNodeOutput) {
  throw new Error("Unable to fund node");
}
console.log(`Funded amount: ${fundNodeOutput.originalValue}`);
```

**В Live Mode** нужно отправить настоящую L1 транзакцию на funding address.

### Шаг 3: Создать тестовый инвойс (Test Mode)

```typescript
const testInvoice = await client.createTestModeInvoice(
  NODE_ID,
  20_000,  // 20k sats
  "example script payment"
);
if (!testInvoice) {
  throw new Error("Unable to create test invoice");
}
console.log(`Invoice created: ${testInvoice}`);
```

### Шаг 4: Оплатить инвойс

```typescript
const maxFeesSats = 1000; // Рекомендуется: max(5 sats, 17 bps * amount)

const payInvoice = await client.payInvoice(
  NODE_ID, 
  testInvoice, 
  maxFeesSats
);

if (!payInvoice) {
  throw new Error("Payment failed");
}

console.log(`Payment done with ID = ${JSON.stringify(payInvoice, null, 2)}`);
```

---

## 5. GraphQL API

Lightspark API построен на **GraphQL**.

### Преимущества:
- Запрос только нужных данных
- Множественные запросы в одном HTTP request
- Типизированные схемы

### Endpoints:
- **Test Mode:** `REGTEST` network
- **Production:** `MAINNET` network

### Rate Limiting:
- Есть ограничения по количеству запросов
- Можно делать bulk операции через один GraphQL запрос

---

## 6. Режимы работы

### Test Mode (REGTEST)
- **Сеть:** `bitcoin_network: REGTEST`
- **Node Password:** `1234!@#$`
- **Funding:** Через `client.fundNode()` (симуляция)
- **Invoices:** Через `client.createTestModeInvoice()`
- **Не затрагивает:** production данные, реальные деньги

### Live Mode (MAINNET)
- **Сеть:** `bitcoin_network: MAINNET`
- **Node Password:** Устанавливается при активации
- **Funding:** Реальные L1 транзакции
- **Invoices:** Реальные Lightning инвойсы
- **Работа с:** Реальными BTC

---

## 7. Возможности API

### Операции с узлами:
- `createNodeWalletAddress()` - создать L1 адрес
- `fundNode()` - пополнить узел (test mode)
- `loadNodeSigningKey()` - загрузить ключ подписи

### Lightning платежи:
- `createTestModeInvoice()` - создать тестовый инвойс
- `payInvoice()` - оплатить инвойс
- `createInvoice()` - создать реальный инвойс (live mode)

### Управление каналами:
- Автоматическое открытие/закрытие
- Автоматическая ребалансировка
- Управление ликвидностью

---

## 8. Рекомендации по комиссиям

**Максимальные routing fees:**
```javascript
maxFees = Math.max(5, Math.ceil(amount * 0.0017)); // 17 bps или 5 sats
```

**Где:**
- `5 sats` - минимальная комиссия
- `17 bps` - 0.17% от суммы транзакции
- `amount` - сумма платежа в satoshi

---

## 9. Безопасность

### Best Practices:
1. ✅ Хранить credentials в `.env`
2. ✅ Использовать environment variables
3. ✅ Использовать secret management (AWS Secrets, Azure Key Vault)
4. ❌ НЕ коммитить secrets в git
5. ❌ НЕ делиться Client Secret
6. ❌ НЕ hardcode credentials в коде

### .env Example:
```bash
# Lightspark API Credentials
LIGHTSPARK_API_TOKEN_CLIENT_ID=your_client_id_here
LIGHTSPARK_API_TOKEN_CLIENT_SECRET=your_client_secret_here
LIGHTSPARK_NODE_ID=your_node_id_here
LIGHTSPARK_NODE_PASSWORD=1234!@#$
```

---

## 10. Следующие шаги

### Документация:
- SDK Examples: https://docs.lightspark.com/lightspark-sdk/
- GraphQL API Reference: https://docs.lightspark.com/api/
- Authentication Guide: https://docs.lightspark.com/authentication/

### Примеры использования:
- Marketplace платежи
- Payment solutions
- Instant bitcoin transactions
- Low-cost transfers

---

## 11. Сравнение: Lightspark vs Flashnet

| Параметр | Lightspark SDK | Flashnet AMM API |
|----------|----------------|------------------|
| **Доступность** | ✅ Официальный SDK | ❌ Cloudflare 403 |
| **Документация** | ✅ Полная | ✅ Полная (но недоступна) |
| **Аутентификация** | ✅ API tokens | ❌ secp256k1 signatures |
| **Test Mode** | ✅ REGTEST | ❓ Неизвестно |
| **Python SDK** | ✅ Есть | ❌ Нет |
| **Lightning** | ✅ Полная поддержка | ❓ AMM только |
| **Управление узлом** | ✅ Автоматическое | 🤷 Вручную |

---

## 12. Интеграция с нашим ботом

### Что нужно сделать:

1. **Зарегистрироваться в Lightspark**
   - Создать аккаунт
   - Получить API credentials
   - Сохранить в `.env`

2. **Установить Lightspark SDK**
   ```bash
   pip install lightspark
   ```

3. **Создать Lightspark клиент**
   - Инициализация с API tokens
   - Загрузка node signing key

4. **Интегрировать в bot**
   - Заменить Flashnet AMM на Lightspark
   - Использовать `payInvoice()` для покупок
   - Использовать `createInvoice()` для продаж

5. **Тестировать в REGTEST**
   - Использовать test mode
   - Проверить все операции
   - Затем переключиться на MAINNET

---

## 13. Возможные API методы (предположительно)

Исходя из TypeScript примеров, Python SDK должен иметь:

```python
# Клиент
client = LightsparkClient(auth_provider)

# Узел
await client.create_node_wallet_address(node_id)
await client.fund_node(node_id, amount_sats)
await client.load_node_signing_key(node_id, password)

# Платежи
await client.create_test_mode_invoice(node_id, amount_sats, memo)
await client.pay_invoice(node_id, invoice, max_fees_sats)
await client.create_invoice(node_id, amount_sats, memo)

# GraphQL запросы
await client.execute_graphql(query, variables)
```

---

## Заключение

Lightspark SDK - это **официальный** и **правильный** способ работы с Lightning Network.

**Преимущества:**
- ✅ Нет Cloudflare блокировок
- ✅ Официальная поддержка
- ✅ Test mode для разработки
- ✅ Автоматическое управление узлами
- ✅ Python SDK доступен

**Следующий шаг:**
Зарегистрироваться в Lightspark и получить API credentials для интеграции в бота.

---

**Создано:** 2025-11-04  
**Автор:** AI Assistant  
**Источники:** Lightspark Official Documentation
