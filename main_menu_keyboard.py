"""
Главное меню бота с кнопками
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def create_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру главного меню (внизу экрана)"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👛 Wallets"),
                KeyboardButton(text="➕ Create Wallet")
            ],
            [
                KeyboardButton(text="📊 Positions"),
            ],
            [
                KeyboardButton(text="🛒 Buy"),
                KeyboardButton(text="💸 Sell")
            ],
            [
                KeyboardButton(text="💳 Deposit"),
                KeyboardButton(text="💸 Withdraw")
            ],
            [
                KeyboardButton(text="❓ Help")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an action..."
    )
    
    return keyboard


def create_main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру главного меню (в сообщении)"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👛 Wallets", callback_data="menu_wallets"),
                InlineKeyboardButton(text="➕ Create Wallet", callback_data="menu_create_wallet")
            ],
            [
                InlineKeyboardButton(text="📊 Positions", callback_data="menu_positions")
            ],
            [
                InlineKeyboardButton(text="🛒 Buy", callback_data="menu_buy"),
                InlineKeyboardButton(text="💸 Sell", callback_data="menu_sell")
            ],
            [
                InlineKeyboardButton(text="💳 Deposit", callback_data="menu_deposit"),
                InlineKeyboardButton(text="💸 Withdraw", callback_data="menu_withdraw")
            ],
            [
                InlineKeyboardButton(text="❓ Help", callback_data="menu_help")
            ]
        ]
    )
    
    return keyboard
