"""
Обработчики для функции покупки токенов
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from token_info import token_service
from buy_keyboards import create_buy_keyboard, create_tip_keyboard, create_slippage_keyboard
from wallet_service import get_wallet_manager
import sys


async def ensure_user_storage(user_id: int, username: str | None):
    from telegram_bot import ensure_user_storage as ensure_storage_impl

    await ensure_storage_impl(user_id, username)


def get_wallet_states():
    """Получить WalletStates из telegram_bot"""
    from telegram_bot import WalletStates
    return WalletStates


async def cmd_buy_new(message: types.Message, state: FSMContext):
    """
    Команда /buy - начало процесса покупки токена
    """
    WalletStates = get_wallet_states()
    user_id = message.from_user.id
    await ensure_user_storage(user_id, message.from_user.username)
    wallet_manager = get_wallet_manager(user_id)
    print(f"[BUY_CMD] User {user_id} started /buy command")
    
    # Проверяем наличие кошельков
    wallets = wallet_manager.list_wallets()
    if not wallets:
        print(f"[BUY_CMD] User {user_id} has no wallets")
        await message.answer(
            "❌ У вас нет кошельков!\n\n"
            "Сначала создайте кошелек: /create_wallet"
        )
        return
    
    print(f"[BUY_CMD] User {user_id} has {len(wallets)} wallet(s)")
    
    # Устанавливаем состояние ожидания адреса токена
    print(f"[BUY_CMD] Setting state to waiting_token_address")
    await state.set_state(WalletStates.waiting_token_address)
    
    # Проверяем что состояние установлено
    current_state = await state.get_state()
    print(f"[BUY_CMD] Current state after set: {current_state}")
    
    await message.answer(
        "🛒 <b>Покупка токена</b>\n\n"
        "📝 Введите адрес токена или символ:\n\n"
        "📋 <b>Формат адреса токена:</b>\n"
        "• Начинается с <code>btkn1</code>\n"
        "• Пример: <code>btkn1qyg5c7vxq7z2h9j3k4l5m6n7p8</code>\n\n"
        "🔍 <b>Или введите символ:</b>\n"
        "• Например: PEPE, DOGE, SHIB\n"
        "• (поиск по символу в разработке)\n\n"
        "💡 <b>Где взять адрес:</b>\n"
        "• Скопируйте с <a href='https://luminex.io'>Luminex.io</a>\n"
        "• Или из проводника токенов SPARK\n\n"
        "✍️ Введите адрес или символ:",
        parse_mode="HTML"
    )
    print(f"[BUY_CMD] Sent prompt to user {user_id}")


async def handle_token_address_input(message: types.Message, state: FSMContext):
    """
    Обработка ввода адреса/символа токена
    """
    WalletStates = get_wallet_states()
    user_id = message.from_user.id
    await ensure_user_storage(user_id, message.from_user.username)
    wallet_manager = get_wallet_manager(user_id)
    token_input = message.text.strip()
    
    print(f"[BUY_HANDLER] User {user_id} entered token: {token_input}")
    print(f"[BUY_HANDLER] Token length: {len(token_input)}")
    print(f"[BUY_HANDLER] Starts with btkn1: {token_input.startswith('btkn1')}")
    
    # Проверяем формат адреса
    if not token_input.startswith("btkn1") and len(token_input) < 3:
        print(f"[BUY_HANDLER] Token too short or wrong prefix")
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Введите адрес токена (btkn1...) или символ (минимум 3 символа)"
        )
        return
    
    # Если это не адрес, а символ - показываем заглушку
    if not token_input.startswith("btkn1"):
        print(f"[BUY_HANDLER] Not a btkn1 address, treating as symbol")
        await message.answer(
            f"🔍 Поиск токена по символу '{token_input}'...\n\n"
            "⚠️ Функция поиска по символу в разработке.\n"
            "Пожалуйста, используйте полный адрес токена (btkn1...)"
        )
        return
    
    # Валидация адреса
    print(f"[BUY_HANDLER] Validating address...")
    is_valid = wallet_manager.validate_spark_btkn_address(token_input)
    print(f"[BUY_HANDLER] Validation result: {is_valid}")
    
    if not is_valid:
        print(f"[BUY_HANDLER] Address validation FAILED")
        await message.answer(
            "❌ Неверный адрес токена!\n\n"
            "📋 <b>Требования к адресу:</b>\n"
            "• Должен начинаться с <code>btkn1</code>\n"
            "• Длина: 20-120 символов\n"
            "• Только латинские буквы и цифры (без 1, b, i, o)\n\n"
            "📝 <b>Пример правильного адреса:</b>\n"
            "<code>btkn1qyg5c7vxq7z2h9j3k4l5m6n7p8q9r0s2t3u4v5w6x7y8z9</code>\n\n"
            "💡 <b>Где взять адрес:</b>\n"
            "• Скопируйте из Luminex.io\n"
            "• Или из проводника токенов SPARK\n\n"
            "🔄 Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    print(f"[BUY_HANDLER] Address is VALID, fetching token info...")
    
    # Получаем информацию о токене
    try:
        await message.answer("⏳ Загрузка информации о токене...")
        
        token_info = await token_service.get_token_info(token_input)
        
        # Получаем список кошельков пользователя
        wallets = wallet_manager.list_wallets()
        wallet_list = list(wallets.keys())
        
        # Получаем баланс первого кошелька
        first_wallet = wallet_list[0]
        wallet_address = wallets[first_wallet]['address']
        
        try:
            balance_info = await wallet_manager.get_wallet_balance(wallet_address)
            balance_sats = balance_info.get("balance_sats", 0)
        except:
            balance_sats = 0
        
        # Сохраняем данные в состояние
        await state.update_data(
            token_address=token_input,
            token_info=token_info,
            selected_wallet="W1",
            selected_wallet_name=first_wallet,
            selected_amount=0.001,  # По умолчанию 0.001 BTC
            buy_tip=0.0000001,      # По умолчанию
            slippage=10.0,          # По умолчанию 10%
            wallet_balance_sats=balance_sats
        )
        
        # Формируем сообщение с информацией о токене
        message_text = await format_buy_message(token_info, balance_sats, "W1")
        
        # Создаем клавиатуру
        keyboard = create_buy_keyboard(
            wallets=wallet_list,
            selected_wallet="W1",
            selected_amount=0.001,
            buy_tip=0.0000001,
            slippage=10.0
        )
        
        # Переходим в состояние подтверждения покупки
        await state.set_state(WalletStates.buy_confirming)
        
        await message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to load token info: {error_msg}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        
        await message.answer(
            f"❌ Ошибка при загрузке информации о токене:\n{error_msg}\n\n"
            "Попробуйте еще раз: /buy"
        )
        await state.clear()


async def format_buy_message(token_info: dict, wallet_balance_sats: int, selected_wallet: str) -> str:
    """
    Форматирование сообщения с информацией о покупке токена
    """
    symbol = token_info.get("symbol", "UNKNOWN")
    name = token_info.get("name", "Unknown Token")
    address = token_info.get("address", "")
    price = token_info.get("price_usd", 0)
    liquidity = token_info.get("liquidity_usd", 0)
    market_cap = token_info.get("market_cap_usd", 0)
    
    # Форматируем значения
    price_str = token_service.format_price(price)
    liq_str = token_service.format_liquidity(liquidity)
    mc_str = token_service.format_market_cap(market_cap)
    
    # Сокращаем адрес для отображения
    addr_short = f"{address[:10]}...{address[-10:]}" if len(address) > 20 else address
    
    # Форматируем баланс в SATS с USD (как в главном меню)
    try:
        from btc_price import btc_price_service
        # Получаем цену BTC асинхронно
        btc_price = await btc_price_service.get_btc_price_usd()
        usd_value = btc_price_service.sats_to_usd(wallet_balance_sats, btc_price)
        usd_str = btc_price_service.format_usd(usd_value)
        balance_display = f"{wallet_balance_sats:,} SATS ({usd_str})"
    except Exception as e:
        print(f"[DEBUG] Error getting USD conversion: {e}", file=sys.stderr)
        balance_display = f"{wallet_balance_sats:,} SATS"
    
    message = (
        f"🛒 <b>Buy ${symbol}</b> — {name} 📈\n\n"
        f"📍 <code>{addr_short}</code>\n\n"
        f"💰 Balance: {balance_display} — {selected_wallet}\n"
        f"💵 Price: {price_str}\n"
        f"💧 LIQ: {liq_str} — 📊 MC: {mc_str}\n\n"
        f"👇 Select options below:"
    )
    
    return message


async def handle_buy_refresh(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка нажатия кнопки Refresh
    """
    await callback.answer("🔄 Обновление данных...")
    
    data = await state.get_data()
    token_address = data.get("token_address")
    
    if not token_address:
        await callback.message.answer("❌ Ошибка: токен не выбран")
        return
    
    try:
        # Обновляем информацию о токене
        token_info = await token_service.get_token_info(token_address)
        
        # Обновляем баланс кошелька
        selected_wallet_name = data.get("selected_wallet_name")
        wallets = wallet_manager.list_wallets()
        wallet_address = wallets[selected_wallet_name]['address']
        
        try:
            balance_info = await wallet_manager.get_wallet_balance(wallet_address)
            balance_sats = balance_info.get("balance_sats", 0)
        except:
            balance_sats = data.get("wallet_balance_sats", 0)
        
        # Обновляем данные в состоянии
        await state.update_data(
            token_info=token_info,
            wallet_balance_sats=balance_sats
        )
        
        # Обновляем сообщение
        message_text = await format_buy_message(
            token_info,
            balance_sats,
            data.get("selected_wallet", "W1")
        )
        
        # Получаем список кошельков
        wallet_list = list(wallets.keys())
        
        # Обновляем клавиатуру
        keyboard = create_buy_keyboard(
            wallets=wallet_list,
            selected_wallet=data.get("selected_wallet", "W1"),
            selected_amount=data.get("selected_amount", 0.001),
            buy_tip=data.get("buy_tip", 0.0000001),
            slippage=data.get("slippage", 10.0)
        )
        
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"[ERROR] Refresh failed: {e}", file=sys.stderr)
        await callback.answer("❌ Ошибка обновления", show_alert=True)


