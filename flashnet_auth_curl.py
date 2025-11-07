"""
Flashnet Authentication with curl-cffi (Cloudflare bypass)
Использует curl-cffi для обхода Cloudflare TLS fingerprinting
"""
import asyncio
import hashlib
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from ecdsa import SigningKey, SECP256k1
from mnemonic import Mnemonic

try:
    from curl_cffi import requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    print("[WARN] curl-cffi not installed. Install: pip install curl-cffi")


class FlashnetAuthCurl:
    """
    JWT аутентификация для Flashnet AMM API с обходом Cloudflare
    Использует curl-cffi для имитации браузера Chrome
    """
    
    API_BASE_URL = "https://api.amm.flashnet.xyz/v1"
    
    def __init__(self):
        """Инициализация клиента"""
        if not CURL_CFFI_AVAILABLE:
            raise ImportError("curl-cffi required. Install: pip install curl-cffi")
        
        # Создаем сессию с browser impersonation
        self.session = requests.Session()
        
        # Имитируем Chrome 110
        self.impersonate = "chrome110"
        
        # Thread pool для async wrapper
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Кэш JWT токенов
        self.jwt_cache = {}
    
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
    
    def _sync_get_challenge(self, public_key: str) -> Dict[str, str]:
        """
        Синхронный запрос challenge (для curl-cffi)
        
        Args:
            public_key: Публичный ключ пользователя (hex)
        
        Returns:
            dict с challenge и challengeString
        """
        try:
            url = f"{self.API_BASE_URL}/auth/challenge"
            
            payload = {
                "publicKey": public_key
            }
            
            headers = {
                "Content-Type": "application/json",
                "Origin": "https://flashnet.xyz",
                "Referer": "https://flashnet.xyz/",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            print(f"[AUTH-CURL] Requesting challenge for public key: {public_key[:20]}...")
            
            # Используем curl-cffi с browser impersonation
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                impersonate=self.impersonate,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"[ERROR] HTTP {response.status_code}: {response.text[:500]}")
                raise Exception(f"Failed to get challenge: HTTP {response.status_code}")
            
            result = response.json()
            
            print(f"[AUTH-CURL] ✅ Challenge received: {result.get('challengeString', '')[:50]}...")
            
            return {
                "challenge": result["challenge"],
                "challengeString": result["challengeString"],
                "requestId": result.get("requestId", "")
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to get challenge: {e}")
            raise
    
    async def get_challenge(self, public_key: str) -> Dict[str, str]:
        """
        Асинхронный wrapper для запроса challenge
        
        Args:
            public_key: Публичный ключ пользователя (hex)
        
        Returns:
            dict с challenge и challengeString
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_get_challenge,
            public_key
        )
    
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
            
            # Подписываем challenge (хешируем SHA256 и подписываем)
            signature_bytes = sk.sign_digest(hashlib.sha256(challenge_bytes).digest())
            
            # Возвращаем DER-encoded signature в hex
            return signature_bytes.hex()
            
        except Exception as e:
            print(f"[ERROR] Failed to sign challenge: {e}")
            raise
    
    def _sync_verify_challenge(self, public_key: str, signature: str) -> str:
        """
        Синхронная верификация подписи и получение JWT (для curl-cffi)
        
        Args:
            public_key: Публичный ключ пользователя (hex)
            signature: Подпись challenge (hex)
        
        Returns:
            JWT access token
        """
        try:
            url = f"{self.API_BASE_URL}/auth/verify"
            
            payload = {
                "publicKey": public_key,
                "signature": signature
            }
            
            headers = {
                "Content-Type": "application/json",
                "Origin": "https://flashnet.xyz",
                "Referer": "https://flashnet.xyz/",
                "Accept": "application/json, text/plain, */*",
            }
            
            print(f"[AUTH-CURL] Verifying signature...")
            
            # Используем curl-cffi с browser impersonation
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                impersonate=self.impersonate,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"[ERROR] HTTP {response.status_code}: {response.text[:500]}")
                raise Exception(f"Failed to verify challenge: HTTP {response.status_code}")
            
            result = response.json()
            
            access_token = result.get("accessToken")
            
            if not access_token:
                raise Exception("No accessToken in response")
            
            print(f"[AUTH-CURL] ✅ JWT token received: {access_token[:50]}...")
            
            return access_token
            
        except Exception as e:
            print(f"[ERROR] Failed to verify challenge: {e}")
            raise
    
    async def verify_challenge(self, public_key: str, signature: str) -> str:
        """
        Асинхронный wrapper для верификации challenge
        
        Args:
            public_key: Публичный ключ пользователя (hex)
            signature: Подпись challenge (hex)
        
        Returns:
            JWT access token
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_verify_challenge,
            public_key,
            signature
        )
    
    async def get_jwt_token(self, mnemonic: str, user_public_key: str = None) -> str:
        """
        Полный flow аутентификации: получить JWT токен
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            user_public_key: Публичный ключ (опционально, будет извлечен из mnemonic)
        
        Returns:
            JWT access token
        """
        try:
            # 1. Получаем публичный ключ
            if not user_public_key:
                user_public_key = self._get_public_key_from_mnemonic(mnemonic)
            
            # Проверяем кэш
            if user_public_key in self.jwt_cache:
                print(f"[AUTH-CURL] Using cached JWT token for {user_public_key[:20]}...")
                return self.jwt_cache[user_public_key]
            
            print(f"[AUTH-CURL] Starting authentication flow...")
            print(f"[AUTH-CURL] Public key: {user_public_key}")
            
            # 2. Запрашиваем challenge
            challenge_data = await self.get_challenge(user_public_key)
            challenge_hex = challenge_data["challenge"]
            
            # 3. Подписываем challenge
            print(f"[AUTH-CURL] Signing challenge...")
            signature = self._sign_challenge(challenge_hex, mnemonic)
            print(f"[AUTH-CURL] Signature: {signature[:50]}...")
            
            # 4. Верифицируем и получаем JWT
            jwt_token = await self.verify_challenge(user_public_key, signature)
            
            # Кэшируем токен
            self.jwt_cache[user_public_key] = jwt_token
            
            print(f"[AUTH-CURL] ✅ Authentication successful!")
            
            return jwt_token
            
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            raise Exception(f"Flashnet authentication failed: {e}")
    
    def close(self):
        """Закрыть сессию и executor"""
        self.session.close()
        self.executor.shutdown(wait=False)


# Singleton instance
_flashnet_auth_curl = None

def get_flashnet_auth_curl() -> FlashnetAuthCurl:
    """Получить singleton instance FlashnetAuthCurl"""
    global _flashnet_auth_curl
    if _flashnet_auth_curl is None:
        _flashnet_auth_curl = FlashnetAuthCurl()
    return _flashnet_auth_curl
