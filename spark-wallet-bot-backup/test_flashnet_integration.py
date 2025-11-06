"""
Test Flashnet AMM Integration
Тестирование новой системы покупки/продажи через Flashnet AMM
"""
import asyncio
from spark_wallet import SparkWalletManager


async def test_flashnet_integration():
    """Тест новой Flashnet интеграции"""
    
    print("=" * 70)
    print("[TEST] TESTING FLASHNET AMM INTEGRATION")
    print("=" * 70)
    print()
    
    # Инициализация wallet manager
    print("[1/5] Initializing Wallet Manager...")
    wallet_manager = SparkWalletManager()
    wallet_manager.set_master_password("test_password_123")
    
    # Создание тестового кошелька
    print("[2/5] Creating test wallet...")
    wallet_result = wallet_manager.create_new_wallet("test_wallet")
    print(f"[OK] Wallet created: {wallet_result['address'][:20]}...")
    print(f"   Mnemonic: {wallet_result['mnemonic'][:50]}...")
    print()
    
    # Пример токена (реальный адрес из Flashnet)
    token_address = "66471063147ab9f53515bf18d1cea9a8ad166840ba9de93d46018d7007426e17"
    
    print("[3/5] Getting token price...")
    try:
        from flashnet_integration import FlashnetSwapIntegration
        
        integration = FlashnetSwapIntegration(wallet_manager)
        
        # Получить цену токена
        price = await integration.get_token_price("test_wallet", token_address)
        if price:
            print(f"[OK] Token price: {price:.10f} BTC")
            print(f"   Price in sats: {price * 100_000_000:.2f} sats")
        else:
            print(f"[WARN] Could not get token price (pool may not exist)")
        print()
        
        # Получить котировку для покупки
        print("[4/5] Getting buy quote...")
        amount_btc_sats = 100000  # 0.001 BTC
        quote = await integration.get_quote(
            wallet_name="test_wallet",
            token_address=token_address,
            amount_btc_sats=amount_btc_sats,
            is_buy=True
        )
        
        if quote:
            print(f"[OK] Quote received:")
            print(f"   Input: {quote['amount_in']} sats ({quote['amount_in'] / 100_000_000:.8f} BTC)")
            print(f"   Output: {quote['amount_out']} tokens")
            print(f"   Price: {quote['execution_price']}")
            print(f"   Price Impact: {quote['price_impact']}")
            print(f"   Fee: {quote['fee_paid']} sats")
            if quote['warning']:
                print(f"   [WARN] Warning: {quote['warning']}")
        else:
            print(f"[WARN] Could not get quote (pool may not exist)")
        print()
        
        # Симуляция покупки (БЕЗ реального выполнения)
        print("[5/5] Testing buy method (simulation only)...")
        print(f"[WARN] NOTE: This will FAIL because we don't have real BTC deposited")
        print(f"[WARN] In production, you need to:")
        print(f"   1. Deposit BTC to Spark")
        print(f"   2. Get Spark transfer ID")
        print(f"   3. Use that transfer ID for the swap")
        print()
        
        try:
            buy_result = await integration.buy_token(
                wallet_name="test_wallet",
                token_address=token_address,
                amount_btc_sats=amount_btc_sats,
                slippage_pct=1.0  # 1% slippage
            )
            
            print(f"Result: {buy_result['status']}")
            print(f"Message: {buy_result.get('message', 'No message')}")
            
            if buy_result['status'] == 'success':
                print(f"[OK] SUCCESS!")
                print(f"   TxID: {buy_result.get('txid', 'N/A')}")
                print(f"   Tokens received: {buy_result.get('tokens_received', 0)}")
            else:
                print(f"[WARN] Expected failure: {buy_result.get('error', 'No error')}")
        
        except Exception as e:
            print(f"[WARN] Expected error: {str(e)}")
        
        print()
        await integration.close_all()
    
    except Exception as e:
        print(f"[ERROR] Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)
    print("[DONE] TEST COMPLETED")
    print("=" * 70)
    print()
    print("[INFO] NEXT STEPS:")
    print("   1. Fund wallet with BTC on Spark network")
    print("   2. Create Spark transfer to deposit BTC")
    print("   3. Use real transfer ID for actual swap")
    print("   4. Verify transaction on Spark explorer")
    print()


async def test_authentication():
    """Тест только аутентификации"""
    print("=" * 70)
    print("[AUTH] TESTING AUTHENTICATION ONLY")
    print("=" * 70)
    print()
    
    # Инициализация
    wallet_manager = SparkWalletManager()
    wallet_manager.set_master_password("test_password_123")
    
    # Создать кошелек
    wallet_result = wallet_manager.create_new_wallet("auth_test_wallet")
    print(f"Wallet: {wallet_result['address'][:20]}...")
    print()
    
    # Получить private key
    from generate_spark_wallet import derive_private_key_from_mnemonic
    
    wallet_data = wallet_manager.wallets.get("auth_test_wallet")
    private_key_hex = derive_private_key_from_mnemonic(wallet_data.mnemonic, account=1)
    
    print(f"Private Key: {private_key_hex[:20]}...")
    print(f"Public Key: {wallet_data.public_key[:20]}...")
    print()
    
    # Тест аутентификации
    from flashnet_amm_client import FlashnetAMMClient
    
    print("Testing authentication...")
    async with FlashnetAMMClient(private_key_hex) as client:
        try:
            jwt_token = await client.authenticate()
            print(f"[OK] Authentication successful!")
            print(f"   JWT Token: {jwt_token[:50]}...")
            print(f"   Token length: {len(jwt_token)} chars")
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    print("\n" * 2)
    
    # Выбор теста
    print("Select test:")
    print("1. Full integration test (recommended)")
    print("2. Authentication only")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(test_authentication())
    else:
        asyncio.run(test_flashnet_integration())
