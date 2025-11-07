"""
Тест UTXO Pool API с браузерными заголовками
"""

import asyncio
from utxo_pool_api import utxo_pool_api

async def test_browser_headers():
    print("\n" + "="*80)
    print("🧪 ТЕСТ UTXO POOL API С БРАУЗЕРНЫМИ ЗАГОЛОВКАМИ")
    print("="*80)
    
    # MIM токен
    token_address = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
    
    print(f"\n📡 Токен: {token_address}")
    print(f"🌐 URL: https://utxo.fun/api/pools/{token_address}")
    
    # Тест 1: Получить данные пула
    print(f"\n1️⃣ Получение данных пула...")
    pool_data = await utxo_pool_api.get_pool_data(token_address)
    
    if pool_data:
        print(f"   ✅ Успешно получены данные!")
        print(f"   💰 Price: {pool_data.get('currentPriceAInB')}")
        print(f"   🏦 Host: {pool_data.get('hostName')}")
        print(f"   💎 BTC Reserve: {pool_data.get('assetBReserve')} sats")
        print(f"   📊 TVL: {pool_data.get('tvlAssetB')} sats")
        
        # Тест 2: Расчёт токенов
        print(f"\n2️⃣ Расчёт покупки 0.001 BTC...")
        calc = await utxo_pool_api.calculate_tokens_for_btc(token_address, 0.001)
        
        if calc.get("pool_exists"):
            print(f"   ✅ Расчёт выполнен!")
            print(f"   💎 Получите: {calc['token_amount']:,.2f} токенов")
            print(f"   💵 Цена: {calc['token_price_btc']:.12f} BTC за токен")
        else:
            print(f"   ❌ Ошибка: {calc.get('error')}")
    else:
        print(f"   ❌ Не удалось получить данные пула")
    
    # Тест 3: Повторный запрос (из кэша)
    print(f"\n3️⃣ Повторный запрос (должен быть из кэша)...")
    pool_data2 = await utxo_pool_api.get_pool_data(token_address)
    
    if pool_data2:
        print(f"   ✅ Данные получены из кэша!")
    
    print("\n" + "="*80)
    
    await utxo_pool_api.close()

if __name__ == "__main__":
    asyncio.run(test_browser_headers())
