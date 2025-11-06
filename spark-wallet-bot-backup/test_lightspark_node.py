"""
Test script to find and verify the Lightspark node
"""
import os
from dotenv import load_dotenv
from lightspark import LightsparkSyncClient

# Load environment variables
load_dotenv()

def test_find_node():
    """Test finding the node and getting its details"""
    print("🔍 Testing Lightspark Node Discovery...\n")
    
    # Get credentials
    api_token = os.getenv('LIGHTSPARK_API_TOKEN')
    client_secret = os.getenv('LIGHTSPARK_CLIENT_SECRET')
    node_id = os.getenv('LIGHTSPARK_NODE_ID')
    
    print(f"API Token: {api_token[:16]}...")
    print(f"Client Secret: {client_secret[:20]}...")
    print(f"Node ID (full): {node_id}\n")
    
    # Initialize client
    client = LightsparkSyncClient(
        api_token_client_id=api_token,
        api_token_client_secret=client_secret
    )
    
    print("=== Test 1: Get Current Account ===")
    try:
        account = client.get_current_account()
        print(f"✅ Account retrieved: {account.id}")
        print(f"   Name: {account.name if hasattr(account, 'name') else 'N/A'}")
        print(f"   Type: {type(account).__name__}\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
    
    print("=== Test 2: List All Nodes ===")
    try:
        # Try to get nodes from account
        account = client.get_current_account()
        
        # The account should have a nodes connection
        if hasattr(account, 'get_nodes'):
            nodes_connection = account.get_nodes(client, first=10)
            nodes = nodes_connection.entities if hasattr(nodes_connection, 'entities') else []
            
            print(f"✅ Found {len(nodes)} nodes:")
            for node in nodes:
                print(f"   - ID: {node.id}")
                print(f"     Type: {type(node).__name__}")
                if hasattr(node, 'display_name'):
                    print(f"     Name: {node.display_name}")
                if hasattr(node, 'public_key'):
                    print(f"     Public Key: {node.public_key}")
                print()
        else:
            print("❌ Account doesn't have get_nodes method")
            print(f"   Available methods: {[m for m in dir(account) if not m.startswith('_')]}")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
        import traceback
        traceback.print_exc()
    
    print("\n=== Test 3: Try Different Node ID Formats ===")
    # Try different formats of the node ID
    node_id_formats = [
        node_id,  # Full format with prefix
        node_id.split(':')[1] if ':' in node_id else node_id,  # Just UUID part
        "019a3943-2da4-f96b-0000-dbb517ec4b6c",  # Plain UUID
    ]
    
    from lightspark.objects.LightsparkNode import LightsparkNode
    
    for test_id in node_id_formats:
        print(f"Testing ID: {test_id}")
        try:
            # Try to get the node entity
            node = client.get_entity(test_id, LightsparkNode)
            print(f"✅ Success with format: {test_id}")
            print(f"   Node ID: {node.id}")
            print(f"   Node display name: {node.display_name if hasattr(node, 'display_name') else 'N/A'}")
            print(f"   Node type: {type(node).__name__}")
            print(f"   Node status: {node.status if hasattr(node, 'status') else 'N/A'}\n")
            
            # This is the correct ID format to use!
            print(f"✅✅✅ USE THIS NODE ID: {test_id}")
            break
        except Exception as e:
            print(f"❌ Failed: {str(e)[:150]}\n")

if __name__ == "__main__":
    test_find_node()
