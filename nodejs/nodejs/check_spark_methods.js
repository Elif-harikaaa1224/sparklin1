/**
 * Check available methods on Spark Wallet
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2] || "arctic sing lucky bomb trophy weasel marriage plug strategy midnight shoulder bag";

async function checkMethods() {
    try {
        console.log('🔍 Checking Spark Wallet methods...\n');
        
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { network: "MAINNET" }
        });
        
        console.log('✅ Wallet initialized on MAINNET\n');
        console.log('📋 Available methods:\n');
        
        // Get all methods
        const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(wallet))
            .filter(name => typeof wallet[name] === 'function')
            .filter(name => !name.startsWith('_'));
        
        methods.forEach(method => {
            console.log(`  - wallet.${method}()`);
        });
        
        // Check for Lightning-related methods
        console.log('\n⚡ Lightning-related methods:');
        const lightningMethods = methods.filter(m => 
            m.toLowerCase().includes('invoice') || 
            m.toLowerCase().includes('lightning') ||
            m.toLowerCase().includes('ln') ||
            m.toLowerCase().includes('pay')
        );
        
        if (lightningMethods.length > 0) {
            lightningMethods.forEach(m => console.log(`  ✅ wallet.${m}()`));
        } else {
            console.log('  ❌ No obvious Lightning methods found');
        }
        
        console.log('\n📖 Try checking Spark SDK documentation for correct methods');
        
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

checkMethods();

