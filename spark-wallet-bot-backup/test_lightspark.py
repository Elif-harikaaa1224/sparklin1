"""
Test Lightspark Client Integration
"""
import asyncio
from dotenv import load_dotenv
from lightspark_client import get_lightspark_manager

# Load environment variables
load_dotenv()


def test_lightspark_init():
    """Test Lightspark manager initialization"""
    print("=== Test 1: Lightspark Initialization ===")
    try:
        manager = get_lightspark_manager()
        if manager:
            print(f"✅ Lightspark manager created")
            print(f"   Node ID: {manager.node_id}")
            return True
        else:
            print(f"❌ Failed to create manager")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_balance():
    """Test getting node balance"""
    print("\n=== Test 2: Get Balance ===")
    try:
        manager = get_lightspark_manager()
        if not manager:
            print("❌ Manager not available")
            return False
        
        balance = manager.get_balance()
        
        if balance.get("status") == "success":
            print(f"✅ Balance retrieved:")
            print(f"   Total: {balance.get('total_balance_sats', 0)} sats")
            print(f"   Available: {balance.get('available_balance_sats', 0)} sats")
            return True
        else:
            print(f"❌ Failed to get balance: {balance.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_invoice():
    """Test creating Lightning invoice"""
    print("\n=== Test 3: Create Invoice ===")
    try:
        manager = get_lightspark_manager()
        if not manager:
            print("❌ Manager not available")
            return False
        
        # Create invoice for 1000 sats
        amount_sats = 1000
        amount_msats = amount_sats * 1000
        
        result = manager.create_invoice(
            amount_msats=amount_msats,
            memo="Test invoice from SPARK bot",
            expiry_secs=3600
        )
        
        if result.get("status") == "success":
            print(f"✅ Invoice created:")
            print(f"   Invoice ID: {result['invoice_id']}")
            print(f"   Amount: {result['amount_sats']} sats")
            print(f"   Payment request: {result['encoded_payment_request'][:60]}...")
            print(f"\n💡 You can test this invoice with:")
            print(f"   lncli payinvoice {result['encoded_payment_request']}")
            return True
        else:
            print(f"❌ Failed to create invoice: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🧪 Testing Lightspark Integration...\n")
    
    results = []
    
    # Test 1: Initialization
    results.append(test_lightspark_init())
    
    # Test 2: Get Balance
    results.append(test_get_balance())
    
    # Test 3: Create Invoice
    results.append(test_create_invoice())
    
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
        print("\n🎉 All Lightspark tests passed!")
        print("\n✅ Lightspark SDK is ready to use!")
    else:
        print("\n⚠️ Some tests failed. Check output above.")


if __name__ == "__main__":
    main()
