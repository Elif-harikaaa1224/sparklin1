"""
Попытка получить данные через GraphQL с правильными headers
"""
import asyncio
import httpx
import json


async def try_graphql_with_token():
    """Попытка GraphQL запроса с разными вариантами аутентификации"""
    
    token_address = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
    
    # GraphQL query для получения token info
    query = """
    query GetToken($address: String!) {
        token(address: $address) {
            address
            symbol
            name
            decimals
            price
            liquidity
            marketCap
            volume24h
        }
    }
    """
    
    # Альтернативные варианты query
    queries = [
        # Вариант 1: С параметром
        {
            "query": query,
            "variables": {"address": token_address}
        },
        # Вариант 2: Прямой запрос
        {
            "query": f"""
            {{
                token(address: "{token_address}") {{
                    address
                    symbol
                    name
                    decimals
                    price
                    liquidity
                    marketCap
                }}
            }}
            """
        },
        # Вариант 3: Поиск всех токенов
        {
            "query": """
            {
                tokens(first: 10) {
                    address
                    symbol
                    name
                    price
                }
            }
            """
        }
    ]
    
    # Разные варианты headers
    header_variants = [
        # Browser headers
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://sparkscan.io",
            "Referer": f"https://sparkscan.io/token/{token_address}",
        },
        # API headers
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        # С возможным API key (пустой - попробуем)
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": "",
            "Authorization": "Bearer ",
        }
    ]
    
    endpoint = "https://api.sparkscan.io/graphql"
    
    client = httpx.AsyncClient(timeout=15.0)
    
    print(f"🔍 Попытка GraphQL запросов к {endpoint}\n")
    
    for i, headers in enumerate(header_variants, 1):
        print(f"\n{'='*60}")
        print(f"ВАРИАНТ HEADERS #{i}")
        print(f"{'='*60}")
        
        for j, query_data in enumerate(queries, 1):
            print(f"\nQuery #{j}:")
            
            try:
                response = await client.post(
                    endpoint,
                    json=query_data,
                    headers=headers
                )
                
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ SUCCESS!")
                    print(f"  📦 Data: {json.dumps(data, indent=2)}")
                    await client.aclose()
                    return data
                    
                elif response.status_code == 403:
                    print(f"  🚫 Forbidden - нужна аутентификация")
                    
                elif response.status_code == 400:
                    try:
                        error = response.json()
                        print(f"  ❌ Bad Request: {error}")
                    except:
                        print(f"  ❌ Bad Request: {response.text[:200]}")
                        
                else:
                    print(f"  ⚠️ Status {response.status_code}")
                    print(f"  Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"  💥 Error: {e}")
    
    await client.aclose()
    print("\n\n❌ Не удалось получить данные через GraphQL")
    return None


if __name__ == "__main__":
    asyncio.run(try_graphql_with_token())
