"""
Обработчики для функции продажи токенов
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from token_info import token_service
from sell_keyboards import create_sell_keyboard
# ← ДОБАВЛЕНО
from referral_service import get_user_ref_bps
from config import INTEGRATOR_DEV_FEE_BPS
import sys


def get_wallet_states():
    """Получить WalletStates из telegram_bot"""
    from telegram_bot import WalletStates
    return WalletStates


def get_wallet_manager():
    """Безопасное получение wallet_manager из telegram_bot"""
    import sys
    telegram_bot = sys.modules.get("telegram_bot")
    if telegram_bot and hasattr(telegram_bot, "wallet_manager"):
        return telegram_bot.wallet_manager
    from telegram_bot import wallet_manager
    return wallet_manager


async def cmd_sell(message: types.Message, state: FSMContext):
    """
    Команда /sell - начало процесса продажи токена
    """
    wallet_manager = get_wallet_manager()
    WalletStates = get_wallet_states()
    user_id = message.from_user.id
    print(f"[SELL_CMD] User {user_id} started /sell command")

    wallets = wallet_manager.list_wallets()
    if not wallets:
        await message.answer(
            "❌ У вас нет кошельков!\n\n"
            "Сначала создайте кошелек: /create_wallet"
        )
        return

    await state.set_state(WalletStates.waiting_sell_token_address)

    await message.answer(
        "🛍️ <b>Продажа токена</b>\n\n"
        "📝 Введите адрес токена:\n\n"
        "📋 <b>Формат адреса токена:</b>\n"
        "• Начинается с <code>btkn1</code>\n\n"
        "💡 <b>Где взять адрес:</b>\n"
        "• Из вашего портфеля\n"
        "• Или из проводника токенов SPARK\n\n"
        "✍️ Введите адрес:",
        parse_mode="HTML"
    )


async def handle_sell_token_input(message: types.Message, state: FSMContext):
    """
    Обработка ввода адреса токена для продажи
    """
    wallet_manager = get_wallet_manager()
    WalletStates = get_wallet_states()
    user_id = message.from_user.id
    token_input = message.text.strip()

    if not token_input.startswith("btkn1"):
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Адрес токена должен начинаться с <code>btkn1</code>",
            parse_mode="HTML"
        )
        return

    is_valid = wallet_manager.validate_spark_btkn_address(token_input)
    if not is_valid:
        await message.answer(
            "❌ Неверный адрес токена!",
            parse_mode="HTML"
        )
        return

    try:
        await message.answer("⏳ Загрузка информации о токене...")

        token_info = await token_service.get_token_info(token_input)

        wallets = wallet_manager.list_wallets()
        wallet_list = list(wallets.keys())

        first_wallet = wallet_list[0]
        wallet_address = wallets[first_wallet]['address']

        try:
            balance_info = await wallet_manager.get_wallet_balance(wallet_address)
            balance_sats = balance_info.get("balance_sats", 0)
        except:
            balance_sats = 0

        await state.update_data(
            token_address=token_input,
            token_info=token_info,
            selected_wallet="W1",
            selected_wallet_name=first_wallet,
            selected_percent=50,
            wallet_balance_sats=balance_sats
        )

        message_text = await format_sell_message(token_info, balance_sats, "W1")

        keyboard = create_sell_keyboard(
            wallets=wallet_list,
            selected_wallet="W1",
            selected_percent=50,
        )

        await state.set_state(WalletStates.sell_confirming)

        await message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to load token info: {error_msg}", file=sys.stderr)
        await message.answer(
            f"❌ Ошибка при загрузке информации о токене:\n{error_msg}",
        )
        await state.clear()


async def format_sell_message(token_info: dict, wallet_balance_sats: int, selected_wallet: str) -> str:
    """
    Форматирование сообщения с информацией о продаже токена
    """
    symbol = token_info.get("symbol", "UNKNOWN")
    name = token_info.get("name", "Unknown Token")
    address = token_info.get("address", "")

    price_usd = token_info.get("price_usd")
    if price_usd:
        price_str = token_service.format_price(price_usd)
    else:
        price_str = "~ при исполнении"

    liquidity = token_info.get("liquidity_usd", 0)
    market_cap = token_info.get("market_cap_usd", 0)
    liq_str = token_service.format_liquidity(liquidity)
    mc_str = token_service.format_market_cap(market_cap)

    addr_short = f"{address[:10]}...{address[-10:]}" if address and len(address) > 20 else (address or "—")

    try:
        from btc_price import btc_price_service
        btc_price = await btc_price_service.get_btc_price_usd()
        usd_value = btc_price_service.sats_to_usd(wallet_balance_sats, btc_price)
        usd_str = btc_price_service.format_usd(usd_value)
        balance_display = f"{wallet_balance_sats:,} SATS ({usd_str})"
    except Exception as e:
        print(f"[DEBUG] USD conversion error: {e}", file=sys.stderr)
        balance_display = f"{wallet_balance_sats:,} SATS"

    message = (
        f"🛍️ <b>Sell ${symbol}</b> — {name} 📉\n\n"
        f"📍 <code>{addr_short}</code>\n\n"
        f"💰 Balance: {balance_display} — {selected_wallet}\n"
        f"💵 Price: {price_str}\n"
        f"💧 LIQ: {liq_str} — 📊 MC: {mc_str}\n\n"
        f"👇 Select options below:"
    )
    return message


async def handle_sell_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение продажи"""
    WalletStates = get_wallet_states()
    data = await state.get_data()

    token_info = data.get("token_info", {}) or {}
    token_address = token_info.get("address", "")
    symbol = token_info.get("symbol", "UNKNOWN")
    name = token_info.get("name", "Unknown Token")

    selected_percent = float(data.get("selected_percent", 50))
    selected_wallet = data.get("selected_wallet", "W1")

    balance_sats = int(data.get("wallet_balance_sats", 0) or 0)

    try:
        balance_btc = token_service.sats_to_btc(balance_sats)
    except Exception:
        balance_btc = 0.0

    est_token_amount = 0.0
    display_price_usd = float(token_info.get("price_usd") or 0.0)
    try:
        calc = await token_service.calculate_tokens_for_btc(token_address, 0.001)  # условно
        if calc:
            est_token_amount = float(calc.get("token_amount") or 0.0)
            if not display_price_usd:
                display_price_usd = float(calc.get("price_usd") or 0.0)
    except Exception:
        pass

    addr_short = f"{token_address[:15]}...{token_address[-10:]}" if token_address else "—"

    receive_line = "📦 Вы получите: <i>~ будет рассчитано при подтверждении</i>"
    price_line = (
        f"💵 Цена за токен: <b>${display_price_usd:.8f}</b>"
        if display_price_usd > 0
        else "💵 Цена за токен: <i>~ при исполнении</i>"
    )

    # ← ДОБАВЛЕНО: строка с комиссиями
    user_id = callback.from_user.id
    user_ref_bps = get_user_ref_bps(user_id)
    total_bps = INTEGRATOR_DEV_FEE_BPS + user_ref_bps
    fee_line = (
        f"💸 Комиссия: интегратор {INTEGRATOR_DEV_FEE_BPS/100:.2f}% "
        f"+ реф.уровень {user_ref_bps/100:.2f}% (итого {total_bps/100:.2f}%)"
    )

    confirm_message = (
        "🔔 <b>Подтверждение продажи</b>\n\n"
        f"🪙 Токен: <b>${symbol}</b> — {name}\n"
        f"📍 <code>{addr_short}</code>\n\n"
        f"📊 Продаёте: <b>{selected_percent:.1f}%</b> вашего баланса\n\n"
        f"{receive_line}\n"
        f"{price_line}\n\n"
        f"{fee_line}\n"  # ← ВСТАВЛЕНА СТРОКА С КОМИССИЕЙ
        f"💼 Кошелёк: <b>{selected_wallet}</b>"
    )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Confirm", callback_data="sell_execute")],
        [types.InlineKeyboardButton(text="❌ Cancel", callback_data="sell_cancel")]
    ])

    await callback.message.edit_text(confirm_message, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(WalletStates.sell_confirming)
    await callback.answer("👆 Проверь детали и подтверди")


async def handle_sell_execute(callback: types.CallbackQuery, state: FSMContext):
    """Выполнение продажи токена"""
    await callback.answer("⏳ Выполнение продажи...")

    wallet_manager = get_wallet_manager()

    data = await state.get_data()
    user_id = callback.from_user.id

    token_info = data.get("token_info", {}) or {}
    token_address = token_info.get("address", "")
    symbol = token_info.get("symbol", "UNKNOWN")
    selected_percent = float(data.get("selected_percent", 50))
    selected_wallet_name = data.get("selected_wallet_name")

    try:
        await callback.message.edit_text(
            f"⏳ <b>Продажа {symbol}...</b>\n\nПожалуйста, подождите...",
            parse_mode="HTML"
        )

        token_amount = int(selected_percent * 100)  # условно

        # ← ДОБАВЛЕНО: user_id в вызов
        result = await wallet_manager.sell_meme(
            contract_address=token_address,
            token_amount=token_amount,
            wallet_name=selected_wallet_name,
            slippage=10.0,
            user_id=user_id,  # ← ДОБАВЛЕНО
        )

        if result.get("status") != "success":
            error_msg = result.get("error", result.get("message", "Неизвестная ошибка"))
            raise Exception(error_msg)

        txid = result.get("txid")
        if not txid:
            raise Exception("Транзакция не содержит TxID!")

        success_message = (
            f"✅ <b>Продажа выполнена!</b>\n\n"
            f"🪙 Продано: <b>{token_amount} {symbol}</b>\n\n"
            f"📋 Transaction ID:\n<code>{txid}</code>\n\n"
            f"🎉 BTC будут зачислены на ваш кошелёк"
        )
        await callback.message.edit_text(success_message, parse_mode="HTML")
        print(f"[SUCCESS] User {user_id} sold {token_amount} {symbol}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        await callback.message.edit_text(
            "❌ <b>Ошибка при продаже!</b>\n\n"
            f"Детали: {e}\n\n"
            "Попробуйте ещё раз: /sell",
            parse_mode="HTML"
        )
    finally:
        await state.clear()


async def handle_sell_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена продажи"""
    await callback.answer("❌ Продажа отменена")
    await callback.message.edit_text(
        "❌ <b>Продажа отменена</b>\n\nЧтобы продать токен, используйте /sell",
        parse_mode="HTML"
    )
    await state.clear()
