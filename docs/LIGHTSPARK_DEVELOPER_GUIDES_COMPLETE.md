# Lightspark SDK - Developer Guides Complete Documentation

**Источники:**
1. https://docs.lightspark.com/lightspark-sdk/developer-guides/auth-funding-withdrawals
2. https://docs.lightspark.com/lightspark-sdk/developer-guides/sending-receiving-payments
3. https://docs.lightspark.com/lightspark-sdk/developer-guides/reconciliation-error-handling-testing
4. https://docs.lightspark.com/lightspark-sdk/developer-guides/promoting-to-production
5. https://docs.lightspark.com/lightspark-sdk/developer-guides/creating-paying-offers

**Дата изучения:** 2025-11-04

---

## ЧАСТЬ 1: Authentication, Funding & Withdrawals

### 1.1 Authentication

#### Creating API Credentials

**Шаги:**
1. Login: https://app.lightspark.com/
2. Navigate: **Developers → API Config**
3. Click: **"New Token"**
4. Receive: **Client ID** + **Client Secret** (показывается ТОЛЬКО ОДИН раз!)

**⚠️ КРИТИЧЕСКИ ВАЖНО:**
- Client Secret показывается только при создании
- Никогда не коммитить в git
- Хранить в `.env` или secrets manager
- Использовать environment variables

#### Setting Up Authentication (TypeScript)

```typescript
import { 
  AccountTokenAuthProvider, 
  LightsparkClient 
} from "@lightsparkdev/lightspark-sdk";

const API_TOKEN_CLIENT_ID = process.env.LIGHTSPARK_API_TOKEN_CLIENT_ID;
const API_TOKEN_CLIENT_SECRET = process.env.LIGHTSPARK_API_TOKEN_CLIENT_SECRET;

const client = new LightsparkClient(
  new AccountTokenAuthProvider(
    API_TOKEN_CLIENT_ID, 
    API_TOKEN_CLIENT_SECRET
  )
);
```

#### Operation Signing Keys (OSK)

**Что это:**
- Дополнительная безопасность для операций с деньгами
- Любая операция, выводящая деньги, требует подписи OSK
- Private key шифруется паролем, который вы устанавливаете

**Как работает:**
1. **Key Generation**: Браузер генерирует пару ключей при создании ноды
2. **Encryption**: Private key шифруется вашим паролем
3. **Storage**: Зашифрованный ключ хранится на Lightspark, публичный на ноде
4. **Signing**: SDK автоматически подписывает операции после загрузки ключа

**Test Mode Password:** `1234!@#$` (дефолт для REGTEST)

**Loading OSK:**
```typescript
const NODE_ID = process.env.LIGHTSPARK_NODE_ID;
const NODE_PASSWORD = "1234!@#$"; // Test mode
client.loadNodeSigningKey(NODE_ID, { password: NODE_PASSWORD });
```

---

### 1.2 Funding a Node

#### Creating a Funding Address

```typescript
const fundingAddress = await client.createNodeWalletAddress(NODE_ID);
```

**Что это:**
- L1 wallet адрес для получения Bitcoin
- После получения средств нода автоматически создаёт channel с Lightspark routing nodes

#### Funding Process in Live Mode (MAINNET)

**2 шага:**
1. **L1 transaction** - отправка BTC на node wallet address
2. **Auto channel opening** - нода автоматически создаёт zero-confirmation channel

**Confirmations needed:**
- ≤ 0.16777215 BTC: **3 confirmations**
- > 0.16777215 BTC: **6 confirmations**

**Большие суммы:**
- Могут открываться multiple channels

#### Simulated Funding in Test Mode (REGTEST)

```typescript
const fundNodeOutput = await client.fundNode(NODE_ID, 200000); // 200k sats
if (!fundNodeOutput) {
  throw new Error("Unable to fund node");
}
console.log(`Funded amount: ${fundNodeOutput.originalValue}`);
```

**Преимущества Test Mode:**
- Нет реальных BTC
- Instant funding (без подтверждений)
- Идеально для разработки

#### Monitoring Funding Status

**Через Webhooks:**

**1. Создать webhook endpoint:**
```javascript
const express = require('express');
const app = express();

app.post("/webhook", (req, res) => {
  // Handle webhook
  res.send("OK!");
});

app.listen(3000, () => {
  console.log("Server listening on port 3000");
});
```

**2. Configure в Dashboard:**
- URL: https://yourdomain.com/webhook
- Event: `FUNDS_RECEIVED`
- Get webhook signing key

