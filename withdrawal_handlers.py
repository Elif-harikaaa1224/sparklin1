"""
Withdrawal Handlers для Spark Telegram Bot
Обработчики команд вывода средств
"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from spark_withdrawal import SparkWithdrawalManager
from wallet_service import get_wallet_manager

# Создаем роутер для вывода средств
withdrawal_router = Router()
withdrawal_manager = SparkWithdrawalManager()

async def ensure_user_storage(user_id: int, username: str | None):
    from telegram_bot import ensure_user_storage as ensure_storage_impl

    await ensure_storage_impl(user_id, username)


async def get_user_wallet_mnemonic(user_id: int, username: str | None = None) -> tuple:
    """
    Получить mnemonic активного кошелька пользователя
    
    Returns:
        tuple: (wallet_name, mnemonic, error_message)
    """
    await ensure_user_storage(user_id, username)
    manager = get_wallet_manager(user_id)
    wallets = manager.list_wallets()
    
    if not wallets:
        return None, None, "У вас нет кошельков. Создайте кошелек командой /create_wallet"
    
    # Берем последний созданный кошелек (самый новый)
    wallet_name = list(wallets.keys())[-1]
    
    # Получаем полный объект кошелька из wallet_manager
    wallet_obj = manager.wallets.get(wallet_name)
    
    if not wallet_obj:
        return wallet_name, None, "Не удалось загрузить данные кошелька"
    
    # Если это объект WalletData, получаем mnemonic напрямую
    if hasattr(wallet_obj, 'mnemonic'):
        mnemonic = wallet_obj.mnemonic
    else:
        # Если это dict, получаем через get
        wallet_data = wallets[wallet_name]
        mnemonic = wallet_data.get('mnemonic')
    
    if not mnemonic:
        return wallet_name, None, f"Mnemonic не найден для кошелька {wallet_name}. Создайте новый кошелек."
    
    return wallet_name, mnemonic, None

# States для вывода средств
class WithdrawalStates(StatesGroup):
    # Spark Transfer
    waiting_spark_address = State()
    waiting_transfer_amount = State()
    # Lightning invoice
    waiting_invoice_amount = State()
    waiting_invoice_memo = State()
    # Pay Lightning
    waiting_pay_wallet = State()
    waiting_lightning_invoice = State()
    waiting_max_fee = State()
    # Withdraw to L1
    waiting_withdraw_wallet = State()
    waiting_btc_address = State()
    waiting_withdraw_amount = State()
    waiting_withdraw_speed = State()


# ============= Deposit Address (Пополнение с бирж) =============

@withdrawal_router.message(Command("deposit"))
async def cmd_get_deposit_address(message: types.Message):
    """Получить Bitcoin адрес для пополнения"""
    user_id = message.from_user.id
    
    await message.answer("⏳ Получаю адрес для депозита...")
    
    # Получаем mnemonic
    wallet_name, mnemonic, error = await get_user_wallet_mnemonic(user_id, message.from_user.username)
    
    if error:
        await message.answer(f"❌ Ошибка: {error}")
        return
    
    if not mnemonic:
        await message.answer("❌ Не удалось получить mnemonic кошелька")
        return
    
    # Получаем deposit address через Spark SDK
    result = withdrawal_manager.get_deposit_address(mnemonic=mnemonic)
    
    if result.get('success'):
        btc_address = result.get('address')
        await message.answer(
            f"💰 <b>Bitcoin Адрес для Пополнения:</b>\n\n"
            f"<code>{btc_address}</code>\n\n"
            f"📋 <b>Как пополнить с биржи (OKX, Binance и др.):</b>\n\n"
            f"1️⃣ Скопируйте адрес выше\n"
            f"2️⃣ На бирже выберите Withdraw → Bitcoin (BTC)\n"
            f"3️⃣ Вставьте этот адрес\n"
            f"4️⃣ Выберите сеть: <b>Bitcoin (Native SegWit)</b>\n"
            f"5️⃣ Введите сумму и подтвердите\n\n"
            f"⏱️ <b>Время зачисления:</b>\n"
            f"• Bitcoin транзакция: ~30-60 минут\n"
            f"• После подтверждения средства появятся автоматически\n\n"
            f"💡 <b>Важно:</b>\n"
            f"• Это постоянный адрес, можно использовать много раз\n"
            f"• Минимальная сумма зависит от биржи (~0.0001 BTC)\n"
            f"• Комиссия берется биржей, не Spark",
            parse_mode="HTML"
        )
    else:
        error_msg = result.get('error', 'Unknown error')
        await message.answer(
            f"❌ <b>Ошибка получения адреса:</b>\n\n"
            f"{error_msg}",
            parse_mode="HTML"
        )


# ============= Lightning Invoice =============

@withdrawal_router.message(Command("create_invoice"))
async def cmd_create_invoice(message: types.Message, state: FSMContext):
    """Создать Lightning invoice через Spark SDK (MAINNET!)"""
    await message.answer(
        "⚡ <b>Создание Lightning Invoice</b>\n\n"
        "Lightning invoice позволяет пополнить кошелек с биржи мгновенно!\n\n"
        "💡 <b>Как это работает:</b>\n"
        "1. Вы создаете invoice на нужную сумму\n"
        "2. На бирже (OKX, Binance) выбираете Withdraw → Lightning Network\n"
        "3. Вставляете invoice и подтверждаете\n"
        "4. Средства приходят в ваш SPARK кошелек за 5 секунд!\n\n"
        "💰 <b>Введите сумму в satoshi:</b>",
        parse_mode="HTML"
    )
    await state.set_state(WithdrawalStates.waiting_invoice_amount)


@withdrawal_router.message(WithdrawalStates.waiting_invoice_amount)
async def process_invoice_amount(message: types.Message, state: FSMContext):
    """Обработка суммы для invoice"""
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        user_id = message.from_user.id
        
        # Получаем mnemonic кошелька пользователя
        wallet_name, mnemonic, error = await get_user_wallet_mnemonic(user_id, message.from_user.username)
        
        if error:
            await message.answer(f"❌ Ошибка: {error}")
            await state.clear()
            return
        
        # Создаем invoice через Spark SDK (MAINNET!)
        await message.answer("⏳ Создаю Lightning invoice через Spark SDK...")
        
        result = withdrawal_manager.create_lightning_invoice(
            mnemonic=mnemonic,
            amount_sats=amount,
            memo="SPARK Wallet Payment"
        )
        
        if result.get('success'):
            invoice = result.get('invoice', 'N/A')
            await message.answer(
                f"✅ <b>Lightning Invoice создан!</b>\n\n"
                f"⚡ <b>MAINNET Lightning Network</b>\n"
                f"💰 Сумма: {amount:,} sats (~${amount * 0.00001:.2f})\n\n"
                f"📋 <b>Invoice:</b>\n"
                f"<code>{invoice}</code>\n\n"
                f"💡 <b>Как использовать:</b>\n"
                f"1. Откройте биржу (OKX, Binance)\n"
                f"2. Withdraw → Lightning Network\n"
                f"3. Вставьте invoice выше\n"
                f"4. Средства придут за 5 секунд! ⚡\n\n"
                f"✅ Invoice действителен 30 дней",
                parse_mode="HTML"
            )
        else:
            error_msg = result.get('error', 'Unknown error')
            await message.answer(
                f"❌ <b>Ошибка создания invoice:</b>\n\n"
                f"{error_msg}",
                parse_mode="HTML"
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (satoshi)")


@withdrawal_router.callback_query(F.data == "skip_memo")
@withdrawal_router.message(WithdrawalStates.waiting_invoice_memo)
async def process_invoice_memo(message_or_callback, state: FSMContext):
    """Создание invoice с memo или без"""
    # Обработка callback (пропуск) или message (текст memo)
    if isinstance(message_or_callback, types.CallbackQuery):
        callback = message_or_callback
        message = callback.message
        memo = None
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = message_or_callback
        memo = message.text.strip()
        user_id = message.from_user.id
        username = message.from_user.username
    
    data = await state.get_data()
    amount = data.get('invoice_amount')
    
    await message.answer("⏳ Создаю Lightning invoice...")
    
    # Получаем mnemonic активного кошелька
    if isinstance(message_or_callback, types.CallbackQuery):
        username = callback.from_user.username
    wallet_name, mnemonic, error = await get_user_wallet_mnemonic(user_id, username)
    
    if error:
        result = {"success": False, "error": error}
    elif not mnemonic:
        result = {"success": False, "error": "Не удалось получить mnemonic кошелька"}
    else:
        result = withdrawal_manager.create_lightning_invoice(
            mnemonic=mnemonic,
            amount_sats=amount,
            memo=memo
        )
    
    if result.get('success'):
        invoice = result.get('invoice', 'N/A')
        await message.answer(
            f"✅ <b>Lightning Invoice создан!</b>\n\n"
            f"💰 Сумма: {amount:,} sats\n"
            f"📝 Memo: {memo or 'Нет'}\n\n"
            f"<code>{invoice}</code>\n\n"
            f"Отправьте этот invoice плательщику.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ Ошибка создания invoice:\n{result.get('error', 'Unknown error')}",
            parse_mode="HTML"
        )
    
    await state.clear()


# ============= Send Transfer =============

@withdrawal_router.message(Command("send_transfer"))
async def cmd_send_transfer(message: types.Message, state: FSMContext):
    """Отправить средства на Spark Address"""
    # Сбрасываем любое предыдущее состояние
    await state.clear()
    
    await message.answer(
        "💸 <b>Отправка Spark Transfer</b>\n\n"
        "Введите Spark Address получателя\n"
        "(начинается с spark1...):\n\n"
        "Пример: <code>spark1pgss8avx...</code>",
        parse_mode="HTML"
    )
    await state.set_state(WithdrawalStates.waiting_spark_address)


@withdrawal_router.message(WithdrawalStates.waiting_spark_address)
async def process_spark_address(message: types.Message, state: FSMContext):
    """Обработка Spark Address"""
    spark_address = message.text.strip()
    
    if not spark_address.startswith('spark1'):
        await message.answer("❌ Неверный формат адреса. Должен начинаться с spark1...")
        return
    
    await state.update_data(spark_address=spark_address)
    await message.answer(
        f"✅ Адрес: <code>{spark_address}</code>\n\n"
        f"Введите сумму в satoshi:",
        parse_mode="HTML"
    )
    await state.set_state(WithdrawalStates.waiting_transfer_amount)


@withdrawal_router.message(WithdrawalStates.waiting_transfer_amount)
async def process_transfer_amount(message: types.Message, state: FSMContext):
    """Обработка суммы transfer"""
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        data = await state.get_data()
        spark_address = data.get('spark_address')
        user_id = message.from_user.id
        
        await message.answer(f"⏳ Отправляю {amount:,} sats на {spark_address[:20]}...")
        
        # Получаем mnemonic активного кошелька
        wallet_name, mnemonic, error = await get_user_wallet_mnemonic(user_id, message.from_user.username)
        
        if error:
            await message.answer(f"❌ Ошибка: {error}")
            await state.clear()
            return
        
        if not mnemonic:
            await message.answer("❌ Не удалось получить mnemonic кошелька")
            await state.clear()
            return
        
        # Используем Node.js скрипт для Spark transfer (ASYNC!)
        result = await withdrawal_manager.send_spark_transfer(
            mnemonic=mnemonic,
            receiver_address=spark_address,
            amount_sats=amount
        )
        
        if result.get('success'):
            await message.answer(
                f"✅ <b>Transfer выполнен!</b>\n\n"
                f"💰 Отправлено: {amount:,} sats\n"
                f"📍 Получатель: <code>{spark_address}</code>\n\n"
                f"✅ Средства доставлены мгновенно!",
                parse_mode="HTML"
            )
        else:
            error_msg = result.get('error', 'Unknown error')
            await message.answer(
                f"❌ <b>Ошибка отправки:</b>\n\n"
                f"{error_msg}",
                parse_mode="HTML"
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (satoshi)")


# ============= Pay Lightning Invoice =============

@withdrawal_router.message(Command("pay_invoice"))
async def cmd_pay_invoice(message: types.Message, state: FSMContext):
    """Оплатить Lightning invoice"""
    # Сбрасываем любое предыдущее состояние
    await state.clear()
    
    await message.answer(
        "⚡ <b>Оплата Lightning Invoice</b>\n\n"
        "Введите Lightning invoice (начинается с lnbc... или lnbcrt...):\n\n"
        "Пример: <code>lnbc100u1p5shtcw...</code>",
        parse_mode="HTML"
    )
    await state.set_state(WithdrawalStates.waiting_lightning_invoice)


@withdrawal_router.message(WithdrawalStates.waiting_lightning_invoice)
async def process_lightning_invoice(message: types.Message, state: FSMContext):
    """Обработка Lightning invoice"""
    invoice = message.text.strip()
    
    if not invoice.startswith(('lnbc', 'lnbcrt')):
        await message.answer("❌ Неверный формат invoice. Должен начинаться с lnbc... или lnbcrt...")
        return
    
    await state.update_data(lightning_invoice=invoice)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100 sats", callback_data="maxfee_100")],
        [InlineKeyboardButton(text="500 sats", callback_data="maxfee_500")],
        [InlineKeyboardButton(text="1000 sats", callback_data="maxfee_1000")],
        [InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="maxfee_custom")]
    ])
    
    await message.answer(
        "⚙️ Выберите максимальную комиссию для оплаты:",
        reply_markup=keyboard
    )


@withdrawal_router.callback_query(F.data.startswith("maxfee_"))
async def process_max_fee(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора максимальной комиссии"""
    await callback.answer()
    
    fee_choice = callback.data.split("_")[1]
    
    if fee_choice == "custom":
        await callback.message.edit_text("Введите максимальную комиссию в satoshi:")
        await state.set_state(WithdrawalStates.waiting_max_fee)
        return
    
    max_fee = int(fee_choice)
    await finalize_lightning_payment(callback.message, state, max_fee)


