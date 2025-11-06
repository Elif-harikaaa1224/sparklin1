"""
Тестовый скрипт для проверки доступных SPARK API endpoints
Запуск: py test_spark_api.py
"""

import asyncio
import httpx
from typing import Any, List, Dict

async def test_endpoint(url: str, method: str = "GET", payload: Dict = None) -> Dict:
    """Тестировать endpoint"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            headers = {"Content-Type": "application/json"}
            
            if method == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, json=payload or {}, headers=headers)
            
            return {
                "url": url,
                "status": resp.status_code,
                "success": resp.is_success,
                "headers": dict(resp.headers),
                "body": resp.text[:500] if resp.text else None,
                "error": None
            }
    except Exception as e:
        return {
            "url": url,
            "status": None,
            "success": False,
            "headers": {},
            "body": None,
            "error": str(e)
        }

async def main():
    """Тестировать различные SPARK API endpoints"""
    print("Testing SPARK API endpoints...\n")
    
    base_urls = [
        "https://api.spark.money",
        "https://www.spark.money",
        "https://docs.spark.money"
    ]
    
    endpoints_to_test = [
        # API endpoints
        "/api/v1/tokens/buy",
        "/api/v1/tokens/sell",
        "/api/v1/swap",
        "/api/v1/trade",
        "/api/v1/balance",
        "/api/v1/wallet",
        "/v1/tokens/buy",
        "/v1/tokens/sell",
        "/tokens/buy",
        "/tokens/sell",
        "/api/tokens/buy",
        "/swap",
        "/trade",
        # GraphQL
        "/graphql",
        "/api/graphql",
        # Docs/API info
        "/api",
        "/api/docs",
        "/docs",
        "/api/v1",
        # Root
        "/"
    ]
    
    results = []
    
    for base_url in base_urls:
        for endpoint in endpoints_to_test:
            url = f"{base_url}{endpoint}"
            print(f"Testing: {url}")
            result = await test_endpoint(url)
            results.append(result)
            
            if result["success"]:
                print(f"  [OK] Status: {result['status']}")
                if result["body"]:
                    print(f"  Response preview: {result['body'][:100]}")
            else:
                if result["error"]:
                    print(f"  [ERROR] Error: {result['error'][:100]}")
                else:
                    print(f"  [FAIL] Status: {result['status']}")
            print()
    
    # Summary
    successful = [r for r in results if r["success"]]
    print(f"\n{'='*60}")
    print(f"Summary: {len(successful)}/{len(results)} endpoints responded")
    
    if successful:
        print(f"\n[SUCCESS] Successful endpoints:")
        for r in successful:
            print(f"  {r['url']} - Status: {r['status']}")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(main())

