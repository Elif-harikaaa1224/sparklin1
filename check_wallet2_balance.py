#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка реального баланса кошелька через UTXO.fun API (как в бекапе)
"""

import asyncio
import sys
from spark_wallet import SparkWalletManager


async def check_wallet_balance():
    """Проверить баланс кошелька W2 через UTXO.fun"""
    
    # Данные из wallets.json
    wallet_address = "spark1pgssxzm9juyq9nexjm3tmg30zazwfwwppx823nmmnejdwv404dzrw0c265gvjz"
    
    print("=" * 70)
    print("🔍 ПРОВЕРКА РЕАЛЬНОГО БАЛАНСА КОШЕЛЬКА")
    print("=" * 70)
    print(f"\n📍 Адрес: {wallet_address}")
    
    # Инициализируем wallet manager
    wallet_manager = SparkWalletManager()
    
    # Получаем баланс через UTXO.fun API (прямой вызов, как в бекапе)
    print("\n1️⃣ Получение баланса из UTXO.fun API...")
    result = await wallet_manager.get_wallet_balance(wallet_address)
    
    if result.get("status") == "success":
        balance_sats = result.get("balance_sats", 0)
        balance_btc = float(result.get("balance_btc", 0))
        tx_count = result.get("tx_count", 0)
        
        # Конвертируем в USD (примерная цена BTC)
        btc_price_usd = 101600  # Примерная цена
        balance_usd = balance_btc * btc_price_usd
        
        print("\n" + "=" * 70)
        print("💰 РЕАЛЬНЫЙ БАЛАНС (из UTXO.fun транзакций):")
        print("=" * 70)
        print(f"  SATS: {balance_sats:,}")
        print(f"  BTC:  {balance_btc:.8f}")
        print(f"  USD:  ${balance_usd:.2f}")
        print(f"  Транзакций: {tx_count}")
        print("=" * 70)
        
        if balance_sats == 6094:
            print("\n⚠️  ВНИМАНИЕ: Баланс совпадает со старым значением (6,094 sats)")
            print("Это может означать что:")
            print("  • Transfer еще не подтвержден в блокчейне")
            print("  • Нужно подождать 1-2 минуты для подтверждения")
        elif balance_sats < 6094:
            print(f"\n✅ Баланс уменьшился! Было 6,094 → Стало {balance_sats:,}")
            print(f"   Разница: {6094 - balance_sats} sats")
            print("Transfer успешно выполнен!")
        else:
            print(f"\n📈 Баланс увеличился! Было 6,094 → Стало {balance_sats:,}")
            print("Получены новые средства")
    
    else:
        error = result.get("error", "Unknown error")
        status = result.get("status", "unknown")
        
        print(f"\n❌ Ошибка получения баланса:")
        print(f"   Статус: {status}")
        print(f"   Ошибка: {error}")
        
        if status == "rate_limit":
            print("\n🔧 Решение: Подождите 1 минуту (rate limit)")
        else:
            print("\n🔧 Решение: Проверьте интернет соединение")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(check_wallet_balance())
    except KeyboardInterrupt:
        print("\n\n⏹️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
