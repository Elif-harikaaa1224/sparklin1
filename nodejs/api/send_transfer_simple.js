/**
 * Simple transfer - EXACTLY as it worked in test
 */

import { SparkWallet } from '@buildonspark/spark-sdk';
import { bech32m } from 'bech32';

// const mnemonic = process.argv[2];
// const receiverAddress = process.argv[3];
// const amountSats = parseInt(process.argv[4]);

async function sendTransfer(mnemonic, receiverAddress, amountSats) {
    try {
        // Initialize (minimal setup)
        const { wallet } = await SparkWallet.initialize({ 
            mnemonicOrSeed: mnemonic,
            options: { 
                network: "MAINNET",
                // Отключаем оптимизацию листьев
                skipLeafOptimization: true
            }
        });
        
        // Convert spark1 → sp1
        const decoded = bech32m.decode(receiverAddress, 120);
        const sp1Address = bech32m.encode('sp', decoded.words, 120);
        
        // Send WITHOUT optimization
        const result = await wallet.transfer({
            receiverSparkAddress: sp1Address,
            amountSats: amountSats,
            skipOptimization: true  // Пропускаем оптимизацию
        });
        
        console.log(JSON.stringify({
            success: true,
            txid: result.txid || result.hash || result.id || 'completed',
            amount_sats: amountSats,
            receiver: receiverAddress
        }));
        
        await wallet.cleanup();

        return {
            success: true,
            txid: result.txid || result.hash || result.id || 'completed',
            amount_sats: amountSats,
            receiver: receiverAddress
        };       
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message || String(error)
        }));
        // process.exit(1);
    }
}

// sendTransfer();

export { sendTransfer };
