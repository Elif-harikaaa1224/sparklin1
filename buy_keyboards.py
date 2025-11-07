"""
Клавиатуры для торговли токенами
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def create_buy_keyboard(
    wallets: List[str],
    selected_wallet: str = "W1",
    selected_amount: float = 0.001,
    buy_tip: float = 0.0000001,
    slippage: float = 10.0
) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру для покупки токена
    
    Args:
        wallets: Список имен кошельков
        selected_wallet: Выбранный кошелек
        selected_amount: Выбранная сумма в BTC
        buy_tip: Дополнительная комиссия
        slippage: Процент проскальзывания
    """
    buttons = []
    
    # Кнопка Refresh
    buttons.append([
        InlineKeyboardButton(text="🔄 Refresh", callback_data="buy_refresh")
    ])
    
    # Кнопки выбора кошелька
    wallet_buttons = []
    for idx, wallet_name in enumerate(wallets[:5], 1):  # Максимум 5 кошельков
        wallet_label = f"W{idx}"
        # Отмечаем выбранный кошелек
        if wallet_label == selected_wallet or (idx == 1 and selected_wallet == "W1"):
            text = f"✓ {wallet_label}"
        else:
            text = wallet_label
        
        wallet_buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"buy_wallet_W{idx}_{wallet_name}"
            )
        )
    
    # Разбиваем кнопки кошельков по 3 в ряд
    for i in range(0, len(wallet_buttons), 3):
        buttons.append(wallet_buttons[i:i+3])
    
    # Кнопки быстрого выбора суммы (3 в ряд)
    amount_buttons = []
    amounts = [0.001, 0.0001]
    
    for amount in amounts:
        # Отмечаем выбранную сумму
        text = f"{'✓ ' if amount == selected_amount else ''}{amount} BTC"
        amount_buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"buy_amount_{amount}"
            )
        )
    
    # Кнопка custom amount
    amount_buttons.append(
        InlineKeyboardButton(
            text="X BTC",
            callback_data="buy_amount_custom"
        )
    )
    
    buttons.append(amount_buttons)
    
    # Кнопка Buy Tip
    tip_text = f"Buy Tip: {buy_tip:.8f} BTC"
    buttons.append([
        InlineKeyboardButton(
            text=tip_text,
            callback_data="buy_set_tip"
        )
    ])
    
    # Кнопка Slippage
    slippage_text = f"Slippage: {slippage:.1f}%"
    buttons.append([
        InlineKeyboardButton(
            text=slippage_text,
            callback_data="buy_set_slippage"
        )
    ])
    
    # Кнопки методов покупки
    buttons.append([
        InlineKeyboardButton(
            text="⚡ Buy via Flashnet AMM",
            callback_data="buy_flashnet_method"
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text="💫 Buy via Spark Money",
            callback_data="buy_spark_method"
        )
    ])
    
    # Кнопка подтверждения покупки (старая, для обратной совместимости)
    buttons.append([
        InlineKeyboardButton(
            text="✅ Buy Now",
            callback_data="buy_confirm"
        )
    ])
    
    # Кнопка отмены
    buttons.append([
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="buy_cancel"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_tip_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора buy tip"""
    tips = [0.0000001, 0.0000005, 0.000001, 0.000005, 0.00001]
    
    buttons = []
    for tip in tips:
        buttons.append([
            InlineKeyboardButton(
                text=f"{tip:.8f} BTC",
                callback_data=f"tip_{tip}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="Custom Amount",
            callback_data="tip_custom"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Back",
            callback_data="tip_back"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_slippage_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора slippage"""
    slippages = [5.0, 10.0, 15.0, 20.0, 25.0]
    
    buttons = []
    for slippage in slippages:
        buttons.append([
            InlineKeyboardButton(
                text=f"{slippage:.1f}%",
                callback_data=f"slippage_{slippage}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="Custom %",
            callback_data="slippage_custom"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Back",
            callback_data="slippage_back"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения покупки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data="buy_execute"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="buy_cancel")
        ]
    ])
