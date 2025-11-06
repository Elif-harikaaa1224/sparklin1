"""
Получение metadata токена через SPARK SDK
(без цены/ликвидности, только базовая информация)
"""
import asyncio
import httpx
from typing import Optional, Dict, Any


async def get_token_metadata_from_blockchain(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Получить metadata токена из блокчейна SPARK
    Возвращает: symbol, name, decimals, max_supply, is_freezable
    НЕ возвращает: price, liquidity, market_cap (нужен DEX API)
    """
    # TODO: Реализовать через SPARK SDK когда найдем правильный endpoint
    # Пока возвращаем None
    return None


async def scrape_sparkscan_page(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Парсинг HTML страницы Sparkscan для извлечения данных
    (временное решение до появления API)
    """
    try:
        client = httpx.AsyncClient(timeout=15.0)
        url = f"https://sparkscan.io/token/{token_address}"
        
        # Получаем HTML
        response = await client.get(url, follow_redirects=True)
        
        if response.status_code != 200:
            return None
        
        html = response.text
        
        # Простой парсинг: ищем данные в HTML
        # Sparkscan использует Next.js с SSR, поэтому данные могут быть в __NEXT_DATA__
        
        import json
        import re
        
        # Ищем JSON данные в __NEXT_DATA__
        next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        
        if next_data_match:
            try:
                next_data = json.loads(next_data_match.group(1))
                # Извлекаем данные токена
                props = next_data.get("props", {}).get("pageProps", {})
                token_data = props.get("token", {}) or props.get("tokenData", {})
                
                if token_data:
                    return {
                        "symbol": token_data.get("symbol", token_data.get("ticker", "UNKNOWN")),
                        "name": token_data.get("name", "Unknown Token"),
                        "decimals": int(token_data.get("decimals", 8)),
                        "max_supply": token_data.get("maxSupply", token_data.get("max_supply")),
                        "total_supply": token_data.get("totalSupply", token_data.get("total_supply")),
                        "is_freezable": token_data.get("isFreezable", token_data.get("is_freezable", False)),
                        "holders": token_data.get("holders", 0),
                        "price": float(token_data.get("price", 0)) if token_data.get("price") else 0,
                        "liquidity": float(token_data.get("liquidity", 0)) if token_data.get("liquidity") else 0,
                        "market_cap": float(token_data.get("marketCap", token_data.get("market_cap", 0))) if token_data.get("marketCap") or token_data.get("market_cap") else 0,
                    }
            except Exception as e:
                print(f"[DEBUG] Failed to parse __NEXT_DATA__: {e}")
        
        await client.aclose()
        return None
        
    except Exception as e:
        print(f"[ERROR] Sparkscan scraping failed: {e}")
        return None


if __name__ == "__main__":
    async def test():
        token = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
        result = await scrape_sparkscan_page(token)
        print("Scraped data:", result)
    
    asyncio.run(test())