async def handle_buy_wallet_selection(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка выбора кошелька
    """
    # Формат callback_data: "buy_wallet_W1_wallet_name"
    parts = callback.data.split("_", 3)
    if len(parts) < 4:
        await callback.answer("❌ Ошибка")
        return
    
    wallet_label = parts[2]  # W1, W2, etc.
    wallet_name = parts[3]
    
    await callback.answer(f"✓ Выбран {wallet_label}")
    
    # Получаем баланс выбранного кошелька
    wallets = wallet_manager.list_wallets()
    wallet_address = wallets[wallet_name]['address']
    
    try:
        balance_info = await wallet_manager.get_wallet_balance(wallet_address)
        balance_sats = balance_info.get("balance_sats", 0)
    except:
        balance_sats = 0
    
    # Обновляем состояние
    data = await state.get_data()
    await state.update_data(
        selected_wallet=wallet_label,
        selected_wallet_name=wallet_name,
        wallet_balance_sats=balance_sats
    )
    
    # Обновляем сообщение
    token_info = data.get("token_info", {})
    message_text = await format_buy_message(token_info, balance_sats, wallet_label)
    
    wallet_list = list(wallets.keys())
    keyboard = create_buy_keyboard(
        wallets=wallet_list,
        selected_wallet=wallet_label,
        selected_amount=data.get("selected_amount", 0.001),
        buy_tip=data.get("buy_tip", 0.0000001),
        slippage=data.get("slippage", 10.0)
    )
    
    await callback.message.edit_text(
        message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def handle_buy_amount_selection(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка выбора суммы покупки
    """
    # Формат: "buy_amount_0.001" или "buy_amount_custom"
    amount_str = callback.data.replace("buy_amount_", "")
    
    if amount_str == "custom":
        await callback.answer("✏️ Введите сумму")
        await state.set_state(WalletStates.waiting_custom_amount)
        await callback.message.answer(
            "💰 <b>Введите сумму в BTC:</b>\n\n"
            "Например: <code>0.0005</code>\n"
            "Или отправьте /cancel для отмены",
            parse_mode="HTML"
        )
        return
    
    try:
        amount = float(amount_str)
    except ValueError:
        await callback.answer("❌ Неверная сумма")
        return
    
    await callback.answer(f"✓ Выбрано {amount} BTC")
    
    # Обновляем состояние
    data = await state.get_data()
    await state.update_data(selected_amount=amount)
    
    # Обновляем клавиатуру
    wallets = wallet_manager.list_wallets()
    wallet_list = list(wallets.keys())
    
    keyboard = create_buy_keyboard(
        wallets=wallet_list,
        selected_wallet=data.get("selected_wallet", "W1"),
        selected_amount=amount,
        buy_tip=data.get("buy_tip", 0.0000001),
        slippage=data.get("slippage", 10.0)
    )
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)


