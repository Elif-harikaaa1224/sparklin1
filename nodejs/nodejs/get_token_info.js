/**
 * Get token info using Flashnet SDK
 * Usage: node get_token_info.js <token_address>
 */

const tokenAddress = process.argv[2];

if (!tokenAddress) {
    console.error(JSON.stringify({ error: "Token address required" }));
    process.exit(1);
}

async function getTokenInfo() {
    try {
        // Попытка 1: Использовать Flashnet SDK
        // const { FlashnetClient } = await import('@flashnet/sdk');
        // const client = new FlashnetClient();
        // const tokenData = await client.getTokenInfo(tokenAddress);
        
        // Пока SDK не установлен, возвращаем заглушку
        const result = {
            address: tokenAddress,
            symbol: "N/A",
            name: "N/A",
            price_usd: 0,
            liquidity_usd: 0,
            market_cap_usd: 0,
            _error: "Flashnet SDK not installed yet"
        };
        
        console.log(JSON.stringify(result));
        
    } catch (error) {
        console.error(JSON.stringify({ 
            error: error.message,
            address: tokenAddress 
        }));
        process.exit(1);
    }
}

getTokenInfo();
