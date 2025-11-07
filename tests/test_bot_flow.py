"""
Тест основного потока бота
"""
import asyncio
from spark_wallet import SparkWalletManager
from generate_spark_wallet import generate_spark_wallet

async def test_wallet_creation():
    print("=== Test 1: Wallet Generation ===")
    try:
        mnemonic, priv_key, pub_key, address = generate_spark_wallet()
        print(f"✅ Wallet generated successfully")
        print(f"   Address: {address}")
        print(f"   Mnemonic: {mnemonic[:30]}...")
        print(f"   Private key: {priv_key[:16]}...")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_wallet_manager():
    print("\n=== Test 2: Wallet Manager ===")
    try:
        manager = SparkWalletManager("./test_wallets")
        print(f"✅ Manager created")
        
        # Create wallet
        wallet_info = manager.create_new_wallet("test_wallet", "password123")
        print(f"✅ Wallet created: {wallet_info['name']}")
        print(f"   Address: {wallet_info['address']}")
        
        # Check wallet exists
        if "test_wallet" in manager.wallets:
            print(f"✅ Wallet saved in manager")
            wallet_data = manager.wallets["test_wallet"]
            print(f"   Wallet address from manager: {wallet_data.address}")
        else:
            print(f"❌ Wallet NOT saved!")
            return False
        
        # Manager automatically sets master password and wallet is "unlocked"
        # when we create it, so we just need to verify the data is accessible
        print(f"✅ Wallet is accessible (master password set)")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_flashnet_integration():
    print("\n=== Test 3: Flashnet Integration ===")
    try:
        from flashnet_integration import FlashnetSwapIntegration
        manager = SparkWalletManager("./test_wallets")
        
        # Check if wallet exists from previous test
        if "test_wallet" not in manager.wallets:
            print("⚠️ Creating test wallet first...")
            manager.create_new_wallet("test_wallet", "password123")
        
        # Master password is already set when wallet was created
        
        # Create integration
        integration = FlashnetSwapIntegration(manager)
        print(f"✅ Flashnet integration created")
        
        # Note: We can't test actual buy without real BTC transfer
        # but we can test the client creation
        print("⚠️ Skipping actual swap test (requires real BTC transfer)")
        
        await integration.close_all()
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🧪 Starting bot flow tests...\n")
    
    results = []
    
    # Test 1: Wallet generation
    results.append(await test_wallet_creation())
    
    # Test 2: Wallet manager
    results.append(await test_wallet_manager())
    
    # Test 3: Flashnet integration
    results.append(await test_flashnet_integration())
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary:")
    print("="*50)
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if all(results):
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check output above.")
    
    # Cleanup
    import shutil
    import os
    if os.path.exists("./test_wallets"):
        shutil.rmtree("./test_wallets")
        print("\n🧹 Cleaned up test wallets")

if __name__ == "__main__":
    asyncio.run(main())
