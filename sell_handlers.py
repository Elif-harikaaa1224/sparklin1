"""
Обработчики для функции продажи токенов
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from token_info import token_service
from sell_keyboards import create_sell_keyboard, create_wallet_selection_keyboard_sell
from wallet_service import get_wallet_manager
import sys


async def ensure_user_storage(user_id: int, username: str | None):
    from telegram_bot import ensure_user_storage as ensure_storage_impl

    await ensure_storage_impl(user_id, username)


def get_wallet_states():
    """Получить WalletStates из telegram_bot"""
    from telegram_bot import WalletStates
    return WalletStates

def get_token_position(user_id: int, wallet_name: str, token_address: str) -> dict:
    """Получить позицию по токену"""
    from telegram_bot import load_positions
    positions = load_positions(user_id)
    if wallet_name not in positions:
        return None
    
    if token_address not in positions[wallet_name]:
        return None
    
    pos = positions[wallet_name][token_address]
    
    return {
        "amount_tokens": pos.get("amount_sats", 0),
        "total_bought": pos.get("total_bought", 0),
        "total_sold": pos.get("total_sold", 0),
        "wallet_name": wallet_name
    }


async def cmd_sell(message: types.Message, state: FSMContext):
    """
    Команда /sell - начало процесса продажи токена
    """
    WalletStates = get_wallet_states()
    user_id = message.from_user.id
    await ensure_user_storage(user_id, message.from_user.username)
    wallet_manager = get_wallet_manager(user_id)
    print(f"[DEBUG] User {user_id} started /sell command")
    
    # Проверяем наличие кошельков
    wallets = wallet_manager.list_wallets()
    if not wallets:
        await message.answer(
            "❌ You don't have any wallets!\n\n"
            "First create a wallet: /create_wallet"
        )
        return
    
    # Проверяем был ли передан адрес токена
    text_parts = message.text.split()
    if len(text_parts) > 1:
        # Адрес передан, показываем окно продажи сразу
        token_addr = text_parts[1].strip()
        await show_sell_window(message, state, token_addr)
    else:
        # Запрашиваем адрес токена
        await state.set_state(WalletStates.waiting_sell_token_address)
        
        await message.answer(
            "💸 <b>Продажа токена</b>\n\n"
            "📝 Введите адрес токена для продажи:\n\n"
            "📋 <b>Формат адреса:</b>\n"
            "• Начинается с <code>btkn1</code>\n"
            "• Пример: <code>btkn1qyg5c7vxq7z2h9j3k4l5m6n7p8</code>\n\n"
            "💡 <b>Подсказка:</b>\n"
            "• Посмотрите адрес в /portfolio\n"
            "• Или скопируйте с <a href='https://luminex.io'>Luminex.io</a>\n\n"
            "✍️ Введите адрес токена:",
            parse_mode="HTML"
        )


async def show_sell_window(message: types.Message, state: FSMContext, token_addr: str):
    """Показать окно продажи с полной информацией"""
    WalletStates = get_wallet_states()
    user_id = message.from_user.id
    await ensure_user_storage(user_id, message.from_user.username)
    wallet_manager = get_wallet_manager(user_id)
    
    # Валидация адреса
    if not wallet_manager.validate_spark_btkn_address(token_addr):
        await message.answer(
            "❌ Неверный адрес токена!\n\n"
            "📋 <b>Требования к адресу:</b>\n"
            "• Должен начинаться с <code>btkn1</code>\n"
            "• Длина: 20-120 символов\n"
            "• Только латинские буквы и цифры (без 1, b, i, o)\n\n"
            "📝 <b>Пример правильного адреса:</b>\n"
            "<code>btkn1qyg5c7vxq7z2h9j3k4l5m6n7p8q9r0s2t3u4v5w6x7y8z9</code>\n\n"
            "💡 <b>Где взять адрес:</b>\n"
            "• Из вашего портфеля /portfolio\n"
            "• Или скопируйте из Luminex.io\n\n"
            "🔄 Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await message.answer("⏳ Loading token data...")
    
    try:
        # Получаем информацию о токене
        token_info = await token_service.get_token_info(token_addr)
        
        # Получаем кошельки
        wallets = wallet_manager.list_wallets()
        first_wallet = list(wallets.keys())[0]
        wallet_addr = wallets[first_wallet]['address']
        
        # Получаем позицию пользователя
        position = get_token_position(user_id, first_wallet, token_addr)
        
        if not position or position['amount_tokens'] == 0:
            await message.answer(
                "⚠️ You don't have any of this token!\n\n"
                f"Token: <code>{token_addr}</code>\n"
                "Buy tokens using /buy",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Получаем баланс кошелька
        try:
            bal = await wallet_manager.get_wallet_balance(wallet_addr)
            balance_btc = bal.get("balance_btc", "0.00000000")
        except:
            balance_btc = "0.00000000"
        
        # Сохраняем данные в состояние
        await state.update_data(
            token_address=token_addr,
            token_info=token_info,
            selected_wallet="W1",
            selected_wallet_name=first_wallet,
            selected_percent=100,
            sell_slippage=10.0,
            wallet_balance=balance_btc,
            position=position
        )
        
        # Устанавливаем состояние
        await state.set_state(WalletStates.sell_confirming)
        
        # Отправляем сообщение с окном продажи
        await send_sell_message(message, state, user_id)
        
    except Exception as e:
        print(f"[ERROR] Failed to show sell window: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(f"❌ Error: {str(e)}")
        await state.clear()


async def send_sell_message(message: types.Message, state: FSMContext, user_id: int):
    """Отправить/обновить сообщение окна продажи"""
    username = getattr(getattr(message, "from_user", None), "username", None)
    await ensure_user_storage(user_id, username)
    wallet_manager = get_wallet_manager(user_id)
    data = await state.get_data()
    
    token_addr = data['token_address']
    token_info = data['token_info']
    selected_wallet = data['selected_wallet']
    selected_percent = data.get('selected_percent', 100)
    slippage = data.get('sell_slippage', 10.0)
    balance_btc = data['wallet_balance']
    position = data['position']
    
    # Данные токена
    symbol = token_info.get("symbol", "UNKNOWN")
    name = token_info.get("name", "Unknown")
    price_usd = token_info.get("price_usd", 0)
    price = token_service.format_price(price_usd)
    liq = token_service.format_liquidity(token_info.get("liquidity_usd", 0))
    mc = token_service.format_market_cap(token_info.get("market_cap_usd", 0))
    volume = token_service.format_liquidity(token_info.get("volume_24h", 0))
    
    # Данные позиции
    amount_tokens = position['amount_tokens']
    total_bought = position['total_bought']
    total_sold = position['total_sold']
    wallet_name = position['wallet_name']
    
    # Рассчитываем текущую стоимость позиции в USD
    current_value_usd = amount_tokens * price_usd if price_usd > 0 else 0
    
    # Форматируем количество токенов
    if amount_tokens >= 1_000_000:
        tokens_display = f"{amount_tokens / 1_000_000:.2f}M"
    elif amount_tokens >= 1_000:
        tokens_display = f"{amount_tokens / 1_000:.2f}K"
    else:
        tokens_display = f"{amount_tokens}"
    
    # Форматируем стоимость
    if current_value_usd >= 1_000:
        value_display = f"${current_value_usd / 1_000:.2f}K"
    else:
        value_display = f"${current_value_usd:.2f}"
    
    msg = (
        f"💸 <b>Sell Token</b>\n\n"
        f"🏷 <b>{name}</b> ({symbol})\n"
        f"📍 <code>{token_addr[:20]}...{token_addr[-10:]}</code>\n\n"
        f"💵 Price: {price}\n"
        f"💧 Liquidity: {liq}\n"
        f"📊 Market Cap: {mc}\n"
        f"📈 24h Volume: {volume}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💼 <b>Your Position:</b>\n"
        f"🪙 Amount: <b>{tokens_display}</b> tokens\n"
        f"💵 Value: <b>{value_display}</b>\n"
        f"👛 Wallet: <b>{wallet_name[:15]}...</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"👇 <b>Select amount to sell:</b>"
    )
    
    # Создаем клавиатуру
    wallets = wallet_manager.list_wallets()
    keyboard = create_sell_keyboard(
        wallets=list(wallets.keys()),
        selected_wallet=selected_wallet,
        selected_percent=selected_percent,
        slippage=slippage
    )
    
    await message.answer(msg, reply_markup=keyboard, parse_mode="HTML")


async def handle_sell_token_input(message: types.Message, state: FSMContext):
    """Обработка ввода адреса токена для продажи"""
    token_addr = message.text.strip()
    await show_sell_window(message, state, token_addr)


async def handle_sell_callbacks(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик callback для кнопок продажи"""
    data = callback.data
    user_id = callback.from_user.id
    await ensure_user_storage(user_id, callback.from_user.username)
    wallet_manager = get_wallet_manager(user_id)
    
    # Refresh - обновление данных
    if data == "sell_refresh":
        await callback.answer("🔄 Refreshing...")
        state_data = await state.get_data()
        token_addr = state_data.get("token_address")
        
        if not token_addr:
            await callback.answer("❌ Error")
            return
        
        try:
            # Обновляем информацию о токене
            token_info = await token_service.get_token_info(token_addr)
            await state.update_data(token_info=token_info)
            
            # Обновляем сообщение
            await update_sell_message(callback.message, state, user_id, callback.from_user.username)
        except Exception as e:
            print(f"[ERROR] Sell refresh: {e}")
            await callback.answer("❌ Error")
    
    # Back - возврат в меню
    elif data == "sell_back":
        await callback.answer("◀️ Back")
        await state.clear()
        
        # Отправляем главное меню
        try:
            from main_menu_keyboard import create_main_menu_keyboard
            await callback.message.answer(
                "Main menu",
                reply_markup=create_main_menu_keyboard()
            )
        except:
            await callback.message.answer("Use /start to return to main menu")
    
    # Выбор процента продажи
    elif data.startswith("sell_percent_"):
        percent = int(data.replace("sell_percent_", ""))
        await callback.answer(f"Selected {percent}%")
        
        await state.update_data(selected_percent=percent)
        
        # Обновляем сообщение
        await update_sell_message(callback.message, state, user_id, callback.from_user.username)
    
    # Custom процент
    elif data == "sell_custom_percent":
        WalletStates = get_wallet_states()
        await callback.answer("✏️ Enter percent")
        await state.set_state(WalletStates.waiting_custom_sell_percent)
        await callback.message.answer(
            "📊 <b>Enter sell percentage:</b>\n\n"
            "For example: <code>30</code> (for 30%)\n"
            "Range: 1-100%",
            parse_mode="HTML"
        )
    
    else:
        await callback.answer()


