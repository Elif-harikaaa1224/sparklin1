"""
Дополнительные обработчики для покупки (slippage, подтверждение, выполнение)
"""

from aiogram import types
from aiogram.fsm.context import FSMContext
from token_info import token_service
from buy_keyboards import create_buy_keyboard, create_slippage_keyboard
# ← ДОБАВЛЕНО
from referral_service import get_user_ref_bps
from config import INTEGRATOR_DEV_FEE_BPS
import sys


def get_wallet_states():
    """Ленивая загрузка классов состояний из telegram_bot (без циклических импортов)"""
    from telegram_bot import WalletStates
    return WalletStates


_wallet_manager_cached = None
def get_wallet_manager():
    """Безопасно получить wallet_manager из telegram_bot с кэшем."""
    global _wallet_manager_cached

    if _wallet_manager_cached is not None:
        return _wallet_manager_cached

    try:
        import sys
        tg = sys.modules.get("telegram_bot")
        if tg and hasattr(tg, "wallet_manager"):
            _wallet_manager_cached = tg.wallet_manager
            return _wallet_manager_cached
        from telegram_bot import wallet_manager
        _wallet_manager_cached = wallet_manager
        return _wallet_manager_cached
    except Exception as e:
        print(f"[ERROR] Cannot import wallet_manager: {e}")
        return None


async def format_buy_message(token_info: dict, wallet_balance_sats: int, selected_wallet: str) -> str:
    """
    Сообщение с данными токена и баланса (SATS + USD). Цена мягкая: '~ при исполнении', если нет price_usd.
    """
    symbol = token_info.get("symbol", "UNKNOWN")
    name = token_info.get("name", "Unknown Token")
    address = token_info.get("address", "")

    # цена — мягкий плейсхолдер, если нет USD
    price_usd = token_info.get("price_usd")
    if price_usd:
        price_str = token_service.format_price(price_usd)
    else:
        price_str = "~ при исполнении"

    # ликвидность/капитализация
    liquidity = token_info.get("liquidity_usd", 0)
    market_cap = token_info.get("market_cap_usd", 0)
    liq_str = token_service.format_liquidity(liquidity)
    mc_str = token_service.format_market_cap(market_cap)

    # сокращённый адрес
    addr_short = f"{address[:10]}...{address[-10:]}" if address and len(address) > 20 else (address or "—")

    # баланс SATS → USD (мягко)
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
        f"🛒 <b>Buy ${symbol}</b> — {name} 📈\n\n"
        f"📍 <code>{addr_short}</code>\n\n"
        f"💰 Balance: {balance_display} — {selected_wallet}\n"
        f"💵 Price: {price_str}\n"
        f"💧 LIQ: {liq_str} — 📊 MC: {mc_str}\n\n"
        f"👇 Select options below:"
    )
    return message


# ---------- настройка slippage ----------

async def handle_buy_set_slippage(callback: types.CallbackQuery, state: FSMContext):
    """Открыть меню выбора slippage."""
    await callback.answer("📊 Настройка slippage")
    kb = create_slippage_keyboard()
    await callback.message.answer(
        "📊 <b>Slippage — Проскальзывание</b>\n\n"
        "Выберите максимальный процент проскальзывания цены:\n\n"
        "💡 Чем выше slippage, тем больше шанс, что сделка пройдет,\n"
        "но цена может отличаться от ожидаемой.",
        reply_markup=kb,
        parse_mode="HTML"
    )


async def handle_slippage_selection(callback: types.CallbackQuery, state: FSMContext):
    """
    Выбор значения slippage (фиксированное/кастом).
    Кастом → переводим в состояние WalletStates.waiting_buy_slippage.
    """
    WalletStates = get_wallet_states()

    if callback.data == "slippage_back":
        await callback.message.delete()
        await callback.answer("◀️ Возврат")
        return

    if callback.data == "slippage_custom":
        await callback.answer("✏️ Введите slippage (%)")
        await state.set_state(WalletStates.waiting_buy_slippage)
        await callback.message.answer(
            "📊 <b>Введите slippage в %:</b>\n\n"
            "Например: <code>15</code> или <code>20.5</code>\n"
            "Минимум: 0.1%, Максимум: 50%\n\n"
            "Или отправьте /cancel для отмены",
            parse_mode="HTML"
        )
        return

    try:
        slippage = float(callback.data.replace("slippage_", ""))
    except ValueError:
        await callback.answer("❌ Ошибка значения")
        return

    await state.update_data(slippage=slippage)
    await state.set_state(WalletStates.buy_confirming)
    await callback.message.delete()
    await callback.answer(f"✓ Slippage: {slippage:.1f}%")

    # Обновляем главное меню покупки
    data = await state.get_data()
    token_info = data.get("token_info", {}) or {}
    selected_wallet = data.get("selected_wallet", "W1")
    wallet_manager = get_wallet_manager()
    wallets = wallet_manager.list_wallets() if wallet_manager else {}
    wallet_list = list(wallets.keys()) if wallets else []
    balance_sats = int(data.get("wallet_balance_sats", 0))

    text = await format_buy_message(token_info, balance_sats, selected_wallet)
    kb = create_buy_keyboard(
        wallets=wallet_list,
        selected_wallet=selected_wallet,
        selected_amount=float(data.get("selected_amount", 0.001)),
        buy_tip=float(data.get("buy_tip", 0.0000001)),
        slippage=slippage
    )
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")


