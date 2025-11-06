"""
Тест API для получения баланса кошелька
"""
import asyncio
import httpx
import json

async def test_balance_api():
    # Тестовые адреса
    wallets = [
        "spark1pgss8avx2fjx0epmnyk2d8ar5ke4jjpk0wh9e4xkz9a8tu28cdh9kw00ghypjq",
        "spark1pgssxzm9juyq9nexjm3tmg30zazwfwwppx823nmmnejdwv404dzrw0c265gvjz"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
    }
    
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        for wallet_address in wallets:
            print(f"\n{'='*80}")
            print(f"Testing wallet: {wallet_address[:30]}...")
            print(f"{'='*80}")
            
            url = f"https://utxo.fun/api/sparkscan/v1/address/{wallet_address}?network=MAINNET"
            print(f"URL: {url}\n")
            
            try:
                resp = await client.get(url)
                print(f"Status: {resp.status_code}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Выводим весь JSON красиво
                    print(f"\nFull API Response:")
                    print(json.dumps(data, indent=2))
                    
                    # Извлекаем важные поля
                    print(f"\n{'='*80}")
                    print("KEY FIELDS:")
                    print(f"{'='*80}")
                    
                    btc_soft_balance = data.get('btcSoftBalanceSats', 'NOT FOUND')
                    total_value_usd = data.get('totalValueUsd', 'NOT FOUND')
                    
                    print(f"btcSoftBalanceSats: {btc_soft_balance}")
                    print(f"totalValueUsd: {total_value_usd}")
                    
                else:
                    print(f"Error: HTTP {resp.status_code}")
                    print(f"Response: {resp.text}")
                    
            except Exception as e:
                print(f"Exception: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_balance_api())
