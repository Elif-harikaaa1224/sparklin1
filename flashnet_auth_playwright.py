"""
Flashnet Authentication with Playwright (Optimized for Scale)
Использует browser pooling для эффективной работы при высокой нагрузке
"""
import asyncio
import hashlib
from typing import Optional, Dict, Any
from ecdsa import SigningKey, SECP256k1
from mnemonic import Mnemonic
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[WARN] Playwright not installed. Install: pip install playwright && playwright install chromium")


class BrowserPool:
    """
    Pool of browser instances для переиспользования
    Экономит память и время на запуск браузера
    """
    
    def __init__(self, pool_size: int = 3):
        """
        Args:
            pool_size: Количество browser instances в pool (default: 3)
        """
        self.pool_size = pool_size
        self.browsers: list[Browser] = []
        self.playwright = None
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Инициализация browser pool"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            print(f"[BROWSER-POOL] Initializing {self.pool_size} browser instances...")
            
            self.playwright = await async_playwright().start()
            
            # Создаем pool браузеров
            for i in range(self.pool_size):
                browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                    ]
                )
                self.browsers.append(browser)
                print(f"[BROWSER-POOL] Browser {i+1}/{self.pool_size} started")
            
            self._initialized = True
            print(f"[BROWSER-POOL] ✅ Pool initialized with {self.pool_size} browsers")
    
    async def get_browser(self) -> Browser:
        """
        Получить browser из pool (round-robin)
        
        Returns:
            Browser instance
        """
        if not self._initialized:
            await self.initialize()
        
        # Round-robin selection
        import random
        return random.choice(self.browsers)
    
    async def close(self):
        """Закрыть все browsers в pool"""
        if not self._initialized:
            return
        
        print(f"[BROWSER-POOL] Closing {len(self.browsers)} browsers...")
        
        for browser in self.browsers:
            await browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        self.browsers = []
        self._initialized = False
        
        print(f"[BROWSER-POOL] ✅ Pool closed")


