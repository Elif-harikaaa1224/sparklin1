/**
 * Withdraw to Bitcoin L1 using Spark SDK
 * Usage: node withdraw_to_l1.js <mnemonic> <btc_address> <amount_sats> <speed>
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2];
const btcAddress = process.argv[3];
const amountSats = parseInt(process.argv[4]);
const speed = process.argv[5] || "MEDIUM";

async function withdraw() {
    try {
        if (!mnemonic) {
            throw new Error("Mnemonic is required");
        }
        
        if (!btcAddress || (!btcAddress.startsWith('bc1') && !btcAddress.startsWith('bcrt1'))) {
            throw new Error("Valid Bitcoin address is required (bc1... or bcrt1...)");
        }
        
        if (isNaN(amountSats) || amountSats <= 0) {
            throw new Error("Valid amount is required");
        }
        
        const validSpeeds = ["SLOW", "MEDIUM", "FAST"];
        if (!validSpeeds.includes(speed)) {
            throw new Error(`Invalid speed. Must be one of: ${validSpeeds.join(', ')}`);
        }
        
        // Initialize Spark Wallet
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { 
                network: "MAINNET"
            }
        });
        
        // Get withdrawal fee quote first
        const feeQuote = await wallet.getWithdrawalFeeQuote({
            onchainAddress: btcAddress,
            amountSats: amountSats
        });
        
        let exitSpeed;
        switch(speed) {
            case "SLOW":
                exitSpeed = "SLOW";
                break;
            case "MEDIUM":
                exitSpeed = "MEDIUM";
                break;
            case "FAST":
                exitSpeed = "FAST";
                break;
            default:
                exitSpeed = "MEDIUM";
        }
        
        // Perform withdrawal
        const result = await wallet.withdraw({
            onchainAddress: btcAddress,
            amountSats: amountSats,
            exitSpeed: exitSpeed,
            feeQuote: feeQuote,
            deductFeeFromWithdrawalAmount: true
        });
        
        console.log(JSON.stringify({
            success: true,
            tx_id: result.txId || result.transactionId || "pending",
            amount_sats: amountSats,
            address: btcAddress,
            speed: speed,
            message: "Withdrawal initiated successfully"
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

withdraw();

