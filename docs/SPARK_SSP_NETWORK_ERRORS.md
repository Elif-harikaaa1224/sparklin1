# 🌐 Spark SSP Network Errors - Решение проблем

## 🔴 Проблема

При выполнении transfer с кошелька на кошелек возникает ошибка:

```
❌ Ошибка отправки:

Transfer failed: [processSwapBatch] Error details: {
  error: NetworkError: SparkSDKError: Failed to execute GraphQL query
  Context: method: "POST"
  Original Error: fetch failed
```

## 📊 Что это значит?

Это **НЕ проблема вашего бота или HTTP API архитектуры**. 

Это проблема подключения к **Spark SSP (State Service Provider)** - серверу который:
- Хранит состояние Spark блокчейна
- Обрабатывает транзакции
- Синхронизирует кошельки

## 🔍 Причины ошибки

### 1. Spark SSP недоступен
- Сервер на обслуживании
- Сервер перегружен
- Технические работы

### 2. Проблемы с интернетом
- Нет подключения к интернету
- Слабый/нестабильный интернет
- Firewall блокирует запросы

### 3. Временная перегрузка
- Много одновременных запросов
- SSP обрабатывает другие транзакции
- Высокая нагрузка на сеть

## ✅ Решение 1: Retry логика (РЕАЛИЗОВАНО)

В API сервере добавлена автоматическая retry логика:

```javascript
// До 3 попыток для transfer
for (let attempt = 1; attempt <= 3; attempt++) {
  try {
    const transfer = await wallet.transfer(receiver_address, amount_sats);
    return transfer; // Успех!
  } catch (err) {
    if (attempt === 3) throw err; // Последняя попытка
    await sleep(attempt * 1000); // Ждем перед retry
  }
}
```

**Преимущества:**
- ✅ Автоматически повторяет неудавшиеся запросы
- ✅ Экспоненциальная задержка (1s, 2s, 3s)
- ✅ До 3 попыток для transfer
- ✅ До 2 попыток для getBalance

## ✅ Решение 2: Улучшенные сообщения об ошибках

Теперь API возвращает понятные ошибки:

### NetworkError:
```json
{
  "success": false,
  "error": "🌐 Проблема с подключением к Spark SSP. Проверьте интернет соединение или попробуйте позже.",
  "retry": true
}
```

### RESOURCE_EXHAUSTED:
```json
{
  "success": false,
  "error": "⏳ Spark SSP перегружен или на обслуживании. Попробуйте через 1-2 минуты.",
  "retry": true
}
```

### Insufficient funds:
```json
{
  "success": false,
  "error": "💰 Недостаточно средств на кошельке для выполнения transfer.",
  "retry": false
}
```

### Invalid address:
```json
{
  "success": false,
  "error": "❌ Неверный адрес получателя. Используйте адрес формата spark1...",
  "retry": false
}
```

## 🛠️ Решение 3: Ручная retry в Python боте

Если нужна дополнительная retry логика на уровне бота:

```python
from spark_api_client import get_spark_api_client
import asyncio

async def send_transfer_with_retry(mnemonic, receiver, amount, max_retries=3):
    """Transfer с retry логикой"""
    client = get_spark_api_client()
    
    for attempt in range(1, max_retries + 1):
        result = await client.send_spark_transfer(mnemonic, receiver, amount)
        
        # Если успешно - возвращаем результат
        if result.get("success"):
            return result
        
        # Проверяем можно ли повторить
        if not result.get("retry", True):
            # Ошибка не связана с сетью - не повторяем
            return result
        
        # Если это не последняя попытка - ждем
        if attempt < max_retries:
            wait_time = attempt * 2  # 2s, 4s, 6s
            print(f"⏳ Попытка {attempt} не удалась. Жду {wait_time}s перед повтором...")
            await asyncio.sleep(wait_time)
    
    return result

# Использование
result = await send_transfer_with_retry(
    mnemonic="word1 word2 ...",
    receiver="spark1...",
    amount=1000,
    max_retries=5
)
```

## 📋 Решение 4: Проверка статуса SSP

Перед отправкой transfer проверяйте доступность SSP:

