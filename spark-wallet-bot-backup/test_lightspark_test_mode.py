"""
Test if Test Mode invoices work without a node
"""
import os
from dotenv import load_dotenv
from lightspark import LightsparkSyncClient

# Load environment variables
load_dotenv()

def test_test_mode():
    """Test creating invoice in test mode"""
    print("🧪 Testing Lightspark Test Mode...\n")
    
    # Get credentials
    api_token = os.getenv('LIGHTSPARK_API_TOKEN')
    client_secret = os.getenv('LIGHTSPARK_CLIENT_SECRET')
    
    # Initialize client
    client = LightsparkSyncClient(
        api_token_client_id=api_token,
        api_token_client_secret=client_secret
    )
    
    print("=== Test 1: Create Test Mode Invoice ===")
    try:
        # Test mode invoice - doesn't require a real node
        invoice = client.create_test_mode_invoice(
            local_node_id="test_node",  # Fake node ID for testing
            amount_msats=1000000,
            memo="Test mode invoice"
        )
        print(f"✅ Success! Test mode works!")
        print(f"   Invoice ID: {invoice.id if hasattr(invoice, 'id') else invoice}")
        print(f"   Type: {type(invoice)}")
        
        # Print all attributes
        if hasattr(invoice, '__dict__'):
            print(f"\n   Invoice details:")
            for key, value in invoice.__dict__.items():
                if not key.startswith('_'):
                    print(f"     {key}: {value}")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Test 2: Check Test Mode Payment ===")
    try:
        # See if we can pay test invoices
        print("Test mode payment methods:")
        pay_methods = [m for m in dir(client) if 'pay' in m.lower() and 'test' in m.lower()]
        print(f"   {pay_methods}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_test_mode()
