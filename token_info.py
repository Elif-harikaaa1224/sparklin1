"""
Сервис получения информации о токенах
Интегрируется с UTXO.fun API с кэшированием
"""

import asyncio
from typing import Dict, Optional
from token_cache import token_cache
import time

# Импортируем правильно
try:
    from utxo_pool_api import UTXOPoolAPI
    utxo_api = UTXOPoolAPI()
except ImportError:
    try:
        from utxo_pool_api import utxo_api
    except ImportError:
        print("[ERROR] Cannot import UTXO API")
        utxo_api = None


class TokenInfoService:
    """Сервис информации о токенах"""
    
    def __init__(self):
        self.btc_price = None
        self.btc_price_update_time = 0
        self.btc_price_ttl = 60  # Обновлять цену BTC каждую минуту
    
    async def get_token_info(self, token_address: str) -> Dict:
        # 1️⃣ Проверяем кэш
        cached = token_cache.get(token_address)
        if cached:
            return cached

        # 2️⃣ Проверяем таймер запросов
        wait_time = token_cache.should_wait_before_request(token_address)
        if wait_time > 0:
            print(f"[INFO] Waiting {wait_time:.1f}s before request...")
            await asyncio.sleep(wait_time)

        # 3️⃣ Запрос к API
        token_cache.mark_request(token_address)

        try:
            if not utxo_api:
                raise Exception("UTXO API not available")

            print(f"[INFO] Fetching token info for {token_address[:20]}...")
            token_info = await utxo_api.get_token_pool(token_address)

            # 🔹 Если есть цена в BTC, конвертируем в USD
            if token_info and token_info.get("price_btc"):
                price_btc = float(token_info["price_btc"])

                # Если курс BTC не кэширован или устарел — обновляем
                now = time.time()
                if not self.btc_price or now - self.btc_price_update_time > self.btc_price_ttl:
                    try:
                        from btc_price import btc_price_service
                        self.btc_price = await btc_price_service.get_btc_price_usd()
                        self.btc_price_update_time = now
                        print(f"[INFO] BTC price updated: ${self.btc_price}")
                    except Exception as e:
                        print(f"[WARN] Failed to fetch BTC price: {e}")
                        self.btc_price = 0

                # Конвертация
                token_info["price_usd"] = (
                    round(price_btc * self.btc_price, 8) if self.btc_price else 0.0
                )

            # ✅ Сохраняем в кэш и возвращаем
            if token_info and token_info.get("symbol"):
                token_cache.set(token_address, token_info)
                print(f"[SUCCESS] Got token info: {token_info.get('symbol')}")
                return token_info

        except Exception as e:
            print(f"[WARN] Error fetching token info: {e}")

        # 🔻 Если ничего не получили — дефолт
        print(f"[INFO] Using default token info for {token_address[:20]}...")
        return {
            "address": token_address,
            "symbol": "UNKNOWN",
            "name": "Unknown Token",
            "price_btc": 0.0,
            "price_usd": 0.0,
            "market_cap_usd": 0,
            "liquidity_usd": 0,
            "volume_24h": 0,
            "holders": 0
        }

    async def calculate_tokens_for_btc(self, token_address: str, btc_amount: float) -> Dict:
        """
        Рассчитать количество токенов для суммы BTC
        
        Args:
            token_address: Адрес токена
            btc_amount: Сумма в BTC
            
        Returns:
            {token_amount, price_btc, total_cost}
        """
        token_info = await self.get_token_info(token_address)
        price_btc = float(token_info.get('price_btc', 0))
        
        if price_btc <= 0:
            return {
                'token_amount': 0,
                'price_btc': 0,
                'total_cost': btc_amount,
                'error': 'Price not available'
            }
        
        token_amount = btc_amount / price_btc
        
        return {
            'token_amount': token_amount,
            'price_btc': price_btc,
            'total_cost': btc_amount
        }
    
    async def get_token_price(self, token_address: str) -> float:
        """
        Получить цену токена в BTC
        
        Args:
            token_address: Адрес токена
            
        Returns:
            Цена в BTC
        """
        token_info = await self.get_token_info(token_address)
        return float(token_info.get('price_btc', 0))
    
    def btc_to_sats(self, btc: float) -> int:
        """Конвертировать BTC в satoshi"""
        return int(btc * 100_000_000)
    
    def sats_to_btc(self, sats: int) -> float:
        """Конвертировать satoshi в BTC"""
        return sats / 100_000_000
    
    def format_price(self, price_usd: float) -> str:
        """Отформатировать цену USD"""
        if price_usd >= 1:
            return f"${price_usd:,.2f}"
        elif price_usd >= 0.01:
            return f"${price_usd:.4f}"
        elif price_usd >= 0.0001:
            return f"${price_usd:.6f}"
        else:
            return f"${price_usd:.8f}"
    
    def format_market_cap(self, market_cap: float) -> str:
        """Отформатировать market cap"""
        if market_cap >= 1_000_000:
            return f"${market_cap / 1_000_000:.2f}M"
        elif market_cap >= 1_000:
            return f"${market_cap / 1_000:.2f}K"
        else:
            return f"${market_cap:.2f}"
    
    def format_liquidity(self, liquidity: float) -> str:
        """Отформатировать ликвидность"""
        if liquidity >= 1_000_000:
            return f"${liquidity / 1_000_000:.2f}M"
        elif liquidity >= 1_000:
            return f"${liquidity / 1_000:.2f}K"
        else:
            return f"${liquidity:.2f}"


# Глобальный экземпляр сервиса
token_service = TokenInfoService()