**3. Verify & Parse Event:**
```typescript
import {
  WebhookEvent,
  WebhookEventType,
  WEBHOOKS_SIGNATURE_HEADER,
  verifyAndParseWebhook
} from "@lightsparkdev/lightspark-sdk";

app.post("/webhook", async (req, res) => {
  const event = await verifyAndParseWebhook(
    req.body,
    req.headers[WEBHOOKS_SIGNATURE_HEADER],
    process.env.LIGHTSPARK_WEBHOOK_SIGNING_KEY
  );

  if (event.event_type === WebhookEventType.NODE_STATUS) {
    const node_id = event.entity_id;
    // Fetch node details
  } else if (event.event_type === WebhookEventType.WALLET_INCOMING_PAYMENT_FINISHED) {
    const paymentId = event.entity_id;
    const walletId = event.wallet_id;
    // Handle payment
  }
  
  res.send("OK!");
});
```

**4. Query Deposit Object:**
```typescript
let deposit = await client.executeRawQuery(
  getDepositQuery("Deposit:018d8ee3-4443-066a-0000-09a8c905d29e")
);
```

**Deposit Object Example:**
```json
{
  "id": "Deposit:018d8ee3-4443-066a-0000-09a8c905d29e",
  "createdAt": "2024-02-09T17:21:15.331044+00:00",
  "status": "SUCCESS",
  "amount": {
    "originalValue": 80000,
    "originalUnit": "SATOSHI",
    "preferredCurrencyUnit": "USD",
    "preferredCurrencyValueRounded": 5270
  },
  "blockHeight": 829721,
  "destinationAddresses": ["bc1qsffw04rxcwq4dcqzypzy6cld48e3utjgx9v4e..."],
  "transactionHash": "36dd46eb56eba8bce198375912c720a7745b6b5d...",
  "numConfirmations": 24028
}
```

---

### 1.3 Balance Types and Management

#### Types of Balances

**1. Available Balance:**
- Средства для Lightning транзакций
- Total balance - channel reserves

**2. Total Balance:**
- Available balance + locked funds
- Включает pending transactions
- Включает channel reserves
- Может быть withdrawn to L1

**3. Owned Balance:**
- Полная сумма, которой вы владеете
- Включает in-flight outgoing payments
- Включает in-flight withdrawals
- Включает commit fees

**4. Available to Send Balance:**
- Сумма для отправки СЕЙЧАС
- Исключает locked funds
- Исключает channel reserves

**5. Available to Withdraw Balance:**
- Сумма для вывода на L1 СЕЙЧАС
- Обычно = owned_balance
- Исключает in-flight operations

#### Channel Reserves and Dust Limits

**Channel Reserve:**
- Небольшая сумма, зарезервированная в каждом канале
- Для funding L1 channel close transaction

**Dust Limit:**
- Обычно **354 satoshis**
- Плюс размер транзакции: `43 vbytes * L1 fee per vbyte`

#### Querying Node Balance

```typescript
const account = await client.getCurrentAccount();
if (account) {
  let node = await account.getNodes(
    client, 
    1, 
    [BitcoinNetwork.MAINNET], 
    [NODE_ID]
  );
  
  console.log(`Available balance: ${
    node.entities[0].balances?.availableToSendBalance.originalValue
  }`);
}
```

#### Balance Alerts

**Setup в Dashboard → Webhook configuration:**

**HIGH_BALANCE webhook:**
```json
{
  "event_type": "HIGH_BALANCE",
  "event_id": "4b41ae03-01b8-4974-8d26-26a35d28851b",
  "timestamp": "2024-07-24T19:21:52.529Z",
  "entity_id": "WithdrawalRequest:01873482-fe4c-5da6-0000-f9c6e3892b54",
  "data": {
    "network": "MAINNET"
  }
}
```

**LOW_BALANCE webhook:**
```json
{
  "event_type": "LOW_BALANCE",
  "event_id": "...",
  "timestamp": "...",
  "entity_id": "...",
  "data": {
    "network": "MAINNET"
  }
}
```

**Зачем:**
- High balance: предотвращает excessive liquidity
- Low balance: обеспечивает sufficient liquidity
- Triggers для automatic deposits/withdrawals

#### Just-in-Time Inbound Liquidity

**Автоматическая функция Lightspark:**
- Если недостаточно inbound capacity для receiving payment
- Lightspark автоматически создаёт channel
- Обеспечивает sufficient liquidity
- Smooth operation даже при unexpected high-volume

---

### 1.4 Withdrawing from a Node

#### Security Measures

**1. Allow List:**
- Настраивается в Dashboard: https://app.lightspark.com/account#withdrawal-allowlist
- Lightspark проверяет все withdrawals против allow list
- Только админы могут редактировать

**2. Operation Signing Key (OSK):**
- Все withdrawal requests должны быть подписаны OSK