# ---------- кастомный Tip ----------

async def handle_custom_tip_input(message: types.Message, state: FSMContext):
    """Обработка ввода кастомного Buy Tip (в BTC)."""
    WalletStates = get_wallet_states()

    raw = (message.text or "").strip()
    try:
        tip = float(raw)
    except ValueError:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Введите число, например: <code>0.0000005</code>",
            parse_mode="HTML"
        )
        return

    if tip < 0:
        await message.answer("❌ Tip не может быть отрицательным")
        return
    if tip > 0.001:
        await message.answer("❌ Максимальный tip: 0.001 BTC")
        return

    await state.update_data(buy_tip=tip)
    await state.set_state(WalletStates.buy_confirming)

    # Перерисуем главное меню
    data = await state.get_data()
    token_info = data.get("token_info", {}) or {}
    selected_wallet = data.get("selected_wallet", "W1")
    balance_sats = int(data.get("wallet_balance_sats", 0))
    wallet_manager = get_wallet_manager()
    wallets = wallet_manager.list_wallets() if wallet_manager else {}
    wallet_list = list(wallets.keys()) if wallets else []

    text = await format_buy_message(token_info, balance_sats, selected_wallet)
    kb = create_buy_keyboard(
        wallets=wallet_list,
        selected_wallet=selected_wallet,
        selected_amount=float(data.get("selected_amount", 0.001)),
        buy_tip=tip,
        slippage=float(data.get("slippage", 10.0))
    )
    await message.answer(f"✅ Buy Tip установлен: {tip:.8f} BTC\n\n" + text, reply_markup=kb, parse_mode="HTML")


# ---------- кастомный Slippage ----------

async def handle_custom_slippage_input(message: types.Message, state: FSMContext):
    """Обработка ввода кастомного slippage (%)"""
    WalletStates = get_wallet_states()

    raw = (message.text or "").strip()
    try:
        slippage = float(raw)
    except ValueError:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Введите число, например: <code>15</code> или <code>20.5</code>",
            parse_mode="HTML"
        )
        return

    if slippage < 0.1:
        await message.answer("❌ Минимальный slippage: 0.1%")
        return
    if slippage > 50:
        await message.answer("❌ Максимальный slippage: 50%")
        return

    await state.update_data(slippage=slippage)
    await state.set_state(WalletStates.buy_confirming)

    # Перерисуем главное меню
    data = await state.get_data()
    token_info = data.get("token_info", {}) or {}
    selected_wallet = data.get("selected_wallet", "W1")
    balance_sats = int(data.get("wallet_balance_sats", 0))
    wallet_manager = get_wallet_manager()
    wallets = wallet_manager.list_wallets() if wallet_manager else {}
    wallet_list = list(wallets.keys()) if wallets else []

    text = await format_buy_message(token_info, balance_sats, selected_wallet)
    kb = create_buy_keyboard(
        wallets=wallet_list,
        selected_wallet=selected_wallet,
        selected_amount=float(data.get("selected_amount", 0.001)),
        buy_tip=float(data.get("buy_tip", 0.0000001)),
        slippage=slippage
    )
    await message.answer(f"✅ Slippage установлен: {slippage:.1f}%\n\n" + text, reply_markup=kb, parse_mode="HTML")


# ---------- окно подтверждения (без ❌/N/A в "Получите") ----------

