"""
UTXO.fun Pools API Client
Получение данных о токенах и пулах ликвидности
API: https://utxo.fun/api/pools/{token_address}

Управление через переменные окружения:
- UTXO_POOL_API_ENABLED=true/false - включить/выключить UTXO Pool API
- UTXO_POOL_RATE_LIMIT=10 - минимальный интервал между запросами (сек)
- UTXO_POOL_CACHE_TTL=300 - время жизни кэша (сек)
"""

import httpx
import logging
import asyncio
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UtxoPoolApi:
    """Клиент для работы с UTXO.fun Pools API"""
    
    BASE_URL = "https://utxo.fun/api/pools"
    
    # Конфигурация из переменных окружения
    ENABLED = os.getenv("UTXO_POOL_API_ENABLED", "true").lower() == "true"
    
    # Rate limiting: из env или 0 секунд (без лимита как в браузере)
    MIN_REQUEST_INTERVAL = float(os.getenv("UTXO_POOL_RATE_LIMIT", "0"))
    
    # Retry settings для 429 ошибок
    MAX_RETRIES = 1  # Уменьшаем до 1 retry (всего 2 попытки)
    RETRY_DELAY = 5.0  # Ждём 5 секунд перед повторной попыткой
    
    def __init__(self):
        # HTTP клиент с заголовками браузера (чтобы обойти rate limit)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept-Encoding": "gzip, deflate",  # Убрали br (brotli), оставили только gzip
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://utxo.fun/",
            "Origin": "https://utxo.fun"
        }
        
        self.client = httpx.AsyncClient(
            timeout=20.0,
            headers=headers,
            follow_redirects=True
        )
        self.last_request_time = None
        self._cache = {}  # Кэш: {token_address: (data, timestamp)}
        
        # Время жизни кэша из env или 60 секунд по умолчанию
        self.cache_ttl = float(os.getenv("UTXO_POOL_CACHE_TTL", "60"))
        
        if not self.ENABLED:
            logger.warning("⚠️ UTXO Pool API disabled via UTXO_POOL_API_ENABLED=false")
        else:
            logger.info(f"✅ UTXO Pool API enabled (rate_limit={self.MIN_REQUEST_INTERVAL}s, cache_ttl={self.cache_ttl}s)")
    
    async def _rate_limit_wait(self):
        """Ожидание для соблюдения rate limit"""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < self.MIN_REQUEST_INTERVAL:
                wait_time = self.MIN_REQUEST_INTERVAL - elapsed
                logger.info(f"⏱️ Rate limit: waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
        
        self.last_request_time = datetime.now()
    
    def _get_from_cache(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Получить данные из кэша если актуальны"""
        if token_address in self._cache:
            data, timestamp = self._cache[token_address]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self.cache_ttl:
                logger.info(f"✅ Cache hit for {token_address[:20]}... (age: {age:.1f}s)")
                return data
        return None
    
    def _save_to_cache(self, token_address: str, data: Dict[str, Any]):
        """Сохранить данные в кэш"""
        self._cache[token_address] = (data, datetime.now())
        logger.info(f"💾 Cached data for {token_address[:20]}...")
    
    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()
    
    async def get_pool_data(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Получить данные пула для токена
        
        Args:
            token_address: Адрес токена (btkn1...)
            
        Returns:
            Dict с данными пула или None при ошибке
            
        Example response:
        {
            "lpPubkey": "021cda97a28df127f41e480ebede196f6f7d46dd6754feab7c228d8273dce6d39e",
            "hostName": "luminex",
            "hostFeeBps": 100,
            "lpFeeBps": 30,
            "assetAAddress": "d38aca42ee5b3c733a187b56f7c0c541c674b5619dd6648829108f0f97625d57",
            "assetBAddress": "020202020202020202020202020202020202020202020202020202020202020202",
            "assetAReserve": "6367758189623747",
            "assetBReserve": "48944257",
            "currentPriceAInB": "7.686261904618153579E-9",
            "tvlAssetB": "97888514",
            "volume24hAssetB": "0",
            ...
        }
        """
        # Проверяем включен ли API
        if not self.ENABLED:
            logger.debug("UTXO Pool API disabled, skipping...")
            return None
        
        # Проверяем кэш
        cached_data = self._get_from_cache(token_address)
        if cached_data:
            return cached_data
        
        # Пытаемся получить данные с retry при 429
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                # Rate limiting
                await self._rate_limit_wait()
                
                url = f"{self.BASE_URL}/{token_address}"
                logger.info(f"📡 Fetching pool data from UTXO.fun: {token_address[:20]}... (attempt {attempt + 1}/{self.MAX_RETRIES + 1})")
                
                response = await self.client.get(url)
                response.raise_for_status()
                
                # Декодируем JSON (httpx автоматически обрабатывает gzip)
                try:
                    data = response.json()
                except Exception as json_error:
                    logger.error(f"❌ JSON decode error: {json_error}")
                    logger.error(f"   Response content type: {response.headers.get('content-type')}")
                    logger.error(f"   Response encoding: {response.headers.get('content-encoding')}")
                    logger.error(f"   Response first 100 bytes: {response.content[:100]}")
                    return None
                
                logger.info(f"✅ Pool data received for {token_address[:20]}...")
                logger.debug(f"   Price: {data.get('currentPriceAInB', 'N/A')}")
                logger.debug(f"   BTC Reserve: {data.get('assetBReserve', 'N/A')} sats")
                logger.debug(f"   Host: {data.get('hostName', 'N/A')}")
                
                # Сохраняем в кэш
                self._save_to_cache(token_address, data)
                
                return data
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"⚠️ Pool not found for token: {token_address[:20]}...")
                    return None  # Не retry для 404
                    
                elif e.response.status_code == 429:
                    if attempt < self.MAX_RETRIES:
                        logger.warning(f"⚠️ Rate limit (429). Waiting {self.RETRY_DELAY}s before retry {attempt + 2}/{self.MAX_RETRIES + 1}...")
                        logger.debug(f"   Response headers: {dict(e.response.headers)}")
                        await asyncio.sleep(self.RETRY_DELAY)
                        continue  # Повторяем попытку
                    else:
                        logger.error(f"❌ Rate limit (429) after {self.MAX_RETRIES} retries.")
                        logger.error(f"   Response: {e.response.text[:200]}")
                        logger.error(f"   Headers: {dict(e.response.headers)}")
                        return None
                else:
                    logger.error(f"❌ HTTP {e.response.status_code} error getting pool data")
                    logger.error(f"   Response: {e.response.text[:200]}")
                    return None
                
            except Exception as e:
                logger.error(f"❌ Error getting pool data: {e}")
                return None
        
        return None
    
    def calculate_token_price_btc(self, pool_data: Dict[str, Any]) -> float:
        """
        Рассчитать цену токена в BTC из данных пула
        
        Args:
            pool_data: Данные пула из get_pool_data()
            
        Returns:
            Цена токена в BTC (1 токен = X BTC)
            
        Формула:
            currentPriceAInB = цена токена (asset A) в BTC (asset B)
            Например: 7.686261904618153579E-9 = 0.000000007686 BTC за 1 токен
        """
        try:
            # Получаем цену из поля currentPriceAInB
            price_str = pool_data.get("currentPriceAInB", "0")
            price_btc = float(price_str)
            
            logger.info(f"💰 Token price from pool: {price_btc:.12f} BTC")
            
            return price_btc
            
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Error parsing price: {e}")
            return 0.0
    
    def get_pool_info(self, pool_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлечь полезную информацию из данных пула
        
        UTXO API возвращает ПОЛНЫЕ данные включая метаданные!
        
        Returns:
            {
                "price_btc": float,          # Цена токена в BTC
                "price_usd": float,          # Цена токена в USD
                "token_reserve": str,        # Резерв токенов (сатоши токена)
                "btc_reserve": int,          # Резерв BTC (сатоши)
                "tvl_btc": int,              # Total Value Locked в BTC (сатоши)
                "tvl_usd": float,            # TVL в USD
                "volume_24h_btc": int,       # Объём торгов за 24ч в BTC (сатоши)
                "volume_24h_usd": float,     # Объём в USD
                "market_cap_usd": float,     # Market Cap в USD
                "name": str,                 # Название токена
                "ticker": str,               # Тикер (символ)
                "icon_url": str,             # URL иконки
                "holder_count": int,         # Количество holders
                "decimals": int,             # Decimals
                "host": str,                 # Хост пула (luminex, etc)
                "lp_fee_bps": int,           # LP комиссия в базисных пунктах
                "host_fee_bps": int,         # Комиссия хоста в базисных пунктах
            }
        """
        try:
            price_btc = self.calculate_token_price_btc(pool_data)
            
            info = {
                "price_btc": price_btc,
                "price_usd": float(pool_data.get("priceUsd", 0)),
                "token_reserve": pool_data.get("assetAReserve", "0"),
                "btc_reserve": int(pool_data.get("assetBReserve", 0)),
                "tvl_btc": int(pool_data.get("tvlAssetB", 0)),
                "tvl_usd": float(pool_data.get("tvlUsd", 0)),
                "volume_24h_btc": int(pool_data.get("volume24hAssetB", 0)),
                "volume_24h_usd": float(pool_data.get("volume24hUsd", 0)),
                "market_cap_usd": float(pool_data.get("marketCapUsd", 0)),
                
                # Метаданные токена (доступны в API!)
                "name": pool_data.get("name", "Unknown"),
                "ticker": pool_data.get("ticker", "UNKNOWN"),
                "icon_url": pool_data.get("iconUrl", ""),
                "holder_count": int(pool_data.get("holderCount", 0)),
                "decimals": int(pool_data.get("decimals", 8)),
                
                # Информация о пуле
                "host": pool_data.get("hostName", "unknown"),
                "lp_fee_bps": int(pool_data.get("lpFeeBps", 30)),
                "host_fee_bps": int(pool_data.get("hostFeeBps", 100)),
            }
            
            logger.info(f"📊 Pool info extracted:")
            logger.info(f"  - Token: {info['ticker']} ({info['name']})")
            logger.info(f"  - Price: ${info['price_usd']:.8f} ({info['price_btc']:.12f} BTC)")
            logger.info(f"  - Market Cap: ${info['market_cap_usd']:,.2f}")
            logger.info(f"  - TVL: ${info['tvl_usd']:,.2f}")
            logger.info(f"  - Holders: {info['holder_count']}")
            logger.info(f"  - Host: {info['host']}")
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Error extracting pool info: {e}")
            return {
                "price_btc": 0.0,
                "price_usd": 0.0,
                "token_reserve": "0",
                "btc_reserve": 0,
                "tvl_btc": 0,
                "tvl_usd": 0.0,
                "volume_24h_btc": 0,
                "volume_24h_usd": 0.0,
                "market_cap_usd": 0.0,
                "name": "Unknown",
                "ticker": "UNKNOWN",
                "icon_url": "",
                "holder_count": 0,
                "decimals": 8,
                "host": "unknown",
                "lp_fee_bps": 30,
                "host_fee_bps": 100,
            }
    
    async def calculate_tokens_for_btc(
        self, 
        token_address: str, 
        btc_amount: float
    ) -> Dict[str, Any]:
        """
        Рассчитать сколько токенов получится за указанное количество BTC
        
        Args:
            token_address: Адрес токена (btkn1...)
            btc_amount: Количество BTC (например, 0.001)
            
        Returns:
            {
                "token_amount": float,       # Количество токенов
                "token_price_btc": float,    # Цена 1 токена в BTC
                "btc_amount": float,         # Входное количество BTC
                "pool_exists": bool,         # Существует ли пул
                "error": str or None,        # Ошибка если есть
            }
        """
        try:
            pool_data = await self.get_pool_data(token_address)
            
            if not pool_data:
                logger.warning(f"⚠️ No pool data for {token_address[:20]}...")
                return {
                    "token_amount": 0,
                    "token_price_btc": 0,
                    "btc_amount": btc_amount,
                    "pool_exists": False,
                    "error": "Pool not found",
                }
            
            pool_info = self.get_pool_info(pool_data)
            price_btc = pool_info["price_btc"]
            
            if price_btc <= 0:
                logger.warning(f"⚠️ Invalid price for {token_address[:20]}...")
                return {
                    "token_amount": 0,
                    "token_price_btc": 0,
                    "btc_amount": btc_amount,
                    "pool_exists": True,
                    "error": "Invalid price",
                }
            
            # Рассчитываем количество токенов
            # btc_amount BTC / price_btc (BTC за 1 токен) = количество токенов
            token_amount = btc_amount / price_btc
            
            logger.info(f"💎 Calculation: {btc_amount} BTC → {token_amount:,.2f} tokens")
            logger.info(f"   Price: {price_btc:.12f} BTC per token")
            
            return {
                "token_amount": token_amount,
                "token_price_btc": price_btc,
                "btc_amount": btc_amount,
                "pool_exists": True,
                "error": None,
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating tokens: {e}")
            return {
                "token_amount": 0,
                "token_price_btc": 0,
                "btc_amount": btc_amount,
                "pool_exists": False,
                "error": str(e),
            }


# Глобальный экземпляр для использования в боте
utxo_pool_api = UtxoPoolApi()


# Пример использования
async def test_utxo_pool_api():
    """Тестовая функция для проверки API"""
    
    # SOON токен
    token_address = "btkn16w9v5shwtv78xwsc0dt00sx9g8r8fdtpnhtxfzpfzz8sl9mzt4ts7zh0dl"
    
    print("\n" + "="*80)
    print("🧪 ТЕСТИРОВАНИЕ UTXO.FUN POOLS API")
    print("="*80)
    
    # 1. Получить данные пула
    print(f"\n📡 1. Получение данных пула для SOON токена")
    print(f"   Token: {token_address}")
    
    pool_data = await utxo_pool_api.get_pool_data(token_address)
    
    if pool_data:
        print(f"   ✅ Данные получены!")
        
        # 2. Извлечь информацию
        print(f"\n📊 2. Информация о пуле:")
        pool_info = utxo_pool_api.get_pool_info(pool_data)
        
        print(f"   💰 Цена токена: {pool_info['price_btc']:.12f} BTC")
        print(f"   💎 Резерв токенов: {pool_info['token_reserve']}")
        print(f"   ₿  Резерв BTC: {pool_info['btc_reserve']:,} sats")
        print(f"   🔒 TVL: {pool_info['tvl_btc']:,} sats")
        print(f"   📈 Объём 24ч: {pool_info['volume_24h_btc']:,} sats")
        print(f"   🏢 Хост: {pool_info['host']}")
        print(f"   💸 LP комиссия: {pool_info['lp_fee_bps']} bps")
        print(f"   💸 Host комиссия: {pool_info['host_fee_bps']} bps")
        
        # 3. Рассчитать количество токенов за 0.001 BTC
        print(f"\n💎 3. Расчёт покупки:")
        btc_amount = 0.001
        
        calc = await utxo_pool_api.calculate_tokens_for_btc(token_address, btc_amount)
        
        print(f"   Покупка: {btc_amount} BTC")
        print(f"   Получите: ~{calc['token_amount']:,.2f} токенов")
        print(f"   Цена: {calc['token_price_btc']:.12f} BTC за токен")
        print(f"   Пул существует: {calc['pool_exists']}")
        if calc['error']:
            print(f"   ⚠️ Ошибка: {calc['error']}")
        
    else:
        print(f"   ❌ Не удалось получить данные пула")
    
    print("\n" + "="*80)
    
    await utxo_pool_api.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_utxo_pool_api())