async def handle_custom_amount_input(message: types.Message, state: FSMContext):
    """
    Обработка ввода custom суммы
    """
    amount_str = message.text.strip()
    
    try:
        amount = float(amount_str)
        
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        if amount > 1:  # Максимум 1 BTC за раз
            await message.answer("❌ Максимальная сумма: 1 BTC")
            return
        
        # Обновляем состояние
        data = await state.get_data()
        await state.update_data(selected_amount=amount)
        await state.set_state(WalletStates.buy_confirming)
        
        # Показываем обновленное меню
        token_info = data.get("token_info", {})
        balance_sats = data.get("wallet_balance_sats", 0)
        selected_wallet = data.get("selected_wallet", "W1")
        
        message_text = await format_buy_message(token_info, balance_sats, selected_wallet)
        
        wallets = wallet_manager.list_wallets()
        wallet_list = list(wallets.keys())
        
        keyboard = create_buy_keyboard(
            wallets=wallet_list,
            selected_wallet=selected_wallet,
            selected_amount=amount,
            buy_tip=data.get("buy_tip", 0.0000001),
            slippage=data.get("slippage", 10.0)
        )
        
        await message.answer(
            f"✅ Сумма установлена: {amount} BTC\n\n" + message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Введите число, например: <code>0.0005</code>",
            parse_mode="HTML"
        )


