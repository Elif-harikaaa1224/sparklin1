#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прямая проверка транзакций через UTXO.fun API
"""

import asyncio
import httpx
import json
from datetime import datetime


async def check_utxo_transactions():
    """Проверить транзакции напрямую через UTXO.fun API"""
    
    wallet_address = "spark1pgssxzm9juyq9nexjm3tmg30zazwfwwppx823nmmnejdwv404dzrw0c265gvjz"
    
    print("=" * 80)
    print("🔍 ПРЯМАЯ ПРОВЕРКА UTXO.fun API")
    print("=" * 80)
    print(f"\n📍 Адрес: {wallet_address}\n")
    
    # Получаем транзакции с timestamp чтобы избежать кеша
    import time
    timestamp = int(time.time())
    
    url = f"https://utxo.fun/api/sparkscan/v1/address/{wallet_address}/transactions?network=MAINNET&limit=100&_t={timestamp}"
    
    print(f"📡 URL: {url}\n")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
    }
    
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        print("⏳ Отправка запроса...\n")
        resp = await client.get(url)
        
        print(f"📊 Status: {resp.status_code}")
        print(f"📦 Content-Type: {resp.headers.get('content-type')}\n")
        
        if resp.status_code == 200:
            data = resp.json()
            transactions = data.get('data', [])
            
            print("=" * 80)
            print(f"📋 ТРАНЗАКЦИИ (всего: {len(transactions)})")
            print("=" * 80)
            
            balance_sats = 0
            
            for i, tx in enumerate(transactions, 1):
                txid = tx.get('txid', 'N/A')[:16]
                direction = tx.get('direction', 'N/A')
                amount = tx.get('amountSats', 0)
                status = tx.get('status', 'N/A')
                timestamp_ms = tx.get('timestamp', 0)
                
                # Форматируем дату
                if timestamp_ms:
                    dt = datetime.fromtimestamp(timestamp_ms / 1000)
                    date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    date_str = 'N/A'
                
                print(f"\n#{i:2d} TxID: {txid}...")
                print(f"    Direction: {direction:10s} | Amount: {amount:>8,} sats")
                print(f"    Status:    {status:10s} | Date: {date_str}")
                
                # Считаем баланс только из confirmed/sent транзакций
                if status in ['confirmed', 'sent']:
                    if direction == 'incoming':
                        balance_sats += amount
                        print(f"    ✅ Добавлено к балансу: +{amount:,} sats")
                    elif direction == 'outgoing':
                        balance_sats -= amount
                        print(f"    ➖ Вычтено из баланса: -{amount:,} sats")
                else:
                    print(f"    ⏸️  Не учитывается (статус: {status})")
                
                print(f"    💰 Текущий баланс: {balance_sats:,} sats")
            
            print("\n" + "=" * 80)
            print("💰 ИТОГОВЫЙ БАЛАНС")
            print("=" * 80)
            print(f"  SATS: {balance_sats:,}")
            print(f"  BTC:  {balance_sats / 100_000_000:.8f}")
            print(f"  Учтено транзакций: {len([t for t in transactions if t.get('status') in ['confirmed', 'sent']])}/{len(transactions)}")
            print("=" * 80)
            
            # Сохраняем полный JSON для анализа
            with open('utxo_transactions.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print("\n💾 Полный ответ сохранен в utxo_transactions.json")
            
        else:
            print(f"❌ Ошибка: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")


if __name__ == "__main__":
    try:
        asyncio.run(check_utxo_transactions())
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