@withdrawal_router.message(WithdrawalStates.waiting_max_fee)
async def process_custom_max_fee(message: types.Message, state: FSMContext):
    """Обработка кастомной максимальной комиссии"""
    try:
        max_fee = int(message.text.strip())
        if max_fee < 0:
            await message.answer("❌ Комиссия не может быть отрицательной")
            return
        
        await finalize_lightning_payment(message, state, max_fee)
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (satoshi)")


async def finalize_lightning_payment(message: types.Message, state: FSMContext, max_fee: int):
    """Финализация оплаты Lightning invoice"""
    data = await state.get_data()
    invoice = data.get('lightning_invoice')
    user_id = message.from_user.id
    
    await message.answer(
        f"⏳ Оплачиваю Lightning invoice...\n\n"
        f"Максимальная комиссия: {max_fee} sats"
    )
    
    # Получаем mnemonic активного кошелька
    wallet_name, mnemonic, error = await get_user_wallet_mnemonic(user_id, message.from_user.username)
    
    if error:
        result = {"success": False, "error": error}
    elif not mnemonic:
        result = {"success": False, "error": "Не удалось получить mnemonic кошелька"}
    else:
        result = withdrawal_manager.pay_lightning_invoice(
            mnemonic=mnemonic,
            invoice=invoice,
            max_fee_sats=max_fee
        )
    
    if result.get('success'):
        paid_amount = result.get('amount_sats', 0)
        actual_fee = result.get('fee_sats', 0)
        await message.answer(
            f"✅ <b>Платеж выполнен!</b>\n\n"
            f"💰 Оплачено: {paid_amount:,} sats\n"
            f"💸 Комиссия: {actual_fee:,} sats\n"
            f"📊 Всего: {paid_amount + actual_fee:,} sats",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ Ошибка оплаты:\n{result.get('error', 'Unknown error')}",
            parse_mode="HTML"
        )
    
    await state.clear()