async def handle_buy_set_tip(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка нажатия кнопки Buy Tip
    """
    await callback.answer("⚡ Настройка комиссии")
    
    keyboard = create_tip_keyboard()
    
    await callback.message.answer(
        "⚡ <b>Buy Tip - Дополнительная комиссия</b>\n\n"
        "Выберите размер дополнительной комиссии для ускорения транзакции:\n\n"
        "💡 Чем больше tip, тем быстрее подтвердится транзакция",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def handle_tip_selection(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка выбора buy tip
    """
    # Формат: "tip_0.0000001" или "tip_custom" или "tip_back"
    if callback.data == "tip_back":
        await callback.message.delete()
        await callback.answer("Возврат к покупке")
        return
    
    if callback.data == "tip_custom":
        await callback.answer("✏️ Введите tip")
        await state.set_state(WalletStates.waiting_buy_tip)
        await callback.message.answer(
            "⚡ <b>Введите размер Buy Tip в BTC:</b>\n\n"
            "Например: <code>0.0000005</code>\n"
            "Или отправьте /cancel для отмены",
            parse_mode="HTML"
        )
        return
    
    tip_str = callback.data.replace("tip_", "")
    
    try:
        tip = float(tip_str)
    except ValueError:
        await callback.answer("❌ Ошибка")
        return
    
    await callback.answer(f"✓ Buy Tip: {tip:.8f} BTC")
    
    # Обновляем состояние
    await state.update_data(buy_tip=tip)
    await state.set_state(WalletStates.buy_confirming)
    
    await callback.message.delete()
    
    # Показываем обновленное главное меню
    data = await state.get_data()
    token_info = data.get("token_info", {})
    balance_sats = data.get("wallet_balance_sats", 0)
    selected_wallet = data.get("selected_wallet", "W1")
    
    message_text = await format_buy_message(token_info, balance_sats, selected_wallet)
    
    wallets = wallet_manager.list_wallets()
    wallet_list = list(wallets.keys())
    
    keyboard = create_buy_keyboard(
        wallets=wallet_list,
        selected_wallet=selected_wallet,
        selected_amount=data.get("selected_amount", 0.001),
        buy_tip=tip,
        slippage=data.get("slippage", 10.0)
    )
    
    await callback.message.answer(
        message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# Продолжение следует в следующем файле...
