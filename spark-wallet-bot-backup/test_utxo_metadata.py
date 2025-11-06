"""
Тест разных UTXO.fun API endpoints для получения метаданных токена
"""

import asyncio
import httpx

async def test_utxo_endpoints():
    token = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate"
    }
    
    endpoints = [
        f"https://utxo.fun/api/pools/{token}",
        f"https://cap.utxo.fun/api/tokens/{token}",
        f"https://utxo.fun/api/tokens/{token}",
        f"https://api.utxo.fun/tokens/{token}",
        f"https://cap.utxo.fun/api/token/{token}",
    ]
    
    print("\n" + "="*80)
    print("🔍 ПОИСК UTXO.FUN API С МЕТАДАННЫМИ")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        for url in endpoints:
            print(f"\n📡 Testing: {url}")
            try:
                response = await client.get(url)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ SUCCESS!")
                    print(f"   Keys: {list(data.keys())[:10]}")
                    
                    # Показываем интересующие поля
                    if "name" in data:
                        print(f"   📝 name: {data['name']}")
                    if "ticker" in data:
                        print(f"   🏷️ ticker: {data['ticker']}")
                    if "priceUsd" in data:
                        print(f"   💰 priceUsd: {data['priceUsd']}")
                    if "marketCapUsd" in data:
                        print(f"   📊 marketCapUsd: {data['marketCapUsd']}")
                    if "iconUrl" in data:
                        print(f"   🖼️ iconUrl: {data['iconUrl']}")
                    
                    print(f"\n   Full data: {data}")
                else:
                    print(f"   ❌ Status {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_utxo_endpoints())
