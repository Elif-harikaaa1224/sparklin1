"""
Flashnet Swap Integration Module
С динамическим переключением между MOCK и REAL режимами через config
"""

import asyncio
from typing import Dict, Any, Optional

# ✅ Загружаем конфигурацию
from config import USE_MOCK_MODE, is_mock_mode, get_trading_mode

print(f"[FLASHNET] Trading mode: {get_trading_mode()}")


class FlashnetSwapIntegration:
    """Интеграция Flashnet AMM свопов с Spark Wallet"""
    
    def __init__(self, wallet_manager):
        """
        Args:
            wallet_manager: Экземпляр SparkWalletManager
        """
        self.wallet_manager = wallet_manager
        self._clients_cache: Dict[str, any] = {}
        self.mode = get_trading_mode()
    
    async def _mock_buy_token(
        self,
        wallet_name: str,
        token_address: str,
        amount_btc_sats: int,
        slippage_pct: float
    ) -> Dict[str, Any]:
        """🎭 MOCK реализация покупки"""
        import random
        import hashlib
        import time
        
        print(f"[MOCK] 🛒 Buying {amount_btc_sats} sats worth of {token_address[:16]}...")
        await asyncio.sleep(0.3)
        
        price_btc = random.uniform(0.00001, 0.0001)
        tokens_received = int((amount_btc_sats / 100_000_000) / price_btc)
        tokens_received = int(tokens_received * (1 - slippage_pct / 100))
        
        txid = hashlib.sha256(
            f"{wallet_name}{token_address}{amount_btc_sats}{time.time()}".encode()
        ).hexdigest()[:16]
        
        return {
            "status": "success",
            "txid": f"mock_{txid}",
            "tokens_received": tokens_received,
            "tokens_received_sats": tokens_received,
            "btc_spent": amount_btc_sats,
            "btc_spent_sats": amount_btc_sats,
            "execution_price": price_btc,
            "request_id": txid,
            "message": f"✅ MOCK: Bought {tokens_received:,} tokens",
            "mode": "MOCK"
        }
    
    async def _mock_sell_token(
        self,
        wallet_name: str,
        token_address: str,
        amount_tokens: int,
        slippage_pct: float
    ) -> Dict[str, Any]:
        """🎭 MOCK реализация продажи"""
        import random
        import hashlib
        import time
        
        print(f"[MOCK] 💸 Selling {amount_tokens:,} tokens of {token_address[:16]}...")
        await asyncio.sleep(0.3)
        
        price_btc = random.uniform(0.00001, 0.0001)
        btc_received_sats = int((amount_tokens * price_btc) * 100_000_000)
        btc_received_sats = int(btc_received_sats * (1 - slippage_pct / 100))
        
        txid = hashlib.sha256(
            f"{wallet_name}{token_address}{amount_tokens}{time.time()}".encode()
        ).hexdigest()[:16]
        
        return {
            "status": "success",
            "txid": f"mock_{txid}",
            "btc_received": btc_received_sats,
            "btc_received_sats": btc_received_sats,
            "tokens_sold": amount_tokens,
            "tokens_sold_sats": amount_tokens,
            "execution_price": price_btc,
            "request_id": txid,
            "message": f"✅ MOCK: Sold {amount_tokens:,} tokens for {btc_received_sats:,} sats",
            "mode": "MOCK"
        }
    
    async def buy_token(
        self,
        wallet_name: str,
        token_address: str,
        amount_btc_sats: int,
        slippage_pct: float = 1.0
    ) -> Dict[str, Any]:
        """Купить токен за BTC"""
        
        # ✅ MOCK MODE
        if is_mock_mode():
            try:
                return await self._mock_buy_token(
                    wallet_name=wallet_name,
                    token_address=token_address,
                    amount_btc_sats=amount_btc_sats,
                    slippage_pct=slippage_pct
                )
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": f"❌ MOCK Error: {str(e)}",
                    "mode": "MOCK"
                }
        
        # ❌ REAL MODE
        print(f"[REAL] 🛒 Buying from real Flashnet AMM...")
        
        try:
            from flashnet_amm_client import FlashnetAMMClient
            
            wallets = self.wallet_manager.list_wallets()
            if wallet_name not in wallets:
                return {
                    "status": "error",
                    "error": f"Wallet {wallet_name} not found",
                    "message": f"❌ Wallet not found",
                    "mode": "REAL"
                }
            
            # Создаём и используем реальный клиент
            # (реальный код интеграции)
            
            return {
                "status": "error",
                "error": "Real mode not fully implemented",
                "message": "❌ Real Flashnet integration coming soon",
                "mode": "REAL"
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"❌ Real Mode Error: {str(e)}",
                "mode": "REAL"
            }
    
    async def sell_token(
        self,
        wallet_name: str,
        token_address: str,
        amount_tokens: int,
        slippage_pct: float = 1.0
    ) -> Dict[str, Any]:
        """Продать токен за BTC"""
        
        # ✅ MOCK MODE
        if is_mock_mode():
            try:
                return await self._mock_sell_token(
                    wallet_name=wallet_name,
                    token_address=token_address,
                    amount_tokens=amount_tokens,
                    slippage_pct=slippage_pct
                )
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": f"❌ MOCK Error: {str(e)}",
                    "mode": "MOCK"
                }
        
        # ❌ REAL MODE
        print(f"[REAL] 💸 Selling to real Flashnet AMM...")
        
        try:
            return {
                "status": "error",
                "error": "Real mode not fully implemented",
                "message": "❌ Real Flashnet integration coming soon",
                "mode": "REAL"
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"❌ Real Mode Error: {str(e)}",
                "mode": "REAL"
            }
    
    async def close_all(self):
        """Закрыть все соединения"""
        self._clients_cache.clear()


# Convenience функции
async def execute_buy(
    wallet_manager,
    wallet_name: str,
    token_address: str,
    amount_btc_sats: int,
    slippage_pct: float = 1.0
) -> Dict[str, Any]:
    """Купить токен"""
    integration = FlashnetSwapIntegration(wallet_manager)
    try:
        return await integration.buy_token(
            wallet_name=wallet_name,
            token_address=token_address,
            amount_btc_sats=amount_btc_sats,
            slippage_pct=slippage_pct
        )
    finally:
        await integration.close_all()


async def execute_sell(
    wallet_manager,
    wallet_name: str,
    token_address: str,
    amount_tokens: int,
    slippage_pct: float = 1.0
) -> Dict[str, Any]:
    """Продать токен"""
    integration = FlashnetSwapIntegration(wallet_manager)
    try:
        return await integration.sell_token(
            wallet_name=wallet_name,
            token_address=token_address,
            amount_tokens=amount_tokens,
            slippage_pct=slippage_pct
        )
    finally:
        await integration.close_all()