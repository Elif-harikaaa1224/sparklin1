#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spark Withdrawal Manager (HTTP API Version)
Управление выводом средств из Spark wallet через HTTP API
Масштабируется до 1000+ одновременных пользователей
"""

from typing import Dict, Any, Optional
from spark_api_client import get_spark_api_client
import logging

logger = logging.getLogger(__name__)


class SparkWithdrawalManager:
    """
    Менеджер вывода средств из Spark
    
    НОВАЯ АРХИТЕКТУРА:
    - Не создает subprocess для каждого запроса
    - Использует HTTP API сервер (nodejs/api_server.js)
    - Один Node.js процесс обрабатывает все запросы
    - Масштабируется до 1000+ одновременных пользователей
    """
    
    def __init__(self, api_url: str = "http://127.0.0.1:3000"):
        """
        Инициализация менеджера вывода
        
        Args:
            api_url: URL API сервера (по умолчанию http://127.0.0.1:3000)
        """
        self.api_client = get_spark_api_client()
        logger.info(f"SparkWithdrawalManager initialized with API URL: {api_url}")
    
    async def get_deposit_address(self, mnemonic: str) -> Dict[str, Any]:
        """
        Получить Bitcoin адрес для пополнения с биржи
        
        Args:
            mnemonic: Mnemonic фраза кошелька
        
        Returns:
            Dict с Bitcoin адресом для депозита
        """
        return await self.api_client.get_deposit_address(mnemonic)
    
    async def create_lightning_invoice(
        self, 
        mnemonic: str, 
        amount_sats: int,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создать Lightning invoice через Spark SDK (MAINNET!)
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            amount_sats: Сумма в satoshi
            memo: Описание платежа (опционально)
        
        Returns:
            Dict с encoded invoice
        """
        return await self.api_client.create_lightning_invoice(
            mnemonic, 
            amount_sats, 
            memo
        )
    
    async def send_spark_transfer(
        self,
        mnemonic: str,
        receiver_address: str,
        amount_sats: int
    ) -> Dict[str, Any]:
        """
        Отправить Spark transfer на указанный адрес (работает с spark1... адресами!)
        
        Args:
            mnemonic: Mnemonic фраза кошелька отправителя
            receiver_address: Spark address получателя (spark1...)
            amount_sats: Сумма в satoshi
        
        Returns:
            Dict с результатом transfer
        """
        return await self.api_client.send_spark_transfer(
            mnemonic,
            receiver_address,
            amount_sats
        )
    
    async def pay_lightning_invoice(
        self,
        mnemonic: str,
        invoice: str,
        max_fee_sats: int = 100
    ) -> Dict[str, Any]:
        """
        Оплатить Lightning invoice
        
        Args:
            mnemonic: Mnemonic фраза кошелька плательщика
            invoice: Закодированный Lightning invoice (lnbc...)
            max_fee_sats: Максимальная комиссия в satoshi
        
        Returns:
            Dict с результатом платежа
        """
        return await self.api_client.pay_lightning_invoice(
            mnemonic,
            invoice,
            max_fee_sats
        )
    
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
            btc_address: Bitcoin адрес получателя (bc1... или bcrt1...)
            amount_sats: Сумма в satoshi
            speed: Скорость транзакции ("SLOW", "MEDIUM", "FAST")
        
        Returns:
            Dict с результатом вывода
        """
        return await self.api_client.withdraw_to_l1(
            mnemonic,
            btc_address,
            amount_sats,
            speed
        )
    
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
            Dict с комиссиями для разных скоростей
        """
        return await self.api_client.get_withdrawal_fee(
            mnemonic,
            btc_address,
            amount_sats
        )


# Для обратной совместимости - если кто-то импортирует старые методы
__all__ = ['SparkWithdrawalManager']


if __name__ == "__main__":
    import asyncio
    
    async def test():
        """Тест менеджера вывода"""
        manager = SparkWithdrawalManager()
        
        # Проверяем что API сервер запущен
        health = await manager.api_client.health_check()
        print(f"API Server Status: {health}")
        
        if health.get("status") == "ok":
            print("\n✅ API сервер работает!")
            print("SparkWithdrawalManager готов к работе")
        else:
            print("\n❌ API сервер не запущен!")
            print("Запустите: cd nodejs && npm start")
    
    asyncio.run(test())