#### Initiating a Withdrawal

```typescript
const withdrawal = await client.requestWithdrawal(
  NODE_ID,
  20_000, // amount in sats
  "bcrt1qs758ursh4q9z627kt3pp5yysm78ddny6txaqgw", // destination address
  WithdrawalMode.WALLET_THEN_CHANNELS
);
```

#### Monitoring Withdrawal Status

**WITHDRAWAL_FINISHED webhook:**
```json
{
  "event_type": "WITHDRAWAL_FINISHED",
  "event_id": "4b41ae03-01b8-4974-8d26-26a35d28851b",
  "timestamp": "2024-07-24T19:21:52.529Z",
  "entity_id": "WithdrawalRequest:01873482-fe4c-5da6-0000-f9c6e3892b54"
}
```

**Full Withdrawal Object:**
```json
{
  "id": "Withdrawal:018d9005-bbf8-1d02-0000-54b71d2c45e4",
  "createdAt": "2024-02-09T22:39:00+00:00",
  "status": "SUCCESS",
  "amount": {
    "originalValue": -80000000,
    "originalUnit": "MILLISATOSHI",
    "preferredCurrencyValueRounded": -5270
  },
  "blockHeight": 829736,
  "destinationAddresses": ["bc1pw55k5693k5hqlj8qgtpec6defyjq..."],
  "transactionHash": "f1c78e159e88355283effc6f47f520a06a7c5339...",
  "fees": {
    "originalValue": 0,
    "originalUnit": "SATOSHI"
  },
  "numConfirmations": 24013
}
```

#### Understanding Withdrawal Fees

- Fees assessed to channel initiator
- Включены в withdrawal response
- Check `fees` field in response

---

## ЧАСТЬ 2: Sending & Receiving Payments

### 2.1 Lightning BOLT11 Invoices

**Пример invoice:**
```
lnbc173u1pntunzppp5a9dtl03wx0qf3jjxx2gxwcl60h7pt6erqhse7np8p3q7pvvpjrcqsp59mg7xgtqazwfae45p00e9gc33mxr65c3cdmhcaplrct0z0ncmmnqxqy8ayqnp4qf0ru8dxm7pht536amqu6re6jzsf4akdc8y7x9ze3npkcd2fh8he2rzjqwghf7zxvfkxq5a6sr65g0gdkv768p83mhsnt0msszapamzx2qvuxqqqqzudjq473cqqqqqqqqqqqqqq9qrzjq25carzepgd4vqsyn44jrk85ezrpju92xyrk9apw4cdjh...
```

#### Decoding Invoices

**Key Fields:**

| Field | Description | Example |
|-------|-------------|---------|
| **Prefix** | Network indicator | `lnbc` (Bitcoin mainnet) |
| **Amount** | Payment amount in millisatoshis | `173u` |
| **Payee Public Key** | Receiving node public key | `025e3e1da6df8375d23aeec...` |
| **Signature** | Proof from payee | `c2a96658ce6dfd6d2df1bdd...` |
| **Timestamp** | Creation time | `1723747393` |
| **Expiry Time** | Validity duration | `259200` (3 days) |
| **Payment Hash** | Security hash | `e95abfbe2e33c098ca4632...` |
| **Description** | Payment memo | Optional |
| **Routing Hints** | Routing assistance | For non-public nodes |

**Tools:**
- Lightspark SDK: встроенные методы
- Online: https://lightningdecoder.com/

#### Zero Amount Invoices

**Что это:**
- Invoice без указанной суммы
- Sender указывает amount при оплате

**Use Cases:**
- Tipping
- Donations
- Unknown amount scenarios

**Ограничение:**
- Как обычные invoices, **single use only**

---

### 2.2 Receiving Payments

#### Creating an Invoice

```typescript
const invoice = await client.createInvoice(
  NODE_ID,
  100000, // millisatoshis (0.000001 BTC)
  "Payment for services" // memo
);
```

**Важно:**
- Привязать invoice к user account
- Для кредитования правильного пользователя при payment webhook

#### Sharing an Invoice

**Методы:**
- Copy/paste string
- QR code scanning
- NFC protocol

#### Handling Incoming Payments with Webhooks

**Subscribe to:** `PAYMENT_FINISHED`

**Webhook Handler:**
```typescript
import express from "express";
import {
  WebhookEvent,
  WebhookEventType,
  WEBHOOKS_SIGNATURE_HEADER,
  verifyAndParseWebhook,
} from "@lightsparkdev/lightspark-sdk";

const app = express();

app.post("/webhook", async (req, res) => {
  const event = await verifyAndParseWebhook(
    req.body,
    req.headers[WEBHOOKS_SIGNATURE_HEADER],
    process.env.LIGHTSPARK_WEBHOOK_SIGNING_KEY,
  );

  if (event.event_type === WebhookEventType.PAYMENT_FINISHED) {
    const paymentId = event.entity_id;
    await handlePaymentFinished(paymentId);
  }

  res.send("OK!");
});
```

