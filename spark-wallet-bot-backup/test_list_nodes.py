"""
Test script to list all nodes in the account
"""
import os
from dotenv import load_dotenv
from lightspark import LightsparkSyncClient

# Load environment variables
load_dotenv()

def test_list_nodes():
    """Test listing all nodes"""
    print("🔍 Testing Node Listing...\n")
    
    # Get credentials
    api_token = os.getenv('LIGHTSPARK_API_TOKEN')
    client_secret = os.getenv('LIGHTSPARK_CLIENT_SECRET')
    
    # Initialize client
    client = LightsparkSyncClient(
        api_token_client_id=api_token,
        api_token_client_secret=client_secret
    )
    
    print("=== Getting Account and Nodes ===")
    try:
        account = client.get_current_account()
        print(f"✅ Account: {account.id}")
        print(f"   Name: {account.name}\n")
        
        # Try to get nodes without passing client
        print("Attempting to get nodes...")
        nodes_connection = account.get_nodes(first=10)
        
        print(f"Nodes connection type: {type(nodes_connection)}")
        print(f"Nodes connection attributes: {dir(nodes_connection)}\n")
        
        if hasattr(nodes_connection, 'entities'):
            nodes = nodes_connection.entities
            print(f"✅ Found {len(nodes)} nodes:\n")
            
            for idx, node in enumerate(nodes, 1):
                print(f"Node {idx}:")
                print(f"  ID: {node.id if node else 'None'}")
                if node:
                    print(f"  Type: {type(node).__name__}")
                    if hasattr(node, 'display_name'):
                        print(f"  Display Name: {node.display_name}")
                    if hasattr(node, 'status'):
                        print(f"  Status: {node.status}")
                    if hasattr(node, 'public_key'):
                        print(f"  Public Key: {node.public_key}")
                print()
        elif hasattr(nodes_connection, 'count'):
            print(f"Total nodes count: {nodes_connection.count}")
        else:
            print(f"Unknown connection structure: {nodes_connection}")
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_list_nodes()
