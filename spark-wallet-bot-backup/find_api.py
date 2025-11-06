"""
Поиск реального API endpoint для Sparkscan
"""
import asyncio
import httpx
import json


async def find_sparkscan_api():
    """Исследование API Sparkscan"""
    client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
    
    token = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
    
    # Возможные внутренние API endpoints
    endpoints_to_try = [
        # Next.js API routes
        f"https://sparkscan.io/api/token/{token}",
        f"https://sparkscan.io/api/tokens/{token}",
        f"https://www.sparkscan.io/api/token/{token}",
        
        # Internal API
        f"https://sparkscan.io/api/v1/token/{token}",
        f"https://sparkscan.io/api/v1/tokens/{token}",
        
        # Возможный backend
        f"https://backend.sparkscan.io/token/{token}",
        f"https://backend.sparkscan.io/api/token/{token}",
        
        # GraphQL с разными путями
        "https://sparkscan.io/api/graphql",
        "https://www.sparkscan.io/graphql",
        
        # Vercel/Next.js build data
        f"https://sparkscan.io/_next/data/buildId/token/{token}.json",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": f"https://sparkscan.io/token/{token}",
    }
    
    print("🔍 Поиск работающего API...\n")
    
    for url in endpoints_to_try:
        try:
            print(f"Пробую: {url}")
            response = await client.get(url, headers=headers)
            
            print(f"  ↳ Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ JSON получен!")
                    print(f"  📦 Данные: {json.dumps(data, indent=2)[:500]}...")
                    print("\n" + "="*60 + "\n")
                    return url, data
                except:
                    print(f"  ⚠️ Не JSON (HTML/text)")
            elif response.status_code == 404:
                print(f"  ❌ Not Found")
            elif response.status_code == 403:
                print(f"  🚫 Forbidden")
            else:
                print(f"  ⚠️ Другой статус: {response.status_code}")
                
        except Exception as e:
            print(f"  💥 Ошибка: {str(e)[:100]}")
        
        print()
    
    await client.aclose()
    print("\n❌ Ни один endpoint не работает!")
    return None, None


async def try_graphql_introspection():
    """Попытка GraphQL introspection для поиска схемы"""
    client = httpx.AsyncClient(timeout=15.0)
    
    introspection_query = """
    {
      __schema {
        queryType {
          name
          fields {
            name
            description
          }
        }
      }
    }
    """
    
    graphql_endpoints = [
        "https://sparkscan.io/graphql",
        "https://sparkscan.io/api/graphql",
        "https://www.sparkscan.io/graphql",
        "https://api.sparkscan.io/graphql",
    ]
    
    print("\n🔍 Попытка GraphQL introspection...\n")
    
    for endpoint in graphql_endpoints:
        try:
            print(f"Пробую: {endpoint}")
            response = await client.post(
                endpoint,
                json={"query": introspection_query},
                headers={"Content-Type": "application/json"}
            )
            
            print(f"  ↳ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ GraphQL схема найдена!")
                print(f"  📦 {json.dumps(data, indent=2)[:500]}...")
                return endpoint, data
                
        except Exception as e:
            print(f"  💥 {str(e)[:100]}")
        
        print()
    
    await client.aclose()
    return None, None


async def main():
    print("="*60)
    print("ПОИСК API ENDPOINT ДЛЯ SPARKSCAN")
    print("="*60 + "\n")
    
    # Метод 1: REST API
    rest_url, rest_data = await find_sparkscan_api()
    
    if rest_url:
        print(f"\n✅ НАЙДЕН REST API: {rest_url}")
        return
    
    # Метод 2: GraphQL
    graphql_url, graphql_data = await try_graphql_introspection()
    
    if graphql_url:
        print(f"\n✅ НАЙДЕН GraphQL API: {graphql_url}")
        return
    
    print("\n" + "="*60)
    print("ВЫВОД: Публичный API недоступен")
    print("="*60)
    print("\nВОЗМОЖНЫЕ ПРИЧИНЫ:")
    print("1. API требует аутентификацию (API key)")
    print("2. Данные загружаются через WebSocket")
    print("3. Используется приватный gRPC/protobuf API")
    print("4. Данные встроены в HTML через SSR")
    print("\nРЕКОМЕНДАЦИИ:")
    print("1. Написать в Sparkscan/Flashnet support")
    print("2. Проверить их GitHub/Discord")
    print("3. Использовать Flashnet SDK (@flashnet/sdk)")


if __name__ == "__main__":
    asyncio.run(main())
