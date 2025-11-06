"""
Тест получения данных о токене через API
"""
import asyncio
from token_info import token_service


async def test_token_info():
    # Реальный адрес токена для теста
    test_token = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
    
    print(f"Тестирование токена: {test_token}")
    print("=" * 60)
    
    # Получаем информацию
    info = await token_service.get_token_info(test_token)
    
    print("\nПолученные данные:")
    print(f"  Address: {info['address']}")
    print(f"  Symbol: {info['symbol']}")
    print(f"  Name: {info['name']}")
    print(f"  Decimals: {info['decimals']}")
    print(f"  Price USD: {info['price_usd']}")
    print(f"  Price BTC: {info['price_btc']}")
    print(f"  Liquidity: {info['liquidity_usd']}")
    print(f"  Market Cap: {info['market_cap_usd']}")
    print(f"  Volume 24h: {info['volume_24h']}")
    
    if "_error" in info:
        print(f"\n⚠️ Предупреждение: {info['_error']}")
    
    print("\nФорматированный вывод:")
    print(f"  💵 Price: {token_service.format_price(info['price_usd'])}")
    print(f"  💧 LIQ: {token_service.format_liquidity(info['liquidity_usd'])}")
    print(f"  📊 MC: {token_service.format_market_cap(info['market_cap_usd'])}")
    
    await token_service.close()


if __name__ == "__main__":
    asyncio.run(test_token_info())
