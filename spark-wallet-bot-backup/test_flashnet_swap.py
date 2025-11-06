"""
Тест реальных покупок через Flashnet AMM
"""
import asyncio
from flashnet_swap import flashnet_swap_client


async def test_buy_flow():
    """Тест процесса покупки"""
    print("="*70)
    print("FLASHNET AMM BUY TEST")
    print("="*70 + "\n")
    
    # Тестовые параметры
    token_address = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
    amount_sats = 100_000  # 0.001 BTC
    slippage_pct = 10.0  # 10%
    
    print(f"Token: {token_address[:30]}...")
    print(f"Amount: {amount_sats} sats ({amount_sats / 100_000_000:.8f} BTC)")
    print(f"Slippage: {slippage_pct}%\n")
    
    try:
        # 1. Найти пул
        print("Step 1: Finding pool...")
        pool_id = await flashnet_swap_client.find_pool_for_token(token_address)
        
        if pool_id:
            print(f"✅ Pool found: {pool_id}\n")
        else:
            print("❌ Pool not found\n")
            return
        
        # 2. Симуляция
        print("Step 2: Simulating swap...")
        simulation = await flashnet_swap_client.simulate_swap(
            pool_id=pool_id,
            asset_in_address=flashnet_swap_client.BTC_PUBKEY,
            asset_out_address=token_address,
            amount_in=amount_sats,
        )
        
        if simulation:
            print(f"✅ Simulation successful")
            print(f"  Expected output: {simulation['amount_out']} tokens")
            print(f"  Price impact: {simulation['price_impact_pct']:.2f}%\n")
        else:
            print("❌ Simulation failed\n")
            return
        
        # 3. Выполнение (закомментировано для безопасности)
        print("Step 3: Execute swap (DISABLED IN TEST)")
        print("⚠️ To enable real swaps, uncomment execution code in test script\n")
        
        # Раскомментируйте для реального выполнения:
        # result = await flashnet_swap_client.buy_token_with_btc(
        #     token_address=token_address,
        #     amount_btc_sats=amount_sats,
        #     slippage_pct=slippage_pct,
        # )
        # 
        # if result['success']:
        #     print(f"✅ Buy successful!")
        #     print(f"  Tokens received: {result['tokens_received']}")
        #     print(f"  TxID: {result['txid']}")
        # else:
        #     print(f"❌ Buy failed")
        
        print("\n" + "="*70)
        print("TEST COMPLETED (SIMULATION ONLY)")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


async def test_sell_flow():
    """Тест процесса продажи"""
    print("\n" + "="*70)
    print("FLASHNET AMM SELL TEST")
    print("="*70 + "\n")
    
    # Тестовые параметры
    token_address = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
    amount_tokens = 1000  # 1000 tokens
    slippage_pct = 10.0  # 10%
    
    print(f"Token: {token_address[:30]}...")
    print(f"Amount: {amount_tokens} tokens")
    print(f"Slippage: {slippage_pct}%\n")
    
    try:
        # 1. Найти пул
        print("Step 1: Finding pool...")
        pool_id = await flashnet_swap_client.find_pool_for_token(token_address)
        
        if pool_id:
            print(f"✅ Pool found: {pool_id}\n")
        else:
            print("❌ Pool not found\n")
            return
        
        # 2. Симуляция
        print("Step 2: Simulating swap...")
        simulation = await flashnet_swap_client.simulate_swap(
            pool_id=pool_id,
            asset_in_address=token_address,
            asset_out_address=flashnet_swap_client.BTC_PUBKEY,
            amount_in=amount_tokens,
        )
        
        if simulation:
            print(f"✅ Simulation successful")
            print(f"  Expected BTC: {simulation['amount_out']} sats")
            print(f"  Price impact: {simulation['price_impact_pct']:.2f}%\n")
        else:
            print("❌ Simulation failed\n")
            return
        
        # 3. Выполнение (закомментировано для безопасности)
        print("Step 3: Execute swap (DISABLED IN TEST)")
        print("⚠️ To enable real swaps, uncomment execution code in test script\n")
        
        print("\n" + "="*70)
        print("TEST COMPLETED (SIMULATION ONLY)")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Главная функция"""
    print("\n🚀 Flashnet AMM Integration Test\n")
    
    # Тест покупки
    await test_buy_flow()
    
    # Тест продажи
    await test_sell_flow()
    
    print("\n✅ All tests completed")


if __name__ == "__main__":
    asyncio.run(main())
