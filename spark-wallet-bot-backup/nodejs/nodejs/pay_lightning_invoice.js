/**
 * Pay Lightning Invoice using Spark SDK
 * Usage: node pay_lightning_invoice.js <mnemonic> <invoice> <max_fee_sats>
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2];
const invoice = process.argv[3];
const maxFeeSats = parseInt(process.argv[4]);

async function payInvoice() {
    try {
        if (!mnemonic) {
            throw new Error("Mnemonic is required");
        }
        
        if (!invoice || !invoice.startsWith('ln')) {
            throw new Error("Valid Lightning invoice is required");
        }
        
        if (isNaN(maxFeeSats) || maxFeeSats < 0) {
            throw new Error("Valid max fee is required");
        }
        
        // Initialize Spark Wallet
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { 
                network: "MAINNET"
            }
        });
        
        // Pay Lightning Invoice
        const result = await wallet.payLightningInvoice({ 
            invoice: invoice,
            maxFeeSats: maxFeeSats,
            preferSpark: false  // false = use Lightning Network, true = use Spark network
        });
        
        console.log(JSON.stringify({
            success: true,
            amount_sats: result.amountSats || 0,
            fee_sats: result.feeSats || 0,
            payment_hash: result.paymentHash || null,
            message: "Payment successful"
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

payInvoice();

