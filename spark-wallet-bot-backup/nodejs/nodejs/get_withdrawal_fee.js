/**
 * Get withdrawal fee using Spark SDK
 * Usage: node get_withdrawal_fee.js <mnemonic> <btc_address> <amount_sats>
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2];
const btcAddress = process.argv[3];
const amountSats = parseInt(process.argv[4]);

async function getFee() {
    try {
        if (!mnemonic) {
            throw new Error("Mnemonic is required");
        }
        
        if (!btcAddress || (!btcAddress.startsWith('bc1') && !btcAddress.startsWith('bcrt1'))) {
            throw new Error("Valid Bitcoin address is required");
        }
        
        if (isNaN(amountSats) || amountSats <= 0) {
            throw new Error("Valid amount is required");
        }
        
        // Initialize Spark Wallet
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { 
                network: "MAINNET"
            }
        });
        
        // Get withdrawal fee quote
        const feeQuote = await wallet.getWithdrawalFeeQuote({
            onchainAddress: btcAddress,
            amountSats: amountSats
        });
        
        // Extract fees for different speeds
        const fees = {
            slow: (feeQuote.l1BroadcastFeeSlow?.originalValue || 0) + 
                  (feeQuote.userFeeSlow?.originalValue || 0),
            medium: (feeQuote.l1BroadcastFeeMedium?.originalValue || 0) + 
                    (feeQuote.userFeeMedium?.originalValue || 0),
            fast: (feeQuote.l1BroadcastFeeFast?.originalValue || 0) + 
                  (feeQuote.userFeeFast?.originalValue || 0)
        };
        
        console.log(JSON.stringify({
            success: true,
            fees: fees,
            amount_sats: amountSats,
            address: btcAddress,
            quote_id: feeQuote.id || null
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

getFee();

