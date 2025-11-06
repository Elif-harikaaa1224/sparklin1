"""
Клавиатуры для окна SELL
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_sell_keyboard(
    wallets: list,
    selected_wallet: str = "W1",
    selected_percent: int = 100,
    slippage: float = 10.0
) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру для окна продажи
    
    Args:
        wallets: Список имен кошельков
        selected_wallet: Выбранный кошелек (W1, W2, ...)
        selected_percent: Выбранный процент продажи (25, 50, 75, 100)
        slippage: Текущий slippage в %
    """
    # Кнопки процентов продажи
    percent_buttons = []
    for percent in [25, 50, 75, 100]:
        text = f"{'✅' if percent == selected_percent else '⚪️'} Sell {percent}%"
        percent_buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"sell_percent_{percent}"
            )
        )
    
    # Кнопка custom %
    custom_btn = InlineKeyboardButton(
        text="✏️ Sell X%",
        callback_data="sell_custom_percent"
    )
    
    # Кнопка slippage
    slippage_btn = InlineKeyboardButton(
        text=f"⚙️ Slippage: {slippage}%",
        callback_data="sell_slippage"
    )
    
    # Кнопка активного кошелька
    wallet_btn = InlineKeyboardButton(
        text=f"💼 Wallet: {selected_wallet}",
        callback_data="sell_change_wallet"
    )
    
    # Кнопка Refresh
    refresh_btn = InlineKeyboardButton(
        text="🔄 Refresh",
        callback_data="sell_refresh"
    )
    
    # Кнопка Back
    back_btn = InlineKeyboardButton(
        text="◀️ Back",
        callback_data="sell_back"
    )
    
    # Собираем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Строка 1-2: Кнопки процентов (по 2 в ряд)
        [percent_buttons[0], percent_buttons[1]],
        [percent_buttons[2], percent_buttons[3]],
        # Строка 3: Custom % и Slippage
        [custom_btn, slippage_btn],
        # Строка 4: Wallet и Refresh
        [wallet_btn, refresh_btn],
        # Строка 5: Back
        [back_btn]
    ])
    
    return keyboard


def create_wallet_selection_keyboard_sell(wallets: list, current_wallet: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора кошелька для продажи"""
    buttons = []
    for i, wallet_name in enumerate(wallets, 1):
        wallet_id = f"W{i}"
        is_selected = wallet_id == current_wallet
        text = f"{'✅' if is_selected else '⚪️'} {wallet_id} ({wallet_name[:10]}...)"
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"sell_select_wallet_{i}"
            )
        ])
    
    # Кнопка назад
    buttons.append([
        InlineKeyboardButton(text="◀️ Back", callback_data="sell_wallet_back")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
