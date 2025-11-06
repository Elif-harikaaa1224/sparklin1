"""
Система кэширования для данных токенов
Предотвращает Rate Limit от UTXO.fun API
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional

CACHE_FILE = "token_cache.json"
CACHE_TTL = 300  # 5 минут


class TokenCache:
    def __init__(self):
        self.cache_file = Path(CACHE_FILE)
        self.cache = self._load_cache()
        self.request_times = {}  # Отслеживание времени запросов
        self.min_request_interval = 2  # Минимум 2 секунды между запросами к одному токену
    
    def _load_cache(self) -> Dict:
        """Загрузить кэш из файла"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Сохранить кэш в файл"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save cache: {e}")
    
    def get(self, token_address: str) -> Optional[Dict]:
        """
        Получить данные токена из кэша
        
        Args:
            token_address: Адрес токена (btkn1...)
            
        Returns:
            Данные токена или None если кэш устарел/не существует
        """
        if token_address not in self.cache:
            return None
        
        cached_data = self.cache[token_address]
        timestamp = cached_data.get('timestamp', 0)
        
        # Проверяем TTL
        if time.time() - timestamp > CACHE_TTL:
            print(f"[CACHE] Cache expired for {token_address}")
            del self.cache[token_address]
            self._save_cache()
            return None
        
        print(f"[CACHE] Cache HIT for {token_address}")
        return cached_data.get('data')
    
    def set(self, token_address: str, data: Dict):
        """
        Сохранить данные токена в кэш
        
        Args:
            token_address: Адрес токена
            data: Данные для сохранения
        """
        self.cache[token_address] = {
            'timestamp': time.time(),
            'data': data
        }
        self._save_cache()
        print(f"[CACHE] Cached data for {token_address}")
    
    def should_wait_before_request(self, token_address: str) -> float:
        """
        Проверить нужно ли ждать перед следующим запросом
        
        Args:
            token_address: Адрес токена
            
        Returns:
            Количество секунд ожидания (0 если можно запрашивать)
        """
        if token_address not in self.request_times:
            self.request_times[token_address] = 0
            return 0
        
        last_request = self.request_times[token_address]
        elapsed = time.time() - last_request
        
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            print(f"[RATE] Rate limit: wait {wait_time:.1f}s before next request")
            return wait_time
        
        return 0
    
    def mark_request(self, token_address: str):
        """Отметить что был сделан запрос"""
        self.request_times[token_address] = time.time()
    
    def clear(self):
        """Очистить весь кэш"""
        self.cache = {}
        self.request_times = {}
        self._save_cache()
        print("[CACHE] Cache cleared")


# Глобальный экземпляр кэша
token_cache = TokenCache()