async def update_sell_message(message: types.Message, state: FSMContext, user_id: int, username: str | None = None):
    """Обновить сообщение окна продажи"""
    if username is None and getattr(message, "from_user", None):
        username = message.from_user.username
    await ensure_user_storage(user_id, username)
    wallet_manager = get_wallet_manager(user_id)
    data = await state.get_data()
    
    token_addr = data['token_address']
    token_info = data['token_info']
    selected_wallet = data['selected_wallet']
    selected_percent = data.get('selected_percent', 100)
    slippage = data.get('sell_slippage', 10.0)
    position = data['position']
    
    # Данные токена
    symbol = token_info.get("symbol", "UNKNOWN")
    name = token_info.get("name", "Unknown")
    price_usd = token_info.get("price_usd", 0)
    price = token_service.format_price(price_usd)
    liq = token_service.format_liquidity(token_info.get("liquidity_usd", 0))
    mc = token_service.format_market_cap(token_info.get("market_cap_usd", 0))
    volume = token_service.format_liquidity(token_info.get("volume_24h", 0))
    
    # Данные позиции
    amount_tokens = position['amount_tokens']
    wallet_name = position['wallet_name']
    
    # Рассчитываем текущую стоимость позиции в USD
    current_value_usd = amount_tokens * price_usd if price_usd > 0 else 0
    
    # Форматируем количество токенов
    if amount_tokens >= 1_000_000:
        tokens_display = f"{amount_tokens / 1_000_000:.2f}M"
    elif amount_tokens >= 1_000:
        tokens_display = f"{amount_tokens / 1_000:.2f}K"
    else:
        tokens_display = f"{amount_tokens}"
    
    # Форматируем стоимость
    if current_value_usd >= 1_000:
        value_display = f"${current_value_usd / 1_000:.2f}K"
    else:
        value_display = f"${current_value_usd:.2f}"
    
    msg = (
        f"💸 <b>Sell Token</b>\n\n"
        f"🏷 <b>{name}</b> ({symbol})\n"
        f"📍 <code>{token_addr[:20]}...{token_addr[-10:]}</code>\n\n"
        f"💵 Price: {price}\n"
        f"💧 Liquidity: {liq}\n"
        f"📊 Market Cap: {mc}\n"
        f"📈 24h Volume: {volume}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💼 <b>Your Position:</b>\n"
        f"🪙 Amount: <b>{tokens_display}</b> tokens\n"
        f"💵 Value: <b>{value_display}</b>\n"
        f"👛 Wallet: <b>{wallet_name[:15]}...</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"👇 <b>Select amount to sell:</b>"
    )
    
    # Создаем клавиатуру
    wallets = wallet_manager.list_wallets()
    keyboard = create_sell_keyboard(
        wallets=list(wallets.keys()),
        selected_wallet=selected_wallet,
        selected_percent=selected_percent,
        slippage=slippage
    )
    
    try:
        await message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
    except:
        # Если не удалось отредактировать, отправляем новое
        await message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
