"""
Test JWT Authentication Flow with Playwright/curl-cffi
"""
import asyncio

# Приоритет: Playwright > curl-cffi > httpx
USE_METHOD = None

try:
    from flashnet_auth_playwright import get_flashnet_auth_playwright
    USE_METHOD = "playwright"
except ImportError:
    pass

if not USE_METHOD:
    try:
        from flashnet_auth_curl import get_flashnet_auth_curl, CURL_CFFI_AVAILABLE
        if CURL_CFFI_AVAILABLE:
            USE_METHOD = "curl-cffi"
    except ImportError:
        pass

if not USE_METHOD:
    from flashnet_auth import get_flashnet_auth
    USE_METHOD = "httpx"


async def test_jwt_auth():
    """Test JWT authentication"""
    
    # Используем тестовый mnemonic (можно заменить на реальный)
    test_mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    
    print("=" * 60)
    print("Testing JWT Authentication")
    print(f"Using: {USE_METHOD.upper()}")
    print("=" * 60)
    
    try:
        # Получаем auth client
        if USE_METHOD == "playwright":
            print("\n[INFO] Using Playwright (real browser) for Cloudflare bypass...")
            auth = await get_flashnet_auth_playwright(browser_pool_size=1)
        elif USE_METHOD == "curl-cffi":
            print("\n[INFO] Using curl-cffi for Cloudflare bypass...")
            auth = get_flashnet_auth_curl()
        else:
            print("\n[INFO] Using standard httpx...")
            auth = get_flashnet_auth()
        
        print("\n[1] Requesting JWT token...")
        
        import time
        start_time = time.time()
        
        jwt_token = await auth.get_jwt_token(mnemonic=test_mnemonic)
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ JWT Token received in {elapsed:.2f} seconds!")
        print(f"Token (first 100 chars): {jwt_token[:100]}...")
        print(f"Token length: {len(jwt_token)} chars")
        
        # Decode JWT to see payload (без верификации)
        try:
            import jwt as pyjwt
            decoded = pyjwt.decode(jwt_token, options={"verify_signature": False})
            print(f"\nJWT Payload:")
            print(f"  Subject: {decoded.get('sub', 'N/A')[:50]}...")
            print(f"  Expires: {decoded.get('exp', 'N/A')}")
            
            if decoded.get('exp'):
                exp_timestamp = decoded['exp']
                time_left = exp_timestamp - time.time()
                hours_left = time_left / 3600
                print(f"  Time left: {hours_left:.2f} hours")
        except Exception as e:
            print(f"  Could not decode JWT: {e}")
        
        # Close client
        if USE_METHOD == "playwright":
            await auth.close()
        elif USE_METHOD == "curl-cffi":
            auth.close()
        else:
            await auth.close()
        
        print("\n" + "=" * 60)
        print(f"✅ JWT Authentication Test PASSED! ({elapsed:.2f}s)")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ JWT Authentication Test FAILED!")
        print(f"Error: {e}")
        
        import traceback
        traceback.print_exc()
        
        return False


if __name__ == "__main__":
    success = asyncio.run(test_jwt_auth())
    exit(0 if success else 1)
