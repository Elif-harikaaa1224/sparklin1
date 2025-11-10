"""
SPARK Telegram Bot
Telegram-интерфейс для управления кошельками SPARK L2
"""

import json
import os
import sys
import asyncio
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Импортируем наш менеджер кошельков
from wallet_service import (
    get_wallet_manager,
    set_user_storage_alias,
    get_user_storage_alias,
)
from token_info import token_service
# Импортируем withdrawal handlers
from withdrawal_handlers import withdrawal_router
# Импортируем buy/sell handlers
from buy_handlers import cmd_buy_new, handle_token_address_input
from sell_handlers import cmd_sell, handle_sell_token_input, handle_sell_callbacks
from main_menu_keyboard import create_main_menu_keyboard
from back_keyboard import create_back_keyboard
# Импортируем BTC price service
from btc_price import btc_price_service

# Импортируем create_user
from src.create_user import create_user
# Импортируем show_referral_code
from src.ref.get_referral_code import get_referral_code

# Инициализация
# Загружаем токен и credentials из .env файла
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env file!", file=sys.stderr)
    print("Create .env file based on .env.example and add your bot token.", file=sys.stderr)
    exit(1)
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "testsparktradetestbot")
user_passwords: dict = {}  # Временное хранилище паролей в памяти


async def ensure_user_storage(user_id: int, username: Optional[str] = None, referral_code: Optional[str] = None) -> tuple[str, Optional[dict]]:
    """Убедиться, что у пользователя есть уникальный storage alias."""

    existing_alias = get_user_storage_alias(user_id)
    if existing_alias:
        return existing_alias, None

    result = await create_user(user_id, username, referral_code)

    storage_key = result.get("storage_key")
    if not storage_key:
        user_doc = result.get("user")
        if user_doc:
            storage_key = user_doc.get("storage_key")

    if not storage_key:
        storage_key = f"user_{user_id}"

    set_user_storage_alias(user_id, storage_key)
    return storage_key, result


async def get_or_create_wallet_manager(user_id: int, username: Optional[str] = None):
    await ensure_user_storage(user_id, username)
    return get_wallet_manager(user_id)

# Хранение позиций по мемам
def _positions_file_path(user_id: int):
    """Вернуть путь к файлу с позициями для пользователя"""
    manager = get_wallet_manager(user_id)
    return manager.storage_path / "positions.json"


def load_positions(user_id: int) -> dict:
    """Загрузить позиции пользователя из файла"""
    path = _positions_file_path(user_id)
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_positions(user_id: int, positions: dict):
    """Сохранить позиции пользователя в файл"""
    path = _positions_file_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(positions, f, indent=2)


def add_position(user_id: int, wallet_name: str, contract_address: str, amount_sats: int, action: str):
    """Добавить или обновить позицию"""
    positions = load_positions(user_id)
    
    if wallet_name not in positions:
        positions[wallet_name] = {}
    
    if contract_address not in positions[wallet_name]:
        positions[wallet_name][contract_address] = {
            "amount_sats": 0,
            "total_bought": 0,
            "total_sold": 0
        }
    
    pos = positions[wallet_name][contract_address]
    
    if action == "buy":
        pos["amount_sats"] += amount_sats
        pos["total_bought"] += amount_sats
    elif action == "sell":
        pos["amount_sats"] = max(0, pos["amount_sats"] - amount_sats)
        pos["total_sold"] += amount_sats
    
    save_positions(user_id, positions)
    return positions

def get_positions(user_id: int, wallet_name: Optional[str] = None) -> dict:
    """Получить позиции для кошелька или всех кошельков"""
    positions = load_positions(user_id)
    if wallet_name:
        return positions.get(wallet_name, {})
    return positions

def get_token_position(user_id: int, wallet_name: str, token_address: str) -> dict:
    """Получить позицию по конкретному токену (упрощенная версия для handlers)"""
    positions = load_positions(user_id)
    return positions.get(wallet_name, {}).get(token_address, {"amount_tokens": 0, "total_bought": 0, "total_sold": 0})

# States для FSM
class WalletStates(StatesGroup):
    waiting_wallet_name = State()
    waiting_password = State()
    waiting_mnemonic = State()
    waiting_private_key = State()
    waiting_private_key_for_export = State()
    waiting_wallet_selection = State()
    # Торговля мемами (BTKN)
    trade_action = State()  # buy | sell
    trade_wallet = State()
    trade_contract = State()
    trade_amount = State()
    # Buy
    waiting_token_address = State()
    buy_confirming = State()
    waiting_custom_amount = State()
    waiting_buy_tip = State()
    waiting_buy_slippage = State()
    # Sell
    waiting_sell_token_address = State()
    sell_confirming = State()
    waiting_custom_sell_percent = State()
    waiting_sell_slippage = State()