async def handle_buy_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение покупки без красных крестков и с безопасными плейсхолдерами"""
    WalletStates = get_wallet_states()
    data = await state.get_data()

    token_info = data.get("token_info", {}) or {}
    token_address = token_info.get("address", "")
    symbol = token_info.get("symbol", "UNKNOWN")
    name = token_info.get("name", "Unknown Token")

    selected_amount = float(data.get("selected_amount", 0.001))
    buy_tip = float(data.get("buy_tip", 0.0000001))
    slippage = float(data.get("slippage", 10.0))
    selected_wallet = data.get("selected_wallet", "W1")

    # баланс: из SATS → BTC
    balance_sats = int(data.get("wallet_balance_sats", 0) or 0)
    try:
        balance_btc = token_service.sats_to_btc(balance_sats)
    except Exception:
        balance_btc = 0.0

    # мягкая оценка: токены и цена
    est_token_amount = 0.0
    display_price_usd = float(token_info.get("price_usd") or 0.0)
    try:
        calc = await token_service.calculate_tokens_for_btc(token_address, selected_amount)
        if calc:
            est_token_amount = float(calc.get("token_amount") or 0.0)
            if not display_price_usd:
                display_price_usd = float(calc.get("price_usd") or 0.0)
    except Exception:
        pass

    total_btc = selected_amount + buy_tip

    # предупреждаем, но окно не ломаем
    if balance_btc < total_btc:
        await callback.answer("Недостаточно средств на выбранном кошельке.", show_alert=True)

    addr_short = f"{token_address[:15]}...{token_address[-10:]}" if token_address else "—"

    # безопасные строки без ❌/N/A
    receive_line = (
        f"📦 Вы получите: <b>~{est_token_amount:,.2f} {symbol}</b>"
        if est_token_amount > 0
        else "📦 Вы получите: <i>~ будет рассчитано при подтверждении</i>"
    )
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
        "🔔 <b>Подтверждение покупки</b>\n\n"
        f"🪙 Токен: <b>${symbol}</b> — {name}\n"
        f"📍 <code>{addr_short}</code>\n\n"
        f"💰 Вы платите: <b>{selected_amount:.8f} BTC</b>\n"
        f"⚡ Tip: <b>{buy_tip:.8f} BTC</b>\n"
        f"📊 Slippage: <b>{slippage:.1f}%</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💵 Итого: <b>{total_btc:.8f} BTC</b>\n\n"
        f"{receive_line}\n"
        f"{price_line}\n\n"
        f"{fee_line}\n"  # ← ВСТАВЛЕНА СТРОКА С КОМИССИЕЙ
        f"💼 Кошелёк: <b>{selected_wallet}</b>"
    )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Confirm", callback_data="buy_execute")],
        [types.InlineKeyboardButton(text="❌ Cancel", callback_data="buy_cancel")]
    ])

    await callback.message.edit_text(confirm_message, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(WalletStates.buy_confirming)
    await callback.answer("👆 Проверь детали и подтверди")


# ---------- выполнение покупки ----------

async def handle_buy_execute(callback: types.CallbackQuery, state: FSMContext):
    """Выполнение покупки токена (через wallet_manager.buy_meme)."""
    await callback.answer("⏳ Выполнение покупки...")

    wallet_manager = get_wallet_manager()

    data = await state.get_data()
    user_id = callback.from_user.id

    token_info = data.get("token_info", {}) or {}
    token_address = token_info.get("address", "")
    symbol = token_info.get("symbol", "UNKNOWN")
    selected_amount = float(data.get("selected_amount", 0.001))
    buy_tip = float(data.get("buy_tip", 0.0000001))
    slippage = float(data.get("slippage", 10.0))
    selected_wallet_name = data.get("selected_wallet_name")

    try:
        await callback.message.edit_text(
            f"⏳ <b>Покупка {symbol}...</b>\n\nПожалуйста, подождите...",
            parse_mode="HTML"
        )

        # BTC → sats
        amount_sats = token_service.btc_to_sats(selected_amount)
        tip_sats = token_service.btc_to_sats(buy_tip)

        if not wallet_manager:
            raise Exception("Wallet manager недоступен")

        # Выполняем покупку
        # ← ДОБАВЛЕНО: user_id в вызов
        result = await wallet_manager.buy_meme(
            contract_address=token_address,
            amount_sats=amount_sats,
            wallet_name=selected_wallet_name,
            slippage=slippage,
            priority_fee_sats=tip_sats,
            user_id=user_id,  # ← ДОБАВЛЕНО
        )

        if result.get("status") != "success":
            error_msg = result.get("error", result.get("message", "Неизвестная ошибка"))
            raise Exception(error_msg)

        # Оценим количество токенов (для красивого сообщения)
        try:
            calc = await token_service.calculate_tokens_for_btc(token_address, selected_amount)
            token_amount = float(calc.get("token_amount") or 0.0)
        except Exception:
            token_amount = 0.0

        txid = result.get("txid")
        if not txid:
            raise Exception("Транзакция не содержит TxID! Покупка не выполнена.")

        success_message = (
            f"✅ <b>Покупка выполнена!</b>\n\n"
            f"🪙 Куплено: <b>{token_amount:,.2f} {symbol}</b>\n"
            f"💰 Потрачено: <b>{selected_amount:.8f} BTC</b>\n"
            f"⚡ Комиссия: <b>{buy_tip:.8f} BTC</b>\n\n"
            f"📋 Transaction ID:\n<code>{txid}</code>\n\n"
            f"🎉 Токены будут зачислены на ваш кошелёк в течение нескольких секунд"
        )
        await callback.message.edit_text(success_message, parse_mode="HTML")
        print(f"[SUCCESS] User {user_id} bought ~{token_amount} {symbol} for {selected_amount} BTC")

    except Exception as e:
        import traceback
        traceback.print_exc()
        await callback.message.edit_text(
            "❌ <b>Ошибка при покупке!</b>\n\n"
            f"Детали: {e}\n\n"
            "Ваши средства в безопасности.\n"
            "Попробуйте ещё раз: /buy",
            parse_mode="HTML"
        )
    finally:
        await state.clear()


# ---------- отмена ----------

async def handle_buy_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена покупки и очистка состояния."""
    await callback.answer("❌ Покупка отменена")
    await callback.message.edit_text(
        "❌ <b>Покупка отменена</b>\n\nЧтобы купить токен, используйте /buy",
        parse_mode="HTML"
    )
    await state.clear()
