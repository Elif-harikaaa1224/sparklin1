"""
Flashnet Swap Integration Module
Интеграция нового Flashnet AMM клиента с существующим SparkWalletManager
"""
import asyncio
from typing import Dict, Any, Optional
from flashnet_amm_client import FlashnetAMMClient, SwapResult, sats_to_btc, btc_to_sats


class FlashnetSwapIntegration:
    """Интеграция Flashnet AMM свопов с Spark Wallet"""
    
    def __init__(self, wallet_manager):
        """
        Args:
            wallet_manager: Экземпляр SparkWalletManager
        """
        self.wallet_manager = wallet_manager
        self._clients_cache: Dict[str, FlashnetAMMClient] = {}
    
    def _get_client(self, wallet_name: str) -> FlashnetAMMClient:
        """
        Получить или создать клиент для кошелька
        
        Args:
            wallet_name: Имя кошелька
            
        Returns:
            FlashnetAMMClient instance
        """
        if wallet_name in self._clients_cache:
            return self._clients_cache[wallet_name]
        
        wallet_data = self.wallet_manager.wallets.get(wallet_name)
        if not wallet_data:
            raise ValueError(f"Wallet '{wallet_name}' not found")
        
        # В SparkWalletManager приватный ключ уже в hex формате
        # Он хранится как encrypted hash, но нам нужен сам приватный ключ
        # Используем mnemonic для генерации приватного ключа
        if not wallet_data.mnemonic:
            raise ValueError(f"Wallet '{wallet_name}' does not have mnemonic")
        
        # Генерируем приватный ключ из mnemonic
        from generate_spark_wallet import derive_private_key_from_mnemonic
        private_key_hex = derive_private_key_from_mnemonic(wallet_data.mnemonic, account=1)
        
        # Создаем клиент
        client = FlashnetAMMClient(private_key_hex)
        self._clients_cache[wallet_name] = client
        
        return client
    
    async def buy_token(
        self,
        wallet_name: str,
        token_address: str,
        amount_btc_sats: int,
        slippage_pct: float = 1.0
    ) -> Dict[str, Any]:
        """
        Купить токен за BTC
        
        Args:
            wallet_name: Имя кошелька
            token_address: Адрес токена для покупки
            amount_btc_sats: Количество BTC в сатоши
            slippage_pct: Проскальзывание в процентах (1.0 = 1%)
            
        Returns:
            Результат покупки
        """
        client = self._get_client(wallet_name)
        
        try:
            # Аутентификация
            print(f"[AUTH] Authenticating with Flashnet AMM...")
            await client.authenticate()
            print(f"[AUTH] ✅ Authenticated")
            
            # ВАЖНО: В реальности сначала нужен Spark transfer BTC
            # Здесь мы предполагаем что transfer уже сделан
            # TODO: Интеграция с Spark SDK для создания transfer
            
            # Временно используем mock transfer ID
            # В production это должен быть реальный Spark transfer ID
            import time
            import hashlib
            mock_transfer_id = hashlib.sha256(
                f"{wallet_name}{token_address}{amount_btc_sats}{time.time()}".encode()
            ).hexdigest()
            
            print(f"[WARN] Using mock Spark transfer ID: {mock_transfer_id[:16]}...")
            print(f"[WARN] In production, you must create real Spark transfer first!")
            
            # Выполняем покупку
            print(f"[BUY] Buying {amount_btc_sats} sats worth of {token_address[:16]}...")
            result = await client.buy_token(
                token_address=token_address,
                amount_btc_sats=amount_btc_sats,
                btc_transfer_id=mock_transfer_id,
                slippage_pct=slippage_pct
            )
            
            if result.success:
                print(f"[BUY] ✅ Success!")
                print(f"  Amount out: {result.amount_out}")
                print(f"  Execution price: {result.execution_price}")
                print(f"  Transfer ID: {result.outbound_transfer_id}")
                
                return {
                    "status": "success",
                    "txid": result.outbound_transfer_id or result.request_id,
                    "tokens_received": result.amount_out,
                    "tokens_received_sats": result.amount_out,
                    "btc_spent": amount_btc_sats,
                    "btc_spent_sats": amount_btc_sats,
                    "execution_price": result.execution_price,
                    "request_id": result.request_id,
                    "message": "✅ Token purchase successful"
                }
            else:
                print(f"[BUY] ❌ Failed: {result.error}")
                
                # Если есть refund - средства вернулись
                if result.refund_transfer_id:
                    return {
                        "status": "failed_with_refund",
                        "error": result.error,
                        "refund_transfer_id": result.refund_transfer_id,
                        "btc_refunded": amount_btc_sats,
                        "message": f"❌ Purchase failed but BTC refunded: {result.error}"
                    }
                else:
                    return {
                        "status": "failed",
                        "error": result.error,
                        "message": f"❌ Purchase failed: {result.error}"
                    }
        
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Buy token failed: {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                "status": "error",
                "error": error_msg,
                "message": f"❌ Error: {error_msg}"
            }
    
    async def sell_token(
        self,
        wallet_name: str,
        token_address: str,
        amount_tokens: int,
        slippage_pct: float = 1.0
    ) -> Dict[str, Any]:
        """
        Продать токен за BTC
        
        Args:
            wallet_name: Имя кошелька
            token_address: Адрес токена для продажи
            amount_tokens: Количество токенов
            slippage_pct: Проскальзывание в процентах
            
        Returns:
            Результат продажи
        """
        client = self._get_client(wallet_name)
        
        try:
            # Аутентификация
            print(f"[AUTH] Authenticating with Flashnet AMM...")
            await client.authenticate()
            print(f"[AUTH] ✅ Authenticated")
            
            # ВАЖНО: В реальности сначала нужен Spark transfer токенов
            # TODO: Интеграция с Spark SDK
            
            import time
            import hashlib
            mock_transfer_id = hashlib.sha256(
                f"{wallet_name}{token_address}{amount_tokens}{time.time()}".encode()
            ).hexdigest()
            
            print(f"[WARN] Using mock Spark transfer ID: {mock_transfer_id[:16]}...")
            
            # Выполняем продажу
            print(f"[SELL] Selling {amount_tokens} tokens of {token_address[:16]}...")
            result = await client.sell_token(
                token_address=token_address,
                amount_tokens=amount_tokens,
                token_transfer_id=mock_transfer_id,
                slippage_pct=slippage_pct
            )
            
            if result.success:
                print(f"[SELL] ✅ Success!")
                print(f"  BTC received: {result.amount_out} sats")
                print(f"  Execution price: {result.execution_price}")
                
                return {
                    "status": "success",
                    "txid": result.outbound_transfer_id or result.request_id,
                    "btc_received": result.amount_out,
                    "btc_received_sats": result.amount_out,
                    "tokens_sold": amount_tokens,
                    "tokens_sold_sats": amount_tokens,
                    "execution_price": result.execution_price,
                    "request_id": result.request_id,
                    "message": "✅ Token sale successful"
                }
            else:
                print(f"[SELL] ❌ Failed: {result.error}")
                
                if result.refund_transfer_id:
                    return {
                        "status": "failed_with_refund",
                        "error": result.error,
                        "refund_transfer_id": result.refund_transfer_id,
                        "tokens_refunded": amount_tokens,
                        "message": f"❌ Sale failed but tokens refunded: {result.error}"
                    }
                else:
                    return {
                        "status": "failed",
                        "error": result.error,
                        "message": f"❌ Sale failed: {result.error}"
                    }
        
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Sell token failed: {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                "status": "error",
                "error": error_msg,
                "message": f"❌ Error: {error_msg}"
            }
    
    async def get_token_price(
        self,
        wallet_name: str,
        token_address: str
    ) -> Optional[float]:
        """
        Получить текущую цену токена
        
        Args:
            wallet_name: Имя кошелька (для аутентификации)
            token_address: Адрес токена
            
        Returns:
            Цена в BTC или None
        """
        client = self._get_client(wallet_name)
        
        try:
            # Не требует аутентификации
            price = await client.get_token_price(token_address)
            return price
        except Exception as e:
            print(f"[ERROR] Get price failed: {e}")
            return None
    
    async def get_quote(
        self,
        wallet_name: str,
        token_address: str,
        amount_btc_sats: int,
        is_buy: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Получить котировку для покупки/продажи
        
        Args:
            wallet_name: Имя кошелька
            token_address: Адрес токена
            amount_btc_sats: Количество BTC в сатоши (для покупки) или токенов (для продажи)
            is_buy: True = покупка, False = продажа
            
        Returns:
            Котировка или None
        """
        client = self._get_client(wallet_name)
        
        try:
            # Найти пул
            pool = await client.find_pool(token_address)
            if not pool:
                return None
            
            pool_id = pool["lpPublicKey"]
            
            # Определить направление свопа
            if is_buy:
                asset_in = client.BTC_ADDRESS
                asset_out = token_address
            else:
                asset_in = token_address
                asset_out = client.BTC_ADDRESS
            
            # Симулировать своп
            quote = await client.simulate_swap(
                pool_id=pool_id,
                asset_in=asset_in,
                asset_out=asset_out,
                amount_in=amount_btc_sats
            )
            
            return {
                "amount_in": amount_btc_sats,
                "amount_out": quote.amount_out,
                "execution_price": quote.execution_price,
                "price_impact": quote.price_impact_pct,
                "fee_paid": quote.fee_paid,
                "warning": quote.warning_message,
                "pool_id": pool_id
            }
        
        except Exception as e:
            print(f"[ERROR] Get quote failed: {e}")
            return None
    
    async def close_all(self):
        """Закрыть все клиентские соединения"""
        for client in self._clients_cache.values():
            await client.__aexit__(None, None, None)
        self._clients_cache.clear()


# Convenience функция для быстрого использования
async def execute_buy(
    wallet_manager,
    wallet_name: str,
    token_address: str,
    amount_btc_sats: int,
    slippage_pct: float = 1.0
) -> Dict[str, Any]:
    """
    Удобная функция для покупки токена
    
    Args:
        wallet_manager: SparkWalletManager instance
        wallet_name: Имя кошелька
        token_address: Адрес токена
        amount_btc_sats: Количество BTC в сатоши
        slippage_pct: Проскальзывание в процентах
        
    Returns:
        Результат покупки
    """
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
    """
    Удобная функция для продажи токена
    
    Args:
        wallet_manager: SparkWalletManager instance
        wallet_name: Имя кошелька
        token_address: Адрес токена
        amount_tokens: Количество токенов
        slippage_pct: Проскальзывание в процентах
        
    Returns:
        Результат продажи
    """
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
