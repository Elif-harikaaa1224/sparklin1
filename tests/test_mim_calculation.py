"""
Тест расчёта количества токенов для MIM
"""
import asyncio
from token_info import token_service

async def test_mim_calculation():
    print("=" * 80)
    print("🧪 ТЕСТ РАСЧЁТА ТОКЕНОВ ДЛЯ $MIM")
    print("=" * 80)
    
    # Адрес MIM токена
    mim_address = "btkn1qyouraddresshere"  # Замените на реальный адрес MIM
    btc_amount = 0.001  # 0.001 BTC
    
    print(f"\n1. Получение информации о токене MIM...")
    token_info = await token_service.get_token_info(mim_address)
    
    print(f"\n📊 Информация о токене:")
    print(f"   Symbol: {token_info.get('symbol')}")
    print(f"   Name: {token_info.get('name')}")
    print(f"   Price USD: ${token_info.get('price_usd')}")
    print(f"   Price BTC: {token_info.get('price_btc')} BTC")
    print(f"   Liquidity: ${token_info.get('liquidity_usd')}")
    print(f"   Market Cap: ${token_info.get('market_cap_usd')}")
    
    print(f"\n2. Расчёт количества токенов за {btc_amount} BTC...")
    calc = await token_service.calculate_tokens_for_btc(mim_address, btc_amount)
    
    print(f"\n💰 Результаты расчёта:")
    print(f"   BTC сумма: {calc.get('btc_amount')} BTC")
    print(f"   Цена токена (BTC): {calc.get('token_price_btc')} BTC")
    print(f"   Цена токена (USD): ${calc.get('token_price_usd')}")
    print(f"   Количество токенов: {calc.get('token_amount'):,.2f}")
    print(f"   Форматированное: {calc.get('token_amount_formatted')}")
    
    print("\n" + "=" * 80)
    print("🔍 АНАЛИЗ:")
    print("=" * 80)
    
    if calc.get('token_amount') == 0:
        print("❌ Количество токенов = 0")
        print("   Причина: price_btc = 0 или API недоступен")
        print("\n💡 ПРОБЛЕМА:")
        print("   Когда цена токена неизвестна, расчёт возвращает 0 токенов")
        print("   Но в UI показывается моковое значение ~9,000,000,000")
        print("\n📝 РЕШЕНИЕ:")
        print("   1. Получить реальную цену токена из Luminex/Sparkscan")
        print("   2. Или показывать 'N/A' вместо мокового значения")
        print("   3. Или добавить предупреждение 'Цена неизвестна'")
    else:
        token_amount = calc.get('token_amount')
        print(f"✅ Расчёт успешен: {token_amount:,.2f} токенов")
        
        # Проверка на адекватность
        if token_amount > 1_000_000_000:
            print(f"\n⚠️ ВНИМАНИЕ: Очень большое количество токенов!")
            print(f"   Это может быть:")
            print(f"   1. Токен с очень низкой ценой (микро-копейки)")
            print(f"   2. Моковые данные от API")
            print(f"   3. Ошибка в расчётах")
        
        # Проверка адекватности в USD
        btc_price_usd = 102000  # Примерная цена BTC
        btc_amount_usd = btc_amount * btc_price_usd
        token_price_usd = calc.get('token_price_usd', 0)
        
        if token_price_usd > 0:
            expected_tokens = btc_amount_usd / token_price_usd
            print(f"\n🧮 Проверка через USD:")
            print(f"   {btc_amount} BTC = ${btc_amount_usd:.2f} USD")
            print(f"   Цена токена = ${token_price_usd:.10f} USD")
            print(f"   Ожидаемое количество = {expected_tokens:,.2f} токенов")
            
            if abs(token_amount - expected_tokens) / expected_tokens > 0.01:
                print(f"   ❌ РАСХОЖДЕНИЕ: {token_amount:,.2f} vs {expected_tokens:,.2f}")
            else:
                print(f"   ✅ Расчёт корректен")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_mim_calculation())
