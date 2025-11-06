"""
Test creating an invoice - try different approaches
"""
import os
from dotenv import load_dotenv
from lightspark import LightsparkSyncClient, InvoiceType

# Load environment variables
load_dotenv()

def test_create_invoice():
    """Test creating invoice with different methods"""
    print("🧪 Testing Invoice Creation...\n")
    
    # Get credentials
    api_token = os.getenv('LIGHTSPARK_API_TOKEN')
    client_secret = os.getenv('LIGHTSPARK_CLIENT_SECRET')
    node_id_full = os.getenv('LIGHTSPARK_NODE_ID')
    
    # Initialize client
    client = LightsparkSyncClient(
        api_token_client_id=api_token,
        api_token_client_secret=client_secret
    )
    
    print("=== Test 1: Check what methods are available ===")
    invoice_methods = [m for m in dir(client) if 'invoice' in m.lower()]
    print(f"Available invoice methods: {invoice_methods}\n")
    
    print("=== Test 2: Try create_invoice with full node ID ===")
    try:
        invoice = client.create_invoice(
            node_id=node_id_full,
            amount_msats=1000000,
            memo="Test invoice",
            invoice_type=InvoiceType.STANDARD
        )
        print(f"✅ Success!")
        print(f"   Invoice ID: {invoice.id}")
        print(f"   Payment request: {invoice.data.encoded_payment_request if hasattr(invoice, 'data') else 'N/A'}")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:200]}\n")
    
    print("=== Test 3: Try with just UUID ===")
    try:
        node_uuid = node_id_full.split(':')[1] if ':' in node_id_full else node_id_full
        invoice = client.create_invoice(
            node_id=node_uuid,
            amount_msats=1000000,
            memo="Test invoice",
            invoice_type=InvoiceType.STANDARD
        )
        print(f"✅ Success!")
        print(f"   Invoice ID: {invoice.id}")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:200]}\n")
    
    print("=== Test 4: Check if we need to create/fund a node first ===")
    print("Looking for node creation methods...")
    node_methods = [m for m in dir(client) if 'node' in m.lower()]
    print(f"Available node methods: {node_methods}\n")
    
    print("=== Test 5: Try to create a node wallet address ===")
    try:
        # This might auto-create a node if one doesn't exist
        result = client.create_node_wallet_address(node_id=node_id_full)
        print(f"✅ Created wallet address: {result}")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:200]}\n")

if __name__ == "__main__":
    test_create_invoice()
