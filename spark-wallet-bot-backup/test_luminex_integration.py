"""
Тест Luminex Scraper
"""
import asyncio
from token_info import token_service


async def test_luminex_integration():
    """Тест интеграции Luminex scraper в token_info"""
    print("="*70)
    print("LUMINEX INTEGRATION TEST")
    print("="*70 + "\n")
    
    # Тестовый токен MIM
    test_address = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
    
    print(f"Fetching token info for: {test_address[:30]}...\n")
    
    try:
        token_info = await token_service.get_token_info(test_address)
        
        print("✅ Token data received!\n")
        print(f"Symbol: {token_info.get('symbol', 'N/A')}")
        print(f"Name: {token_info.get('name', 'N/A')}")
        print(f"Price USD: ${token_info.get('price_usd', 0)}")
        print(f"Market Cap: ${token_info.get('market_cap_usd', 0):,.2f}")
        print(f"Volume 24h: ${token_info.get('volume_24h', 0):,.2f}")
        print(f"Holders: {token_info.get('holders', 0)}")
        print(f"Source: {token_info.get('source', 'unknown')}")
        
        if 'luminex_url' in token_info:
            print(f"\nLuminex URL: {token_info['luminex_url']}")
        
        print("\n" + "="*70)
        print("TEST PASSED ✅")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await token_service.close()
        print("\n✓ Cleanup completed")


if __name__ == "__main__":
    asyncio.run(test_luminex_integration())
