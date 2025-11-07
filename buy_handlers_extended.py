"""
Дополнительные обработчики для покупки (slippage, подтверждение, выполнение)
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from wallet_service import get_wallet_manager
from telegram_bot import WalletStates, add_position
from token_info import token_service
from buy_keyboards import create_buy_keyboard, create_slippage_keyboard
import sys


async def ensure_user_storage(user_id: int, username: str | None):
    from telegram_bot import ensure_user_storage as ensure_storage_impl

    await ensure_storage_impl(user_id, username)


async def handle_buy_set_slippage(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка нажатия кнопки Slippage
    """
    await callback.answer("📊 Настройка slippage")
    
    keyboard = create_slippage_keyboard()
    
    await callback.message.answer(
        "📊 <b>Slippage - Проскальзывание</b>\n\n"
        "Выберите максимальный процент проскальзывания цены:\n\n"
        "💡 Чем выше slippage, тем больше шансов что сделка пройдет,\n"
        "но цена может отличаться от ожидаемой",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def handle_slippage_selection(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка выбора slippage
    """
    # Формат: "slippage_10.0" или "slippage_custom" или "slippage_back"
    if callback.data == "slippage_back":
        await callback.message.delete()
        await callback.answer("Возврат к покупке")
        return
    
    if callback.data == "slippage_custom":
        await callback.answer("✏️ Введите slippage")
        await state.set_state(WalletStates.waiting_slippage)
        await callback.message.answer(
            "📊 <b>Введите slippage в %:</b>\n\n"
            "Например: <code>15</code> или <code>20.5</code>\n"
            "Минимум: 0.1%, Максимум: 50%\n\n"
            "Или отправьте /cancel для отмены",
            parse_mode="HTML"
        )
        return
    
    slippage_str = callback.data.replace("slippage_", "")
    
    try:
        slippage = float(slippage_str)
    except ValueError:
        await callback.answer("❌ Ошибка")
        return
    
    await callback.answer(f"✓ Slippage: {slippage:.1f}%")
    
    # Обновляем состояние
    await state.update_data(slippage=slippage)
    await state.set_state(WalletStates.buy_confirming)
    
    await callback.message.delete()
    
    # Показываем обновленное главное меню
    data = await state.get_data()
    token_info = data.get("token_info", {})
    balance_btc = data.get("wallet_balance", "0.00000000")
    selected_wallet = data.get("selected_wallet", "W1")
    
    message_text = format_buy_message(token_info, balance_btc, selected_wallet)
    user_id = callback.from_user.id
    await ensure_user_storage(user_id, callback.from_user.username)
    wallet_manager = get_wallet_manager(user_id)
    wallets = wallet_manager.list_wallets()
    wallet_list = list(wallets.keys())
    
    keyboard = create_buy_keyboard(
        wallets=wallet_list,
        selected_wallet=selected_wallet,
        selected_amount=data.get("selected_amount", 0.001),
        buy_tip=data.get("buy_tip", 0.0000001),
        slippage=slippage
    )
    
    await callback.message.answer(
        message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def handle_custom_tip_input(message: types.Message, state: FSMContext):
    """
    Обработка ввода custom buy tip
    """
    tip_str = message.text.strip()
    
    try:
        tip = float(tip_str)
        
        if tip < 0:
            await message.answer("❌ Tip не может быть отрицательным")
            return
        
        if tip > 0.001:  # Максимум 0.001 BTC
            await message.answer("❌ Максимальный tip: 0.001 BTC")
            return
        
        # Обновляем состояние
        await state.update_data(buy_tip=tip)
        await state.set_state(WalletStates.buy_confirming)
        
        # Показываем обновленное меню
        data = await state.get_data()
        token_info = data.get("token_info", {})
        balance_btc = data.get("wallet_balance", "0.00000000")
        selected_wallet = data.get("selected_wallet", "W1")
        
        message_text = format_buy_message(token_info, balance_btc, selected_wallet)
        user_id = message.from_user.id
        await ensure_user_storage(user_id, message.from_user.username)
        wallet_manager = get_wallet_manager(user_id)
        wallets = wallet_manager.list_wallets()
        wallet_list = list(wallets.keys())
        
        keyboard = create_buy_keyboard(
            wallets=wallet_list,
            selected_wallet=selected_wallet,
            selected_amount=data.get("selected_amount", 0.001),
            buy_tip=tip,
            slippage=data.get("slippage", 10.0)
        )
        
        await message.answer(
            f"✅ Buy Tip установлен: {tip:.8f} BTC\n\n" + message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Введите число, например: <code>0.0000005</code>",
            parse_mode="HTML"
        )


async def handle_custom_slippage_input(message: types.Message, state: FSMContext):
    """
    Обработка ввода custom slippage
    """
    slippage_str = message.text.strip()
    
    try:
        slippage = float(slippage_str)
        
        if slippage < 0.1:
            await message.answer("❌ Минимальный slippage: 0.1%")
            return
        
        if slippage > 50:
            await message.answer("❌ Максимальный slippage: 50%")
            return
        
        # Обновляем состояние
        await state.update_data(slippage=slippage)
        await state.set_state(WalletStates.buy_confirming)
        
        # Показываем обновленное меню
        data = await state.get_data()
        token_info = data.get("token_info", {})
        balance_btc = data.get("wallet_balance", "0.00000000")
        selected_wallet = data.get("selected_wallet", "W1")
        
        message_text = format_buy_message(token_info, balance_btc, selected_wallet)
        user_id = message.from_user.id
        await ensure_user_storage(user_id, message.from_user.username)
        wallet_manager = get_wallet_manager(user_id)
        wallets = wallet_manager.list_wallets()
        wallet_list = list(wallets.keys())
        
        keyboard = create_buy_keyboard(
            wallets=wallet_list,
            selected_wallet=selected_wallet,
            selected_amount=data.get("selected_amount", 0.001),
            buy_tip=data.get("buy_tip", 0.0000001),
            slippage=slippage
        )
        
        await message.answer(
            f"✅ Slippage установлен: {slippage:.1f}%\n\n" + message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Введите число, например: <code>15</code> или <code>20.5</code>",
            parse_mode="HTML"
        )


async def handle_buy_confirm(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка нажатия кнопки Buy Now - показ финального подтверждения
    """
    data = await state.get_data()
    
    token_info = data.get("token_info", {})
    selected_amount = data.get("selected_amount", 0.001)
    buy_tip = data.get("buy_tip", 0.0000001)
    slippage = data.get("slippage", 10.0)
    selected_wallet = data.get("selected_wallet", "W1")
    balance_btc = float(data.get("wallet_balance", "0.0"))
    
    # Рассчитываем детали покупки
    token_address = token_info.get("address", "")
    symbol = token_info.get("symbol", "UNKNOWN")
    price_usd = token_info.get("price_usd", 0)
    
    # Рассчитываем количество токенов
    calc = await token_service.calculate_tokens_for_btc(token_address, selected_amount)
    token_amount = calc.get("token_amount", 0)
    
    # Итоговая сумма с tip
    total_btc = selected_amount + buy_tip
    
    # Проверка баланса
    if balance_btc < total_btc:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    # Формируем сообщение подтверждения
    confirm_message = (
        f"🔔 <b>Подтверждение покупки</b>\n\n"
        f"🪙 Токен: <b>${symbol}</b>\n"
        f"📍 <code>{token_address[:15]}...{token_address[-10:]}</code>\n\n"
        f"💰 Вы платите: <b>{selected_amount:.8f} BTC</b>\n"
        f"⚡ Buy Tip: <b>{buy_tip:.8f} BTC</b>\n"
        f"📊 Slippage: <b>{slippage:.1f}%</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💵 Итого: <b>{total_btc:.8f} BTC</b>\n\n"
        f"📦 Вы получите: <b>~{token_amount:,.2f} {symbol}</b>\n"
        f"💵 Цена за токен: <b>${price_usd:.8f}</b>\n\n"
        f"💼 Кошелек: <b>{selected_wallet}</b>\n\n"
        f"⚠️ <i>Подтвердите операцию нажав кнопку ниже</i>"
    )
    
    # Клавиатура подтверждения
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Confirm Purchase", callback_data="buy_execute"),
        ],
        [
            types.InlineKeyboardButton(text="❌ Cancel", callback_data="buy_cancel")
        ]
    ])
    
    await callback.message.edit_text(
        confirm_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await callback.answer("👆 Проверьте детали и подтвердите")


async def handle_buy_execute(callback: types.CallbackQuery, state: FSMContext):
    """
    Выполнение покупки токена
    """
    await callback.answer("⏳ Выполнение покупки...")
    
    data = await state.get_data()
    user_id = callback.from_user.id
    await ensure_user_storage(user_id, callback.from_user.username)
    wallet_manager = get_wallet_manager(user_id)
    
    token_info = data.get("token_info", {})
    token_address = token_info.get("address", "")
    symbol = token_info.get("symbol", "UNKNOWN")
    selected_amount = data.get("selected_amount", 0.001)
    buy_tip = data.get("buy_tip", 0.0000001)
    slippage = data.get("slippage", 10.0)
    selected_wallet_name = data.get("selected_wallet_name")
    
    try:
        await callback.message.edit_text(
            f"⏳ <b>Покупка {symbol}...</b>\n\n"
            f"Пожалуйста, подождите...",
            parse_mode="HTML"
        )
        
        # Конвертируем BTC в satoshis
        amount_sats = token_service.btc_to_sats(selected_amount)
        tip_sats = token_service.btc_to_sats(buy_tip)
        
        # Выполняем покупку через wallet manager
        result = await wallet_manager.buy_meme(
            contract_address=token_address,
            amount_sats=amount_sats,
            wallet_name=selected_wallet_name,
            slippage=slippage,
            priority_fee_sats=tip_sats
        )
        
        # Проверяем статус результата
        if result.get("status") != "success":
            error_msg = result.get("error", result.get("message", "Неизвестная ошибка"))
            raise Exception(error_msg)
        
        # Сохраняем позицию
        add_position(
            user_id=user_id,
            wallet_name=selected_wallet_name,
            contract_address=token_address,
            amount_sats=amount_sats,
            action="buy"
        )
        
        # Рассчитываем количество токенов
        calc = await token_service.calculate_tokens_for_btc(token_address, selected_amount)
        token_amount = calc.get("token_amount", 0)
        
        # Получаем TxID
        txid = result.get("txid")
        if not txid:
            raise Exception("Транзакция не содержит TxID! Покупка не выполнена.")
        
        # Сообщение об успехе
        success_message = (
            f"✅ <b>Покупка выполнена!</b>\n\n"
            f"🪙 Куплено: <b>{token_amount:,.2f} {symbol}</b>\n"
            f"💰 Потрачено: <b>{selected_amount:.8f} BTC</b>\n"
            f"⚡ Комиссия: <b>{buy_tip:.8f} BTC</b>\n\n"
            f"📋 Transaction ID:\n"
            f"<code>{txid}</code>\n\n"
            f"🎉 Токены будут зачислены на ваш кошелек в течение нескольких секунд"
        )
        
        await callback.message.edit_text(
            success_message,
            parse_mode="HTML"
        )
        
        print(f"[SUCCESS] User {user_id} bought {token_amount} {symbol} for {selected_amount} BTC")
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Buy execution failed: {error_msg}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при покупке!</b>\n\n"
            f"Детали: {error_msg}\n\n"
            f"Ваши средства в безопасности.\n"
            f"Попробуйте еще раз: /buy",
            parse_mode="HTML"
        )
    
    finally:
        await state.clear()


async def handle_buy_cancel(callback: types.CallbackQuery, state: FSMContext):
    """
    Отмена покупки
    """
    await callback.answer("❌ Покупка отменена")
    
    await callback.message.edit_text(
        "❌ <b>Покупка отменена</b>\n\n"
        "Чтобы купить токен, используйте /buy",
        parse_mode="HTML"
    )
    
    await state.clear()


def format_buy_message(token_info: dict, wallet_balance: str, selected_wallet: str) -> str:
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
    
    message = (
        f"🛒 <b>Buy ${symbol}</b> — {name} 📈\n\n"
        f"📍 <code>{addr_short}</code>\n\n"
        f"💰 Balance: {wallet_balance} BTC — {selected_wallet}\n"
        f"💵 Price: {price_str}\n"
        f"💧 LIQ: {liq_str} — 📊 MC: {mc_str}\n\n"
        f"👇 Select options below:"
    )
    
    return message
