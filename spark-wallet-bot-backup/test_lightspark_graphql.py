"""
Test Lightspark GraphQL Client (Direct API)
"""
from dotenv import load_dotenv
from lightspark_graphql_client import get_lightspark_graphql_client

# Load environment
load_dotenv()


def test_init():
    """Test GraphQL client initialization"""
    print("=== Test 1: GraphQL Client Initialization ===")
    try:
        client = get_lightspark_graphql_client()
        if client:
            print(f"✅ GraphQL client created")
            print(f"   Node ID: {client.node_id}")
            return True
        else:
            print(f"❌ Failed to create client")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_account():
    """Test getting current account"""
    print("\n=== Test 2: Get Current Account ===")
    try:
        client = get_lightspark_graphql_client()
        if not client:
            print("❌ Client not available")
            return False
        
        result = client.get_current_account()
        
        if result.get("status") == "success":
            account = result.get("data", {}).get("current_account", {})
            print(f"✅ Account retrieved:")
            print(f"   Account ID: {account.get('id')}")
            print(f"   Account Name: {account.get('name')}")
            
            nodes = account.get("nodes", [])
            print(f"   Nodes: {len(nodes)}")
            for node in nodes:
                print(f"     - {node.get('display_name')} ({node.get('id')})")
                print(f"       Status: {node.get('status')}")
            
            return True
        else:
            print(f"❌ Failed: {result.get('errors')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_balance():
    """Test getting node balance"""
    print("\n=== Test 3: Get Node Balance ===")
    try:
        client = get_lightspark_graphql_client()
        if not client:
            print("❌ Client not available")
            return False
        
        balance = client.get_node_balance()
        
        if balance.get("status") == "success":
            print(f"✅ Balance retrieved:")
            print(f"   Total: {balance.get('total_balance_sats', 0):,} sats ({balance.get('total_balance_btc', 0):.8f} BTC)")
            print(f"   Available: {balance.get('available_balance_sats', 0):,} sats ({balance.get('available_balance_btc', 0):.8f} BTC)")
            return True
        else:
            print(f"❌ Failed: {balance.get('errors')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_invoice():
    """Test creating Lightning invoice"""
    print("\n=== Test 4: Create Lightning Invoice ===")
    try:
        client = get_lightspark_graphql_client()
        if not client:
            print("❌ Client not available")
            return False
        
        # Create invoice for 1000 sats
        amount_sats = 1000
        amount_msats = amount_sats * 1000
        
        result = client.create_invoice(
            amount_msats=amount_msats,
            memo="Test invoice from SPARK bot (GraphQL)",
            expiry_secs=3600
        )
        
        if result.get("status") == "success":
            print(f"✅ Invoice created:")
            print(f"   Invoice ID: {result['invoice_id']}")
            print(f"   Amount: {result['amount_sats']} sats")
            print(f"   Payment hash: {result.get('payment_hash', 'N/A')}")
            print(f"   Expires at: {result.get('expires_at', 'N/A')}")
            print(f"\n   Payment request:")
            print(f"   {result['encoded_payment_request']}")
            print(f"\n💡 You can test this invoice with:")
            print(f"   lncli payinvoice {result['encoded_payment_request']}")
            return True
        else:
            print(f"❌ Failed: {result.get('errors')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🧪 Testing Lightspark GraphQL Client...\n")
    
    results = []
    
    # Test 1: Initialization
    results.append(test_init())
    
    # Test 2: Get Account
    results.append(test_get_account())
    
    # Test 3: Get Balance  
    results.append(test_get_balance())
    
    # Test 4: Create Invoice
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
        print("\n🎉 All tests passed!")
        print("\n✅ Lightspark GraphQL API is working!")
        print("✅ Ready to integrate into Telegram bot!")
    else:
        print("\n⚠️ Some tests failed. Check output above.")


if __name__ == "__main__":
    main()
