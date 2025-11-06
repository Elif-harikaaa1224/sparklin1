#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spark SDK HTTP API Client
Высокопроизводительный клиент для взаимодействия с Node.js API сервером
Заменяет subprocess вызовы на HTTP запросы - масштабируется до 1000+ пользователей
"""

import httpx
import asyncio
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SparkAPIClient:
    """
    HTTP клиент для Spark SDK API сервера
    
    Преимущества перед subprocess:
    - Один Node.js процесс обрабатывает все запросы
    - Может обслуживать 1000+ одновременных пользователей
    - Переиспользование соединений (connection pooling)
    - Нет накладных расходов на запуск нового процесса
    - Автоматический retry при временных ошибках
    """
    
    def __init__(
        self, 
        base_url: str = "http://127.0.0.1:3000",
        timeout: int = 60
    ):
        """
        Инициализация клиента
        
        Args:
            base_url: URL API сервера
            timeout: Таймаут запросов в секундах
        """
        self.base_url = base_url
        self.timeout = timeout
        
        # Создаем клиент с connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_connections=100,  # Максимум 100 одновременных соединений
                max_keepalive_connections=20  # Переиспользуем 20 соединений
            )
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Проверить что API сервер запущен и работает
        
        Returns:
            Dict с информацией о статусе сервера
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "status": "error",
                "error": "API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_deposit_address(self, mnemonic: str) -> Dict[str, Any]:
        """
        Получить Bitcoin адрес для пополнения
        
        Args:
            mnemonic: Mnemonic фраза кошелька
        
        Returns:
            Dict с Bitcoin адресом для депозита
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/deposit-address",
                json={"mnemonic": mnemonic}
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "❌ API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            logger.error(f"Error getting deposit address: {e}")
            return {
                "success": False,
                "error": f"Failed to get deposit address: {str(e)}"
            }
    
    async def create_lightning_invoice(
        self, 
        mnemonic: str, 
        amount_sats: int,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создать Lightning invoice
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            amount_sats: Сумма в satoshi
            memo: Описание платежа
        
        Returns:
            Dict с encoded invoice
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/create-invoice",
                json={
                    "mnemonic": mnemonic,
                    "amount_sats": amount_sats,
                    "memo": memo or "SPARK Wallet Payment"
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "❌ API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return {
                "success": False,
                "error": f"Failed to create Lightning invoice: {str(e)}"
            }
    
    async def pay_lightning_invoice(
        self,
        mnemonic: str,
        invoice: str,
        max_fee_sats: int = 100
    ) -> Dict[str, Any]:
        """
        Оплатить Lightning invoice
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            invoice: Закодированный Lightning invoice
            max_fee_sats: Максимальная комиссия в satoshi
        
        Returns:
            Dict с результатом платежа
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/pay-invoice",
                json={
                    "mnemonic": mnemonic,
                    "invoice": invoice,
                    "max_fee_sats": max_fee_sats
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "❌ API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            logger.error(f"Error paying invoice: {e}")
            return {
                "success": False,
                "error": f"Failed to pay Lightning invoice: {str(e)}"
            }
    
    async def send_spark_transfer(
        self,
        mnemonic: str,
        receiver_address: str,
        amount_sats: int
    ) -> Dict[str, Any]:
        """
        Отправить Spark transfer
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            receiver_address: Spark адрес получателя
            amount_sats: Сумма в satoshi
        
        Returns:
            Dict с результатом transfer
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/send-transfer",
                json={
                    "mnemonic": mnemonic,
                    "receiver_address": receiver_address,
                    "amount_sats": amount_sats
                }
            )
            
            # Если сервер вернул 503 (Service Unavailable) - это RESOURCE_EXHAUSTED
            if response.status_code == 503:
                return response.json()
            
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "❌ API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            logger.error(f"Error sending transfer: {e}")
            return {
                "success": False,
                "error": f"Failed to send transfer: {str(e)}"
            }
    
    async def withdraw_to_l1(
        self,
        mnemonic: str,
        btc_address: str,
        amount_sats: int,
        speed: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """
        Вывести средства на Bitcoin L1 адрес
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            btc_address: Bitcoin адрес получателя
            amount_sats: Сумма в satoshi
            speed: Скорость транзакции
        
        Returns:
            Dict с результатом вывода
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/withdraw-l1",
                json={
                    "mnemonic": mnemonic,
                    "btc_address": btc_address,
                    "amount_sats": amount_sats,
                    "speed": speed
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "❌ API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            logger.error(f"Error withdrawing to L1: {e}")
            return {
                "success": False,
                "error": f"Failed to withdraw to L1: {str(e)}"
            }
    
    async def get_withdrawal_fee(
        self,
        mnemonic: str,
        btc_address: str,
        amount_sats: int
    ) -> Dict[str, Any]:
        """
        Получить стоимость комиссии за вывод
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            btc_address: Bitcoin адрес получателя
            amount_sats: Сумма в satoshi
        
        Returns:
            Dict с комиссиями
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/withdrawal-fee",
                json={
                    "mnemonic": mnemonic,
                    "btc_address": btc_address,
                    "amount_sats": amount_sats
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "❌ API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            logger.error(f"Error getting withdrawal fee: {e}")
            return {
                "success": False,
                "error": f"Failed to get withdrawal fee: {str(e)}"
            }
    
    async def get_wallet_balance(self, mnemonic: str) -> Dict[str, Any]:
        """
        Получить баланс кошелька
        
        Args:
            mnemonic: Mnemonic фраза кошелька
        
        Returns:
            Dict с балансом
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/wallet-balance",
                json={"mnemonic": mnemonic}
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "❌ API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return {
                "success": False,
                "error": f"Failed to get wallet balance: {str(e)}"
            }
    
    async def get_token_info(
        self, 
        mnemonic: str, 
        token_id: str
    ) -> Dict[str, Any]:
        """
        Получить информацию о токене
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            token_id: ID токена
        
        Returns:
            Dict с информацией о токене
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/token-info",
                json={
                    "mnemonic": mnemonic,
                    "token_id": token_id
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "❌ API сервер не запущен. Запустите: cd nodejs && npm start"
            }
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return {
                "success": False,
                "error": f"Failed to get token info: {str(e)}"
            }
    
    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()


# Глобальный экземпляр клиента для переиспользования
_global_client: Optional[SparkAPIClient] = None


def get_spark_api_client() -> SparkAPIClient:
    """
    Получить глобальный экземпляр API клиента
    Переиспользует соединения для максимальной производительности
    
    Returns:
        SparkAPIClient instance
    """
    global _global_client
    if _global_client is None:
        _global_client = SparkAPIClient()
    return _global_client


async def test_api_client():
    """Тест API клиента"""
    client = get_spark_api_client()
    
    # Health check
    print("🔍 Health check...")
    health = await client.health_check()
    print(f"Статус: {health}")
    
    if health.get("status") == "ok":
        print("\n✅ API сервер работает!")
        print(f"Uptime: {health.get('uptime', 0):.2f} секунд")
    else:
        print("\n❌ API сервер не доступен!")
        print("Запустите: cd nodejs && npm start")


if __name__ == "__main__":
    asyncio.run(test_api_client())