**⚠️ Важно:**
- Webhook используется для **OutgoingPayments** И **IncomingPayments**
- For incoming: `entity_id` = `IncomingPayment:UUID`
- For outgoing: `entity_id` = `OutgoingPayment:UUID`

#### Query the Incoming Payment

```typescript
async function handlePaymentFinished(paymentId: string) {
  let incoming = await client.executeRawQuery(
    getTransactionQuery(paymentId)
  );

  if (incoming && incoming.typename === "IncomingPayment") {
    console.log(`Payment status: ${incoming.status}`);
    console.log(`Amount received: ${incoming.amount.originalValue}`);
    // Update internal systems
    // Credit user account
  }
}
```

---

### 2.3 Sending Payments

#### Routing Fees

**Что это:**
- Nodes charge fees for routing payments
- Example: Alice → Bob → Charlie (Bob charges fee)

**Lightspark Predict:**
- Оптимизирует routes
- Минимизирует fees
- Максимизирует success probability

**Recommended Max Fee Formula:**
```javascript
maxFees = Math.max(5, Math.ceil(amount * 0.0017));
// 5 sats OR 17 bps * amount (whichever is greater)
```

**Fee Estimation API:**
```typescript
const feeEstimate = await client.getLightningFeeEstimateForInvoice(
  NODE_ID, 
  invoice
);
```

#### Initiating a Payment

**1. Load Node Signing Key (if OSK node):**
```typescript
await client.loadNodeSigningKey(
  "LightsparkNode:0185789d-9948-f96b-0000-4ae0b696c75f",
  { password: "1234!@#$" } // Test mode
);
```

**2. Pay Invoice:**
```typescript
const payment = await client.payInvoice(
  NODE_ID,
  invoice,
  maxFeesSats
);
```

**3. Debit customer account:**
- **IMMEDIATELY** after `payInvoice` call
- Before payment confirmation
- Response includes transaction `id`

**Response Example:**
```json
{
  "id": "OutgoingPayment:0191d7d7-ed80-1d02-0000-06b61b3be2f8",
  "createdAt": "2024-09-09T17:32:18.176560+00:00",
  "status": "PENDING",
  "amount": {
    "originalValue": 20000,
    "originalUnit": "MILLISATOSHI",
    "preferredCurrencyValueRounded": 1
  },
  "originId": "LightsparkNode:018d28e7-dc4a-f96b-0000-f276772e6fb1",
  "destinationId": "GraphNode:0189a572-6dba-cf00-0000-ac0908d34ea6",
  "paymentRequestData": {
    "encodedPaymentRequest": "lnbcrt200n1pnd7vfz...",
    "bitcoinNetwork": "REGTEST",
    "paymentHash": "36a392d57915da018755b5105a859bae...",
    "amount": {
      "originalValue": 20,
      "originalUnit": "SATOSHI"
    },
    "createdAt": "2024-09-09T17:32:18+00:00",
    "expiresAt": "2024-09-10T17:32:18+00:00",
    "memo": "example script payment"
  },
  "failureReason": null
}
```

**If FAILED:**
- Credit sender's account back

#### Tracking Payment Status with Webhooks

**Same webhook handler as receiving:**
- Check `entity_id` type
- If starts with `OutgoingPayment:` → outgoing
- If starts with `IncomingPayment:` → incoming

#### Query the OutgoingPayment

```typescript
async function handlePaymentFinished(paymentId: string) {
  let outgoing = await client.executeRawQuery(
    getTransactionQuery(paymentId)
  );

  if (outgoing) {
    console.log(`Payment status: ${outgoing.status}`);
    console.log(`Amount sent: ${outgoing.amount.originalValue}`);
    // Update internal systems
  }
}
```

#### Lightning Payment Speed

**Типы переводов:**

**1. Custodial-to-Custodial:**
- Funds held by exchange/service
- **Instant** (processed by custodial body)

**2. Self-Custody Wallets:**
- User controls funds
- Requires user node to be **online**
- May take longer

**Best Practices:**
- Educate users about Lightning experience
- Show snackbar/toast for pending payments
- Explain self-custody requirements
- Test with various wallet types

#### Error Handling and Best Practices

**Common Errors:**

**1. NO_ROUTE - No routes available:**
- **Cause:** Insufficient fees
- **Fix:** Use recommended max fee: `max(5 sats, 17 bps * amount)`

