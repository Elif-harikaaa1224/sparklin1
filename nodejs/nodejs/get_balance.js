/**
 * Get Spark wallet balance (BTC + tokens)
 * Usage: node get_balance.js <mnemonic>
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2];

if (!mnemonic) {
    console.error(JSON.stringify({
        success: false,
        error: 'Mnemonic required as argument'
    }));
    process.exit(1);
}

async function getBalance() {
    try {
        // Initialize wallet
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { network: "MAINNET" }
        });
        
        // Get Spark address
        const address = await wallet.getSparkAddress();
        
        // ✅ СИНХРОНИЗАЦИЯ КОШЕЛЬКА ПЕРЕД ПОЛУЧЕНИЕМ БАЛАНСА!
        await wallet.syncWallet();
        
        // Get balance
        const balance = await wallet.getBalance();
        
        // Convert BigInt to Number for JSON serialization
        // Balance usually has structure like: { sats: BigInt, tokens: {} }
        let balanceSats = 0;
        
        if (balance.sats !== undefined && balance.sats !== null) {
            balanceSats = Number(balance.sats);
        } else if (balance.satoshis !== undefined && balance.satoshis !== null) {
            balanceSats = Number(balance.satoshis);
        } else if (typeof balance === 'bigint') {
            balanceSats = Number(balance);
        } else if (typeof balance === 'number') {
            balanceSats = balance;
        }
        
        // Convert tokens (if any have BigInt values)
        const tokens = {};
        if (balance.tokens && typeof balance.tokens === 'object') {
            for (const [key, value] of Object.entries(balance.tokens)) {
                tokens[key] = typeof value === 'bigint' ? Number(value) : value;
            }
        }
        
        // Return structured response
        console.log(JSON.stringify({
            success: true,
            address: address,
            balance_sats: balanceSats,
            balance_btc: (balanceSats / 100000000).toFixed(8),
            tokens: tokens
        }));
        
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message,
            code: error.code || 'UNKNOWN'
        }));
        process.exit(1);
    }
}

getBalance();