# ============= Withdraw to L1 =============

@withdrawal_router.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message, state: FSMContext):
    """Вывести средства на Bitcoin L1 адрес"""
    await message.answer(
        "🏦 <b>Вывод на Bitcoin L1</b>\n\n"
        "Введите Bitcoin адрес получателя\n"
        "(bc1... для mainnet или bcrt1... для regtest):",
        parse_mode="HTML"
    )
    await state.set_state(WithdrawalStates.waiting_btc_address)


@withdrawal_router.message(WithdrawalStates.waiting_btc_address)
async def process_btc_address(message: types.Message, state: FSMContext):
    """Обработка Bitcoin адреса"""
    btc_address = message.text.strip()
    
    if not (btc_address.startswith('bc1') or btc_address.startswith('bcrt1')):
        await message.answer("❌ Неверный формат адреса. Должен начинаться с bc1... или bcrt1...")
        return
    
    await state.update_data(btc_address=btc_address)
    await message.answer(
        f"✅ Адрес: <code>{btc_address}</code>\n\n"
        f"Введите сумму для вывода (в satoshi):",
        parse_mode="HTML"
    )
    await state.set_state(WithdrawalStates.waiting_withdraw_amount)


@withdrawal_router.message(WithdrawalStates.waiting_withdraw_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext):
    """Обработка суммы вывода"""
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        await state.update_data(withdraw_amount=amount)
        
        data = await state.get_data()
        btc_address = data.get('btc_address')
        user_id = message.from_user.id
        
        await message.answer("⏳ Проверяю комиссию за вывод...")
        
        # Получаем mnemonic активного кошелька
        wallet_name, mnemonic, error = await get_user_wallet_mnemonic(user_id, message.from_user.username)
        
        if error:
            fee_result = {"success": False, "error": error}
        elif not mnemonic:
            fee_result = {"success": False, "error": "Не удалось получить mnemonic кошелька"}
        else:
            fee_result = withdrawal_manager.get_withdrawal_fee(
                mnemonic=mnemonic,
                btc_address=btc_address,
                amount_sats=amount
            )
        
        if fee_result.get('success'):
            fees = fee_result.get('fees', {})
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🐌 Медленно ({fees.get('slow', 0):,} sats)", 
                    callback_data="speed_SLOW"
                )],
                [InlineKeyboardButton(
                    text=f"⚡ Средне ({fees.get('medium', 0):,} sats)", 
                    callback_data="speed_MEDIUM"
                )],
                [InlineKeyboardButton(
                    text=f"🚀 Быстро ({fees.get('fast', 0):,} sats)", 
                    callback_data="speed_FAST"
                )],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_withdraw")]
            ])
            
            await message.answer(
                f"📊 <b>Комиссии за вывод {amount:,} sats:</b>\n\n"
                f"🐌 Медленно: {fees.get('slow', 0):,} sats\n"
                f"⚡ Средне: {fees.get('medium', 0):,} sats\n"
                f"🚀 Быстро: {fees.get('fast', 0):,} sats\n\n"
                f"Выберите скорость:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await state.set_state(WithdrawalStates.waiting_withdraw_speed)
        else:
            # Если не удалось получить комиссию, предлагаем выбрать скорость без точных значений
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐌 Медленно", callback_data="speed_SLOW")],
                [InlineKeyboardButton(text="⚡ Средне", callback_data="speed_MEDIUM")],
                [InlineKeyboardButton(text="🚀 Быстро", callback_data="speed_FAST")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_withdraw")]
            ])
            
            await message.answer(
                f"⚙️ Выберите скорость транзакции:\n\n"
                f"<i>Примечание: {fee_result.get('error')}</i>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await state.set_state(WithdrawalStates.waiting_withdraw_speed)
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (satoshi)")


@withdrawal_router.callback_query(F.data.startswith("speed_"))
async def process_withdraw_speed(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора скорости вывода"""
    await callback.answer()
    
    speed = callback.data.split("_")[1]
    data = await state.get_data()
    user_id = callback.from_user.id
    
    btc_address = data.get('btc_address')
    amount = data.get('withdraw_amount')
    
    await callback.message.edit_text(
        f"⏳ Отправляю {amount:,} sats на {btc_address}...\n"
        f"Скорость: {speed}"
    )
    
    # Получаем mnemonic активного кошелька
    wallet_name, mnemonic, error = await get_user_wallet_mnemonic(user_id, callback.from_user.username)
    
    if error:
        result = {"success": False, "error": error}
    elif not mnemonic:
        result = {"success": False, "error": "Не удалось получить mnemonic кошелька"}
    else:
        result = withdrawal_manager.withdraw_to_l1(
            mnemonic=mnemonic,
            btc_address=btc_address,
            amount_sats=amount,
            speed=speed
        )
    
    if result.get('success'):
        tx_id = result.get('tx_id', 'N/A')
        await callback.message.answer(
            f"✅ <b>Вывод выполнен!</b>\n\n"
            f"💰 Сумма: {amount:,} sats\n"
            f"📍 Адрес: <code>{btc_address}</code>\n"
            f"🔗 TX ID: <code>{tx_id}</code>\n\n"
            f"⏰ Транзакция будет подтверждена в ближайшее время.",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            f"❌ Ошибка вывода:\n{result.get('error', 'Unknown error')}",
            parse_mode="HTML"
        )
    
    await state.clear()


@withdrawal_router.callback_query(F.data == "cancel_withdraw")
async def cancel_withdraw(callback: types.CallbackQuery, state: FSMContext):
    """Отмена вывода"""
    await callback.answer("Вывод отменен")
    await callback.message.edit_text("❌ Вывод средств отменен")
    await state.clear()


# Вспомогательные команды

@withdrawal_router.message(Command("withdrawal_help"))
async def cmd_withdrawal_help(message: types.Message):
    """Помощь по выводу средств"""
    await message.answer(
        "💸 <b>Вывод Средств из Spark</b>\n\n"
        
        "<b>Lightning Network:</b>\n"
        "• /create_invoice - создать invoice для получения\n"
        "• /pay_invoice - оплатить Lightning invoice\n\n"
        
        "<b>Bitcoin L1:</b>\n"
        "• /withdraw - вывести на Bitcoin адрес\n\n"
        
        "<b>Примечания:</b>\n"
        "• Lightning - мгновенные переводы с низкими комиссиями\n"
        "• L1 withdrawal - вывод на обычный Bitcoin адрес\n"
        "• Комиссии зависят от выбранной скорости транзакции\n\n"
        
        "⚠️ <b>Важно:</b> Проверяйте адреса перед отправкой!",
        parse_mode="HTML"
    )

