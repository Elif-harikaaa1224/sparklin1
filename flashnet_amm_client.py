"""
Flashnet AMM Client - Complete Implementation
Полная реализация покупки/продажи токенов через Flashnet AMM
Base URL: https://api.amm.flashnet.xyz/v1
"""
import asyncio
import httpx
import hashlib
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der


@dataclass
class SwapQuote:
    """Котировка свопа"""
    amount_out: int
    execution_price: str
    price_impact_pct: str
    fee_paid: int
    warning_message: Optional[str] = None


@dataclass
class SwapResult:
    """Результат выполнения свопа"""
    success: bool
    request_id: str
    amount_out: int = 0
    execution_price: str = "0"
    outbound_transfer_id: Optional[str] = None
    error: Optional[str] = None
    refund_transfer_id: Optional[str] = None


class FlashnetAMMClient:
    """Клиент для работы с Flashnet AMM API"""
    
    BASE_URL = "https://api.amm.flashnet.xyz/v1"
    
    # Bitcoin address на Flashnet (константа для всех пулов)
    BTC_ADDRESS = "020202020202020202020202020202020202020202020202020202020202020202"
    
    def __init__(self, private_key_hex: str):
        """
        Инициализация клиента
        
        Args:
            private_key_hex: Приватный ключ в hex формате
        """
        self.private_key = SigningKey.from_string(
            bytes.fromhex(private_key_hex),
            curve=SECP256k1
        )
        self.public_key = self.private_key.get_verifying_key()
        self.public_key_hex = "03" + self.public_key.to_string()[:32].hex()  # Compressed format
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Content-Type": "application/json",
                "Origin": "https://flashnet.xyz",
                "Referer": "https://flashnet.xyz/",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site"
            },
            follow_redirects=True
        )
        self.jwt_token: Optional[str] = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    # ==================== AUTHENTICATION ====================
    
    async def authenticate(self) -> str:
        """
        Получить JWT токен через challenge-response аутентификацию
        
        Returns:
            JWT токен
        """
        # Step 1: Get challenge
        challenge_response = await self.client.post(
            f"{self.BASE_URL}/auth/challenge",
            json={"publicKey": self.public_key_hex}
        )
        challenge_response.raise_for_status()
        challenge_data = challenge_response.json()
        challenge_string = challenge_data["challengeString"]
        
        # Step 2: Sign challenge
        signature = self._sign_message(challenge_string)
        
        # Step 3: Verify and get JWT
        verify_response = await self.client.post(
            f"{self.BASE_URL}/auth/verify",
            json={
                "publicKey": self.public_key_hex,
                "signature": signature
            }
        )
        verify_response.raise_for_status()
        verify_data = verify_response.json()
        
        self.jwt_token = verify_data["accessToken"]
        self.client.headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        return self.jwt_token
    
    def _sign_message(self, message: str) -> str:
        """
        Подписать сообщение приватным ключом
        
        Args:
            message: Сообщение для подписи
            
        Returns:
            Hex-encoded подпись
        """
        message_hash = hashlib.sha256(message.encode()).digest()
        signature = self.private_key.sign_digest(
            message_hash,
            sigencode=sigencode_der
        )
        return signature.hex()
    
    async def ensure_authenticated(self):
        """Убедиться что есть валидный JWT токен"""
        if not self.jwt_token:
            await self.authenticate()
    
    # ==================== POOLS ====================
    
    async def find_pool(
        self,
        token_address: str,
        quote_address: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Найти пул для пары токенов
        
        Args:
            token_address: Адрес токена для торговли
            quote_address: Адрес quote валюты (по умолчанию BTC)
            
        Returns:
            Данные пула или None
        """
        if quote_address is None:
            quote_address = self.BTC_ADDRESS
        
        # Search for pool
        response = await self.client.get(
            f"{self.BASE_URL}/pools",
            params={
                "assetAAddress": token_address,
                "assetBAddress": quote_address,
                "limit": 10
            }
        )
        response.raise_for_status()
        data = response.json()
        
        pools = data.get("pools", [])
        if not pools:
            # Try reverse pair
            response = await self.client.get(
                f"{self.BASE_URL}/pools",
                params={
                    "assetAAddress": quote_address,
                    "assetBAddress": token_address,
                    "limit": 10
                }
            )
            response.raise_for_status()
            data = response.json()
            pools = data.get("pools", [])
        
        if not pools:
            return None
        
        # Return pool with highest liquidity
        return max(pools, key=lambda p: int(p.get("tvlAssetB", 0)))
    
    async def get_pool(self, pool_id: str) -> Dict[str, Any]:
        """
        Получить информацию о пуле
        
        Args:
            pool_id: ID пула (LP public key)
            
        Returns:
            Данные пула
        """
        response = await self.client.get(f"{self.BASE_URL}/pools/{pool_id}")
        response.raise_for_status()
        return response.json()
    
    # ==================== SWAP SIMULATION ====================
    
    async def simulate_swap(
        self,
        pool_id: str,
        asset_in: str,
        asset_out: str,
        amount_in: int,
        integrator_bps: int = 0
    ) -> SwapQuote:
        """
        Симулировать своп для получения котировки
        
        Args:
            pool_id: ID пула
            asset_in: Адрес входящего актива
            asset_out: Адрес исходящего актива
            amount_in: Количество для свопа (в минимальных единицах)
            integrator_bps: Комиссия интегратора в BPS
            
        Returns:
            Котировка свопа
        """
        response = await self.client.post(
            f"{self.BASE_URL}/swap/simulate",
            json={
                "poolId": pool_id,
                "assetInAddress": asset_in,
                "assetOutAddress": asset_out,
                "amountIn": amount_in,
                "integratorBps": integrator_bps
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return SwapQuote(
            amount_out=data["amountOut"],
            execution_price=data.get("executionPrice", "0"),
            price_impact_pct=data.get("priceImpactPct", "0%"),
            fee_paid=data.get("feePaidAssetIn", 0),
            warning_message=data.get("warningMessage")
        )
    
    # ==================== SWAP EXECUTION ====================
    
    async def execute_swap(
        self,
        pool_id: str,
        asset_in: str,
        asset_out: str,
        amount_in: int,
        min_amount_out: int,
        spark_transfer_id: str,
        max_slippage_bps: int = 100,  # 1% по умолчанию
        integrator_fee_bps: int = 0,
        integrator_pubkey: str = None
    ) -> SwapResult:
        """
        Выполнить своп через один пул
        
        Args:
            pool_id: ID пула
            asset_in: Адрес входящего актива
            asset_out: Адрес исходящего актива
            amount_in: Количество для свопа
            min_amount_out: Минимальное количество на выходе (slippage protection)
            spark_transfer_id: ID Spark трансфера с депозитом
            max_slippage_bps: Максимальное проскальзывание в BPS
            integrator_fee_bps: Комиссия интегратора
            integrator_pubkey: Публичный ключ интегратора
            
        Returns:
            Результат свопа
        """
        await self.ensure_authenticated()
        
        # Generate unique nonce
        nonce = f"swap-{int(time.time() * 1000)}-{hash(spark_transfer_id) % 10000}"
        
        # Sign request
        signature = self._sign_message(nonce)
        
        # Default integrator to self if not provided
        if integrator_pubkey is None:
            integrator_pubkey = self.public_key_hex
        
        # Execute swap
        response = await self.client.post(
            f"{self.BASE_URL}/swap",
            json={
                "userPublicKey": self.public_key_hex,
                "poolId": pool_id,
                "assetInAddress": asset_in,
                "assetOutAddress": asset_out,
                "amountIn": amount_in,
                "minAmountOut": min_amount_out,
                "maxSlippageBps": max_slippage_bps,
                "assetInSparkTransferId": spark_transfer_id,
                "totalIntegratorFeeRateBps": integrator_fee_bps,
                "integratorPublicKey": integrator_pubkey,
                "nonce": nonce,
                "signature": signature
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return SwapResult(
            success=data.get("accepted", False),
            request_id=data["requestId"],
            amount_out=data.get("amountOut", 0),
            execution_price=data.get("executionPrice", "0"),
            outbound_transfer_id=data.get("outboundTransferId"),
            error=data.get("error"),
            refund_transfer_id=data.get("refundTransferId")
        )
    
    # ==================== HIGH-LEVEL BUY/SELL ====================
    
    async def buy_token(
        self,
        token_address: str,
        amount_btc_sats: int,
        btc_transfer_id: str,
        slippage_pct: float = 1.0,
        quote_currency: str = None
    ) -> SwapResult:
        """
        Купить токен за BTC
        
        Args:
            token_address: Адрес токена для покупки
            amount_btc_sats: Количество BTC в сатоши
            btc_transfer_id: ID Spark трансфера с BTC
            slippage_pct: Допустимое проскальзывание в процентах (1.0 = 1%)
            quote_currency: Адрес quote валюты (по умолчанию BTC)
            
        Returns:
            Результат покупки
        """
        if quote_currency is None:
            quote_currency = self.BTC_ADDRESS
        
        # Find pool
        pool = await self.find_pool(token_address, quote_currency)
        if not pool:
            return SwapResult(
                success=False,
                request_id="",
                error=f"Pool not found for token {token_address[:16]}..."
            )
        
        pool_id = pool["lpPublicKey"]
        
        # Simulate to get quote
        try:
            quote = await self.simulate_swap(
                pool_id=pool_id,
                asset_in=quote_currency,
                asset_out=token_address,
                amount_in=amount_btc_sats
            )
        except Exception as e:
            return SwapResult(
                success=False,
                request_id="",
                error=f"Simulation failed: {str(e)}"
            )
        
        # Calculate min amount out with slippage
        slippage_bps = int(slippage_pct * 100)  # Convert % to BPS
        min_amount_out = int(quote.amount_out * (1 - slippage_pct / 100))
        
        # Execute swap
        return await self.execute_swap(
            pool_id=pool_id,
            asset_in=quote_currency,
            asset_out=token_address,
            amount_in=amount_btc_sats,
            min_amount_out=min_amount_out,
            spark_transfer_id=btc_transfer_id,
            max_slippage_bps=slippage_bps
        )
    
    async def sell_token(
        self,
        token_address: str,
        amount_tokens: int,
        token_transfer_id: str,
        slippage_pct: float = 1.0,
        quote_currency: str = None
    ) -> SwapResult:
        """
        Продать токен за BTC
        
        Args:
            token_address: Адрес токена для продажи
            amount_tokens: Количество токенов
            token_transfer_id: ID Spark трансфера с токенами
            slippage_pct: Допустимое проскальзывание в процентах
            quote_currency: Адрес quote валюты (по умолчанию BTC)
            
        Returns:
            Результат продажи
        """
        if quote_currency is None:
            quote_currency = self.BTC_ADDRESS
        
        # Find pool
        pool = await self.find_pool(token_address, quote_currency)
        if not pool:
            return SwapResult(
                success=False,
                request_id="",
                error=f"Pool not found for token {token_address[:16]}..."
            )
        
        pool_id = pool["lpPublicKey"]
        
        # Simulate to get quote
        try:
            quote = await self.simulate_swap(
                pool_id=pool_id,
                asset_in=token_address,
                asset_out=quote_currency,
                amount_in=amount_tokens
            )
        except Exception as e:
            return SwapResult(
                success=False,
                request_id="",
                error=f"Simulation failed: {str(e)}"
            )
        
        # Calculate min amount out with slippage
        slippage_bps = int(slippage_pct * 100)
        min_amount_out = int(quote.amount_out * (1 - slippage_pct / 100))
        
        # Execute swap
        return await self.execute_swap(
            pool_id=pool_id,
            asset_in=token_address,
            asset_out=quote_currency,
            amount_in=amount_tokens,
            min_amount_out=min_amount_out,
            spark_transfer_id=token_transfer_id,
            max_slippage_bps=slippage_bps
        )
    
    async def get_token_price(
        self,
        token_address: str,
        quote_currency: str = None
    ) -> Optional[float]:
        """
        Получить текущую цену токена
        
        Args:
            token_address: Адрес токена
            quote_currency: Адрес quote валюты
            
        Returns:
            Цена или None
        """
        if quote_currency is None:
            quote_currency = self.BTC_ADDRESS
        
        pool = await self.find_pool(token_address, quote_currency)
        if not pool:
            return None
        
        price_str = pool.get("currentPriceAInB")
        if price_str:
            return float(price_str)
        
        return None


# ==================== UTILITY FUNCTIONS ====================

def sats_to_btc(sats: int) -> float:
    """Конвертировать сатоши в BTC"""
    return sats / 100_000_000


def btc_to_sats(btc: float) -> int:
    """Конвертировать BTC в сатоши"""
    return int(btc * 100_000_000)


async def main():
    """Пример использования"""
    # Example private key (NEVER use in production!)
    private_key_hex = "your_private_key_here"
    
    async with FlashnetAMMClient(private_key_hex) as client:
        # Authenticate
        print("Authenticating...")
        await client.authenticate()
        print(f"JWT Token: {client.jwt_token[:50]}...")
        
        # Example token address
        token_address = "66471063147ab9f53515bf18d1cea9a8ad166840ba9de93d46018d7007426e17"
        
        # Get token price
        price = await client.get_token_price(token_address)
        print(f"Token price: {price} BTC")
        
        # Find pool
        pool = await client.find_pool(token_address)
        if pool:
            print(f"Pool found: {pool['lpPublicKey']}")
            print(f"TVL: {pool.get('tvlAssetB')} sats")
            print(f"Volume 24h: {pool.get('volume24hAssetB')} sats")


if __name__ == "__main__":
    asyncio.run(main())