**2. Failed to offline self-custody wallets:**
- **Cause:** Receiver offline
- **Fix:** Inform receiver to stay online

**3. Exceeding max receivable amount:**
- **Cause:** Custodial app limits (e.g. CashApp)
- **Fix:** Try at different time, send smaller amounts

---

## ЧАСТЬ 3: Reconciliation, Error Handling & Testing

### 3.1 Reconciliation

#### Check Node Balance

```typescript
const nodeId = "your_node_id_here";
const query = getLightsparkNodeQuery(nodeId);
const response = await client.executeQuery(query);

if (response && response.balances) {
  console.log(`Owned balance: ${
    response.balances.ownedBalance.originalValue
  } ${response.balances.ownedBalance.originalUnit}`);

  console.log(`Available to send: ${
    response.balances.availableToSendBalance.originalValue
  } ${response.balances.availableToSendBalance.originalUnit}`);

  console.log(`Available to withdraw: ${
    response.balances.availableToWithdrawBalance.originalValue
  } ${response.balances.availableToWithdrawBalance.originalUnit}`);
} else {
  console.log("Unable to fetch balances");
}
```

**Balance Types reminder:**
- **owned_balance**: Total owned (including locked)
- **available_to_send_balance**: Available for Lightning NOW
- **available_to_withdraw_balance**: Available to withdraw to L1 NOW

#### Querying Transactions

```typescript
const account = await client.getCurrentAccount();

if (account) {
  const startDate = new Date('2024-01-01T00:00:00Z').toISOString();
  const endDate = new Date('2024-03-31T23:59:59Z').toISOString();

  const transactions = await account.getTransactions(
    client,
    100, // Limit
    undefined, // No cursor
    undefined, // No type filter
    startDate,
    endDate,
    BitcoinNetwork.MAINNET
  );

  console.log(`Total transactions: ${transactions.count}`);

  transactions.entities.forEach(transaction => {
    console.log(`Transaction ID: ${transaction.id}`);
    console.log(`Amount: ${transaction.amount.originalValue} ${transaction.amount.originalUnit}`);
    console.log(`Status: ${transaction.status}`);
    console.log('---');
  });
}
```

**Pagination:**
- Use `cursor` for pages > 100 transactions

**Transaction Object Example:**
```json
{
  "entities": [
    {
      "id": "Transaction:01234567-89ab-cdef-0123-456789abcdef",
      "created_at": "2024-03-15T10:30:00Z",
      "status": "SUCCESS",
      "amount": {
        "original_value": 100000,
        "original_unit": "SATOSHI",
        "preferred_currency_value_rounded": 3456
      },
      "transaction_hash": "3a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p...",
      "typename": "IncomingPayment"
    },
    {
      "id": "Transaction:fedcba98-7654-3210-fedc-ba9876543210",
      "status": "PENDING",
      "amount": {
        "original_value": 50000,
        "original_unit": "SATOSHI"
      },
      "typename": "OutgoingPayment"
    }
  ],
  "count": 2
}
```

---

### 3.2 Error Handling and Resilience

#### Types of Errors

**Transaction Errors and Payment Failures:**

| Error | Description | Resolution |
|-------|-------------|------------|
| **NO_ROUTE** | No route at current fee rate | 1. Increase max fee: `max(5 sats, 17 bps * amount)` <br> 2. Check receiver online <br> 3. Check network connectivity |
| **INSUFFICIENT_BALANCE** | Not enough local balance | Fund node with more bitcoin |
| **INVOICE_ALREADY_PAID** | Invoice paid previously | Check payment history |
| **INVOICE_EXPIRED** | Invoice expired | Request new invoice |
| **INVOICE_CANCELLED** | Invoice cancelled | Request new invoice |
| **RISK_SCREENING_FAILED** | Recipient failed screening | Review compliance settings |
| **INCORRECT_PAYMENT_DETAILS** | Invalid payment details | Verify details and retry |
| **TIMEOUT** | Payment timed out | Retry with exponential backoff |
| **ERROR** | Non-recoverable error | Check logs, contact support |

**Funding Errors:**

| Error | Description | Resolution |
|-------|-------------|------------|
| **INSUFFICIENT_FUNDS** | Not enough for channel opening | Ensure ≥50,000 sats (test mainnet) |

**Withdrawal Errors:**

| Error | Description | Resolution |
|-------|-------------|------------|
| **INSUFFICIENT_BALANCE** | Not enough balance | Check available balance |

#### Timeouts and Retries

**Idempotency Support:**
- Lightspark supports idempotency for API calls
- Same call with identical parameters → same result
- Prevents duplicate transactions on network failures

