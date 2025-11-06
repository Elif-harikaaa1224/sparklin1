/**
 * Create Lightning Invoice using Spark SDK
 * Usage: node create_lightning_invoice.js <mnemonic> <amount_sats> <memo>
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2];
const amountSats = parseInt(process.argv[3]);
const memo = process.argv[4] || "";

async function createInvoice() {
    try {
        if (!mnemonic) {
            throw new Error("Mnemonic is required");
        }
        
        if (isNaN(amountSats) || amountSats <= 0) {
            throw new Error("Valid amount is required");
        }
        
        // Initialize Spark Wallet on MAINNET (БЕЗ автосинхронизации!)
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { 
                network: "MAINNET",
                // НЕ делаем syncWallet - это ускоряет создание invoice!
            }
        });
        
        // Create Lightning Invoice (быстрый метод, не требует синхронизации)
        const invoice = await wallet.createLightningInvoice({ 
            amountSats: amountSats, 
            memo: memo || undefined
        });
        
        console.log(JSON.stringify({
            success: true,
            invoice: invoice,
            amount: amountSats,
            memo: memo
        }));
        
        // Cleanup wallet connection
        await wallet.cleanup();
        
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message || String(error),
            stack: error.stack
        }));
        process.exit(1);
    }
}

createInvoice();

