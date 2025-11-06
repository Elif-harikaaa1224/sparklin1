"""
Получение клиента Spark SDK
Обертка для интеграции с Flashnet AMM
"""
import os
from typing import Optional
from flashnet_swap import FlashnetSwapClient


# Глобальный экземпляр клиента
_spark_client: Optional[FlashnetSwapClient] = None


async def get_spark_client() -> FlashnetSwapClient:
    """
    Получить или создать клиента Flashnet Swap
    
    Returns:
        FlashnetSwapClient instance
    """
    global _spark_client
    
    if _spark_client is None:
        _spark_client = FlashnetSwapClient()
        print("[INFO] Flashnet Swap Client initialized")
    
    return _spark_client


async def close_spark_client():
    """Закрыть клиент при завершении"""
    global _spark_client
    
    if _spark_client is not None:
        # Cleanup если необходимо
        _spark_client = None
        print("[INFO] Flashnet Swap Client closed")