**Example with idempotency-key:**
```typescript
const idempotencyKey = "unique_payment_id_123";

const paymentResult = await client.payInvoice({
  nodeId: "your_node_id",
  encodedInvoice: "lnbc...",
  amountMsats: 1000000,
  timeoutSecs: 60,
  maximumFeeMsats: 1000,
  idempotencyKey,
});
```

**Retry Strategies:**

**1. User-Facing Operations (User in Session):**
- Limit: 1-2 retries
- Delay: Short (1 second)
- Feedback: Immediate
- On failure: Clear communication + next steps

**2. Server-to-Server Operations (User Not in Session):**
- Strategy: Exponential backoff
- Max attempts: ~5
- Logging: Log each retry

**Best Practices:**
- Set appropriate timeout limits per operation type
- Log all retry attempts and failures
- Create fallback mechanisms for critical operations
- Manual review processes for edge cases

---

### 3.3 Compliance

#### Chainalysis Integration

**What it is:**
- Blockchain data platform
- Crypto compliance solutions
- Transaction screening
- Due diligence
- Fraud prevention

**Setup:**
1. Obtain Chainalysis API key
2. Provide API key to Lightspark

**Data Passed:**
- **When screening:** Receiver node's pubkey
- **When registering transaction:**
  - Node pubkey
  - Payment hash
  - Amount
  - Timestamp

---

### 3.4 Testing

#### Funding Tests

**Checklist:**
- ✅ Test funding with various amounts
- ✅ Verify withdrawal webhooks received/processed
- ✅ Ensure internal accounting reflects all transactions

#### Balance Tests

**High Balance Scenario:**
- ✅ Verify `HIGH_BALANCE` webhook received
- ✅ Verify system response (e.g. auto-withdraw)

**Low Balance Scenario:**
- ✅ Verify `LOW_BALANCE` webhook received
- ✅ Verify system response (e.g. auto-deposit)

#### Payment Tests

**Send Small Payment (1,000 sats):**
- ✅ Verify system controls for initiating
- ✅ Ensure webhook received
- ✅ Verify user account debited

**Send Large Payment (1,000,000 sats):**
- ✅ Verify system controls for large amounts
- ✅ Ensure webhook received
- ✅ Verify user account debited

**Receive Small Payment (1,000 sats):**
- ✅ Verify system controls
- ✅ Ensure webhook received
- ✅ Verify user account credited

**Receive Large Payment (1,000,000 sats):**
- ✅ Verify system controls
- ✅ Ensure webhook received
- ✅ Verify user account credited

#### Error Handling Tests

**Scenarios:**
- ✅ Simulate 'no route' error
- ✅ Simulate 'insufficient balance' error
- ✅ Attempt to send more than available balance
- ✅ Send payment with invalid/expired invoice

---

## ЧАСТЬ 4: Promoting to Production

### 4.1 Enabling Live Mode

**Steps:**
1. Login: https://app.lightspark.com/
2. Locate: **Test Mode toggle switch**
3. Click to request live mode

**Review Process:**
- Lightspark reviews account
- Typically < 24 hours
- Contact Lightspark contact to expedite

**After Approval:**
- Enter business information
- Select subscription plan

---

### 4.2 Security Setup

#### Node Password Management

**Test Mode:**
- Password: `1234!@#$` (default for REGTEST)

**Live Mode:**
- Must create Mainnet node password
- **Permanent** (set at creation time ONLY)
- Cannot be changed later

**Best Practices:**
1. Set **strong, unique** password
2. Store **securely**
3. Follow password security protocols
4. Never hardcode in application

**Why Important:**
- Decrypts Operation Signing Key (OSK)
- Required for ALL outbound payments
- Required for ALL withdrawals
- Must be stored with API credentials

#### Production Credentials

**Steps:**
1. Generate new API credentials
2. URL: https://app.lightspark.com/api-config
3. Store in environment variables or secrets manager

**Never:**
- ❌ Use test credentials in production
- ❌ Commit to version control
- ❌ Share publicly

#### Funds Recovery Kit

**What it is:**
- Emergency recovery mechanism
- Unilaterally recover funds to L1 if Lightspark inaccessible
- Copies node data to your S3 bucket
- Provides scripts for publishable transactions

**Setup (3 steps):**
1. **Provide L1 recovery address** for receiving Bitcoin
2. **Create S3 bucket** and specify bucket name
3. **Grant Lightspark IAM role** access to S3 bucket

**Final:**
- Review risks
- Acknowledge
- Save configuration

**URL:** https://app.lightspark.com/funds-recovery-kit

---

### 4.3 Production Funding Strategy

**Recommended Approach:**
- **Split initial funding into 2 payments**

