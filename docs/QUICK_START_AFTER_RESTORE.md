# 🚀 Быстрый старт после восстановления Flashnet

## ✅ Что сделано

1. **Восстановлено 6 модулей Flashnet** из бекапа bot999
2. **Удалены все моковые данные** - теперь только реальные ошибки
3. **Бот запущен и работает**

## 🧪 Как протестировать

### Шаг 1: Откройте Telegram бота
Найдите вашего бота: `@testsparktradetestbot`

### Шаг 2: Попробуйте купить токен
```
/buy
```

### Шаг 3: Введите адрес токена
Например:
```
btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl
```

### Шаг 4: Следуйте инструкциям бота
- Выберите кошелек
- Выберите сумму (или введите свою)
- Настройте slippage (или оставьте 10%)
- Настройте tip (или оставьте 0.0000001 BTC)
- Подтвердите покупку

### Шаг 5: Выберите метод покупки
Когда появится выбор:
- **"💰 Flashnet AMM"** ← ВЫБЕРИТЕ ЭТО
- "🔸 Spark Money" (не работает)

## ⚠️ Ожидаемые ошибки

### Ошибка 1: Connection Error
```
ERROR: Flashnet API недоступен. Проверьте подключение.
```
**Что делать:**
1. Откройте `flashnet_integration.py`
2. Найдите строку с API URL
3. Проверьте, что URL доступен
4. Проверьте API ключи в `.env`

### Ошибка 2: Authentication Error
```
ERROR: Authentication failed
```
**Что делать:**
1. Откройте `flashnet_auth.py`
2. Проверьте credentials
3. Возможно нужно обновить токен доступа

### Ошибка 3: Pool Not Found
```
ERROR: Пул для токена не найден
```
**Что делать:**
- Этот токен не торгуется на Flashnet
- Попробуйте другой токен
- Или используйте другой DEX

### Ошибка 4: NotImplementedError
```
NotImplementedError: buy_meme_native() не реализован!
```
**Что делать:**
- Вы случайно выбрали "Spark Money" вместо "Flashnet AMM"
- Вернитесь и выберите "💰 Flashnet AMM"

## 📝 Где смотреть ошибки

### В терминале VS Code:
```powershell
# Бот уже запущен, смотрите вывод в терминале
# Каждая ошибка будет видна в консоли
```

### Логи бота:
```powershell
# Просмотр логов
Get-Content bot_error.log -Tail 20
```

## 🔧 Файлы для настройки

### 1. Flashnet Integration
**Файл:** `flashnet_integration.py`
**Что проверить:**
- API endpoints
- Функция `execute_buy()`
- Error handling

### 2. Flashnet Auth
**Файл:** `flashnet_auth.py`
**Что проверить:**
- Credentials
- API tokens
- Auth method

### 3. Environment Variables
**Файл:** `.env`
**Что проверить:**
```env
FLASHNET_API_KEY=your_key_here
FLASHNET_API_URL=https://api.flashnet.example
```

## 💡 Советы по отладке

### 1. Включите подробные логи
Добавьте в начало `flashnet_integration.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Тестируйте по частям
Не пытайтесь исправить все сразу:
1. Сначала проверьте connection
2. Потом auth
3. Потом quote (получение цены)
4. Потом swap (покупка)

### 3. Используйте тестовые токены
Не используйте реальные деньги сразу:
- Используйте testnet если доступен
- Или минимальные суммы (0.0001 BTC)

## 📚 Дополнительная документация

- **Полное описание изменений:** `docs/FLASHNET_RESTORE.md`
- **Структура проекта:** `docs/PROJECT_STRUCTURE.md`
- **История изменений:** `CLEANUP_SUMMARY.md`

## 🆘 Если ничего не работает

### План Б: Вернуть тестовый режим
Если вы не можете настроить Flashnet прямо сейчас:

1. **Откройте `spark_wallet.py`**
2. **Найдите функцию `buy_meme()` (line 631)**
3. **Замените:**
```python
# ВРЕМЕННО верните к тестовому режиму
result = await self.buy_meme_native(...)
```

### План В: Восстановить из bot456
Если что-то пошло не так:
```powershell
Copy-Item "C:\spark-wallet-bot3\spark-wallet-bot456\*" "C:\spark-wallet-bot3\" -Recurse -Force
```

---

**Вопросы?** Просто покажите мне ошибку из терминала, и я помогу исправить!

**Успехов в тестировании! 🚀**