```python
async def check_ssp_availability():
    """Проверить доступность Spark SSP"""
    client = get_spark_api_client()
    
    # Пытаемся получить health check
    health = await client.health_check()
    if health.get("status") != "ok":
        return False, "API сервер не доступен"
    
    # Пытаемся получить баланс (минимальный запрос к SSP)
    test_mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    result = await client.get_wallet_balance(test_mnemonic)
    
    if not result.get("success"):
        error = result.get("error", "")
        if "NetworkError" in error or "fetch failed" in error:
            return False, "Spark SSP недоступен"
    
    return True, "SSP работает"

# Использование
available, message = await check_ssp_availability()
if not available:
    print(f"⚠️  {message}")
    print("Подождите несколько минут и попробуйте снова")
else:
    # Можно отправлять transfer
    result = await send_transfer(...)
```

## 🔄 Решение 5: Fallback механизм

Если SSP недоступен, показывайте пользователю альтернативы:

```python
result = await client.send_spark_transfer(mnemonic, receiver, amount)

if not result.get("success"):
    error = result.get("error", "")
    
    if "NetworkError" in error or "SSP" in error:
        # Показываем пользователю альтернативы
        await message.answer(
            "⚠️ Spark SSP временно недоступен.\n\n"
            "Вы можете:\n"
            "1️⃣ Попробовать через 5-10 минут\n"
            "2️⃣ Использовать Lightning Network (если получатель поддерживает)\n"
            "3️⃣ Вывести на Bitcoin L1 адрес\n\n"
            "Выберите вариант или попробуйте позже."
        )
```

## 📊 Мониторинг SSP

Добавьте логирование для отслеживания проблем:

```python
import logging

logger = logging.getLogger(__name__)

async def send_transfer_with_logging(mnemonic, receiver, amount):
    """Transfer с логированием"""
    logger.info(f"Начало transfer: {amount} sats → {receiver[:15]}...")
    
    start_time = time.time()
    result = await client.send_spark_transfer(mnemonic, receiver, amount)
    elapsed = time.time() - start_time
    
    if result.get("success"):
        logger.info(f"✅ Transfer успешен за {elapsed:.2f}s")
        attempts = result.get("attempts", 1)
        if attempts > 1:
            logger.warning(f"⚠️  Потребовалось {attempts} попыток")
    else:
        error = result.get("error", "Unknown")
        logger.error(f"❌ Transfer не удался: {error}")
        logger.error(f"Время выполнения: {elapsed:.2f}s")
    
    return result
```

## 🎯 Рекомендации

### Для разработки:
1. ✅ Используйте retry логику (уже реализовано в API)
2. ✅ Проверяйте `retry` флаг в ответе
3. ✅ Показывайте понятные сообщения пользователю
4. ✅ Логируйте все ошибки для анализа

### Для production:
1. ✅ Добавьте мониторинг SSP статуса
2. ✅ Настройте алерты при частых ошибках
3. ✅ Используйте fallback варианты
4. ✅ Информируйте пользователей о проблемах

### Для пользователей:
1. ⏰ Если ошибка - подождите 1-2 минуты
2. 🔄 Попробуйте снова (бот автоматически повторит)
3. 🌐 Проверьте интернет соединение
4. 📞 Если проблема сохраняется >10 минут - свяжитесь с поддержкой

## ❓ FAQ

### Q: Почему ошибка появляется не всегда?
**A:** Spark SSP - это внешний сервис. Его доступность может меняться в зависимости от нагрузки, технических работ, и т.д.

### Q: Это проблема моего бота?
**A:** Нет. Это проблема подключения к Spark SSP (внешний сервис Spark Network).

### Q: Что делать если ошибка постоянная?
**A:** 
1. Проверьте интернет
2. Проверьте статус Spark Network (Discord, Twitter)
3. Подождите 10-30 минут
4. Свяжитесь с поддержкой Spark

### Q: HTTP API архитектура влияет на это?
**A:** Нет. HTTP API только передает запросы к Spark SDK. Сама ошибка возникает внутри Spark SDK при попытке связаться с SSP.

### Q: Можно ли это полностью исправить?
**A:** Нельзя полностью исключить - это зависит от внешнего сервиса. Но можно:
- ✅ Добавить retry (реализовано)
- ✅ Улучшить обработку ошибок (реализовано)
- ✅ Показывать понятные сообщения (реализовано)
- ✅ Предлагать альтернативы пользователю

## 📝 Итог

**NetworkError при transfer** - это нормальная ситуация для любого приложения работающего с внешними сервисами.

**Что сделано:**
- ✅ Автоматический retry до 3 попыток
- ✅ Понятные сообщения об ошибках
- ✅ Флаг `retry` для определения можно ли повторить
- ✅ Логирование всех попыток

**Бот готов работать даже при временных проблемах с SSP!** 🚀