**Why:**
- Lightspark has multiple routing nodes
- Each funding transaction → channel to separate routing node
- Improves redundancy
- Reduces likelihood of transaction errors

---

### 4.4 Testing and Deployment

#### Manual Testing

**Before Public Access:**
- ✅ Send payments to crypto exchanges
  - Coinbase
  - CashApp
  - Other Lightning-enabled services
- ✅ Verify user balances updated
- ✅ Run through user-facing flows
- ✅ Validate expected behavior

#### Phased Rollout

**Recommended Phases:**

**Phase 1: 1% users**
- Enable Lightning for small subset
- Monitor closely
- Validate no issues

**Phase 2: 10% users**
- After validating experimental impact
- Expand gradually
- Continue monitoring

**Phase 3: 100% users**
- Full rollout
- Ongoing monitoring

**If Issues:**
- Contact Lightspark team immediately

---

### 4.5 Post-Launch

#### Monitoring and Optimization

**Key Metrics:**
- Transaction success rates
- Total payment volume
- Server error rates
- UX flow completion rates

**Focus Areas:**
- User entry points for transactions
- Payment initiation flows
- Payment completion flows

**Optimization:**
- Streamline UX flows
- Reduce friction
- Minimize confusion
- Improve conversion rates

#### Marketing Support

**Lightspark offers:**
- GTM communications support
- Community showcasing
- Success story sharing

**Contact Lightspark** for marketing assistance

---

### 4.6 Future Expansion

#### UMA (Universal Money Address)

**What it enhances:**
- ✅ Fiat currency sending/receiving
- ✅ Email-like addresses (simplified UX)
- ✅ Cross-border fiat-to-fiat payments

**Benefits:**
- Builds on Lightning infrastructure
- More payment options
- Same speed and efficiency
- Better user experience

**Learn More:**
- https://docs.lightspark.com/uma-sdk/introduction

---

## ЧАСТЬ 5: Creating & Paying Offers (BOLT 12)

### 5.1 What is BOLT 12?

**Definition:**
- Lightning Network specification
- Introduces "offers" - reusable payment requests
- Alternative to single-use BOLT11 invoices

**Main Benefits:**
1. **Reusable Payment Requests** - One offer, multiple payments
2. **Increased Receiver Privacy** - Better anonymity
3. **Censorship Resistance** - Decentralized protocol

**Use Case Example:**
- Cafe creates one offer
- Customers use same offer for multiple payments
- Over days, months, or years

**Wallet Support:**
- Check: https://bolt12.org/
- Growing availability

### 5.2 BOLT 12 vs LNURL

| Feature | BOLT 12 (Offers) | LNURL |
|---------|------------------|-------|
| **Message Format** | Onion routing (encrypted) | HTTP |
| **Privacy** | High (onion encryption) | Lower |
| **Availability** | Growing | Wide |
| **Native Implementation** | Yes | Via HTTP layer |

**When to use BOLT 12:**
- Privacy is important
- Native implementation preferred
- Notable anonymity benefits

**Onion Routing:**
- Uses encryption for privacy
- More details: https://lightningdevkit.org/blog/onion-messages-demystified/

### 5.3 BOLT 12 in Lightspark SDK

**New Types Introduced:**
1. **Offers** - Static payment request (NOT payment request itself)
2. **InvoiceRequests** - Request for payment (response to paying offer)
3. **Bolt12Invoices** - Generated from Offer (actual payment request)

**Key Distinction:**
- Offers ≠ Payment Requests
- Bolt12Invoices = Payment Requests (generated FROM offers)
- Query `PaymentRequests` returns Bolt12Invoices, NOT Offers

**New Mutations:**
- `CreateOffer`
- `PayOffer`

**Support:**
- ✅ Remote Signing nodes
- ⏳ Coming soon for other SDKs and OSK nodes

**Encoding:**
- Follows BOLT 12 specification
- Prefix: `lno` (offers)
- Prefix: `lnr` (invoice requests)

**Example Offer:**
```
lno1dp3wqkrkpp5qqfhmmv0evgq99ud5zpk9336t5gusat044tf4vhs6dm62qvz4swqdqqcqzpgxqyz5vqsp5s25rl2su05pkrd99ph95ja8v45j4gwd7m8k4t32fe79ncxx6eldq9qyyssqm52ke54wpfaaz72q6wnchfv4dy7233rja4c9578ddxxx2lrsmd83vr4e5dz0rwgcy9yfqvv9y0539mge2rkw9837vpxx4k8kq6r23tgq9u2f96
```

**E2E Flow (from LDK):**

