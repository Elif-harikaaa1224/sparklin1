/**
 * Get Bitcoin Deposit Address using Spark SDK
 * Usage: node get_deposit_address.js <mnemonic>
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2];

async function getDepositAddress() {
    try {
        if (!mnemonic) {
            throw new Error("Mnemonic is required");
        }
        
        // Initialize Spark Wallet
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { 
                network: "MAINNET"
            }
        });
        
        // Get static deposit address (permanent, can be reused)
        const depositAddress = await wallet.getStaticDepositAddress();
        
        console.log(JSON.stringify({
            success: true,
            address: depositAddress,
            type: "static",
            network: "bitcoin",
            message: "Use this address to deposit Bitcoin from exchanges"
        }));
        
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message || String(error),
            stack: error.stack
        }));
        process.exit(1);
    }
}

getDepositAddress();