# Клавиатуры
def main_menu() -> ReplyKeyboardMarkup:
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать кошелек")],
            [KeyboardButton(text="📥 Импортировать кошелек")],
            [KeyboardButton(text="📋 Мои кошельки")],
            [KeyboardButton(text="🛒 Купить мем"), KeyboardButton(text="💸 Продать мем")],
            [KeyboardButton(text="🔑 Показать приватный ключ")],
            [KeyboardButton(text="🆘 Помощь")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def import_menu() -> InlineKeyboardMarkup:
    """Меню импорта"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Из Mnemonic", callback_data="import_mnemonic")],
            [InlineKeyboardButton(text="🔐 Из приватного ключа", callback_data="import_pk")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ]
    )


def back_button() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]]
    )


# Обработчики команд
async def cmd_start(message: types.Message, state: FSMContext):
    """Команда /start"""
    user_id = message.from_user.id
    print(f"[DEBUG] Received /start from user {user_id}")
    message_text = message.text
    referral_code = None
    if message_text:
        if message_text.startswith("/start ref_"):
            referral_code = message_text.split("_")[1]

    storage_key, create_result = await ensure_user_storage(
        user_id,
        message.from_user.username,
        referral_code,
    )

    if create_result is not None:
        print(f"[DEBUG] ensure_user_storage result for {user_id}: {create_result}")
    print(f"[DEBUG] Storage alias for {user_id}: {storage_key}")

    manager = get_wallet_manager(user_id)

    # Проверяем, есть ли у пользователя кошельки
    wallets = manager.list_wallets()
    
    # Если кошельков нет - создаем автоматически первый кошелек
    if not wallets:
        try:
            import time
            timestamp = int(time.time())
            wallet_name = f"wallet_{user_id}_{timestamp}"
            default_password = f"spark_{user_id}_{timestamp}"
            
            manager.set_master_password(default_password)
            result = manager.create_new_wallet(wallet_name)
            
            user_passwords[user_id] = default_password
            
            # Устанавливаем как активный
            manager.set_active_wallet(wallet_name)
            
            # Отправляем welcome сообщение с информацией о кошельке
            await message.answer(
                f"🎉 <b>Welcome to SPARK Wallet Bot!</b>\n\n"
                f"SPARK is a Layer 2 solution for Bitcoin with lightning-fast transfers and meme token trading.\n\n"
                f"✅ <b>Your first wallet W1 created!</b>\n\n"
                f"📍 Address:\n<code>{result['address']}</code>\n\n"
                f"🔑 <b>Private Key:</b>\n<code>{result['private_key']}</code>\n\n"
                f"📝 <b>Mnemonic Phrase:</b>\n<code>{result['mnemonic']}</code>\n\n"
                f"⚠️ <b>IMPORTANT:</b> Save your mnemonic and private key in a safe place!\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"ℹ️ Use /help to see all commands",
                parse_mode="HTML",
                reply_markup=main_menu()
            )
            print(f"[DEBUG] Auto-created wallet for new user {user_id}")
            return
            
        except Exception as e:
            print(f"[ERROR] Failed to create wallet for user {user_id}: {e}", file=sys.stderr)
            await message.answer(
                "❌ Error creating wallet. Try /create_wallet",
                reply_markup=main_menu()
            )
            return
    
    # Получаем информацию об активном кошельке
    active_wallet_info = manager.get_active_wallet()
    
    if active_wallet_info:
        wallet_name, wallet_data = active_wallet_info
        wallet_address = wallet_data.address
        # Извлекаем номер кошелька из имени
        wallet_list = list(manager.wallets.keys())
        wallet_num = wallet_list.index(wallet_name) + 1
        
        # ПОЛУЧАЕМ РЕАЛЬНЫЙ БАЛАНС!
        try:
            from btc_price import btc_price_service
            balance_info = await manager.get_wallet_balance(wallet_address)
            balance_sats = balance_info.get("balance_sats", 0)
            
            # Получаем цену BTC для конвертации
            try:
                btc_price = await btc_price_service.get_btc_price_usd()
                usd_value = btc_price_service.sats_to_usd(balance_sats, btc_price)
                usd_str = btc_price_service.format_usd(usd_value)
                balance_display = f"{balance_sats:,} SATS ({usd_str})"
            except:
                balance_display = f"{balance_sats:,} SATS"
        except Exception as e:
            print(f"[ERROR] Failed to get balance in main menu: {e}", file=sys.stderr)
            balance_display = "0 SATS"
        
        wallet_info = f"""
💼 <b>Active Wallet W{wallet_num}:</b>
<code>{wallet_address}</code>
💰 Balance: {balance_display}

<i>Switch wallet: /my_wallets</i>
"""
    else:
        wallet_info = """
💼 <b>You don't have a wallet yet</b>

<i>Create wallet: /create_wallet</i>
"""
    
    welcome_text = f"""🚀 <b>Welcome to SPARK Wallet Bot!</b>

SPARK is a Layer 2 solution for Bitcoin with lightning-fast transfers and meme token trading.
{wallet_info}
━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️ Use /help to see all commands"""
    
    # Создаем inline клавиатуру с кнопками
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    home_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💼 My Wallets", callback_data="home_my_wallets"),
            InlineKeyboardButton(text="📊 Positions", callback_data="home_positions")
        ],
        [
            InlineKeyboardButton(text="� Buy", callback_data="home_buy"),
            InlineKeyboardButton(text="💸 Sell", callback_data="home_sell")
        ],
        [
            InlineKeyboardButton(text="�💰 Deposit", callback_data="home_deposit"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="home_refresh")
        ],
        [
            InlineKeyboardButton(text="💰 Referral", callback_data="home_referral")
        ]
    ])
    
    try:
        await message.answer(welcome_text, parse_mode="HTML", reply_markup=home_keyboard)
        print(f"[DEBUG] Response sent to user {user_id}")
    except Exception as e:
        print(f"[ERROR] Failed to send response: {e}", file=sys.stderr)


async def cmd_create_wallet(message: types.Message, state: FSMContext):
    """Команда /create_wallet - создает кошелек и показывает приватный ключ"""
    user_id = message.from_user.id
    print(f"[DEBUG] Creating wallet for user {user_id}")
    await ensure_user_storage(user_id, message.from_user.username)
    manager = get_wallet_manager(user_id)
    
    try:
        import time
        timestamp = int(time.time())
        wallet_name = f"wallet_{user_id}_{timestamp}"
        default_password = f"spark_{user_id}_{timestamp}"
        
        manager.set_master_password(default_password)
        result = manager.create_new_wallet(wallet_name)
        print(f"[DEBUG] Wallet created: {result.get('address', 'N/A')}")
        
        user_passwords[user_id] = default_password
        
        from mnemonic import Mnemonic as MnemonicLib
        mnemo = MnemonicLib("english")
        seed = mnemo.to_seed(result['mnemonic'])
        private_key_hex = seed[:32].hex()
        
        await message.answer(
            "SPARK Wallet created successfully!\n\n"
            f"Name: `{wallet_name}`\n"
            f"Address: `{result['address']}`\n\n"
            "YOUR PRIVATE KEY (SAVE IT!):\n"
            f"`{private_key_hex}`\n\n"
            "Mnemonic phrase (also save this):\n"
            f"`{result['mnemonic']}`\n\n"
            "⚠️ KEEP THESE SAFE - YOU CANNOT RECOVER THEM!",
            parse_mode="markdown"
        )
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to create wallet: {error_msg}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        await message.answer(f"Error creating wallet: {error_msg}")


async def cmd_my_wallets(
    message: types.Message,
    *,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
):
    """Команда /my_wallets - показывает все кошельки с балансами"""

    actual_user_id = user_id
    actual_username = username

    if actual_user_id is None and getattr(message, "from_user", None):
        actual_user_id = message.from_user.id
    if actual_username is None and getattr(message, "from_user", None):
        actual_username = getattr(message.from_user, "username", None)

    if actual_user_id is None:
        raise RuntimeError("Не удалось определить пользователя для отображения кошельков")

    await ensure_user_storage(actual_user_id, actual_username)
    manager = get_wallet_manager(actual_user_id)
    wallets = manager.list_wallets()
    if not wallets:
        await message.answer("У вас пока нет кошельков. Используйте /create_wallet для создания.")
    else:
        text_msg = "🔧 <b>Настройки кошельков</b>\n\n"
        text_msg += "Управляйте всеми своими кошельками с легкостью.\n\n"
        
        # Получаем активный кошелек
        active_wallet_name = manager.active_wallet
        
        # Получаем актуальную цену BTC (один раз для всех кошельков)
        try:
            from btc_price import btc_price_service
            btc_price = await btc_price_service.get_btc_price_usd()
        except:
            btc_price = 100000.0  # Фоллбэк
        
        # Получаем балансы для каждого кошелька
        wallet_list = list(wallets.items())
        for idx, (name, info) in enumerate(wallet_list, 1):
            wallet_num = idx
            address = info['address']
            
            # Зеленый кружок для активного кошелька
            is_active = (name == active_wallet_name)
            status_icon = "🟢" if is_active else "⚪"
            
            # ПОЛУЧАЕМ РЕАЛЬНЫЙ БАЛАНС!
            try:
                from btc_price import btc_price_service
                balance_info = await manager.get_wallet_balance(address)
                balance_sats = balance_info.get("balance_sats", 0)
                
                # Конвертируем в USD
                usd_value = btc_price_service.sats_to_usd(balance_sats, btc_price)
                usd_str = btc_price_service.format_usd(usd_value)
                
                if balance_sats > 0:
                    balance_str = f"{balance_sats:,} SATS ({usd_str})"
                else:
                    balance_str = "0 SATS ($0.00)"
            except Exception as e:
                balance_str = "0 SATS ($0.00)"
                print(f"[ERROR] Failed to get balance for {address[:20]}: {e}", file=sys.stderr)
            
            # Показываем ПОЛНЫЙ адрес (без сокращений!)
            text_msg += f"{status_icon} <b>W{wallet_num}</b>\n<code>{address}</code>\n💰 {balance_str}\n\n"
        
        # Добавляем кнопки для переключения активного кошелька
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Создаем кнопки: по одному ряду на кошелек (кнопка выбора + кнопка удаления)
        buttons = []
        for idx, (name, info) in enumerate(wallet_list, 1):
            is_active = (name == active_wallet_name)
            button_text = f"{'🟢 ' if is_active else ''}W{idx}"
            
            row = [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"set_active_wallet:{name}"
                ),
                InlineKeyboardButton(
                    text="🗑️",
                    callback_data=f"delete_wallet_ask:{name}"
                )
            ]
            buttons.append(row)
        
        # Добавляем кнопки управления
        buttons.append([
            InlineKeyboardButton(text="💼 Создать кошелек", callback_data="create_new_wallet"),
            InlineKeyboardButton(text="🔑 Импортировать кошелек", callback_data="import_wallet")
        ])
        buttons.append([
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_wallets"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
        ])
        buttons.append([
            InlineKeyboardButton(text="❌ Закрыть", callback_data="close_wallets")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        text_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text_msg += "🟢 <b>Last updated:</b> {}\n".format(
            datetime.now().strftime("%H:%M:%S")
        )
        
        await message.answer(text_msg, parse_mode="HTML", reply_markup=keyboard)


async def cmd_buy(message: types.Message):
    """Команда /buy <contract_address> <amount_sats> - покупка мема"""
    text = message.text.split()
    if len(text) < 3:
        await message.answer("Usage: /buy <contract_address> <amount_sats>\nExample: /buy btkn1jg3s2lsdznlv49rapax862vkcfh6tc2gpravg0a7wy0mnpn7rkqqfgh0dl 10000")
        return
    
    contract_address = text[1]
    try:
        amount_sats = int(text[2])
    except ValueError:
        await message.answer("Error: amount must be a number")
        return
    
    await ensure_user_storage(message.from_user.id, message.from_user.username)
    manager = get_wallet_manager(message.from_user.id)
    wallets = manager.list_wallets()
    if not wallets:
        await message.answer("You don't have any wallets. Create one with /create_wallet")
        return
    
    wallet_name = list(wallets.keys())[0]
    
    try:
        result = await manager.buy_meme(contract_address, amount_sats, wallet_name)
        # Сохраняем позицию
        add_position(message.from_user.id, wallet_name, contract_address, amount_sats, "buy")
        await message.answer(
            f"Buy order created!\n"
            f"Contract: `{contract_address}`\n"
            f"Amount: {amount_sats} sats\n"
            f"Wallet: {wallet_name}\n"
            f"Txid: `{result.get('txid', 'pending')}`",
            parse_mode="markdown"
        )
    except Exception as e:
        await message.answer(f"Error: {str(e)}")


async def cmd_sell(message: types.Message, state: FSMContext = None):
    """Команда /sell <contract_address> <amount_sats> - продажа мема"""
    text = message.text.split()
    if len(text) < 3:
        await message.answer("Usage: /sell <contract_address> <amount_sats>\nExample: /sell btkn1jg3s2lsdznlv49rapax862vkcfh6tc2gpravg0a7wy0mnpn7rkqqfgh0dl 10000")
        return
    
    contract_address = text[1]
    try:
        amount_sats = int(text[2])
    except ValueError:
        await message.answer("Error: amount must be a number")
        return
    
    manager = get_wallet_manager(message.from_user.id)
    wallets = manager.list_wallets()
    if not wallets:
        await message.answer("You don't have any wallets. Create one with /create_wallet")
        return
    
    wallet_name = list(wallets.keys())[0]
    
    try:
        result = await manager.sell_meme(contract_address, amount_sats, wallet_name)
        # Обновляем позицию
        add_position(message.from_user.id, wallet_name, contract_address, amount_sats, "sell")
        await message.answer(
            f"Sell order created!\n"
            f"Contract: `{contract_address}`\n"
            f"Amount: {amount_sats} sats\n"
            f"Wallet: {wallet_name}\n"
            f"Txid: `{result.get('txid', 'pending')}`",
            parse_mode="markdown"
        )
    except Exception as e:
        await message.answer(f"Error: {str(e)}")


async def cmd_positions(
    message: types.Message,
    *,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
):
    """Команда /positions - показывает открытые позиции"""

    actual_user_id = user_id
    actual_username = username

    if actual_user_id is None and getattr(message, "from_user", None):
        actual_user_id = message.from_user.id
    if actual_username is None and getattr(message, "from_user", None):
        actual_username = getattr(message.from_user, "username", None)

    if actual_user_id is None:
        raise RuntimeError("Не удалось определить пользователя для отображения позиций")

    await ensure_user_storage(actual_user_id, actual_username)
    manager = get_wallet_manager(actual_user_id)
    wallets = manager.list_wallets()
    if not wallets:
        await message.answer("You don't have any wallets. Create one with /create_wallet")
        return
    
    positions = get_positions(message.from_user.id)
    
    if not positions:
        await message.answer("No open positions found.")
        return
    
    text_msg = "Open positions:\n\n"
    
    for wallet_name, wallet_positions in positions.items():
        if not wallet_positions:
            continue
        
        text_msg += f"*Wallet: {wallet_name}*\n"
        
        for contract_address, pos_data in wallet_positions.items():
            amount = pos_data.get("amount_sats", 0)
            total_bought = pos_data.get("total_bought", 0)
            total_sold = pos_data.get("total_sold", 0)
            
            if amount > 0:  # Показываем только открытые позиции
                text_msg += f"  Contract: `{contract_address}`\n"
                text_msg += f"  Amount: {amount} sats\n"
                text_msg += f"  Total bought: {total_bought} sats\n"
                text_msg += f"  Total sold: {total_sold} sats\n\n"
        
        text_msg += "\n"
    
    await message.answer(text_msg, parse_mode="markdown")


async def cmd_help(message: types.Message):
    """Команда /help"""
    help_text = """
    🆘 СПРАВКА

    **Кошельки:**
    /start - Главное меню
    /create_wallet - Создать кошелек
    /my_wallets - Показать кошельки
    /positions - Ваши позиции

    **Торговля:**
    /buy - Купить мем токен
    /sell - Продать токен
    /check <адрес> - Инфо о токене

    **Пополнение:**
    /deposit - Bitcoin адрес для пополнения с биржи
    
    **Переводы:**
    /create_invoice - Показать адрес для получения
    /send_transfer - Отправить на Spark адрес
    /pay_invoice - Оплатить Lightning invoice
    
    **Вывод:**
    /withdraw - Вывод на Bitcoin L1
    /withdrawal_help - Помощь

    **Как использовать:**

    1️⃣ **Создание кошелька**
       • Используйте /create_wallet
       • Бот сгенерирует mnemonic фразу
       ⚠️ СОХРАНИТЕ её в безопасном месте!

    2️⃣ **Торговля Мемами**
       • /buy - выбрать токен и сумму
       • /sell - продать ваши токены
       • /check - информация о токене

    3️⃣ **Вывод Средств**
       • Lightning - мгновенно и дешево
       • L1 - вывод на Bitcoin адрес
       • См. /withdrawal_help

    **Безопасность:**
    🔒 Все приватные ключи зашифрованы
    🔒 Mnemonic хранится безопасно
    ⚠️ Проверяйте адреса перед отправкой
    🔒 Mnemonic показывается только при создании

    **Что такое SPARK?**
    SPARK - это L2 решение для Bitcoin, которое:
    • Обеспечивает быстрые транзакции
    • Поддерживает создание и торговлю мемами (BTKN)
    • Работает без промежуточных посредников

    **Торговля мемами (BTKN):**
    • Нажмите "🛒 Купить мем" или "💸 Продать мем"
    • Выберите кошелек, введите адрес контракта (btkn1...) и сумму в сатоши
    """
    
    await message.answer(help_text, parse_mode="markdown")


# Обработчик сообщений
async def handle_message(message: types.Message, state: FSMContext):
    """Обработка текстовых сообщений"""
    text = message.text
    user_id = message.from_user.id
    print(f"[DEBUG] Received message from {user_id}: {text[:50]}")  # Debug
    await ensure_user_storage(user_id, message.from_user.username)
    manager = get_wallet_manager(user_id)
    
    # Проверка на кнопку создания кошелька - создаем сразу
    if text and (("Создать" in text and "кошелек" in text.lower()) or text == "➕ Создать кошелек"):
        print(f"[DEBUG] Creating wallet immediately for user {user_id}")
        try:
            # Генерируем автоматическое имя кошелька
            import time
            timestamp = int(time.time())
            wallet_name = f"wallet_{user_id}_{timestamp}"
            # Используем простой пароль по умолчанию
            default_password = f"spark_{user_id}_{timestamp}"
            
            manager.set_master_password(default_password)
            result = manager.create_new_wallet(wallet_name)
            print(f"[DEBUG] Wallet created: {result.get('address', 'N/A')}")
            
            # Получаем приватный ключ (нужно его получить из сохраненного кошелька)
            # Для этого используем временный способ - сохраняем пароль для этого пользователя
            user_passwords[user_id] = default_password
            
            # Получаем приватный ключ через верификацию (временное решение)
            # В реальности нужно хранить приватный ключ в расшифрованном виде для показа
            wallet_info = manager.get_wallet_info(wallet_name)
            
            # Для получения приватного ключа нужно знать оригинальный ключ
            # Попробуем получить его из созданного кошелька через восстановление из mnemonic
            from mnemonic import Mnemonic as MnemonicLib
            mnemo = MnemonicLib("english")
            seed = mnemo.to_seed(result['mnemonic'])
            private_key_hex = seed[:32].hex()
            
            await message.answer(
                "SPARK Wallet created successfully!\n\n"
                f"Name: `{wallet_name}`\n"
                f"Address: `{result['address']}`\n\n"
                "YOUR PRIVATE KEY (SAVE IT!):\n"
                f"`{private_key_hex}`\n\n"
                "Mnemonic phrase (also save this):\n"
                f"`{result['mnemonic']}`\n\n"
                "⚠️ KEEP THESE SAFE - YOU CANNOT RECOVER THEM!",
                parse_mode="markdown"
            )
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to create wallet: {error_msg}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            await message.answer(f"Error creating wallet: {error_msg}", reply_markup=main_menu())
    
    elif text == "📥 Импортировать кошелек":
        await message.answer(
            "Выберите способ импорта:",
            reply_markup=import_menu()
        )
    
    elif text == "📋 Мои кошельки":
        wallets = manager.list_wallets()
        if not wallets:
            await message.answer("У вас еще нет кошельков 😔")
        else:
            text_msg = "Ваши кошельки:\n\n"
            
            # Получаем балансы для каждого кошелька
            wallet_list = list(wallets.items())
            for idx, (name, info) in enumerate(wallet_list, 1):
                wallet_num = idx
                address = info['address']
                
                # Получаем баланс
                try:
                    balance_info = await manager.get_wallet_balance(address)
                    balance_sats = balance_info.get("balance_sats", 0)
                    balance_btc = balance_info.get("balance_btc", "0.00000000")
                    
                    # Форматируем баланс
                    if balance_sats == 0:
                        balance_str = "0 sats"
                    elif balance_sats < 1000:
                        balance_str = f"{balance_sats} sats"
                    else:
                        balance_str = f"{balance_btc} BTC ({balance_sats:,} sats)"
                    
                except Exception as e:
                    balance_str = "N/A"
                    print(f"[WARN] Could not get balance for {address}: {e}", file=sys.stderr)
                
                text_msg += f"W{wallet_num} - `{address}` - {balance_str}\n"
            
            await message.answer(text_msg, parse_mode="markdown")
    
    elif text == "🛒 Купить мем":
        # Вызываем новый buy handler
        await cmd_buy_new(message, state)
    
    elif text == "💸 Продать мем":
        # Вызываем новый sell handler
        await cmd_sell(message, state)
    
    elif text == "🔑 Показать приватный ключ":
        wallets = manager.list_wallets()
        if not wallets:
            await message.answer("У вас еще нет кошельков")
            return
        
        buttons = []
        for wallet_name in wallets.keys():
            buttons.append([InlineKeyboardButton(text=wallet_name, callback_data=f"select_wallet_{wallet_name}")])
        
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
        
        await message.answer(
            "Выберите кошелек:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    
    elif text == "🆘 Помощь":
        await cmd_help(message)
    
    # Обработка состояний
    else:
        current_state = await state.get_state()
        
        if current_state == WalletStates.waiting_wallet_name:
            wallet_name = text.strip()
            if not wallet_name:
                await message.answer("Wallet name cannot be empty")
                return
            
            print(f"[DEBUG] Wallet name received: {wallet_name}")
            await state.update_data(wallet_name=wallet_name)
            await state.set_state(WalletStates.waiting_password)
            await message.answer(
                f"Name: {wallet_name}\n\n"
                "Now enter password to protect the wallet:\n"
                "(Minimum 8 characters)"
            )
        
        elif current_state == WalletStates.waiting_password:
            password = text.strip()
            if len(password) < 8:
                await message.answer("Password must be at least 8 characters")
                return
            
            data = await state.get_data()
            wallet_name = data.get('wallet_name')
            
            if not wallet_name:
                await message.answer("Error: Wallet name not found. Please start over.", reply_markup=main_menu())
                await state.clear()
                return
            
            print(f"[DEBUG] Creating wallet '{wallet_name}' for user {user_id}")
            user_passwords[user_id] = password
            manager.set_master_password(password)
            
            # Создаем кошелек
            try:
                result = manager.create_new_wallet(wallet_name)
                print(f"[DEBUG] Wallet created successfully: {result.get('address', 'N/A')}")
                
                await message.answer(
                    "Wallet created successfully!\n\n"
                    f"Name: `{result['name']}`\n"
                    f"Address: `{result['address']}`\n\n"
                    "IMPORTANT! Save your Mnemonic phrase:\n\n"
                    f"`{result['mnemonic']}`\n\n"
                    "This phrase allows you to recover your wallet!",
                    parse_mode="markdown"
                )
                
                await asyncio.sleep(1)
                await message.answer(
                    "Wallet is ready to use!",
                    reply_markup=main_menu()
                )
            
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Failed to create wallet: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                await message.answer(f"Error creating wallet: {error_msg}\n\nPlease try again.", reply_markup=main_menu())
            
            await state.clear()
        
        elif current_state == WalletStates.waiting_mnemonic:
            mnemonic = text.strip()
            data = await state.get_data()
            wallet_name = data['wallet_name']
            
            try:
                password = user_passwords.get(message.from_user.id)
                if password:
                    manager.set_master_password(password)

                result = manager.import_wallet(wallet_name, mnemonic)
                await message.answer(
                    f"✅ Кошелек `{wallet_name}` успешно импортирован!\n\n"
                    f"📍 Адрес: `{result['address']}`",
                    parse_mode="markdown",
                    reply_markup=main_menu()
                )
            
            except Exception as e:
                await message.answer(f"❌ Ошибка: {str(e)}")
            
            await state.clear()
        
        elif current_state == WalletStates.waiting_private_key:
            private_key = text.strip()
            data = await state.get_data()
            wallet_name = data['wallet_name']
            
            try:
                password = user_passwords.get(message.from_user.id)
                if password:
                    manager.set_master_password(password)

                result = manager.import_from_private_key(wallet_name, private_key)
                if result['status'] == 'success':
                    await message.answer(
                        f"✅ Кошелек `{wallet_name}` успешно импортирован!\n\n"
                        f"📍 Адрес: `{result['address']}`",
                        parse_mode="markdown",
                        reply_markup=main_menu()
                    )
                else:
                    await message.answer(f"❌ Ошибка: {result['message']}")
            
            except Exception as e:
                await message.answer(f"❌ Ошибка: {str(e)}")
            
            await state.clear()
        
        elif current_state == WalletStates.waiting_private_key_for_export:
            private_key = text.strip()
            data = await state.get_data()
            wallet_name = data['wallet_name']
            
            try:
                password = user_passwords.get(message.from_user.id)
                if password:
                    manager.set_master_password(password)

                result = manager.get_private_key(wallet_name, private_key)
                if result:
                    await message.answer(
                        f"✅ **Приватный ключ кошелька `{wallet_name}`:**\n\n"
                        f"`{result}`\n\n"
                        "⚠️ **НИКОМУ не показывайте этот ключ!**",
                        parse_mode="markdown"
                    )
                else:
                    await message.answer(
                        "❌ Неверный приватный ключ. Доступ запрещен.",
                        reply_markup=main_menu()
                    )
            
            except Exception as e:
                await message.answer(f"❌ Ошибка: {str(e)}")
            
            await state.clear()

        elif current_state == WalletStates.trade_contract:
            contract = text.strip()
            try:
                if not manager.validate_spark_btkn_address(contract):
                    await message.answer(
                        "❌ Неверный адрес токена!\n\n"
                        "📋 <b>Требования:</b>\n"
                        "• Начинается с <code>btkn1</code>\n"
                        "• Длина 20-120 символов\n\n"
                        "📝 <b>Пример:</b>\n"
                        "<code>btkn1qyg5c7vxq7z2h9j3k4l5m6n7p8q9r0s2t3u4v5w6x7y8z9</code>\n\n"
                        "🔄 Попробуйте снова:",
                        parse_mode="HTML"
                    )
                    return
                await state.update_data(trade_contract=contract)
                await state.set_state(WalletStates.trade_amount)
                await message.answer("Введите сумму в сатоши:")
            except Exception as e:
                await message.answer(f"❌ Ошибка: {str(e)}")

        elif current_state == WalletStates.trade_amount:
            amount_text = text.strip()
            if not amount_text.isdigit():
                await message.answer("Введите целое число в сатоши")
                return
            amount = int(amount_text)
            data = await state.get_data()
            action = data.get('trade_action')
            wallet_name = data.get('trade_wallet')
            contract = data.get('trade_contract')
            try:
                if action == 'buy':
                    result = await manager.buy_meme(contract, amount, wallet_name)
                else:
                    result = await manager.sell_meme(contract, amount, wallet_name)
                await message.answer(
                    "✅ Сделка создана (заглушка).\n"
                    f"Действие: {result['action']}\n"
                    f"Кошелек: {result['wallet']}\n"
                    f"Контракт: {result['contract']}\n"
                    f"Сумма (sats): {result['amount_sats']}\n"
                    f"Txid: {result['txid']}",
                )
            except Exception as e:
                await message.answer(f"❌ Ошибка: {str(e)}")
            await state.clear()


# Обработчик callback'ов
async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка inline кнопок"""
    data = callback.data
    user_id = callback.from_user.id
    await ensure_user_storage(user_id, callback.from_user.username)
    manager = get_wallet_manager(user_id)
    
    # ========== ОБРАБОТЧИКИ ДОМАШНЕГО ЭКРАНА ==========
    
    # Кнопка My Wallets на домашнем экране
    if data == "home_my_wallets":
        await cmd_my_wallets(
            callback.message,
            user_id=user_id,
            username=callback.from_user.username,
        )
        await callback.answer()
        return
    
    # Кнопка Referral на домашнем экране
    elif data == "home_referral":        
        message, keyboard = await _build_referral_overview(user_id, manager)
        await callback.message.answer(
            message,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await callback.answer()
        return
    
    elif data == "refresh_referral":
        message, keyboard = await _build_referral_overview(user_id, manager)
        try:
            await callback.message.edit_text(
                message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as exc:
            # Если нельзя отредактировать (например, сообщение удалено), отправляем новое
            print(f"[WARN] Failed to edit referral message: {exc}")
            await callback.message.answer(
                message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        await callback.answer("🔄 Обновлено!")
        return
    
    elif data == "close_referral":
        try:
            await callback.message.delete()
        except Exception as exc:
            print(f"[WARN] Failed to delete referral message: {exc}")
        await callback.answer()
        return
    
    # Кнопка Positions на домашнем экране
    elif data == "home_positions":
        await cmd_positions(
            callback.message,
            user_id=user_id,
            username=callback.from_user.username,
        )
        await callback.answer()
        return
    
    # Кнопка Buy на домашнем экране
    elif data == "home_buy":
        await cmd_buy_new(callback.message, state, user_id=callback.from_user.id, username=callback.from_user.username)
        await callback.answer()
        return
    
    # Кнопка Sell на домашнем экране
    elif data == "home_sell":
        await cmd_sell(callback.message, state, user_id=callback.from_user.id, username=callback.from_user.username)
        await callback.answer()
        return
    
    # Кнопка Deposit на домашнем экране (показывает меню выбора)
    elif data == "home_deposit":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        deposit_menu = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Lightning Network",
                    callback_data="deposit_lightning"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏦 Bitcoin (L1)",
                    callback_data="deposit_bitcoin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="deposit_back"
                )
            ]
        ])
        
        await callback.message.answer(
            "💰 <b>Choose deposit method:</b>\n\n"
            "⚡ <b>Lightning Network</b>\n"
            "• Instant (5-10 seconds)\n"
            "• Low fees (~0.1%)\n"
            "• Min: 1,000 sats\n\n"
            "🏦 <b>Bitcoin (L1)</b>\n"
            "• Slower (10-60 min)\n"
            "• Higher fees\n"
            "• Permanent address\n"
            "• Min: 10,000 sats",
            parse_mode="HTML",
            reply_markup=deposit_menu
        )
        await callback.answer()
        return
    
    # Обработчик выбора Lightning депозита
    elif data == "deposit_lightning":
        from withdrawal_handlers import cmd_create_invoice
        await cmd_create_invoice(callback.message, state)
        await callback.answer()
        return
    
    # Обработчик выбора Bitcoin депозита
    elif data == "deposit_bitcoin":
        # Получаем mnemonic активного кошелька
        from withdrawal_handlers import get_user_wallet_mnemonic
        wallet_name, mnemonic, error = await get_user_wallet_mnemonic(user_id, callback.from_user.username)
        
        if error:
            await callback.answer(f"❌ {error}", show_alert=True)
            return
        
        # Проверяем, есть ли уже сохраненный Bitcoin адрес
        saved_address = manager.get_bitcoin_deposit_address(wallet_name)
        
        if saved_address:
            # Используем сохраненный адрес
            btc_address = saved_address
            await callback.message.answer(
                f"🏦 <b>Bitcoin Deposit Address (L1)</b>\n\n"
                f"📍 <b>Address:</b>\n<code>{btc_address}</code>\n\n"
                f"💡 <b>How to use:</b>\n"
                f"1. Open exchange (Binance, OKX, Kraken)\n"
                f"2. Withdraw → Bitcoin Network\n"
                f"3. Paste address above\n"
                f"4. Wait for confirmations (~10-60 min)\n"
                f"5. Funds will appear in your Spark wallet!\n\n"
                f"✅ This address is <b>permanent</b> - use it anytime!\n"
                f"⚠️ Min: 10,000 sats (~$1)\n\n"
                f"<i>Your Spark address: {manager.get_active_wallet()[1].address[:20]}...</i>",
                parse_mode="HTML"
            )
            await callback.answer("✅ Address ready!")
        else:
            # Генерируем новый адрес через Spark SDK
            await callback.message.answer("⏳ Generating your Bitcoin deposit address...")
            
            from spark_withdrawal import SparkWithdrawalManager
            withdrawal_mgr = SparkWithdrawalManager()
            
            result = withdrawal_mgr.get_deposit_address(mnemonic)
            
            if result.get('success'):
                btc_address = result.get('address')
                
                # Сохраняем адрес для постоянного использования
                manager.set_bitcoin_deposit_address(wallet_name, btc_address)
                
                await callback.message.answer(
                    f"🏦 <b>Bitcoin Deposit Address (L1)</b>\n\n"
                    f"📍 <b>Address:</b>\n<code>{btc_address}</code>\n\n"
                    f"💡 <b>How to use:</b>\n"
                    f"1. Open exchange (Binance, OKX, Kraken)\n"
                    f"2. Withdraw → Bitcoin Network\n"
                    f"3. Paste address above\n"
                    f"4. Wait for confirmations (~10-60 min)\n"
                    f"5. Funds will appear in your Spark wallet!\n\n"
                    f"✅ This address is <b>permanent</b> - saved for future use!\n"
                    f"⚠️ Min: 10,000 sats (~$1)\n\n"
                    f"<i>Your Spark address: {manager.get_active_wallet()[1].address[:20]}...</i>",
                    parse_mode="HTML"
                )
                await callback.answer("✅ Address generated & saved!")
            else:
                error_msg = result.get('error', 'Unknown error')
                await callback.message.answer(
                    f"❌ <b>Error getting deposit address:</b>\n\n{error_msg}",
                    parse_mode="HTML"
                )
                await callback.answer("❌ Error")
        return
    
    # Кнопка "Назад" в меню депозита
    elif data == "deposit_back":
        await callback.message.delete()
        await callback.answer()
        return
    
    # Кнопка Refresh на домашнем экране (обновляет баланс)
    elif data == "home_refresh":
        # Получаем информацию об активном кошельке
        active_wallet_info = manager.get_active_wallet()
        
        if active_wallet_info:
            wallet_name, wallet_data = active_wallet_info
            wallet_address = wallet_data.address
            wallet_list = list(manager.wallets.keys())
            wallet_num = wallet_list.index(wallet_name) + 1
            
            # ПОЛУЧАЕМ РЕАЛЬНЫЙ БАЛАНС!
            try:
                from btc_price import btc_price_service
                balance_info = await manager.get_wallet_balance(wallet_address)
                balance_sats = balance_info.get("balance_sats", 0)
                
                # Получаем цену BTC для конвертации
                try:
                    btc_price = await btc_price_service.get_btc_price_usd()
                    usd_value = btc_price_service.sats_to_usd(balance_sats, btc_price)
                    usd_str = btc_price_service.format_usd(usd_value)
                    balance_display = f"{balance_sats:,} SATS ({usd_str})"
                except:
                    balance_display = f"{balance_sats:,} SATS"
            except Exception as e:
                print(f"[ERROR] Failed to get balance on refresh: {e}", file=sys.stderr)
                balance_display = "0 SATS"
            
            wallet_info = f"""
💼 <b>Active Wallet W{wallet_num}:</b>
<code>{wallet_address}</code>
💰 Balance: {balance_display}

<i>Switch wallet: /my_wallets</i>
"""
        else:
            wallet_info = """
💼 <b>You don't have a wallet yet</b>

<i>Create wallet: /create_wallet</i>
"""
        
        # Добавляем timestamp для гарантированного изменения контента
        from datetime import datetime
        last_update = datetime.now().strftime("%H:%M:%S")
        
        welcome_text = f"""🚀 <b>Welcome to SPARK Wallet Bot!</b>

SPARK is a Layer 2 solution for Bitcoin with lightning-fast transfers and meme token trading.
{wallet_info}
━━━━━━━━━━━━━━━━━━━━━━━━━

🕐 Updated: {last_update}
ℹ️ Use /help to see all commands"""
        
        # Создаем клавиатуру
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        home_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💼 My Wallets", callback_data="home_my_wallets"),
                InlineKeyboardButton(text="📊 Positions", callback_data="home_positions")
            ],
            [
                InlineKeyboardButton(text="� Buy", callback_data="home_buy"),
                InlineKeyboardButton(text="💸 Sell", callback_data="home_sell")
            ],
            [
                InlineKeyboardButton(text="�💰 Deposit", callback_data="home_deposit"),
                InlineKeyboardButton(text="🔄 Refresh", callback_data="home_refresh")
            ]
        ])
        
        # ОБНОВЛЯЕМ существующее сообщение (не создаем новое!)
        try:
            await callback.message.edit_text(
                text=welcome_text,
                parse_mode="HTML",
                reply_markup=home_keyboard
            )
            await callback.answer("✅ Updated!")
        except Exception as e:
            # Если не удалось обновить (например, контент идентичен), просто показываем уведомление
            await callback.answer("✅ Already up to date!")
            print(f"[DEBUG] Refresh handled: {e}", file=sys.stderr)
        return
    
    # ========== ОБРАБОТЧИКИ УПРАВЛЕНИЯ КОШЕЛЬКАМИ ==========
    
    # Переключение активного кошелька
    if data.startswith("set_active_wallet:"):
        wallet_name = data.split(":", 1)[1]
        success = manager.set_active_wallet(wallet_name)
        
        if success:
            await callback.answer(f"✅ Установлен как активный!")
            # Обновляем сообщение
            await cmd_my_wallets(
                callback.message,
                user_id=user_id,
                username=callback.from_user.username,
            )
        else:
            await callback.answer("❌ Ошибка: кошелек не найден")
        return
    
    # Запрос на удаление кошелька (показываем подтверждение)
    elif data.startswith("delete_wallet_ask:"):
        wallet_name = data.split(":", 1)[1]
        
        # Извлекаем номер кошелька
        wallet_list = list(manager.wallets.keys())
        if wallet_name in wallet_list:
            wallet_num = wallet_list.index(wallet_name) + 1
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Да, удалить",
                        callback_data=f"delete_wallet_confirm:{wallet_name}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data="delete_wallet_cancel"
                    )
                ]
            ])
            
            await callback.message.answer(
                f"⚠️ <b>Удаление кошелька W{wallet_num}</b>\n\n"
                f"Вы уверены, что хотите удалить этот кошелек?\n\n"
                f"⚠️ <b>ВНИМАНИЕ:</b> Убедитесь, что у вас сохранен mnemonic или приватный ключ! "
                f"После удаления восстановить кошелек можно будет только через импорт.",
                parse_mode="HTML",
                reply_markup=confirm_keyboard
            )
            await callback.answer()
        else:
            await callback.answer("❌ Кошелек не найден")
        return
    
    # Подтверждение удаления кошелька
    elif data.startswith("delete_wallet_confirm:"):
        wallet_name = data.split(":", 1)[1]
        
        success = manager.delete_wallet(wallet_name)
        
        if success:
            # Удаляем сообщение с подтверждением
            await callback.message.delete()
            
            # Обновляем список кошельков
            await cmd_my_wallets(
                callback.message,
                user_id=user_id,
                username=callback.from_user.username,
            )
            
            await callback.answer("✅ Кошелек удален")
        else:
            await callback.answer("❌ Ошибка при удалении кошелька")
        return
    
    # Отмена удаления
    elif data == "delete_wallet_cancel":
        await callback.message.delete()
        await callback.answer("❌ Удаление отменено")
        return
    
    # Создание нового кошелька из my_wallets
    elif data == "create_new_wallet":
        try:
            import time
            timestamp = int(time.time())
            wallet_name = f"wallet_{user_id}_{timestamp}"
            default_password = f"spark_{user_id}_{timestamp}"
            
            manager.set_master_password(default_password)
            result = manager.create_new_wallet(wallet_name)
            
            user_passwords[user_id] = default_password
            
            # Устанавливаем новый кошелек как активный
            manager.set_active_wallet(wallet_name)
            
            # Показываем информацию о созданном кошельке
            wallet_num = len(manager.wallets)
            
            # ВАЖНО: Используем bot.send_message вместо callback.message.answer
            # чтобы отправить НОВОЕ сообщение с полной информацией
            from aiogram import Bot
            
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=(
                    f"✅ <b>Кошелек W{wallet_num} создан!</b>\n\n"
                    f"📍 <b>Адрес:</b>\n<code>{result['address']}</code>\n\n"
                    f"🔑 <b>Приватный ключ:</b>\n<code>{result['private_key']}</code>\n\n"
                    f"📝 <b>Mnemonic фраза:</b>\n<code>{result['mnemonic']}</code>\n\n"
                    f"⚠️ <b>ВАЖНО:</b> Сохраните mnemonic и приватный ключ в безопасном месте! "
                    f"Они нужны для восстановления доступа к кошельку.\n\n"
                    f"💡 Этот кошелек автоматически установлен как активный.\n\n"
                    f"Управление кошельками: /my_wallets"
                ),
                parse_mode="HTML"
            )

            await cmd_my_wallets(
                callback.message,
                user_id=user_id,
                username=callback.from_user.username,
            )

            await callback.answer("✅ Кошелек создан!")
            
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
            import traceback
            print(f"[ERROR] Failed to create wallet: {e}", file=sys.stderr)
            traceback.print_exc()
        return

        # Обработка кнопки Refresh в my_wallets
    elif data == "refresh_wallets":
        # Просто обновляем список кошельков (балансы получаются заново)
        await cmd_my_wallets(
            callback.message,
            user_id=user_id,
            username=callback.from_user.username,
        )
        await callback.answer("🔄 Обновлено!")
        return
    
    
    # Другие callback для wallets
    elif data == "close_wallets":
        await callback.message.delete()
        await callback.answer()
        return
    
    elif data == "import_wallet":
        await callback.answer("Используйте /import для импорта кошелька")
        return
    
    # Кнопка "Назад" - возврат на домашний экран
    elif data == "back_to_menu":
        # Получаем информацию об активном кошельке
        active_wallet_info = manager.get_active_wallet()
        
        if active_wallet_info:
            wallet_name, wallet_data = active_wallet_info
            wallet_address = wallet_data.address
            wallet_list = list(manager.wallets.keys())
            wallet_num = wallet_list.index(wallet_name) + 1
            
            wallet_info = f"""
💼 <b>Active Wallet W{wallet_num}:</b>
<code>{wallet_address}</code>
💰 Balance: 0 SATS

<i>Switch wallet: /my_wallets</i>
"""
        else:
            wallet_info = """
💼 <b>You don't have a wallet yet</b>

<i>Create wallet: /create_wallet</i>
"""
        
        welcome_text = f"""🚀 <b>Welcome to SPARK Wallet Bot!</b>

SPARK is a Layer 2 solution for Bitcoin with lightning-fast transfers and meme token trading.
{wallet_info}
━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️ Use /help to see all commands"""
        
        # Создаем inline клавиатуру с кнопками домашнего экрана
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        home_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💼 My Wallets", callback_data="home_my_wallets"),
                InlineKeyboardButton(text="📊 Positions", callback_data="home_positions")
            ],
            [
                InlineKeyboardButton(text="� Buy", callback_data="home_buy"),
                InlineKeyboardButton(text="💸 Sell", callback_data="home_sell")
            ],
            [
                InlineKeyboardButton(text="�💰 Deposit", callback_data="home_deposit"),
                InlineKeyboardButton(text="🔄 Refresh", callback_data="home_refresh")
            ]
        ])
        
        # Обновляем сообщение (возвращаемся на домашний экран)
        try:
            await callback.message.edit_text(
                text=welcome_text,
                parse_mode="HTML",
                reply_markup=home_keyboard
            )
            await callback.answer("⬅️ Home")
        except Exception as e:
            await callback.answer("❌ Error")
            print(f"[ERROR] Failed to go back to menu: {e}", file=sys.stderr)
        return
    
    elif data == "back_to_main":
        await callback.message.answer("Вернулись в главное меню", reply_markup=main_menu())
        await callback.answer()
        await state.clear()
    
    elif data == "import_mnemonic":
        await state.set_state(WalletStates.waiting_wallet_name)
        await callback.message.answer(
            "Введите имя для импортируемого кошелька:",
            reply_markup=back_button()
        )
        await callback.message.edit_text("Ввод имени кошелька...")
        
        # Сохраняем тип импорта
        await state.update_data(import_type="mnemonic")
        await callback.answer()
    
    elif data == "import_pk":
        await state.set_state(WalletStates.waiting_wallet_name)
        await callback.message.answer(
            "Введите имя для импортируемого кошелька:",
            reply_markup=back_button()
        )
        await callback.message.edit_text("Ввод имени кошелька...")
        
        # Сохраняем тип импорта
        await state.update_data(import_type="private_key")
        await callback.answer()
    
    elif data.startswith("select_wallet_"):
        wallet_name = data.replace("select_wallet_", "")
        await state.set_state(WalletStates.waiting_private_key_for_export)
        await state.update_data(wallet_name=wallet_name)
        
        await callback.message.answer(
            f"🔐 Для доступа к приватному ключу кошелька `{wallet_name}`\n\n"
            "Введите приватный ключ для верификации:",
            parse_mode="markdown"
        )
        await callback.answer()
    
    elif data.startswith("trade_wallet_"):
        wallet_name = data.replace("trade_wallet_", "")
        await state.update_data(trade_wallet=wallet_name)
        await state.set_state(WalletStates.trade_contract)
        await callback.message.answer(
            f"Выбран кошелек: `{wallet_name}`\nВведите адрес контракта (btkn1...):",
            parse_mode="markdown"
        )
        await callback.answer()
    
    else:
        await callback.answer()


