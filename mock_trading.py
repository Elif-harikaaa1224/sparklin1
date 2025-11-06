"""
MOCK режим для тестирования Buy/Sell без реальной интеграции
Генерирует фальшивые TxID для демонстрации
"""

import random
import string
from datetime import datetime
from typing import Dict


def generate_mock_txid() -> str:
    """Генерировать фальшивый TxID"""
    # Формат: tx_YYYYMMDD_XXXXXX
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"tx_{date_str}_{random_str}"


def mock_buy_token(
    token_address: str,
    amount_sats: int,
    wallet_name: str,
    slippage: float = 10.0,
    tip_sats: int = 100
) -> Dict:
    """
    Имитировать покупку токена (MOCK)
    
    Args:
        token_address: Адрес токена (btkn1...)
        amount_sats: Сумма в satoshi
        wallet_name: Имя кошелька
        slippage: Slippage процент
        tip_sats: Комиссия в satoshi
        
    Returns:
        {
            'status': 'success' или 'error',
            'txid': str,
            'token_amount': int,
            'message': str
        }
    """
    
    print(f"[MOCK] 🛒 BUY TOKEN (MOCK MODE)")
    print(f"  Token: {token_address[:30]}...")
    print(f"  Amount: {amount_sats} sats")
    print(f"  Wallet: {wallet_name}")
    print(f"  Slippage: {slippage}%")
    print(f"  Tip: {tip_sats} sats")
    
    try:
        # Имитируем задержку сети
        import asyncio
        import time
        time.sleep(0.5)
        
        # Рассчитываем количество токенов
        # Случайная цена токена между 0.00001 - 0.0001 BTC
        price_btc = random.uniform(0.00001, 0.0001)
        btc_amount = amount_sats / 100_000_000  # Конвертируем в BTC
        token_amount = int(btc_amount / price_btc)
        
        txid = generate_mock_txid()
        
        return {
            'status': 'success',
            'txid': txid,
            'token_amount': token_amount,
            'price_btc': price_btc,
            'message': f'✅ MOCK: Купили {token_amount:,} токенов'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'txid': 'N/A',
            'token_amount': 0,
            'message': f'❌ MOCK Error: {str(e)}'
        }


def mock_sell_token(
    token_address: str,
    token_amount: int,
    wallet_name: str,
    slippage: float = 10.0
) -> Dict:
    """
    Имитировать продажу токена (MOCK)
    
    Args:
        token_address: Адрес токена (btkn1...)
        token_amount: Количество токенов
        wallet_name: Имя кошелька
        slippage: Slippage процент
        
    Returns:
        {
            'status': 'success' или 'error',
            'txid': str,
            'btc_received': float,
            'message': str
        }
    """
    
    print(f"[MOCK] 💸 SELL TOKEN (MOCK MODE)")
    print(f"  Token: {token_address[:30]}...")
    print(f"  Amount: {token_amount:,} tokens")
    print(f"  Wallet: {wallet_name}")
    print(f"  Slippage: {slippage}%")
    
    try:
        # Имитируем задержку сети
        import time
        time.sleep(0.5)
        
        # Рассчитываем полученный BTC
        # Случайная цена токена между 0.00001 - 0.0001 BTC
        price_btc = random.uniform(0.00001, 0.0001)
        btc_amount = (token_amount * price_btc) * (1 - slippage / 100)  # Учитываем slippage
        sats_received = int(btc_amount * 100_000_000)
        
        # Применяем slippage
        slippage_sats = int(sats_received * (slippage / 100))
        sats_final = sats_received - slippage_sats
        
        txid = generate_mock_txid()
        
        return {
            'status': 'success',
            'txid': txid,
            'btc_received': btc_amount,
            'sats_received': sats_final,
            'price_btc': price_btc,
            'slippage_sats': slippage_sats,
            'message': f'✅ MOCK: Продали {token_amount:,} токенов за {sats_final:,} sats'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'txid': 'N/A',
            'btc_received': 0,
            'message': f'❌ MOCK Error: {str(e)}'
        }


def mock_get_token_info(token_address: str) -> Dict:
    """
    Получить информацию о токене (MOCK)
    
    Args:
        token_address: Адрес токена
        
    Returns:
        {
            'symbol': str,
            'name': str,
            'price_btc': float,
            'price_usd': float,
            'market_cap_usd': int,
            'liquidity_usd': int,
            'volume_24h': int,
            'holders': int
        }
    """
    
    # Генерируем случайные данные
    symbols = ['MOON', 'DOGE2', 'SPARK', 'MEME', 'PUMP', 'TEST', 'BETA', 'ALPHA']
    symbol = random.choice(symbols)
    
    price_btc = random.uniform(0.00001, 0.0001)
    price_usd = price_btc * random.uniform(40000, 100000)
    market_cap = random.randint(1_000_000, 100_000_000)
    liquidity = random.randint(100_000, 10_000_000)
    volume = random.randint(10_000, 1_000_000)
    holders = random.randint(100, 10_000)
    
    return {
        'address': token_address,
        'symbol': symbol,
        'name': f'{symbol} Token (MOCK)',
        'price_btc': price_btc,
        'price_usd': price_usd,
        'market_cap_usd': market_cap,
        'liquidity_usd': liquidity,
        'volume_24h': volume,
        'holders': holders
    }


# Флаг для включения/отключения MOCK режима
MOCK_MODE_ENABLED = True

print("[MOCK] Mock trading mode initialized")
print("[MOCK] All buy/sell operations will return fake data")