/**
 * Test Spark SDK connection to SSP
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2] || "arctic sing lucky bomb trophy weasel marriage plug strategy midnight shoulder bag";

async function testConnection() {
    try {
        console.log('🔍 Testing Spark SDK connection...\n');
        
        console.log('1️⃣ Initializing wallet...');
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { 
                network: "MAINNET"
            }
        });
        console.log('✅ Wallet initialized\n');
        
        console.log('2️⃣ Getting Spark address...');
        const address = await wallet.getSparkAddress();
        console.log('✅ Address:', address);
        console.log();
        
        console.log('3️⃣ Testing balance query...');
        const balance = await wallet.getBalance();
        console.log('✅ Balance:', balance);
        console.log();
        
        console.log('4️⃣ Testing Lightning invoice creation...');
        const invoice = await wallet.createLightningInvoice({ 
            amountSats: 100, 
            memo: "Connection test"
        });
        console.log('✅ Invoice created!');
        console.log(JSON.stringify(invoice, null, 2));
        
    } catch (error) {
        console.error('\n❌ Error:', error.message);
        console.error('\nError details:', {
            name: error.name,
            code: error.code,
            cause: error.cause
        });
        
        if (error.message.includes('fetch failed') || error.message.includes('ENOTFOUND')) {
            console.error('\n💡 Network issue detected!');
            console.error('Possible causes:');
            console.error('  1. No internet connection');
            console.error('  2. Firewall blocking Spark API');
            console.error('  3. Spark SSP servers down');
            console.error('  4. Need VPN/proxy for Spark mainnet');
        }
        
        process.exit(1);
    }
}

testConnection();