# ========== НОВЫЕ ОБРАБОТЧИКИ ДЛЯ ПОКУПКИ ==========

async def cmd_check_token(message: types.Message):
    """Команда /check - проверить токен на Sparkscan"""
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        await message.answer(
            "📍 <b>Check Token on Sparkscan</b>\n\n"
            "Usage: <code>/check &lt;token_address&gt;</code>\n\n"
            "Example:\n"
            "<code>/check btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl</code>",
            parse_mode="HTML"
        )
        return
    
    token_addr = parts[1].strip()
    
    if not token_addr.startswith("btkn1"):
        await message.answer("❌ Invalid! SPARK token addresses start with <code>btkn1</code>", parse_mode="HTML")
        return
    
    sparkscan_url = f"https://sparkscan.io/token/{token_addr}"
    addr_short = f"{token_addr[:12]}...{token_addr[-10:]}"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🌐 Open on Sparkscan", url=sparkscan_url)],
    ])
    
    await message.answer(
        f"🔍 <b>Token Check</b>\n\n"
        f"📍 <code>{addr_short}</code>\n\n"
        f"Click button below to view:\n"
        f"• Symbol & Name\n"
        f"• Current Price\n"
        f"• Liquidity & Market Cap\n"
        f"• Holders & Transactions",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def cmd_buy_advanced(message: types.Message, state: FSMContext):
    """Улучшенная команда /buy с полным интерфейсом"""
    user_id = message.from_user.id
    print(f"[DEBUG] User {user_id} started advanced /buy")
    await ensure_user_storage(user_id, message.from_user.username)
    manager = get_wallet_manager(user_id)
    wallets = manager.list_wallets()
    if not wallets:
        await message.answer("❌ У вас нет кошельков! Создайте: /create_wallet")
        return
    
    await state.set_state(WalletStates.waiting_token_address)
    await message.answer(
        "🛒 <b>Покупка токена</b>\n\n"
        "📝 Enter a token symbol or address to buy:\n\n"
        "Формат: <code>btkn1...</code>",
        parse_mode="HTML"
    )


async def handle_token_input(message: types.Message, state: FSMContext):
    """Обработка ввода адреса токена"""
    token_addr = message.text.strip()
    await ensure_user_storage(message.from_user.id, message.from_user.username)
    manager = get_wallet_manager(message.from_user.id)
    
    if not manager.validate_spark_btkn_address(token_addr):
        await message.answer("❌ Неверный адрес! Формат: btkn1...")
        return
    
    await message.answer("⏳ Загрузка...")
    
    try:
        token_info = await token_service.get_token_info(token_addr)
        
        wallets = manager.list_wallets()
        first_wallet = list(wallets.keys())[0]
        wallet_addr = wallets[first_wallet]['address']
        
        try:
            bal = await manager.get_wallet_balance(wallet_addr)
            balance_btc = bal.get("balance_btc", "0.00000000")
        except:
            balance_btc = "0.00000000"
        
        await state.update_data(
            token_address=token_addr,
            token_info=token_info,
            selected_wallet="W1",
            selected_wallet_name=first_wallet,
            selected_amount=0.001,
            buy_tip=0.0000001,
            slippage=10.0,
            wallet_balance=balance_btc
        )
        
        # Формируем сообщение
        symbol = token_info.get("symbol", "UNKNOWN")
        name = token_info.get("name", "Unknown")
        price = token_service.format_price(token_info.get("price_usd", 0))
        liq = token_service.format_liquidity(token_info.get("liquidity_usd", 0))
        mc = token_service.format_market_cap(token_info.get("market_cap_usd", 0))
        
        addr_short = f"{token_addr[:10]}...{token_addr[-10:]}"
        sparkscan_url = token_info.get("sparkscan_url", f"https://sparkscan.io/token/{token_addr}")
        
        # Проверяем доступность API
        api_note = ""
        if token_info.get("_api_status") == "unavailable":
            api_note = (
                f"\n\n⚠️ <i>Market data API unavailable</i>\n"
                f"📊 <a href='{sparkscan_url}'>View token on Sparkscan →</a>\n\n"
                f"<b>Note:</b> You can still buy this token.\n"
                f"Check price manually on Sparkscan or DEX."
            )
        
        msg = (
            f"🛒 <b>Buy Token</b>\n\n"
            f"📍 <code>{token_addr}</code>\n\n"
            f"💰 Your Balance: <b>{balance_btc} BTC</b> — W1\n"
            f"💵 Price: {price}\n"
            f"💧 Liquidity: {liq}\n"
            f"📊 Market Cap: {mc}"
            f"{api_note}\n\n"
            f"👇 <b>Select amount to buy:</b>"
        )
        
        # Создаем клавиатуру
        from buy_keyboards import create_buy_keyboard
        keyboard = create_buy_keyboard(
            wallets=list(wallets.keys()),
            selected_wallet="W1",
            selected_amount=0.001,
            buy_tip=0.0000001,
            slippage=10.0
        )
        
        await state.set_state(WalletStates.buy_confirming)
        await message.answer(msg, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


# ========== CALLBACK ОБРАБОТЧИКИ ДЛЯ КНОПОК ПОКУПКИ ==========

async def handle_buy_callbacks(callback: types.CallbackQuery, state: FSMContext):
    """Универсальный обработчик всех callback для покупки"""
    data = callback.data
    user_id = callback.from_user.id
    await ensure_user_storage(user_id, callback.from_user.username)
    manager = get_wallet_manager(user_id)
    
    # Refresh - обновление данных
    if data == "buy_refresh":
        await callback.answer("🔄 Обновление...")
        state_data = await state.get_data()
        token_addr = state_data.get("token_address")
        
        if not token_addr:
            await callback.answer("❌ Ошибка")
            return
        
        try:
            token_info = await token_service.get_token_info(token_addr)
            await state.update_data(token_info=token_info)
            
            # Обновляем сообщение
            symbol = token_info.get("symbol", "UNKNOWN")
            name = token_info.get("name", "Unknown")
            price = token_service.format_price(token_info.get("price_usd", 0))
            liq = token_service.format_liquidity(token_info.get("liquidity_usd", 0))
            mc = token_service.format_market_cap(token_info.get("market_cap_usd", 0))
            addr_short = f"{token_addr[:10]}...{token_addr[-10:]}"
            balance_btc = state_data.get("wallet_balance", "0.00000000")
            selected_wallet = state_data.get("selected_wallet", "W1")
            
            msg = (
                f"🛒 <b>Buy ${symbol}</b> — {name} 📈\n\n"
                f"📍 <code>{addr_short}</code>\n\n"
                f"💰 Balance: {balance_btc} BTC — {selected_wallet}\n"
                f"💵 Price: {price}\n"
                f"💧 LIQ: {liq} — 📊 MC: {mc}\n\n"
                f"👇 Select options:"
            )
            
            from buy_keyboards import create_buy_keyboard
            wallets = manager.list_wallets()
            keyboard = create_buy_keyboard(
                wallets=list(wallets.keys()),
                selected_wallet=state_data.get("selected_wallet", "W1"),
                selected_amount=state_data.get("selected_amount", 0.001),
                buy_tip=state_data.get("buy_tip", 0.0000001),
                slippage=state_data.get("slippage", 10.0)
            )
            
            await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            print(f"[ERROR] Refresh failed: {e}")
            await callback.answer("❌ Ошибка обновления", show_alert=True)
    
    # Выбор кошелька (W1, W2, etc)
    elif data.startswith("buy_wallet_"):
        parts = data.split("_", 3)
        wallet_label = parts[2]  # W1, W2
        wallet_name = parts[3]
        
        await callback.answer(f"✓ {wallet_label}")
        
        # Обновляем баланс
        wallets = manager.list_wallets()
        wallet_addr = wallets[wallet_name]['address']
        try:
            bal = await manager.get_wallet_balance(wallet_addr)
            balance_btc = bal.get("balance_btc", "0.00000000")
        except:
            balance_btc = "0.00000000"
        
        await state.update_data(
            selected_wallet=wallet_label,
            selected_wallet_name=wallet_name,
            wallet_balance=balance_btc
        )
        
        # Обновляем сообщение
        state_data = await state.get_data()
        token_info = state_data.get("token_info", {})
        symbol = token_info.get("symbol", "UNKNOWN")
        name = token_info.get("name", "Unknown")
        price = token_service.format_price(token_info.get("price_usd", 0))
        liq = token_service.format_liquidity(token_info.get("liquidity_usd", 0))
        mc = token_service.format_market_cap(token_info.get("market_cap_usd", 0))
        token_addr = state_data.get("token_address", "")
        addr_short = f"{token_addr[:10]}...{token_addr[-10:]}"
        
        msg = (
            f"🛒 <b>Buy ${symbol}</b> — {name} 📈\n\n"
            f"📍 <code>{addr_short}</code>\n\n"
            f"💰 Balance: {balance_btc} BTC — {wallet_label}\n"
            f"💵 Price: {price}\n"
            f"💧 LIQ: {liq} — 📊 MC: {mc}\n\n"
            f"👇 Select options:"
        )
        
        from buy_keyboards import create_buy_keyboard
        keyboard = create_buy_keyboard(
            wallets=list(wallets.keys()),
            selected_wallet=wallet_label,
            selected_amount=state_data.get("selected_amount", 0.001),
            buy_tip=state_data.get("buy_tip", 0.0000001),
            slippage=state_data.get("slippage", 10.0)
        )
        
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    # Выбор суммы (0.001, 0.0001, custom)
    elif data.startswith("buy_amount_"):
        amount_str = data.replace("buy_amount_", "")
        
        if amount_str == "custom":
            await callback.answer("✏️ Введите сумму")
            await state.set_state(WalletStates.waiting_custom_amount)
            await callback.message.answer(
                "💰 <b>Введите сумму в BTC:</b>\n\n"
                "Например: <code>0.0005</code>",
                parse_mode="HTML"
            )
            return
        
        try:
            amount = float(amount_str)
            await callback.answer(f"✓ {amount} BTC")
            await state.update_data(selected_amount=amount)
            
            # Обновляем клавиатуру
            state_data = await state.get_data()
            from buy_keyboards import create_buy_keyboard
            wallets = manager.list_wallets()
            keyboard = create_buy_keyboard(
                wallets=list(wallets.keys()),
                selected_wallet=state_data.get("selected_wallet", "W1"),
                selected_amount=amount,
                buy_tip=state_data.get("buy_tip", 0.0000001),
                slippage=state_data.get("slippage", 10.0)
            )
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except:
            await callback.answer("❌ Ошибка")
    
    # Buy Tip - открыть меню
    elif data == "buy_set_tip":
        await callback.answer("⚡ Настройка tip")
        from buy_keyboards import create_tip_keyboard
        await callback.message.answer(
            "⚡ <b>Buy Tip</b>\n\nВыберите размер комиссии:",
            reply_markup=create_tip_keyboard(),
            parse_mode="HTML"
        )
    
    # Выбор tip
    elif data.startswith("tip_"):
        if data == "tip_back":
            await callback.message.delete()
            await callback.answer()
            return
        
        if data == "tip_custom":
            await callback.answer("✏️ Введите tip")
            await state.set_state(WalletStates.waiting_buy_tip)
            await callback.message.answer(
                "⚡ <b>Введите Buy Tip в BTC:</b>\n\n"
                "Например: <code>0.0000005</code>",
                parse_mode="HTML"
            )
            return
        
        tip_str = data.replace("tip_", "")
        try:
            tip = float(tip_str)
            await callback.answer(f"✓ Tip: {tip:.8f} BTC")
            await state.update_data(buy_tip=tip)
            await callback.message.delete()
        except:
            await callback.answer("❌ Ошибка")
    
    # Slippage - открыть меню
    elif data == "buy_set_slippage":
        await callback.answer("📊 Настройка slippage")
        from buy_keyboards import create_slippage_keyboard
        await callback.message.answer(
            "📊 <b>Slippage</b>\n\nВыберите процент проскальзывания:",
            reply_markup=create_slippage_keyboard(),
            parse_mode="HTML"
        )
    
    # Выбор slippage
    elif data.startswith("slippage_"):
        if data == "slippage_back":
            await callback.message.delete()
            await callback.answer()
            return
        
        if data == "slippage_custom":
            await callback.answer("✏️ Введите slippage")
            await state.set_state(WalletStates.waiting_buy_slippage)
            await callback.message.answer(
                "📊 <b>Введите slippage в %:</b>\n\n"
                "Например: <code>15</code>",
                parse_mode="HTML"
            )
            return
        
        slip_str = data.replace("slippage_", "")
        try:
            slippage = float(slip_str)
            await callback.answer(f"✓ Slippage: {slippage:.1f}%")
            await state.update_data(slippage=slippage)
            await callback.message.delete()
        except:
            await callback.answer("❌ Ошибка")
    
    # Buy via Flashnet AMM
    elif data == "buy_flashnet_method":
        await callback.answer("⚡ Покупка через Flashnet AMM")
        await state.update_data(buy_method="flashnet")
        
        state_data = await state.get_data()
        token_info = state_data.get("token_info", {})
        token_addr = state_data.get("token_address", "")
        symbol = token_info.get("symbol", "UNKNOWN")
        name = token_info.get("name", "Unknown Token")
        amount = state_data.get("selected_amount", 0.001)
        tip = state_data.get("buy_tip", 0.0000001)
        slippage = state_data.get("slippage", 10.0)
        wallet = state_data.get("selected_wallet", "W1")
        
        # Если symbol == UNKNOWN, показываем адрес
        if symbol == "UNKNOWN" or "Token (" in symbol:
            addr_short = f"{token_addr[:10]}...{token_addr[-8:]}"
            display_name = f"{addr_short}"
        else:
            display_name = f"${symbol}"
        
        calc = await token_service.calculate_tokens_for_btc(token_addr, amount)
        token_amount = calc.get("token_amount", 0)
        token_price_btc = calc.get("token_price_btc", 0)
        total = amount + tip
        
        # Проверка доступности цены токена
        price_available = token_price_btc > 0 and token_amount > 0
        
        if price_available:
            token_display = f"~{token_amount:,.2f} токенов"
            warning_msg = f"⚠️ Подтвердите покупку:"
        else:
            token_display = "❌ N/A (цена неизвестна)"
            warning_msg = (
                f"⚠️ <b>ВНИМАНИЕ:</b>\n"
                f"Цена токена недоступна!\n"
                f"Причина: Flashnet AMM API заблокирован (403)\n\n"
                f"Покупка невозможна до разблокировки API."
            )
        
        msg = (
            f"⚡ <b>Покупка через Flashnet AMM</b>\n\n"
            f"🪙 Токен: <b>{display_name}</b>\n"
            f"📝 {name}\n"
            f"💰 Сумма: <b>{amount:.8f} BTC</b>\n"
            f"⚡ Tip: <b>{tip:.8f} BTC</b>\n"
            f"📊 Slippage: <b>{slippage:.1f}%</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 Итого: <b>{total:.8f} BTC</b>\n\n"
            f"📦 Получите: <b>{token_display}</b>\n"
            f"💼 Кошелек: <b>{wallet}</b>\n\n"
            f"{warning_msg}"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Confirm", callback_data="buy_execute_flashnet")],
            [types.InlineKeyboardButton(text="❌ Cancel", callback_data="buy_cancel")]
        ])
        
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
    
    # Buy via Spark Money
    elif data == "buy_spark_method":
        await callback.answer("💫 Покупка через Spark Money")
        await state.update_data(buy_method="spark")
        
        state_data = await state.get_data()
        token_info = state_data.get("token_info", {})
        token_addr = state_data.get("token_address", "")
        symbol = token_info.get("symbol", "UNKNOWN")
        name = token_info.get("name", "Unknown Token")
        amount = state_data.get("selected_amount", 0.001)
        tip = state_data.get("buy_tip", 0.0000001)
        slippage = state_data.get("slippage", 10.0)
        wallet = state_data.get("selected_wallet", "W1")
        
        # Если symbol == UNKNOWN, показываем адрес
        if symbol == "UNKNOWN" or "Token (" in symbol:
            addr_short = f"{token_addr[:10]}...{token_addr[-8:]}"
            display_name = f"{addr_short}"
        else:
            display_name = f"${symbol}"
        
        calc = await token_service.calculate_tokens_for_btc(token_addr, amount)
        token_amount = calc.get("token_amount", 0)
        token_price_btc = calc.get("token_price_btc", 0)
        total = amount + tip
        
        # Проверка доступности цены токена
        price_available = token_price_btc > 0 and token_amount > 0
        
        if price_available:
            token_display = f"~{token_amount:,.2f} токенов"
            warning_msg = f"⚠️ Подтвердите покупку:"
        else:
            token_display = "❌ N/A (цена неизвестна)"
            warning_msg = (
                f"⚠️ <b>ВНИМАНИЕ:</b>\n"
                f"Цена токена недоступна!\n"
                f"API недоступен или токен не найден.\n\n"
                f"Покупка невозможна без цены токена."
            )
        
        msg = (
            f"💫 <b>Покупка через Spark Money API</b>\n\n"
            f"🪙 Токен: <b>{display_name}</b>\n"
            f"📝 {name}\n"
            f"💰 Сумма: <b>{amount:.8f} BTC</b>\n"
            f"⚡ Tip: <b>{tip:.8f} BTC</b>\n"
            f"📊 Slippage: <b>{slippage:.1f}%</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 Итого: <b>{total:.8f} BTC</b>\n\n"
            f"📦 Получите: <b>{token_display}</b>\n"
            f"💼 Кошелек: <b>{wallet}</b>\n\n"
            f"{warning_msg}"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Confirm", callback_data="buy_execute_spark")],
            [types.InlineKeyboardButton(text="❌ Cancel", callback_data="buy_cancel")]
        ])
        
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
    
    # Buy Now - показать подтверждение (старый метод, для обратной совместимости)
    elif data == "buy_confirm":
        state_data = await state.get_data()
        token_info = state_data.get("token_info", {})
        token_addr = state_data.get("token_address", "")
        symbol = token_info.get("symbol", "UNKNOWN")
        name = token_info.get("name", "Unknown Token")
        amount = state_data.get("selected_amount", 0.001)
        tip = state_data.get("buy_tip", 0.0000001)
        slippage = state_data.get("slippage", 10.0)
        wallet = state_data.get("selected_wallet", "W1")
        
        # Если symbol == UNKNOWN, показываем адрес
        if symbol == "UNKNOWN" or "Token (" in symbol:
            addr_short = f"{token_addr[:10]}...{token_addr[-8:]}"
            display_name = f"{addr_short}"
        else:
            display_name = f"${symbol}"
        
        calc = await token_service.calculate_tokens_for_btc(token_addr, amount)
        token_amount = calc.get("token_amount", 0)
        token_price_btc = calc.get("token_price_btc", 0)
        price_usd = token_info.get("price_usd", 0)
        
        total = amount + tip
        
        # Проверка доступности цены токена
        price_available = token_price_btc > 0 and token_amount > 0
        
        if price_available:
            token_display = f"~{token_amount:,.2f} токенов"
            warning_msg = f"⚠️ Подтвердите покупку:"
        else:
            token_display = "❌ N/A (цена неизвестна)"
            warning_msg = (
                f"⚠️ <b>ВНИМАНИЕ:</b>\n"
                f"Цена токена недоступна!\n"
                f"API недоступен или токен не найден.\n\n"
                f"Покупка невозможна без цены токена."
            )
        
        msg = (
            f"🔔 <b>Подтверждение</b>\n\n"
            f"🪙 Токен: <b>{display_name}</b>\n"
            f"📝 {name}\n"
            f"💰 Сумма: <b>{amount:.8f} BTC</b>\n"
            f"⚡ Tip: <b>{tip:.8f} BTC</b>\n"
            f"📊 Slippage: <b>{slippage:.1f}%</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 Итого: <b>{total:.8f} BTC</b>\n\n"
            f"📦 Получите: <b>{token_display}</b>\n"
            f"💼 Кошелек: <b>{wallet}</b>\n\n"
            f"{warning_msg}"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Confirm", callback_data="buy_execute")],
            [types.InlineKeyboardButton(text="❌ Cancel", callback_data="buy_cancel")]
        ])
        
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("👆 Проверьте детали")
    
    # Execute - выполнить покупку
    elif data == "buy_execute":
        await callback.answer("⏳ Выполнение...")
        
        state_data = await state.get_data()
        token_info = state_data.get("token_info", {})
        # ИСПРАВЛЕНО: используем token_address из state, а не из token_info
        token_addr = state_data.get("token_address", "")
        symbol = token_info.get("symbol", "UNKNOWN")
        amount = state_data.get("selected_amount", 0.001)
        tip = state_data.get("buy_tip", 0.0000001)
        slippage = state_data.get("slippage", 10.0)
        wallet_name = state_data.get("selected_wallet_name")
        
        print(f"[BUY_EXECUTE] Token address: {token_addr}")
        print(f"[BUY_EXECUTE] Wallet: {wallet_name}")
        print(f"[BUY_EXECUTE] Amount: {amount} BTC")
        
        try:
            await callback.message.edit_text(
                f"⏳ <b>Покупка {symbol}...</b>\n\nПодождите...",
                parse_mode="HTML"
            )
            
            amount_sats = token_service.btc_to_sats(amount)
            tip_sats = token_service.btc_to_sats(tip)
            
            print(f"[BUY_EXECUTE] Amount in sats: {amount_sats}")
            print(f"[BUY_EXECUTE] Calling buy_meme()...")
            
            result = await manager.buy_meme(
                contract_address=token_addr,
                amount_sats=amount_sats,
                wallet_name=wallet_name,
                slippage=slippage,
                priority_fee_sats=tip_sats
            )
            
            print(f"[BUY_EXECUTE] Result: {result}")
            
            # Проверяем статус результата
            if result.get("status") != "success":
                # Ошибка при покупке
                error_msg = result.get("error", result.get("message", "Неизвестная ошибка"))
                raise Exception(error_msg)
            
            add_position(user_id, wallet_name, token_addr, amount_sats, "buy")
            
            # Получаем количество токенов из результата
            tokens_received_sats = result.get("tokens_received_sats", result.get("tokens_received", 0))
            tokens_received = tokens_received_sats / 100_000_000  # Конвертируем в целые токены
            
            # Получаем TxID
            txid = result.get("txid")
            if not txid:
                raise Exception("Транзакция не содержит TxID! Покупка не выполнена.")
            
            # Реальная транзакция
            msg = (
                f"✅ <b>Покупка выполнена!</b>\n\n"
                f"🪙 Куплено: <b>{tokens_received:,.2f} {symbol}</b>\n"
                f"💰 Потрачено: <b>{amount:.8f} BTC</b> (<code>{amount_sats} sats</code>)\n"
                f"⚡ Комиссия: <b>{tip:.8f} BTC</b> (<code>{tip_sats} sats</code>)\n\n"
                f"📋 TxID:\n<code>{txid}</code>\n\n"
                f"🎉 Токены зачислены на кошелек!"
            )
            
            await callback.message.edit_text(msg, parse_mode="HTML")
            
        except Exception as e:
            print(f"[ERROR] Buy execute failed: {e}")
            import traceback
            traceback.print_exc()
            await callback.message.edit_text(
                f"❌ <b>Ошибка при покупке!</b>\n\n{str(e)}",
                parse_mode="HTML"
            )
        
        await state.clear()
    
    # Execute Flashnet - выполнить покупку через Flashnet AMM
    elif data == "buy_execute_flashnet":
        await callback.answer("⏳ Выполнение через Flashnet AMM...")
        
        state_data = await state.get_data()
        token_info = state_data.get("token_info", {})
        token_addr = state_data.get("token_address", "")
        symbol = token_info.get("symbol", "UNKNOWN")
        amount = state_data.get("selected_amount", 0.001)
        tip = state_data.get("buy_tip", 0.0000001)
        slippage = state_data.get("slippage", 10.0)
        wallet_name = state_data.get("selected_wallet_name")
        
        print(f"[BUY_FLASHNET] Token address: {token_addr}")
        print(f"[BUY_FLASHNET] Wallet: {wallet_name}")
        print(f"[BUY_FLASHNET] Amount: {amount} BTC")
        
        try:
            await callback.message.edit_text(
                f"⏳ <b>Покупка {symbol} через Flashnet AMM...</b>\n\nПодождите...",
                parse_mode="HTML"
            )
            
            amount_sats = token_service.btc_to_sats(amount)
            tip_sats = token_service.btc_to_sats(tip)
            
            # Используем новую Flashnet AMM интеграцию
            from flashnet_integration import execute_buy
            
            result = await execute_buy(
                wallet_manager=manager,
                wallet_name=wallet_name,
                token_address=token_addr,
                amount_btc_sats=amount_sats,
                slippage_pct=slippage
            )
            
            print(f"[BUY_FLASHNET] Result: {result}")
            
            if result.get("status") == "success":
                add_position(user_id, wallet_name, token_addr, amount_sats, "buy")
                
                tokens_received_sats = result.get("tokens_received_sats", result.get("tokens_received", 0))
                tokens_received = tokens_received_sats / 100_000_000
                
                msg = (
                    f"✅ <b>Покупка через Flashnet AMM выполнена!</b>\n\n"
                    f"🪙 Куплено: <b>{tokens_received:,.2f} {symbol}</b>\n"
                    f"💰 Потрачено: <b>{amount:.8f} BTC</b> (<code>{amount_sats} sats</code>)\n"
                    f"⚡ Комиссия: <b>{tip:.8f} BTC</b> (<code>{tip_sats} sats</code>)\n\n"
                    f"📋 TxID:\n<code>{result.get('txid', 'N/A')}</code>\n\n"
                    f"🎉 Токены зачислены на кошелек!"
                )
                
                await callback.message.edit_text(msg, parse_mode="HTML")
            else:
                # Ошибка выполнения
                error_msg = result.get("message", result.get("error", "Неизвестная ошибка"))
                await callback.message.edit_text(
                    f"❌ <b>Ошибка Flashnet AMM!</b>\n\n{error_msg}\n\n"
                    f"💡 Попробуйте метод Spark Money",
                    parse_mode="HTML"
                )
            
        except Exception as e:
            print(f"[ERROR] Flashnet buy failed: {e}")
            import traceback
            traceback.print_exc()
            await callback.message.edit_text(
                f"❌ <b>Ошибка Flashnet AMM!</b>\n\n{str(e)}\n\n"
                f"💡 Попробуйте метод Spark Money",
                parse_mode="HTML"
            )
        
        await state.clear()
    
    # Execute Spark - выполнить покупку через Spark Money
    elif data == "buy_execute_spark":
        await callback.answer("⏳ Выполнение через Spark Money...")
        
        state_data = await state.get_data()
        token_info = state_data.get("token_info", {})
        token_addr = state_data.get("token_address", "")
        symbol = token_info.get("symbol", "UNKNOWN")
        amount = state_data.get("selected_amount", 0.001)
        tip = state_data.get("buy_tip", 0.0000001)
        slippage = state_data.get("slippage", 10.0)
        wallet_name = state_data.get("selected_wallet_name")
        
        print(f"[BUY_SPARK] Token address: {token_addr}")
        print(f"[BUY_SPARK] Wallet: {wallet_name}")
        print(f"[BUY_SPARK] Amount: {amount} BTC")
        
        try:
            await callback.message.edit_text(
                f"⏳ <b>Покупка {symbol} через Spark Money...</b>\n\nПодождите...",
                parse_mode="HTML"
            )
            
            amount_sats = token_service.btc_to_sats(amount)
            tip_sats = token_service.btc_to_sats(tip)
            
            print(f"[BUY_SPARK] Amount in sats: {amount_sats}")
            print(f"[BUY_SPARK] Calling wallet_manager.buy_meme_native()...")
            
            # Используем нативный метод Spark SDK (ВЫБРОСИТ NotImplementedError)
            result = await manager.buy_meme_native(
                contract_address=token_addr,
                amount_sats=amount_sats,
                wallet_name=wallet_name,
                slippage=slippage,
                priority_fee_sats=tip_sats
            )
            
            # Этот код никогда не выполнится, т.к. buy_meme_native() выбрасывает NotImplementedError
            print(f"[BUY_SPARK] Result: {result}")
            
            # Проверяем статус результата
            if result.get("status") != "success":
                error_msg = result.get("error", result.get("message", "Неизвестная ошибка"))
                raise Exception(error_msg)
            
            add_position(user_id, wallet_name, token_addr, amount_sats, "buy")
            
            tokens_received_sats = result.get("tokens_received_sats", result.get("tokens_received", 0))
            tokens_received = tokens_received_sats / 100_000_000
            
            txid = result.get("txid")
            if not txid:
                raise Exception("Транзакция не содержит TxID!")
            
            msg = (
                f"✅ <b>Покупка через Spark Money выполнена!</b>\n\n"
                f"🪙 Куплено: <b>{tokens_received:,.2f} {symbol}</b>\n"
                f"💰 Потрачено: <b>{amount:.8f} BTC</b> (<code>{amount_sats} sats</code>)\n"
                f"⚡ Комиссия: <b>{tip:.8f} BTC</b> (<code>{tip_sats} sats</code>)\n\n"
                f"📋 TxID:\n<code>{txid}</code>\n\n"
                f"🎉 Токены зачислены на кошелек!"
            )
            
            await callback.message.edit_text(msg, parse_mode="HTML")
            
        except NotImplementedError as e:
            # buy_meme_native() не реализован
            print(f"[ERROR] Spark native not implemented: {e}")
            await callback.message.edit_text(
                f"❌ <b>Spark Money не реализован!</b>\n\n"
                f"{str(e)}\n\n"
                f"💡 Используйте <b>Flashnet AMM</b> вместо этого метода.",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[ERROR] Spark buy failed: {e}")
            import traceback
            traceback.print_exc()
            await callback.message.edit_text(
                f"❌ <b>Ошибка Spark Money!</b>\n\n{str(e)}\n\n"
                f"💡 Попробуйте метод Flashnet AMM",
                parse_mode="HTML"
            )
        
        await state.clear()
    
    # Cancel - отмена
    elif data == "buy_cancel":
        await callback.answer("❌ Отменено")
        await callback.message.edit_text(
            "❌ <b>Покупка отменена</b>\n\nИспользуйте /buy для новой покупки",
            parse_mode="HTML"
        )
        await state.clear()
    
    # Back - назад
    elif data == "buy_back":
        await callback.answer("◀️ Назад")
        await callback.message.delete()
        await state.clear()

# Обработчики custom ввода

async def handle_custom_amount(message: types.Message, state: FSMContext):
    """Обработка custom суммы"""
    try:
        amount = float(message.text.strip())
        if amount <= 0 or amount > 1:
            await message.answer("❌ Сумма должна быть 0 < amount <= 1 BTC")
            return
        
        await state.update_data(selected_amount=amount)
        await state.set_state(WalletStates.buy_confirming)
        await message.answer(f"✅ Сумма: {amount:.8f} BTC\n\nВозврат к меню покупки...")
    except:
        await message.answer("❌ Неверный формат! Введите число.")


async def handle_custom_tip(message: types.Message, state: FSMContext):
    """Обработка custom tip"""
    try:
        tip = float(message.text.strip())
        if tip < 0 or tip > 0.001:
            await message.answer("❌ Tip должен быть 0 <= tip <= 0.001 BTC")
            return
        
        await state.update_data(buy_tip=tip)
        await state.set_state(WalletStates.buy_confirming)
        await message.answer(f"✅ Buy Tip: {tip:.8f} BTC")
    except:
        await message.answer("❌ Неверный формат!")


async def handle_custom_slippage(message: types.Message, state: FSMContext):
    """Обработка custom slippage"""
    try:
        slippage = float(message.text.strip())
        if slippage < 0.1 or slippage > 50:
            await message.answer("❌ Slippage должен быть 0.1% <= s <= 50%")
            return
        
        await state.update_data(slippage=slippage)
        await state.set_state(WalletStates.buy_confirming)
        await message.answer(f"✅ Slippage: {slippage:.1f}%")
    except:
        await message.answer("❌ Неверный формат!")


async def handle_custom_sell_percent(message: types.Message, state: FSMContext):
    """Обработка custom процента продажи"""
    try:
        percent = float(message.text.strip())
        if percent <= 0 or percent > 100:
            return await message.answer("❌ 0 < % <= 100")
        await state.update_data(selected_percent=percent)
        await state.set_state(WalletStates.sell_confirming)
        await message.answer(f"✅ {percent:.1f}%")
    except:
        await message.answer("❌ Неверный формат!")


async def handle_custom_sell_slippage(message: types.Message, state: FSMContext):
    """Обработка custom slippage для продажи"""
    try:
        slippage = float(message.text.strip())
        if slippage < 0.1 or slippage > 50:
            return await message.answer("❌ 0.1% - 50%")
        await state.update_data(slippage=slippage)
        await state.set_state(WalletStates.sell_confirming)
        await message.answer(f"✅ Slippage: {slippage:.1f}%")
    except:
        await message.answer("❌ Неверный формат!")


def _format_sats(value: Optional[int]) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


async def _build_referral_overview(user_id: int, manager) -> tuple[str, InlineKeyboardMarkup]:
    referral_info = await get_referral_code(user_id)

    if not referral_info or not referral_info.get("code"):
        message = (
            "🌸 <b>Bloom Referral Program</b>\n\n"
            "🔗 <b>Your referral link</b>\n"
            f"<a href=\"{referral_link}\">{referral_link}</a>\n\n"
            "👛 <b>Payout address</b>\n"
            f"<code>{payout_address}</code>\n\n"
            "📊 <b>Referral overview</b>\n"
            f"• Level 1: {level1_count} users / {_format_sats(level1_volume_sats)} SATS\n"
            f"• Level 2: {level2_count} users / 0 SATS\n"
            f"• Level 3: {level3_count} users / 0 SATS\n"
            "• Referred trades: 0\n\n"
            "🎁 <b>Rewards</b>\n"
            f"• Pending: {_format_sats(total_unclaimed_sats)} SATS\n"
            f"• Claimed: {_format_sats(total_claimed_sats)} SATS\n"
            f"• Lifetime earnings: {_format_sats(lifetime_sats)} SATS\n\n"
            "👥 <b>Invited users</b>\n"
            f"{referrals_list}\n\n"
            "🏁 Reach 10 000 SATS to unlock reward withdrawals.\n\n"
            f"🕒 <i>Last updated: {last_updated}</i>"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
                [InlineKeyboardButton(text="🚪 Закрыть", callback_data="close_referral")],
            ]
        )
        return message, keyboard

    referral_code = referral_info["code"]
    level1_users = referral_info.get("referrals") or []
    level1_count = len(level1_users)
    level1_volume_sats = referral_info.get("level1_volume_sats", 0)
    level2_count = referral_info.get("level2_count", 0)
    level3_count = referral_info.get("level3_count", 0)

    total_unclaimed_sats = referral_info.get("rewards_unclaimed_sats", 0)
    total_claimed_sats = referral_info.get("rewards_claimed_sats", 0)
    lifetime_sats = total_unclaimed_sats + total_claimed_sats

    referral_link = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start=ref_{referral_code}"

    active_wallet_info = manager.get_active_wallet()
    if active_wallet_info:
        _, wallet_data = active_wallet_info
        payout_address = getattr(wallet_data, "address", None)
        if not payout_address and isinstance(wallet_data, dict):
            payout_address = wallet_data.get("address")
    else:
        payout_address = "—"

    referrals_list = (
        "\n".join(f"   • <code>{uid}</code>" for uid in level1_users)
        if level1_users
        else "   • Пока нет приглашённых"
    )

    last_updated = datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S UTC")

    message = (
        "<b> Sparkling Referral Program</b>\n\n"
        "🔗 <b>Your referral link</b>\n"
        f"<a href=\"{referral_link}\">{referral_link}</a>\n\n"
        "👛 <b>Payout address</b>\n"
        f"<code>{payout_address}</code>\n\n"
        "📊 <b>Referral overview</b>\n"
        f"• Level 1: {level1_count} users / {_format_sats(level1_volume_sats)} SATS\n"
        f"• Level 2: {level2_count} users / 0 SATS\n"
        f"• Level 3: {level3_count} users / 0 SATS\n"
        "• Referred trades: 0\n\n"
        "🎁 <b>Rewards</b>\n"
        f"• Pending: {_format_sats(total_unclaimed_sats)} SATS\n"
        f"• Claimed: {_format_sats(total_claimed_sats)} SATS\n"
        f"• Lifetime earnings: {_format_sats(lifetime_sats)} SATS\n\n"
        "👥 <b>Invited users</b>\n"
        f"{referrals_list}\n\n"
        "🏁 Reach 10 000 SATS to unlock reward withdrawals.\n\n"
        f"🕒 <i>Last updated: {last_updated}</i>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_referral"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
            [InlineKeyboardButton(text="🚪 Закрыть", callback_data="close_referral")],
        ]
    )

    return message, keyboard


