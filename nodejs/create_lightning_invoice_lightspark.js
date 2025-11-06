/**
 * Create Lightning Invoice using Lightspark SDK
 * Usage: node create_lightning_invoice_lightspark.js <amount_sats> <memo>
 */

import { LightsparkClient, ClientJsonWebTokenAuthProvider } from '@lightsparkdev/lightspark-sdk';
import dotenv from 'dotenv';

dotenv.config({ path: '../.env' });

const amountSats = parseInt(process.argv[2]);
const memo = process.argv[3] || "SPARK Wallet Payment";

async function createInvoice() {
    try {
        if (isNaN(amountSats) || amountSats <= 0) {
            throw new Error("Valid amount is required");
        }
        
        const clientId = process.env.LIGHTSPARK_API_TOKEN_CLIENT_ID;
        const clientSecret = process.env.LIGHTSPARK_API_TOKEN_CLIENT_SECRET;
        
        if (!clientId || !clientSecret) {
            throw new Error(
                "Missing Lightspark API credentials. Add to .env:\n" +
                "LIGHTSPARK_API_TOKEN_CLIENT_ID=your_client_id\n" +
                "LIGHTSPARK_API_TOKEN_CLIENT_SECRET=your_client_secret"
            );
        }
        
        // Initialize Lightspark Client
        const authProvider = new ClientJsonWebTokenAuthProvider(clientId, clientSecret);
        const client = new LightsparkClient(authProvider);
        
        // Create Lightning Invoice
        // Amount in msats (1 sat = 1000 msats)
        const amountMsats = amountSats * 1000;
        
        const invoice = await client.createInvoice({
            amountMsats: amountMsats,
            memo: memo,
            expirySeconds: 3600  // 1 hour
        });
        
        console.log(JSON.stringify({
            success: true,
            invoice: invoice.data.encodedPaymentRequest,
            amount_sats: amountSats,
            amount_msats: amountMsats,
            memo: memo,
            payment_hash: invoice.data.paymentHash,
            expires_at: invoice.data.expiresAt,
            message: "Lightning invoice created successfully"
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

createInvoice();

