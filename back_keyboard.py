"""
Универсальные клавиатуры с кнопкой Back
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def create_back_keyboard() -> ReplyKeyboardMarkup:
    """Создает простую клавиатуру с кнопкой Back"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="◀️ Back")]
        ],
        resize_keyboard=True
    )
    return keyboard


def create_back_inline_keyboard() -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру с кнопкой Back"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_menu")]
        ]
    )
    return keyboard


def add_back_button(keyboard: InlineKeyboardMarkup, callback_data: str = "back_to_menu") -> InlineKeyboardMarkup:
    """Добавляет кнопку Back к существующей inline-клавиатуре"""
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Back", callback_data=callback_data)
    ])
    return keyboard
