"""
Flashnet Authentication Module
Реализация JWT аутентификации для Flashnet AMM API
"""
import httpx
import hashlib
from typing import Optional, Dict, Any
from ecdsa import SigningKey, SECP256k1
from mnemonic import Mnemonic


class FlashnetAuth:
    """Клиент для аутентификации в Flashnet AMM API"""
    
    API_BASE_URL = "https://api.amm.flashnet.xyz/v1"
    
    def __init__(self):
        """Инициализация клиента"""
        # Используем те же headers что и в FlashnetSwapClient для обхода Cloudflare
        headers = {
            "Content-Type": "application/json",
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
        self.jwt_cache = {}  # Кэш JWT токенов по public_key
    
    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()
    
    def _get_public_key_from_mnemonic(self, mnemonic: str) -> str:
        """
        Получить публичный ключ из mnemonic phrase
        
        Args:
            mnemonic: BIP39 mnemonic phrase
        
        Returns:
            Hex-encoded публичный ключ (compressed)
        """
        try:
            # Генерируем seed из mnemonic
            mnemo = Mnemonic("english")
            seed = mnemo.to_seed(mnemonic)
            
            # Извлекаем приватный ключ (первые 32 байта)
            private_key_bytes = seed[:32]
            
            # Создаем signing key
            sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
            
            # Получаем публичный ключ (compressed format)
            vk = sk.get_verifying_key()
            public_key_bytes = vk.to_string("compressed")
            
            return public_key_bytes.hex()
            
        except Exception as e:
            print(f"[ERROR] Failed to get public key from mnemonic: {e}")
            raise
    
    async def get_challenge(self, public_key: str) -> Dict[str, str]:
        """
        Запросить challenge для аутентификации
        
        Args:
            public_key: Публичный ключ пользователя (hex)
        
        Returns:
            dict с challenge и challengeString
        
        Raises:
            Exception если запрос не удался
        """
        try:
            url = f"{self.API_BASE_URL}/auth/challenge"
            
            payload = {
                "publicKey": public_key
            }
            
            print(f"[AUTH] Requesting challenge for public key: {public_key[:20]}...")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            print(f"[AUTH] Challenge received: {result.get('challengeString', '')[:50]}...")
            
            return {
                "challenge": result["challenge"],
                "challengeString": result["challengeString"],
                "requestId": result.get("requestId", "")
            }
            
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] HTTP {e.response.status_code} getting challenge: {e.response.text[:500]}")
            raise Exception(f"Failed to get challenge: HTTP {e.response.status_code}")
        except Exception as e:
            print(f"[ERROR] Failed to get challenge: {e}")
            raise
    
    def _sign_challenge(self, challenge_hex: str, mnemonic: str) -> str:
        """
        Подписать challenge приватным ключом
        
        Args:
            challenge_hex: Challenge в hex формате
            mnemonic: BIP39 mnemonic phrase
        
        Returns:
            Hex-encoded подпись
        """
        try:
            # Конвертируем challenge из hex в bytes
            challenge_bytes = bytes.fromhex(challenge_hex)
            
            # Генерируем seed из mnemonic
            mnemo = Mnemonic("english")
            seed = mnemo.to_seed(mnemonic)
            
            # Извлекаем приватный ключ
            private_key_bytes = seed[:32]
            
            # Создаем signing key
            sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
            
            # Подписываем challenge напрямую (без хеширования - уже есть в challenge)
            signature_bytes = sk.sign_digest(hashlib.sha256(challenge_bytes).digest())
            
            # Возвращаем DER-encoded signature в hex
            return signature_bytes.hex()
            
        except Exception as e:
            print(f"[ERROR] Failed to sign challenge: {e}")
            raise
    
    async def verify_challenge(self, public_key: str, signature: str) -> str:
        """
        Верифицировать подпись и получить JWT токен
        
        Args:
            public_key: Публичный ключ пользователя (hex)
            signature: Подпись challenge (hex)
        
        Returns:
            JWT access token
        
        Raises:
            Exception если верификация не удалась
        """
        try:
            url = f"{self.API_BASE_URL}/auth/verify"
            
            payload = {
                "publicKey": public_key,
                "signature": signature
            }
            
            print(f"[AUTH] Verifying signature...")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            access_token = result.get("accessToken")
            
            if not access_token:
                raise Exception("No accessToken in response")
            
            print(f"[AUTH] ✅ JWT token received: {access_token[:50]}...")
            
            return access_token
            
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] HTTP {e.response.status_code} verifying challenge: {e.response.text[:500]}")
            raise Exception(f"Failed to verify challenge: HTTP {e.response.status_code}")
        except Exception as e:
            print(f"[ERROR] Failed to verify challenge: {e}")
            raise
    
    async def get_jwt_token(self, mnemonic: str, user_public_key: str = None) -> str:
        """
        Полный flow аутентификации: получить JWT токен
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            user_public_key: Публичный ключ (опционально, будет извлечен из mnemonic)
        
        Returns:
            JWT access token
        
        Process:
            1. Получить public key из mnemonic (если не передан)
            2. Запросить challenge
            3. Подписать challenge
            4. Верифицировать и получить JWT
        """
        try:
            # 1. Получаем публичный ключ
            if not user_public_key:
                user_public_key = self._get_public_key_from_mnemonic(mnemonic)
            
            # Проверяем кэш
            if user_public_key in self.jwt_cache:
                print(f"[AUTH] Using cached JWT token for {user_public_key[:20]}...")
                return self.jwt_cache[user_public_key]
            
            print(f"[AUTH] Starting authentication flow...")
            print(f"[AUTH] Public key: {user_public_key}")
            
            # 2. Запрашиваем challenge
            challenge_data = await self.get_challenge(user_public_key)
            challenge_hex = challenge_data["challenge"]
            
            # 3. Подписываем challenge
            print(f"[AUTH] Signing challenge...")
            signature = self._sign_challenge(challenge_hex, mnemonic)
            print(f"[AUTH] Signature: {signature[:50]}...")
            
            # 4. Верифицируем и получаем JWT
            jwt_token = await self.verify_challenge(user_public_key, signature)
            
            # Кэшируем токен
            self.jwt_cache[user_public_key] = jwt_token
            
            print(f"[AUTH] ✅ Authentication successful!")
            
            return jwt_token
            
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            raise Exception(f"Flashnet authentication failed: {e}")


# Singleton instance
_flashnet_auth = None

def get_flashnet_auth() -> FlashnetAuth:
    """Получить singleton instance FlashnetAuth"""
    global _flashnet_auth
    if _flashnet_auth is None:
        _flashnet_auth = FlashnetAuth()
    return _flashnet_auth
