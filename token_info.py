"""
Token Information Service
Получение информации о токенах SPARK: цена, ликвидность, market cap
"""

import httpx
from typing import Dict, Any, Optional
from decimal import Decimal


class TokenInfoService:
    """Сервис для получения информации о токенах"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        # API endpoints для получения данных о токенах
        self.sparkscan_web = "https://sparkscan.io"  # Web explorer  
        self.flashnet_web = "https://trade.flashnet.xyz"  # DEX UI
        self.luminex_scraper = None  # Lazy initialization
        
        # UTXO.fun Pool API (ПРИОРИТЕТНЫЙ ИСТОЧНИК)
        self.utxo_pool_api = None  # Lazy initialization
        
        # Попробуем найти GraphQL endpoints
        self.graphql_endpoints = [
            "https://sparkscan.io/graphql",
            "https://api.sparkscan.io/graphql",
            "https://www.sparkscan.io/api/graphql",
        ]
    
    def _get_luminex_scraper(self):
        """Ленивая инициализация Luminex scraper"""
        if not self.luminex_scraper:
            try:
                from luminex_scraper import LuminexScraper
                self.luminex_scraper = LuminexScraper(headless=True)
                print("[INFO] Luminex scraper initialized")
            except ImportError:
                print("[WARN] Luminex scraper not available (selenium not installed)")
                return None
        return self.luminex_scraper
    
    def _get_utxo_pool_api(self):
        """Ленивая инициализация UTXO Pool API"""
        if not self.utxo_pool_api:
            try:
                from utxo_pool_api import UtxoPoolApi
                self.utxo_pool_api = UtxoPoolApi()
                print("[INFO] UTXO Pool API initialized")
            except ImportError:
                print("[WARN] UTXO Pool API not available")
                return None
        return self.utxo_pool_api
        
    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """
        Получить полную информацию о токене
        
        Порядок источников данных:
        1. UTXO.fun Pool API (точные данные пула)
        2. GraphQL endpoints  
        3. Luminex scraper (резервный)
        4. Базовые данные (если все недоступны)
        
        Args:
            token_address: Адрес токена (btkn1...)
        
        Returns:
            dict с информацией: symbol, name, price, liquidity, market_cap, decimals
        """
        try:
            # ПРИОРИТЕТ 1: UTXO.fun Pool API (самые точные данные)
            token_data = await self._fetch_from_utxo_pool(token_address)
            
            if not token_data:
                # ПРИОРИТЕТ 2: Попытка через GraphQL
                token_data = await self._fetch_via_graphql(token_address)
            
            if not token_data:
                # ПРИОРИТЕТ 3: Попытка через Luminex scraper
                token_data = await self._fetch_from_luminex(token_address)
            
            if not token_data:
                # ПРИОРИТЕТ 4: Базовые данные (API пока недоступен)
                print(f"[INFO] API unavailable for {token_address[:20]}..., showing basic info")
                token_data = self._get_basic_token_data(token_address)
                # Добавляем ссылку на Sparkscan для просмотра деталей
                token_data["sparkscan_url"] = f"https://sparkscan.io/token/{token_address}"
            
            return token_data
            
        except Exception as e:
            print(f"[ERROR] Failed to get token info for {token_address}: {e}")
            # Возвращаем базовые данные при ошибке
            data = self._get_basic_token_data(token_address)
            data["sparkscan_url"] = f"https://sparkscan.io/token/{token_address}"
            return data
    
    async def _fetch_from_utxo_pool(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Получить данные токена из UTXO.fun Pool API
        
        Этот источник предоставляет самые точные данные о пуле ликвидности:
        - Точная цена токена в BTC
        - Резервы ликвидности
        - TVL (Total Value Locked)
        - Объём торгов за 24ч
        """
        try:
            api = self._get_utxo_pool_api()
            if not api:
                print("[WARN] UTXO Pool API not available")
                return None
            
            print(f"[INFO] Fetching token from UTXO Pool API: {token_address[:20]}...")
            
            # Получаем данные пула
            pool_data = await api.get_pool_data(token_address)
            if not pool_data:
                print(f"[INFO] No pool data from UTXO API for {token_address[:20]}...")
                return None
            
            print(f"[DEBUG] Pool data received, extracting info...")
            
            # Извлекаем информацию о пуле
            pool_info = api.get_pool_info(pool_data)
            price_btc = pool_info['price_btc']
            
            print(f"[DEBUG] Pool price_btc: {price_btc}")
            
            if price_btc <= 0:
                print(f"[WARN] Invalid price from UTXO Pool API: {price_btc}")
                return None
            
            # UTXO API теперь возвращает ВСЕ метаданные!
            # Не нужно идти в Luminex!
            symbol = pool_info.get('ticker', 'UNKNOWN')
            name = pool_info.get('name', f"Token ({token_address[:10]}...)")
            icon_url = pool_info.get('icon_url', '')
            market_cap_usd = pool_info.get('market_cap_usd', 0)
            holders = pool_info.get('holder_count', 0)
            decimals = pool_info.get('decimals', 8)
            
            print(f"[SUCCESS] ✅ Using UTXO Pool API data - ALL metadata included!")
            print(f"  Token: {symbol} - {name}")
            print(f"  Price: ${pool_info['price_usd']:.8f}")
            print(f"  Market Cap: ${market_cap_usd:,.2f}")
            print(f"  Holders: {holders}")
            
            # Получаем цену BTC в USD для конвертации (уже не нужно, т.к. priceUsd есть в API)
            # try:
            #     from btc_price import btc_price_service
            #     btc_price_usd = await btc_price_service.get_btc_price_usd()
            # except:
            #     btc_price_usd = 100000.0  # Fallback
            
            # price_usd = price_btc * btc_price_usd  # Старый способ
            price_usd = pool_info['price_usd']  # Новый способ - берём из API
            
            # TVL и Volume в USD (уже есть в API!)
            tvl_usd = pool_info['tvl_usd']
            volume_24h_usd = pool_info['volume_24h_usd']
            
            return {
                "address": token_address,
                "symbol": symbol,
                "name": name,
                "price": price_usd,
                "price_usd": price_usd,
                "price_btc": price_btc,
                "liquidity": tvl_usd,
                "liquidity_usd": tvl_usd,
                "market_cap": market_cap_usd,
                "market_cap_usd": market_cap_usd,
                "volume_24h": volume_24h_usd,
                "holders": holders,
                "bonding_progress": 0.0,
                "decimals": decimals,
                "source": f"utxo.fun ({pool_info['host']})",
                "pool_host": pool_info['host'],
                "icon_url": icon_url,
                "btc_reserve_sats": pool_info['btc_reserve'],
                "lp_fee_bps": pool_info['lp_fee_bps'],
                "host_fee_bps": pool_info['host_fee_bps'],
                "sparkscan_url": f"https://sparkscan.io/token/{token_address}",
                "utxo_pool_url": f"https://utxo.fun/api/pools/{token_address}"
            }
            
        except Exception as e:
            print(f"[ERROR] UTXO Pool API failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _fetch_from_luminex(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Получить данные токена с Luminex через scraper"""
        try:
            import asyncio
            import functools
            
            scraper = self._get_luminex_scraper()
            if not scraper:
                return None
            
            print(f"[INFO] Fetching token from Luminex: {token_address[:20]}...")
            
            # Запускаем scraper в thread pool (т.к. Selenium синхронный)
            loop = asyncio.get_event_loop()
            token_data = await loop.run_in_executor(
                None, 
                functools.partial(scraper.get_token_by_address, token_address)
            )
            
            if token_data:
                # Конвертируем в формат токена
                return {
                    "address": token_address,
                    "symbol": token_data['symbol'],
                    "name": token_data['name'],
                    "price": token_data['price_usd'],
                    "price_usd": token_data['price_usd'],
                    "price_btc": token_data['price_usd'] / 90000.0,  # Примерная конвертация
                    "liquidity": token_data.get('volume_24h', 0),
                    "liquidity_usd": token_data.get('volume_24h', 0),
                    "market_cap": token_data['market_cap'],
                    "market_cap_usd": token_data['market_cap'],
                    "volume_24h": token_data['volume_24h'],
                    "holders": token_data['holders'],
                    "bonding_progress": 0.0,
                    "decimals": 8,
                    "source": "luminex.io (live)",
                    "sparkscan_url": f"https://sparkscan.io/token/{token_address}",
                    "luminex_url": f"https://luminex.io/spark/token/{token_address}"
                }
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Luminex scraper failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _fetch_via_graphql(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Попытка получить данные через GraphQL"""
        # GraphQL query для получения metadata токена
        query = """
        query GetToken($address: String!) {
            token(address: $address) {
                address
                symbol
                name
                decimals
                price
                priceUsd
                priceBtc
                liquidity
                liquidityUsd
                marketCap
                marketCapUsd
                volume24h
                holders
                maxSupply
                totalSupply
                isFreezable
            }
        }
        """
        
        for endpoint in self.graphql_endpoints:
            try:
                print(f"[DEBUG] Trying GraphQL: {endpoint}")
                response = await self.client.post(
                    endpoint,
                    json={"query": query, "variables": {"address": token_address}},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "data" in data and "token" in data["data"]:
                        token = data["data"]["token"]
                        print(f"[SUCCESS] GraphQL data: {token}")
                        
                        return {
                            "address": token_address,
                            "symbol": token.get("symbol", "UNKNOWN"),
                            "name": token.get("name", "Unknown Token"),
                            "decimals": token.get("decimals", 8),
                            "price_usd": float(token.get("priceUsd", token.get("price", 0))),
                            "price_btc": float(token.get("priceBtc", 0)),
                            "liquidity_usd": float(token.get("liquidityUsd", token.get("liquidity", 0))),
                            "market_cap_usd": float(token.get("marketCapUsd", token.get("marketCap", 0))),
                            "volume_24h": float(token.get("volume24h", 0)),
                        }
            except Exception as e:
                print(f"[DEBUG] GraphQL failed ({endpoint}): {e}")
                continue
        
        return None
    
    def _get_basic_token_data(self, token_address: str) -> Dict[str, Any]:
        """
        Получить базовые данные токена без цены
        (когда API недоступен, показываем хотя бы адрес)
        """
        # Извлекаем короткий адрес для отображения
        short_addr = f"{token_address[:10]}...{token_address[-8:]}"
        
        return {
            "address": token_address,
            "symbol": short_addr,  # Показываем адрес вместо "Token (...)"
            "name": f"Token at {short_addr}",
            "decimals": 8,
            "price_usd": 0,
            "price_btc": 0,
            "liquidity_usd": 0,
            "market_cap_usd": 0,
            "volume_24h": 0,
            "_api_status": "unavailable",
            "_note": "Visit Sparkscan for details"
        }
    
    def format_price(self, price: float) -> str:
        """Форматирование цены для отображения"""
        if price == 0:
            return "N/A"
        elif price < 0.00001:
            return f"${price:.10f}"
        elif price < 0.01:
            return f"${price:.8f}"
        elif price < 1:
            return f"${price:.6f}"
        else:
            return f"${price:.2f}"
    
    def format_liquidity(self, liquidity: float) -> str:
        """Форматирование ликвидности"""
        if liquidity == 0:
            return "N/A"
        elif liquidity >= 1_000_000:
            return f"${liquidity/1_000_000:.2f}M"
        elif liquidity >= 1_000:
            return f"${liquidity/1_000:.2f}K"
        else:
            return f"${liquidity:.2f}"
    
    def format_market_cap(self, market_cap: float) -> str:
        """Форматирование market cap"""
        if market_cap == 0:
            return "N/A"
        elif market_cap >= 1_000_000:
            return f"${market_cap/1_000_000:.2f}M"
        elif market_cap >= 1_000:
            return f"${market_cap/1_000:.2f}K"
        else:
            return f"${market_cap:.2f}"
    
    def btc_to_sats(self, btc_amount: float) -> int:
        """Конвертация BTC в satoshis"""
        return int(btc_amount * 100_000_000)
    
    def sats_to_btc(self, sats: int) -> float:
        """Конвертация satoshis в BTC"""
        return sats / 100_000_000
    
    def format_btc_amount(self, btc_amount: float) -> str:
        """Форматирование суммы BTC"""
        if btc_amount >= 1:
            return f"{btc_amount:.8f} BTC"
        else:
            sats = self.btc_to_sats(btc_amount)
            if sats < 1000:
                return f"{sats} sats"
            else:
                return f"{btc_amount:.8f} BTC"
    
    async def calculate_tokens_for_btc(self, token_address: str, btc_amount: float) -> Dict[str, Any]:
        """
        Рассчитать количество токенов, которые можно купить за указанную сумму BTC
        
        Использует приоритетный источник - UTXO Pool API для точных расчётов
        
        Args:
            token_address: Адрес токена
            btc_amount: Сумма в BTC
        
        Returns:
            dict с расчетами:
            {
                "token_amount": float,       # Количество токенов
                "token_price_btc": float,    # Цена 1 токена в BTC
                "btc_amount": float,         # Входная сумма BTC
                "source": str,               # Источник данных
            }
        """
        # ПРИОРИТЕТ 1: Используем UTXO Pool API для самых точных данных
        try:
            api = self._get_utxo_pool_api()
            if api:
                calc = await api.calculate_tokens_for_btc(token_address, btc_amount)
                if calc.get("pool_exists") and calc.get("token_price_btc", 0) > 0:
                    print(f"[INFO] Using UTXO Pool API for calculation")
                    return {
                        "token_amount": calc["token_amount"],
                        "token_price_btc": calc["token_price_btc"],
                        "btc_amount": btc_amount,
                        "source": "utxo.fun pool",
                    }
        except Exception as e:
            print(f"[WARN] UTXO Pool API calculation failed: {e}")
        
        # ПРИОРИТЕТ 2: Fallback на get_token_info (GraphQL / Luminex)
        token_info = await self.get_token_info(token_address)
        
        # Получаем цену токена в BTC
        token_price_btc = token_info.get("price_btc", 0)
        
        if token_price_btc == 0:
            # Если цена в BTC не доступна, конвертируем из USD
            price_usd = token_info.get("price_usd", 0)
            # Получаем реальную цену BTC
            try:
                from btc_price import btc_price_service
                btc_price_usd = await btc_price_service.get_btc_price_usd()
            except:
                btc_price_usd = 100000.0  # Fallback
            
            token_price_btc = price_usd / btc_price_usd if btc_price_usd > 0 else 0
        
        # Рассчитываем количество токенов
        if token_price_btc > 0:
            token_amount = btc_amount / token_price_btc
            source = token_info.get("source", "fallback")
        else:
            token_amount = 0
            source = "unavailable"
        
        print(f"[INFO] Fallback calculation: {btc_amount} BTC → {token_amount:,.2f} tokens (source: {source})")
        
        return {
            "token_address": token_address,
            "token_symbol": token_info.get("symbol", "UNKNOWN"),
            "btc_amount": btc_amount,
            "token_price_btc": token_price_btc,
            "token_price_usd": token_info.get("price_usd", 0),
            "token_amount": token_amount,
            "token_amount_formatted": f"{token_amount:,.2f} {token_info.get('symbol', 'tokens')}",
            "source": source,
        }
    
    async def close(self):
        """Закрыть HTTP клиент, scraper и pool API"""
        await self.client.aclose()
        
        # Закрываем Luminex scraper если он был инициализирован
        if self.luminex_scraper:
            try:
                self.luminex_scraper.close()
                print("[INFO] Luminex scraper closed")
            except Exception as e:
                print(f"[WARN] Error closing Luminex scraper: {e}")
        
        # Закрываем UTXO Pool API если был инициализирован
        if self.utxo_pool_api:
            try:
                await self.utxo_pool_api.close()
                print("[INFO] UTXO Pool API closed")
            except Exception as e:
                print(f"[WARN] Error closing UTXO Pool API: {e}")


# Глобальный экземпляр сервиса
token_service = TokenInfoService()