async def main():
    """Запуск бота"""
    storage = MemoryStorage()
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # Подключаем withdrawal router (включает все команды вывода средств)
    dp.include_router(withdrawal_router)
    
    # Регистрируем обработчики команд
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_create_wallet, Command("create_wallet"))
    dp.message.register(cmd_my_wallets, Command("my_wallets"))
    dp.message.register(cmd_positions, Command("positions"))
    dp.message.register(cmd_check_token, Command("check"))
    
    # Buy/Sell команды
    dp.message.register(cmd_buy_new, Command("buy"))
    dp.message.register(handle_token_address_input, WalletStates.waiting_token_address)
    dp.message.register(cmd_sell, Command("sell"))
    dp.message.register(handle_sell_token_input, WalletStates.waiting_sell_token_address)
    
    # Custom handlers
    dp.message.register(handle_custom_amount, WalletStates.waiting_custom_amount)
    dp.message.register(handle_custom_tip, WalletStates.waiting_buy_tip)
    dp.message.register(handle_custom_slippage, WalletStates.waiting_buy_slippage)
    dp.message.register(handle_custom_sell_percent, WalletStates.waiting_custom_sell_percent)
    dp.message.register(handle_custom_sell_slippage, WalletStates.waiting_sell_slippage)
    
    # CALLBACK HANDLERS - ОБЯЗАТЕЛЬНО ПЕРЕД generic handle_callback!
    dp.callback_query.register(handle_sell_callbacks, lambda c: c.data and c.data.startswith("sell_"))
    dp.callback_query.register(handle_buy_callbacks, lambda c: c.data.startswith(("buy_", "tip_", "slippage_")))
    
    # Обработчик остальных сообщений (должен быть последним)
    # ВАЖНО: Фильтр убирает команды И проверяет отсутствие активного состояния FSM
    async def message_filter(message: types.Message, state: FSMContext):
        # Пропускаем команды
        if message.text and message.text.startswith('/'):
            return False
        # Пропускаем если есть активное состояние (FSM обрабатывает)
        current_state = await state.get_state()
        if current_state is not None:
            return False
        return True
    
    dp.message.register(handle_message, message_filter)
    dp.callback_query.register(handle_callback)
    
    # Запускаем polling
    try:
        print("Bot started and running...")
        print(f"Bot token: {TELEGRAM_TOKEN[:10]}...")
        # Получаем информацию о боте для проверки
        bot_info = await bot.get_me()
        print(f"Bot connected: @{bot_info.username} ({bot_info.first_name})")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"[ERROR] Bot failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    # Проверка наличия обязательных переменных
    required_vars = ["TELEGRAM_BOT_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("ERROR: Missing required variables in .env file:", file=sys.stderr)
        for var in missing_vars:
            print(f"   - {var}", file=sys.stderr)
        print("\nCreate .env file based on .env.example and fill all values.", file=sys.stderr)
        exit(1)
    
    print("OK: All credentials loaded from .env file")
    print("Starting bot...")
    
    asyncio.run(main())
