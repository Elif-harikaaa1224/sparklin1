"""
Тест нового API с реальными credentials
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv
import base64
import json

load_dotenv()

CLIENT_ID = os.getenv("LIGHTSPARK_CLIENT_ID")
CLIENT_SECRET = os.getenv("LIGHTSPARK_CLIENT_SECRET")


async def test_lightspark_auth():
    """Тест аутентификации Lightspark API"""
    
    print(f"Client ID: {CLIENT_ID}")
    print(f"Client Secret: {CLIENT_SECRET[:10]}...")
    print("\n" + "="*60)
    
    client = httpx.AsyncClient(timeout=30.0)
    
    # OAuth2 token endpoint
    token_url = "https://api.lightspark.com/oauth2/token"
    
    # Basic Auth
    credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "client_credentials"
    }
    
    try:
        print("\n🔐 Получение access token...")
        response = await client.post(token_url, data=data, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            print(f"✅ Успешно получен access token!")
            print(f"Token: {access_token[:20]}...")
            
            # Теперь попробуем GraphQL запрос
            await test_graphql_query(client, access_token)
            
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Ошибка: {e}")
    
    await client.aclose()


async def test_graphql_query(client, access_token):
    """Тест GraphQL запроса к Lightspark API"""
    
    print("\n" + "="*60)
    print("📊 Тестирование GraphQL запросов...")
    
    graphql_url = "https://api.lightspark.com/graphql/server/2024-01-01"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Запрос 1: Получить информацию об аккаунте
    query1 = """
    query GetAccount {
        current_account {
            id
            name
        }
    }
    """
    
    try:
        print("\n1. Запрос информации об аккаунте...")
        response = await client.post(
            graphql_url,
            json={"query": query1},
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Успешно!")
            print(f"Data: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Ошибка: {response.text[:500]}")
    
    except Exception as e:
        print(f"💥 Ошибка: {e}")
    
    # Запрос 2: Попытка получить данные о токенах (если есть такой endpoint)
    query2 = """
    query GetTokens {
        tokens {
            address
            symbol
            name
        }
    }
    """
    
    try:
        print("\n2. Запрос списка токенов...")
        response = await client.post(
            graphql_url,
            json={"query": query2},
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Успешно!")
            print(f"Data: {json.dumps(data, indent=2)}")
        else:
            error_data = response.json()
            print(f"⚠️ Ошибка GraphQL:")
            print(f"{json.dumps(error_data, indent=2)[:500]}")
    
    except Exception as e:
        print(f"💥 Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(test_lightspark_auth())