class FlashnetAuthPlaywright:
    """
    JWT аутентификация для Flashnet AMM API с Playwright
    Использует browser pooling для оптимизации производительности
    """
    
    API_BASE_URL = "https://api.amm.flashnet.xyz/v1"
    
    def __init__(self, browser_pool_size: int = 3):
        """
        Args:
            browser_pool_size: Размер browser pool (default: 3)
                - Для 10k users/day: 3-5 browsers достаточно
                - Каждый browser ~100-150 MB RAM
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright required. Install: pip install playwright && playwright install chromium")
        
        self.browser_pool = BrowserPool(pool_size=browser_pool_size)
        self.jwt_cache = {}  # Кэш JWT токенов по public_key
        
        # Metrics для мониторинга
        self.metrics = {
            "auth_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0
        }
    
    def _get_public_key_from_mnemonic(self, mnemonic: str) -> str:
        """
        Получить публичный ключ из mnemonic phrase
        
        Args:
            mnemonic: BIP39 mnemonic phrase
        
        Returns:
            Hex-encoded публичный ключ (compressed)
        """
        try:
            mnemo = Mnemonic("english")
            seed = mnemo.to_seed(mnemonic)
            private_key_bytes = seed[:32]
            sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
            vk = sk.get_verifying_key()
            public_key_bytes = vk.to_string("compressed")
            return public_key_bytes.hex()
        except Exception as e:
            print(f"[ERROR] Failed to get public key: {e}")
            raise
    
    async def _make_browser_request(
        self, 
        url: str, 
        method: str = "POST", 
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Выполнить HTTP запрос через browser с обходом Cloudflare
        
        Args:
            url: URL endpoint
            method: HTTP method (GET/POST)
            data: Request payload
        
        Returns:
            Response JSON
        """
        browser = await self.browser_pool.get_browser()
        
        # Создаем новый context для изоляции
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        try:
            page = await context.new_page()
            
            # ВАЖНО: Сначала навигируемся на главную страницу для получения cookies
            print(f"[BROWSER] Navigating to flashnet.xyz to get cookies...")
            try:
                await page.goto('https://flashnet.xyz', wait_until='networkidle', timeout=15000)
                # Ждем 2 секунды для Cloudflare challenge
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"[WARN] Could not navigate to flashnet.xyz: {e}")
            
            # Теперь выполняем запрос к API (с cookies от главной страницы)
            if method == "POST":
                print(f"[BROWSER] Making POST request to {url}...")
                response = await page.request.post(
                    url,
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Origin": "https://flashnet.xyz",
                        "Referer": "https://flashnet.xyz/"
                    }
                )
            else:
                print(f"[BROWSER] Making GET request to {url}...")
                response = await page.request.get(url)
            
            print(f"[BROWSER] Response status: {response.status}")
            
            # Проверяем статус
            if response.status != 200:
                error_text = await response.text()
                print(f"[BROWSER] Error response: {error_text[:500]}")
                raise Exception(f"HTTP {response.status}: {error_text[:200]}")
            
            # Парсим JSON
            result = await response.json()
            
            return result
            
        finally:
            # Всегда закрываем context для освобождения памяти
            await context.close()
    
    async def get_challenge(self, public_key: str) -> Dict[str, str]:
        """
        Запросить challenge через browser
        
        Args:
            public_key: Публичный ключ пользователя (hex)
        
        Returns:
            dict с challenge и challengeString
        """
        try:
            print(f"[AUTH-BROWSER] Requesting challenge for {public_key[:20]}...")
            
            result = await self._make_browser_request(
                url=f"{self.API_BASE_URL}/auth/challenge",
                method="POST",
                data={"publicKey": public_key}
            )
            
            print(f"[AUTH-BROWSER] ✅ Challenge received: {result.get('challengeString', '')[:50]}...")
            
            return {
                "challenge": result["challenge"],
                "challengeString": result["challengeString"],
                "requestId": result.get("requestId", "")
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to get challenge: {e}")
            self.metrics["errors"] += 1
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
            challenge_bytes = bytes.fromhex(challenge_hex)
            mnemo = Mnemonic("english")
            seed = mnemo.to_seed(mnemonic)
            private_key_bytes = seed[:32]
            sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
            signature_bytes = sk.sign_digest(hashlib.sha256(challenge_bytes).digest())
            return signature_bytes.hex()
        except Exception as e:
            print(f"[ERROR] Failed to sign challenge: {e}")
            raise
    
    async def verify_challenge(self, public_key: str, signature: str) -> str:
        """
        Верифицировать подпись и получить JWT через browser
        
        Args:
            public_key: Публичный ключ пользователя (hex)
            signature: Подпись challenge (hex)
        
        Returns:
            JWT access token
        """
        try:
            print(f"[AUTH-BROWSER] Verifying signature...")
            
            result = await self._make_browser_request(
                url=f"{self.API_BASE_URL}/auth/verify",
                method="POST",
                data={
                    "publicKey": public_key,
                    "signature": signature
                }
            )
            
            access_token = result.get("accessToken")
            
            if not access_token:
                raise Exception("No accessToken in response")
            
            print(f"[AUTH-BROWSER] ✅ JWT token received: {access_token[:50]}...")
            
            return access_token
            
        except Exception as e:
            print(f"[ERROR] Failed to verify challenge: {e}")
            self.metrics["errors"] += 1
            raise
    
    async def get_jwt_token(self, mnemonic: str, user_public_key: str = None) -> str:
        """
        Полный flow аутентификации через browser
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            user_public_key: Публичный ключ (опционально)
        
        Returns:
            JWT access token
        """
        try:
            self.metrics["auth_requests"] += 1
            
            # 1. Получаем публичный ключ
            if not user_public_key:
                user_public_key = self._get_public_key_from_mnemonic(mnemonic)
            
            # 2. Проверяем кэш (экономия времени)
            if user_public_key in self.jwt_cache:
                print(f"[AUTH-BROWSER] ✅ Using cached JWT token for {user_public_key[:20]}...")
                self.metrics["cache_hits"] += 1
                return self.jwt_cache[user_public_key]
            
            self.metrics["cache_misses"] += 1
            
            print(f"[AUTH-BROWSER] Starting authentication flow...")
            print(f"[AUTH-BROWSER] Public key: {user_public_key}")
            
            # 3. Запрашиваем challenge через browser
            challenge_data = await self.get_challenge(user_public_key)
            challenge_hex = challenge_data["challenge"]
            
            # 4. Подписываем challenge (локально, быстро)
            print(f"[AUTH-BROWSER] Signing challenge...")
            signature = self._sign_challenge(challenge_hex, mnemonic)
            print(f"[AUTH-BROWSER] Signature: {signature[:50]}...")
            
            # 5. Верифицируем через browser
            jwt_token = await self.verify_challenge(user_public_key, signature)
            
            # 6. Кэшируем токен
            self.jwt_cache[user_public_key] = jwt_token
            
            print(f"[AUTH-BROWSER] ✅ Authentication successful!")
            
            # Логируем метрики каждые 10 запросов
            if self.metrics["auth_requests"] % 10 == 0:
                self._log_metrics()
            
            return jwt_token
            
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            self.metrics["errors"] += 1
            raise Exception(f"Flashnet authentication failed: {e}")
    
    def _log_metrics(self):
        """Логировать метрики производительности"""
        total = self.metrics["auth_requests"]
        hits = self.metrics["cache_hits"]
        misses = self.metrics["cache_misses"]
        errors = self.metrics["errors"]
        
        cache_hit_rate = (hits / total * 100) if total > 0 else 0
        
        print(f"\n[METRICS] Auth Performance:")
        print(f"  Total requests: {total}")
        print(f"  Cache hits: {hits} ({cache_hit_rate:.1f}%)")
        print(f"  Cache misses: {misses}")
        print(f"  Errors: {errors}")
        print(f"  Active browsers: {len(self.browser_pool.browsers)}\n")
    
    async def initialize(self):
        """Инициализация browser pool"""
        await self.browser_pool.initialize()
    
    async def close(self):
        """Закрыть browser pool"""
        self._log_metrics()
        await self.browser_pool.close()


# Singleton instance
_flashnet_auth_playwright = None

async def get_flashnet_auth_playwright(browser_pool_size: int = 3) -> FlashnetAuthPlaywright:
    """
    Получить singleton instance FlashnetAuthPlaywright
    
    Args:
        browser_pool_size: Размер browser pool
            - 3 browsers: для 5-10k users/day
            - 5 browsers: для 10-20k users/day
            - 10 browsers: для 20-50k users/day
    """
    global _flashnet_auth_playwright
    if _flashnet_auth_playwright is None:
        _flashnet_auth_playwright = FlashnetAuthPlaywright(browser_pool_size=browser_pool_size)
        await _flashnet_auth_playwright.initialize()
    return _flashnet_auth_playwright
