"""
Flashnet AMM Swap Module
Реализация покупки/продажи токенов через Flashnet AMM API
https://api.amm.flashnet.xyz/v1/
"""
import os
import time
import asyncio
import httpx
from typing import Dict, Any, Optional, List
from decimal import Decimal
from flashnet_auth import get_flashnet_auth

# Попытка использовать curl-cffi версию для обхода Cloudflare
try:
    from flashnet_auth_curl import get_flashnet_auth_curl, CURL_CFFI_AVAILABLE
    USE_CURL_CFFI = CURL_CFFI_AVAILABLE
    print(f"[INFO] curl-cffi available: {USE_CURL_CFFI}")
except ImportError:
    USE_CURL_CFFI = False
    print(f"[WARN] curl-cffi not available, using standard httpx")

# Попытка использовать Playwright (лучший обход Cloudflare)
try:
    from flashnet_auth_playwright import get_flashnet_auth_playwright
    USE_PLAYWRIGHT = True
    print(f"[INFO] Playwright available: {USE_PLAYWRIGHT}")
except ImportError:
    USE_PLAYWRIGHT = False
    print(f"[WARN] Playwright not available")


class FlashnetSwapClient:
    """Клиент для выполнения свопов через Flashnet AMM API"""
    
    # Flashnet AMM API endpoint
    API_BASE_URL = "https://api.amm.flashnet.xyz/v1"
    
    # Bitcoin pubkey (константа для Flashnet)
    BTC_PUBKEY = "020202020202020202020202020202020202020202020202020202020202020202"
    
    def __init__(self, mnemonic: str = None):
        """
        Инициализация клиента
        
        Args:
            mnemonic: BIP39 mnemonic для JWT аутентификации (опционально)
        """
        # Добавляем headers для обхода Cloudflare protection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://flashnet.xyz",
            "Referer": "https://flashnet.xyz/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
            follow_redirects=True
        )
        self.pools_cache = {}  # Кэш пулов
        self.mnemonic = mnemonic
        self.jwt_token = None  # JWT токен для авторизации
        
    async def ensure_authenticated(self):
        """
        Обеспечить наличие валидного JWT токена
        
        Raises:
            Exception если не удалось получить токен
        """
        if self.jwt_token:
            return  # Токен уже есть
        
        if not self.mnemonic:
            raise Exception("Mnemonic required for authentication")
        
        try:
            print(f"[AUTH] Authenticating with Flashnet API...")
            
            # Приоритет: Playwright > curl-cffi > httpx
            if USE_PLAYWRIGHT:
                print(f"[AUTH] Using Playwright (real browser) for Cloudflare bypass...")
                auth_client = await get_flashnet_auth_playwright(browser_pool_size=3)
            elif USE_CURL_CFFI:
                print(f"[AUTH] Using curl-cffi for Cloudflare bypass...")
                auth_client = get_flashnet_auth_curl()
            else:
                print(f"[AUTH] Using standard httpx (may be blocked by Cloudflare)...")
                auth_client = get_flashnet_auth()
            
            self.jwt_token = await auth_client.get_jwt_token(self.mnemonic)
            
            # Добавляем токен в headers
            self.client.headers["Authorization"] = f"Bearer {self.jwt_token}"
            
            print(f"[AUTH] ✅ Authenticated successfully!")
            
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            raise Exception(f"Failed to authenticate with Flashnet API: {e}")
        
    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()
    
    async def get_pool(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о пуле
        
        Args:
            pool_id: LP public key пула
        
        Returns:
            dict с информацией о пуле
        """
        try:
            # Обеспечиваем аутентификацию
            await self.ensure_authenticated()
            
            url = f"{self.API_BASE_URL}/pools/{pool_id}"
            print(f"[DEBUG] GET {url}")
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            pool_data = response.json()
            print(f"[DEBUG] Pool data: {pool_data.get('lpPublicKey', 'N/A')[:20]}...")
            
            return pool_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"[WARN] Pool not found: {pool_id[:20]}...")
                return None
            print(f"[ERROR] HTTP error getting pool: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to get pool: {e}")
            return None
    
    async def find_pool_for_token(self, token_address: str) -> Optional[str]:
        """
        Найти пул для торговли BTC <-> Token
        
        Пока используется hardcoded pool ID.
        TODO: Реализовать поиск через API get_pools
        
        Args:
            token_address: Адрес токена (btkn1... или hex)
        
        Returns:
            pool_id если найден, иначе None
        """
        try:
            print(f"[INFO] Searching pool for token {token_address[:20]}...")
            
            # TODO: Получить список всех пулов и найти подходящий
            # url = f"{self.API_BASE_URL}/pools"
            # response = await self.client.get(url)
            # pools = response.json()
            # 
            # for pool in pools:
            #     if ((pool['assetAAddress'] == self.BTC_PUBKEY and pool['assetBAddress'] == token_address) or
            #         (pool['assetBAddress'] == self.BTC_PUBKEY and pool['assetAAddress'] == token_address)):
            #         return pool['lpPublicKey']
            
            # Пока возвращаем mock pool ID
            # В production здесь должен быть реальный поиск пула
            mock_pool_id = f"pool_{token_address[:10]}"
            print(f"[WARN] Using mock pool ID: {mock_pool_id}")
            print(f"[TODO] Implement real pool search via /v1/pools API")
            
            return mock_pool_id
            
        except Exception as e:
            print(f"[ERROR] Failed to find pool: {e}")
            return None
    
    async def simulate_swap(
        self,
        pool_id: str,
        asset_in_address: str,
        asset_out_address: str,
        amount_in: int,  # в satoshis
    ) -> Optional[Dict[str, Any]]:
        """
        Симуляция свопа через Flashnet API
        POST /v1/swap/simulate
        
        Args:
            pool_id: ID пула (LP public key)
            asset_in_address: Адрес входящего актива
            asset_out_address: Адрес исходящего актива
            amount_in: Сумма входящего актива в satoshis
        
        Returns:
            dict с результатами симуляции или None при ошибке
        """
        try:
            # Обеспечиваем аутентификацию
            await self.ensure_authenticated()
            
            url = f"{self.API_BASE_URL}/swap/simulate"
            
            # Тело запроса согласно API документации
            payload = {
                "poolId": pool_id,
                "assetInAddress": asset_in_address,
                "assetOutAddress": asset_out_address,
                "amountIn": amount_in,
                "integratorBps": 0  # Опционально: комиссия интегратора
            }
            
            print(f"[INFO] Simulating swap...")
            print(f"  POST {url}")
            print(f"  Pool: {pool_id[:20]}...")
            print(f"  Amount In: {amount_in} sats")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            simulation = response.json()
            
            # Парсим ответ согласно API
            result = {
                "amount_out": int(simulation["amountOut"]),
                "execution_price": simulation.get("executionPrice", "0"),
                "price_impact_pct": float(simulation.get("priceImpactPct", "0%").replace("%", "")),
                "fee_paid_asset_in": simulation.get("feePaidAssetIn", 0),
                "warning_message": simulation.get("warningMessage"),
            }
            
            print(f"  ✅ Simulation successful")
            print(f"  Expected Output: {result['amount_out']}")
            print(f"  Price Impact: {result['price_impact_pct']:.2f}%")
            
            if result["warning_message"]:
                print(f"  ⚠️  Warning: {result['warning_message']}")
            
            return result
            
        except httpx.HTTPStatusError as e:
            # Cloudflare блокирует - ОСТАНАВЛИВАЕМ выполнение
            if e.response.status_code == 403:
                print(f"[ERROR] Cloudflare blocking API (403 Forbidden)")
                print(f"[ERROR] Cannot execute real swap without API access")
                print(f"[ERROR] Need: API key, JWT token, or Cloudflare bypass")
                raise Exception("Flashnet API недоступен (Cloudflare protection). Требуется API ключ или обход Cloudflare.")
            
            print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:500]}")
            return None
        except Exception as e:
            print(f"[ERROR] Swap simulation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def execute_swap(
        self,
        pool_id: str,
        asset_in_address: str,
        asset_out_address: str,
        amount_in: int,  # в satoshis
        min_amount_out: int,  # минимальная сумма с учетом slippage
        max_slippage_bps: int = 100,  # 1% по умолчанию
        priority_fee_sats: int = 10000,  # комиссия приоритета
        user_public_key: str = None,  # публичный ключ пользователя
        mnemonic: str = None,  # mnemonic для подписи
    ) -> Optional[Dict[str, Any]]:
        """
        Выполнить своп через Flashnet API
        POST /v1/swap
        
        Args:
            pool_id: ID пула (LP public key)
            asset_in_address: Адрес входящего актива
            asset_out_address: Адрес исходящего актива
            amount_in: Сумма входящего актива в satoshis
            min_amount_out: Минимальная сумма на выходе (защита от slippage)
            max_slippage_bps: Максимальный slippage в базисных пунктах (100 = 1%)
            priority_fee_sats: Комиссия приоритета в satoshis
            user_public_key: Публичный ключ пользователя
            mnemonic: Mnemonic phrase для подписи транзакции
        
        Returns:
            dict с результатами свопа или None при ошибке
        """
        try:
            # Обеспечиваем аутентификацию
            await self.ensure_authenticated()
            
            # Шаг 1: Создаем Spark transfer (депозит в пул)
            from spark_withdrawal import SparkWithdrawalManager
            withdrawal_manager = SparkWithdrawalManager()
            
            print(f"[INFO] Creating Spark transfer to pool...")
            print(f"  Amount: {amount_in} sats")
            print(f"  Pool: {pool_id[:20]}...")
            
            transfer_result = withdrawal_manager.send_spark_transfer(
                mnemonic=mnemonic,
                receiver_address=pool_id,  # Отправляем в адрес пула
                amount_sats=amount_in
            )
            
            if not transfer_result.get("success"):
                raise Exception(f"Failed to create Spark transfer: {transfer_result.get('error')}")
            
            # Извлекаем transfer ID из результата
            spark_transfer_id = transfer_result.get("transfer_id") or transfer_result.get("txid")
            if not spark_transfer_id:
                raise Exception("Transfer ID not found in response")
            
            print(f"  ✅ Transfer created: {spark_transfer_id}")
            
            # Шаг 2: Генерируем уникальный nonce
            import time
            nonce = int(time.time() * 1000)  # Timestamp в миллисекундах
            
            # Шаг 3: Формируем payload для подписи
            payload = {
                "poolId": pool_id,
                "assetInAddress": asset_in_address,
                "assetOutAddress": asset_out_address,
                "amountIn": amount_in,
                "slippageBps": max_slippage_bps,
                "userPublicKey": user_public_key,
                "assetInSparkTransferId": spark_transfer_id,
                "nonce": nonce,
                "integratorBps": 0
            }
            
            # Шаг 4: Подписываем payload
            print(f"[INFO] Signing payload...")
            signature = self._sign_payload(payload, mnemonic)
            payload["signature"] = signature
            
            # Шаг 5: Выполняем swap (JWT токен уже в headers)
            url = f"{self.API_BASE_URL}/swap"
            
            print(f"[INFO] Executing swap...")
            print(f"  POST {url}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            swap_result = response.json()
            
            # Проверяем результат
            if swap_result.get("accepted"):
                result = {
                    "success": True,
                    "txid": spark_transfer_id,
                    "amount_out": int(swap_result.get("amountOut", 0)),
                    "execution_price": swap_result.get("executionPrice", "0"),
                    "outbound_transfer_id": swap_result.get("outboundTransferId"),
                    "fee_amount": swap_result.get("feeAmount", 0),
                }
                print(f"  ✅ Swap accepted!")
                print(f"  Amount out: {result['amount_out']}")
                return result
            else:
                error = swap_result.get("error", "Unknown error")
                raise Exception(f"Swap rejected: {error}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Swap execution failed: {error_msg}")
            import traceback
            traceback.print_exc()
            raise
    
    def _sign_payload(self, payload: Dict[str, Any], mnemonic: str) -> str:
        """
        Подписать payload с помощью приватного ключа из mnemonic
        
        Args:
            payload: Данные для подписи
            mnemonic: Mnemonic phrase
        
        Returns:
            Hex-encoded signature
        """
        import hashlib
        import json
        from mnemonic import Mnemonic as MnemonicGenerator
        from ecdsa import SigningKey, SECP256k1
        
        # Генерируем приватный ключ из mnemonic
        mnemo = MnemonicGenerator("english")
        seed = mnemo.to_seed(mnemonic)
        private_key_bytes = seed[:32]
        
        # Создаем signing key (используем SECP256k1 для Bitcoin)
        sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
        
        # Сериализуем payload в строку для подписи (без поля signature)
        payload_copy = {k: v for k, v in payload.items() if k != "signature"}
        payload_str = json.dumps(payload_copy, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode()).digest()
        
        # Подписываем
        signature_bytes = sk.sign_digest(payload_hash)
        
        return signature_bytes.hex()
    
    async def buy_token_with_btc(
        self,
        token_address: str,
        amount_btc_sats: int,
        slippage_pct: float = 1.0,
        priority_fee_sats: int = 10000,
        user_public_key: str = None,
        mnemonic: str = None,
    ) -> Dict[str, Any]:
        """
        Купить токен за BTC через Flashnet AMM
        
        Args:
            token_address: Адрес токена для покупки
            amount_btc_sats: Сумма BTC в satoshis
            slippage_pct: Допустимый slippage в процентах (по умолчанию 1%)
            priority_fee_sats: Комиссия приоритета
            user_public_key: Публичный ключ пользователя (обязательно для реального выполнения)
            mnemonic: Mnemonic phrase (обязательно для реального выполнения)
        
        Returns:
            dict с результатами покупки
        """
        try:
            # 1. Найти пул для торговли
            pool_id = await self.find_pool_for_token(token_address)
            if not pool_id:
                raise Exception("❌ Пул для данного токена не найден")
            
            # 2. Симулировать своп через реальный API
            simulation = await self.simulate_swap(
                pool_id=pool_id,
                asset_in_address=self.BTC_PUBKEY,
                asset_out_address=token_address,
                amount_in=amount_btc_sats,
            )
            
            if not simulation:
                raise Exception("❌ Не удалось симулировать своп. Проверьте pool_id и адреса активов.")
            
            # Проверка price impact
            if simulation["price_impact_pct"] > 10.0:
                print(f"⚠️ WARNING: High price impact ({simulation['price_impact_pct']:.2f}%)")
            
            # 3. Рассчитать минимальную сумму с учетом slippage
            expected_out = simulation["amount_out"]
            slippage_multiplier = (100 - slippage_pct) / 100
            min_amount_out = int(expected_out * slippage_multiplier)
            
            print(f"[INFO] Simulation completed:")
            print(f"  Expected tokens: {expected_out}")
            print(f"  Min tokens (with {slippage_pct}% slippage): {min_amount_out}")
            
            # 4. Если есть user_public_key и mnemonic - выполняем реальный своп
            if user_public_key and mnemonic:
                slippage_bps = int(slippage_pct * 100)  # Конвертируем % в BPS
                
                swap_result = await self.execute_swap(
                    pool_id=pool_id,
                    asset_in_address=self.BTC_PUBKEY,
                    asset_out_address=token_address,
                    amount_in=amount_btc_sats,
                    min_amount_out=min_amount_out,
                    max_slippage_bps=slippage_bps,
                    priority_fee_sats=priority_fee_sats,
                    user_public_key=user_public_key,
                    mnemonic=mnemonic,
                )
                
                if swap_result.get("success"):
                    return {
                        "status": "success",
                        "txid": swap_result["txid"],
                        "tokens_received": swap_result["amount_out"],
                        "tokens_received_sats": swap_result["amount_out"],  # В satoshis
                        "btc_spent": amount_btc_sats,
                        "btc_spent_sats": amount_btc_sats,  # Уже в satoshis
                        "price_impact_pct": simulation["price_impact_pct"],
                        "execution_price": swap_result.get("execution_price", "0"),
                    }
                else:
                    raise Exception(f"Swap failed: {swap_result.get('error')}")
            
            # Только симуляция (если нет wallet данных)
            else:
                print(f"\n⚠️  SIMULATION ONLY")
                print(f"To execute real swap, provide user_public_key and mnemonic")
                
                return {
                    "simulation_only": True,
                    "expected_tokens": expected_out,
                    "min_tokens": min_amount_out,
                    "btc_amount": amount_btc_sats,
                    "price_impact_pct": simulation["price_impact_pct"],
                }
            
            # Возвращаем результат симуляции
            return {
                "success": False,
                "simulation_only": True,
                "token_address": token_address,
                "btc_amount_sats": amount_btc_sats,
                "expected_tokens": expected_out,
                "min_tokens": min_amount_out,
                "price_impact_pct": simulation["price_impact_pct"],
                "execution_price": simulation["execution_price"],
                "message": "Simulation successful. Real execution not implemented yet."
            }
            
        except Exception as e:
            print(f"[ERROR] Buy token failed: {e}")
            raise
    
    async def sell_token_for_btc(
        self,
        token_address: str,
        amount_tokens: int,
        slippage_pct: float = 1.0,
        priority_fee_sats: int = 10000,
        user_public_key: str = None,
        mnemonic: str = None,
    ) -> Dict[str, Any]:
        """
        Продать токен за BTC через Flashnet AMM
        
        Args:
            token_address: Адрес токена для продажи
            amount_tokens: Количество токенов для продажи
            slippage_pct: Допустимый slippage в процентах
            priority_fee_sats: Комиссия приоритета
            user_public_key: Публичный ключ пользователя (обязательно для реального выполнения)
            mnemonic: Mnemonic phrase (обязательно для реального выполнения)
        
        Returns:
            dict с результатами продажи
        """
        try:
            # 1. Найти пул
            pool_id = await self.find_pool_for_token(token_address)
            if not pool_id:
                raise Exception("❌ Пул для данного токена не найден")
            
            # 2. Симулировать своп (токены -> BTC) через реальный API
            simulation = await self.simulate_swap(
                pool_id=pool_id,
                asset_in_address=token_address,
                asset_out_address=self.BTC_PUBKEY,
                amount_in=amount_tokens,
            )
            
            if not simulation:
                raise Exception("❌ Не удалось симулировать своп. Проверьте pool_id и адреса активов.")
            
            # Проверка price impact
            if simulation["price_impact_pct"] > 10.0:
                print(f"⚠️ WARNING: High price impact ({simulation['price_impact_pct']:.2f}%)")
            
            # 3. Рассчитать минимальную сумму BTC
            expected_btc = simulation["amount_out"]
            slippage_multiplier = (100 - slippage_pct) / 100
            min_btc_out = int(expected_btc * slippage_multiplier)
            
            print(f"[INFO] Simulation completed:")
            print(f"  Expected BTC: {expected_btc} sats")
            print(f"  Min BTC (with {slippage_pct}% slippage): {min_btc_out} sats")
            
            # 4. Если есть user_public_key и mnemonic - выполняем реальный своп
            if user_public_key and mnemonic:
                slippage_bps = int(slippage_pct * 100)  # Конвертируем % в BPS
                
                swap_result = await self.execute_swap(
                    pool_id=pool_id,
                    asset_in_address=token_address,
                    asset_out_address=self.BTC_PUBKEY,
                    amount_in=amount_tokens,
                    min_amount_out=min_btc_out,
                    max_slippage_bps=slippage_bps,
                    priority_fee_sats=priority_fee_sats,
                    user_public_key=user_public_key,
                    mnemonic=mnemonic,
                )
                
                if swap_result.get("success"):
                    return {
                        "status": "success",
                        "txid": swap_result["txid"],
                        "btc_received_sats": swap_result["amount_out"],
                        "tokens_sold": amount_tokens,
                        "price_impact_pct": simulation["price_impact_pct"],
                        "execution_price": swap_result.get("execution_price", "0"),
                    }
                else:
                    raise Exception(f"Swap failed: {swap_result.get('error')}")
            
            # Только симуляция (если нет wallet данных)
            else:
                print(f"\n⚠️  SIMULATION ONLY")
                print(f"To execute real swap, provide user_public_key and mnemonic")
                
                return {
                    "simulation_only": True,
                    "expected_btc_sats": expected_btc,
                    "min_btc_sats": min_btc_out,
                    "tokens_amount": amount_tokens,
                    "price_impact_pct": simulation["price_impact_pct"],
                }
            print(f"\n⚠️  EXECUTION NOT IMPLEMENTED")
            print(f"Real swap requires wallet integration")
            
            # Возвращаем результат симуляции
            return {
                "success": False,
                "simulation_only": True,
                "token_address": token_address,
                "tokens_amount": amount_tokens,
                "expected_btc_sats": expected_btc,
                "min_btc_sats": min_btc_out,
                "price_impact_pct": simulation["price_impact_pct"],
                "execution_price": simulation["execution_price"],
                "message": "Simulation successful. Real execution not implemented yet."
            }
            
        except Exception as e:
            print(f"[ERROR] Sell token failed: {e}")
            raise


# Singleton экземпляр с поддержкой mnemonic
_flashnet_swap_client = None

def get_flashnet_swap_client(mnemonic: str = None) -> FlashnetSwapClient:
    """
    Получить singleton экземпляр FlashnetSwapClient
    
    Args:
        mnemonic: BIP39 mnemonic для JWT аутентификации
    
    Returns:
        FlashnetSwapClient instance
    """
    global _flashnet_swap_client
    if _flashnet_swap_client is None or (_flashnet_swap_client.mnemonic != mnemonic and mnemonic):
        print(f"[DEBUG] Creating new FlashnetSwapClient instance...")
        _flashnet_swap_client = FlashnetSwapClient(mnemonic=mnemonic)
    return _flashnet_swap_client


# Backward compatibility (без mnemonic)
flashnet_swap_client = FlashnetSwapClient()
