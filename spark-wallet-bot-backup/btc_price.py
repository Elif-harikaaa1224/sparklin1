"""
Получение актуальной цены BTC
"""

import httpx
import asyncio
from typing import Optional

class BTCPriceService:
    """Сервис для получения актуальной цены BTC"""
    
    def __init__(self):
        self._cached_price: Optional[float] = None
        self._cache_timestamp: float = 0
        self._cache_duration: int = 60  # Кеш на 60 секунд
    
    async def get_btc_price_usd(self) -> float:
        """
        Получить актуальную цену BTC в USD
        
        Returns:
            float: Цена BTC в USD
        """
        import time
        
        # Проверяем кеш
        if self._cached_price and (time.time() - self._cache_timestamp) < self._cache_duration:
            return self._cached_price
        
        # Пробуем несколько источников
        try:
            # 1. CoinGecko (бесплатный, без API key)
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
                if resp.status_code == 200:
                    data = resp.json()
                    price = data.get('bitcoin', {}).get('usd')
                    if price:
                        self._cached_price = float(price)
                        self._cache_timestamp = time.time()
                        return self._cached_price
        except:
            pass
        
        try:
            # 2. Binance (быстрый и надежный)
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
                if resp.status_code == 200:
                    data = resp.json()
                    price = data.get('price')
                    if price:
                        self._cached_price = float(price)
                        self._cache_timestamp = time.time()
                        return self._cached_price
        except:
            pass
        
        try:
            # 3. Coinbase
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://api.coinbase.com/v2/prices/BTC-USD/spot")
                if resp.status_code == 200:
                    data = resp.json()
                    price = data.get('data', {}).get('amount')
                    if price:
                        self._cached_price = float(price)
                        self._cache_timestamp = time.time()
                        return self._cached_price
        except:
            pass
        
        # Фоллбэк - используем последнюю закешированную цену или дефолт
        if self._cached_price:
            return self._cached_price
        
        # Дефолтная цена если все источники не работают
        return 100000.0  # $100k
    
    def sats_to_usd(self, sats: int, btc_price: float) -> float:
        """
        Конвертировать satoshi в USD
        
        Args:
            sats: Количество satoshi
            btc_price: Цена BTC в USD
        
        Returns:
            float: Эквивалент в USD
        """
        btc_amount = sats / 100_000_000
        return btc_amount * btc_price
    
    def format_usd(self, usd_amount: float) -> str:
        """
        Форматировать USD сумму для отображения
        
        Args:
            usd_amount: Сумма в USD
        
        Returns:
            str: Отформатированная строка
        """
        if usd_amount < 0.01:
            return f"${usd_amount:.4f}"
        elif usd_amount < 1:
            return f"${usd_amount:.2f}"
        else:
            return f"${usd_amount:,.2f}"


# Глобальный экземпляр
btc_price_service = BTCPriceService()


# Тест
async def test():
    price = await btc_price_service.get_btc_price_usd()
    print(f"BTC Price: ${price:,.2f}")
    
    test_amounts = [1000, 14394, 100000, 1000000]
    for sats in test_amounts:
        usd = btc_price_service.sats_to_usd(sats, price)
        formatted = btc_price_service.format_usd(usd)
        print(f"{sats:,} sats = {formatted}")

if __name__ == "__main__":
    asyncio.run(test())