![BOLT12 Flow](https://docs.lightspark.com/articles/ldk-bolt12-e2e.svg)

1. Payer requests payment
2. Payee receives via onion message
3. Payee creates invoice
4. Payee sends invoice via onion message
5. Payer receives invoice
6. Payer pays invoice
7. Payment complete

### 5.4 Creating an Offer

**Go SDK Example:**
```go
offer, err := client.CreateOffer(
    nodeId,
    100000, // millisatoshis
    "Coffee shop tip."
)
```

#### No-Amount Offers

**Features:**
- Offer without specified amount
- Sender specifies amount when paying
- Like zero-amount invoices

**Use Cases:**
- Tipping
- Donations
- Variable amount scenarios

**Auto Calculation:**
- If offer has NO amount → use invoice request amount
- If offer HAS amount → invoice request amount MUST match exactly

---

### 5.5 Paying an Offer

```go
outgoingPayment, err := client.PayOffer(
    nodeId,
    encodedOffer,
    timeoutSecs,
    maximumFeesMsats,
    amountMsats,      // Optional: required if offer has no amount
    idempotencyKey    // Optional: auto-generated if not specified
)
```

**Optional Parameters:**

**amountMsats:**
- **Required** if offer has NO amount
- **Optional** if offer has amount
- **Must match** offer amount if both specified

**idempotencyKey:**
- Optional
- Auto-generated if not provided

#### Query for OutgoingPayment

**Updated Fields:**
1. **status** - `PENDING` → `SUCCEEDED` or `FAILED`
2. **payment_hash** - Updated after receiving from remote signer

```go
func handlePaymentFinished(paymentId string) {
    entity, err := client.GetEntity(paymentId)
    if err != nil {
        log.Printf("Error fetching payment: %v", err)
        return
    }

    if outgoingPayment, ok := entity.(*objects.OutgoingPayment); ok {
        fmt.Printf("Payment status: %s\n", outgoingPayment.Status)
        fmt.Printf("Amount sent: %d\n", outgoingPayment.Amount.OriginalValue)
    }
}
```

**Note:**
- OutgoingPayments for invoices and offers are identical
- Use same handling logic

---

## Заключение

### Полный Workflow для Интеграции

**1. Development (Test Mode):**
- ✅ Create Lightspark account
- ✅ Get API credentials (Test)
- ✅ Set up authentication
- ✅ Load OSK with `1234!@#$`
- ✅ Fund node via `fundNode()` simulation
- ✅ Create test invoices
- ✅ Test send/receive payments
- ✅ Implement webhook handlers
- ✅ Test error scenarios

**2. Testing:**
- ✅ Funding tests
- ✅ Balance tests
- ✅ Payment tests (small/large)
- ✅ Error handling tests
- ✅ Reconciliation tests

**3. Production (Live Mode):**
- ✅ Request Live Mode
- ✅ Create production credentials
- ✅ Set node password (permanent!)
- ✅ Set up Funds Recovery Kit
- ✅ Configure production webhooks
- ✅ Split initial funding (2 payments)
- ✅ Manual testing with real exchanges
- ✅ Phased rollout (1% → 10% → 100%)

**4. Post-Launch:**
- ✅ Monitor metrics
- ✅ Optimize UX flows
- ✅ Consider UMA expansion
- ✅ Marketing with Lightspark

---

## SDK Availability

**Current Support:**
- ✅ TypeScript/JavaScript
- ✅ Go
- ✅ Python (основной интерес!)
- ✅ Kotlin
- ✅ Flutter
- ✅ React Native

**BOLT 12 (Offers):**
- ✅ Go SDK v0.16.0+
- ⏳ Other SDKs coming soon
- ✅ Remote Signing nodes
- ⏳ OSK nodes coming soon

---

## Важные Ссылки

**Dashboard:**
- Main: https://app.lightspark.com/
- API Config: https://app.lightspark.com/api-config
- Webhooks: https://app.lightspark.com/webhooks
- Withdrawal Allowlist: https://app.lightspark.com/account#withdrawal-allowlist
- Funds Recovery Kit: https://app.lightspark.com/funds-recovery-kit

**Documentation:**
- API Reference: https://docs.lightspark.com/lightspark-sdk/api-reference/
- Webhooks: https://docs.lightspark.com/lightspark-sdk/webhooks
- Remote Signing: https://docs.lightspark.com/lightspark-sdk/remote-signing
- UMA SDK: https://docs.lightspark.com/uma-sdk/introduction
- BOLT 12: https://bolt12.org/

**Tools:**
- Lightning Decoder: https://lightningdecoder.com/
- LDK Blog: https://lightningdevkit.org/

---

**Дата создания:** 2025-11-04  
**Автор:** AI Assistant  
**Статус:** Complete Developer Guide Documentation  
**Следующий шаг:** Получить API credentials и начать интеграцию
