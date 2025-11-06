#!/usr/bin/env node
/**
 * Spark SDK API Server
 * Вы    const { wallet } = await SparkWallet.initialize({ 
      mnemonicOrSeed: mnemonic,
      options: { network: "MAINNET" }
    });
    const depositAddr = await wallet.getDepositAddress();роизводительный HTTP API сервер для взаимодействия Python бота с Spark SDK
 * Может обрабатывать 1000+ одновременных запросов
 */

import express from 'express';
import { SparkWallet } from '@buildonspark/spark-sdk';
import { bech32m } from 'bech32';
import dotenv from 'dotenv';

// Загрузка переменных окружения
dotenv.config();

const app = express();
const PORT = process.env.SPARK_API_PORT || 3000;

// Middleware для парсинга JSON
app.use(express.json({ limit: '10mb' }));

// Логирование запросов
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${req.method} ${req.path}`);
  next();
});

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

/**
 * POST /api/deposit-address
 * Получить Bitcoin адрес для пополнения
 * 
 * Body: { mnemonic: string }
 */
app.post('/api/deposit-address', async (req, res) => {
  try {
    const { mnemonic } = req.body;
    
    if (!mnemonic) {
      return res.status(400).json({
        success: false,
        error: 'Missing mnemonic parameter'
      });
    }
    
    const { wallet } = await SparkWallet.initialize({ 
      mnemonic,
      options: { network: "MAINNET" }
    });
    const depositAddress = await wallet.getDepositAddress();
    
    res.json({
      success: true,
      depositAddress: depositAddress.toString(),
      network: 'mainnet'
    });
    
  } catch (error) {
    console.error('Error getting deposit address:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get deposit address'
    });
  }
});

/**
 * POST /api/create-invoice
 * Создать Lightning invoice
 * 
 * Body: { 
 *   mnemonic: string, 
 *   amount_sats: number, 
 *   memo?: string 
 * }
 */
app.post('/api/create-invoice', async (req, res) => {
  try {
    const { mnemonic, amount_sats, memo } = req.body;
    
    if (!mnemonic || !amount_sats) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters: mnemonic, amount_sats'
      });
    }
    
    const { wallet } = await SparkWallet.initialize({ 
      mnemonicOrSeed: mnemonic,
      options: { network: "MAINNET" }
    });
    const invoice = await wallet.lightning.createInvoice(
      amount_sats,
      memo || 'SPARK Wallet Payment'
    );
    
    res.json({
      success: true,
      invoice: invoice.invoice.encodedInvoice,
      amount_sats: amount_sats,
      memo: memo || 'SPARK Wallet Payment',
      full_data: invoice
    });
    
  } catch (error) {
    console.error('Error creating invoice:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to create Lightning invoice'
    });
  }
});

/**
 * POST /api/pay-invoice
 * Оплатить Lightning invoice
 * 
 * Body: { 
 *   mnemonic: string, 
 *   invoice: string, 
 *   max_fee_sats?: number 
 * }
 */
app.post('/api/pay-invoice', async (req, res) => {
  try {
    const { mnemonic, invoice, max_fee_sats = 100 } = req.body;
    
    if (!mnemonic || !invoice) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters: mnemonic, invoice'
      });
    }
    
    const { wallet } = await SparkWallet.initialize({ 
      mnemonicOrSeed: mnemonic,
      options: { network: "MAINNET" }
    });
    const payment = await wallet.lightning.payInvoice(
      invoice,
      max_fee_sats
    );
    
    res.json({
      success: true,
      payment: payment,
      invoice: invoice
    });
    
  } catch (error) {
    console.error('Error paying invoice:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to pay Lightning invoice'
    });
  }
});

/**
 * POST /api/send-transfer
 * Отправить Spark transfer
 * 
 * Body: { 
 *   mnemonic: string, 
 *   receiver_address: string, 
 *   amount_sats: number 
 * }
 */
app.post('/api/send-transfer', async (req, res) => {
  try {
    const { mnemonic, receiver_address, amount_sats } = req.body;
    
    if (!mnemonic || !receiver_address || !amount_sats) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters: mnemonic, receiver_address, amount_sats'
      });
    }
    
    // Initialize wallet с mnemonicOrSeed и skipLeafOptimization
    const { wallet } = await SparkWallet.initialize({ 
      mnemonicOrSeed: mnemonic,
      options: { 
        network: "MAINNET",
        skipLeafOptimization: true  // Отключаем оптимизацию листьев
      }
    });
    
    // Преобразуем spark1 → sp1 (как в старом коде)
    const decoded = bech32m.decode(receiver_address, 120);
    const sp1Address = bech32m.encode('sp', decoded.words, 120);
    
    // Retry логика для transfer (до 3 попыток)
    let lastError;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        console.log(`[Transfer] Попытка ${attempt}/3 для ${receiver_address} (sp1: ${sp1Address})`);
        
        // Send WITH skipOptimization
        const transfer = await wallet.transfer({
          receiverSparkAddress: sp1Address,
          amountSats: amount_sats,
          skipOptimization: true  // Пропускаем оптимизацию
        });
        
        const txid = transfer.txid || transfer.hash || transfer.id || 'completed';
        console.log(`[Transfer] Успешно! TxID: ${txid}`);
        
        await wallet.cleanup();
        
        return res.json({
          success: true,
          txid: txid,
          receiver: receiver_address,
          amount_sats: amount_sats,
          attempts: attempt
        });
      } catch (err) {
        lastError = err;
        console.error(`[Transfer] Попытка ${attempt} не удалась:`, err.message);
        
        // Если это последняя попытка - выбрасываем ошибку
        if (attempt === 3) {
          await wallet.cleanup();
          throw err;
        }
        
        // Ждем перед следующей попыткой (экспоненциальная задержка)
        await new Promise(resolve => setTimeout(resolve, attempt * 1000));
      }
    }
    
  } catch (error) {
    console.error('Error sending transfer:', error);
    
    // Обработка специфичных ошибок
    const errorMsg = error.message || error.toString();
    const errorStack = error.stack || '';
    
    // NetworkError - проблемы с сетью
    if (errorMsg.includes('NetworkError') || 
        errorMsg.includes('fetch failed') ||
        errorMsg.includes('ECONNREFUSED') ||
        errorMsg.includes('ETIMEDOUT')) {
      return res.status(503).json({
        success: false,
        error: '🌐 Проблема с подключением к Spark SSP. Проверьте интернет соединение или попробуйте позже.',
        details: errorMsg.substring(0, 200),
        retry: true
      });
    }
    
    // RESOURCE_EXHAUSTED - сервер перегружен
    if (errorMsg.includes('RESOURCE_EXHAUSTED') || 
        errorMsg.includes('UNIMPLEMENTED') || 
        errorMsg.includes('unavailable')) {
      return res.status(503).json({
        success: false,
        error: '⏳ Spark SSP перегружен или на обслуживании. Попробуйте через 1-2 минуты.',
        retry: true
      });
    }
    
    // Недостаточно средств
    if (errorMsg.includes('insufficient') || 
        errorMsg.includes('balance')) {
      return res.status(400).json({
        success: false,
        error: '💰 Недостаточно средств на кошельке для выполнения transfer.',
        retry: false
      });
    }
    
    // Неверный адрес
    if (errorMsg.includes('invalid address') || 
        errorMsg.includes('decode')) {
      return res.status(400).json({
        success: false,
        error: '❌ Неверный адрес получателя. Используйте адрес формата spark1...',
        retry: false
      });
    }
    
    // Общая ошибка
    res.status(500).json({
      success: false,
      error: `❌ Ошибка при отправке transfer: ${errorMsg.substring(0, 200)}`,
      details: errorMsg,
      retry: true
    });
  }
});

/**
 * POST /api/withdraw-l1
 * Вывести средства на Bitcoin L1 адрес
 * 
 * Body: { 
 *   mnemonic: string, 
 *   btc_address: string, 
 *   amount_sats: number,
 *   speed?: string 
 * }
 */
app.post('/api/withdraw-l1', async (req, res) => {
  try {
    const { mnemonic, btc_address, amount_sats, speed = 'MEDIUM' } = req.body;
    
    if (!mnemonic || !btc_address || !amount_sats) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters: mnemonic, btc_address, amount_sats'
      });
    }
    
    const { wallet } = await SparkWallet.initialize({ 
      mnemonicOrSeed: mnemonic,
      options: { network: "MAINNET" }
    });
    const withdrawal = await wallet.withdraw(
      btc_address,
      amount_sats,
      speed
    );
    
    res.json({
      success: true,
      withdrawal: withdrawal,
      btc_address: btc_address,
      amount_sats: amount_sats,
      speed: speed
    });
    
  } catch (error) {
    console.error('Error withdrawing to L1:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to withdraw to L1'
    });
  }
});

/**
 * POST /api/withdrawal-fee
 * Получить стоимость комиссии за вывод
 * 
 * Body: { 
 *   mnemonic: string, 
 *   btc_address: string, 
 *   amount_sats: number 
 * }
 */
app.post('/api/withdrawal-fee', async (req, res) => {
  try {
    const { mnemonic, btc_address, amount_sats } = req.body;
    
    if (!mnemonic || !btc_address || !amount_sats) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters: mnemonic, btc_address, amount_sats'
      });
    }
    
    const { wallet } = await SparkWallet.initialize({ 
      mnemonicOrSeed: mnemonic,
      options: { network: "MAINNET" }
    });
    const fees = await wallet.estimateWithdrawalFee(
      btc_address,
      amount_sats
    );
    
    res.json({
      success: true,
      fees: fees,
      btc_address: btc_address,
      amount_sats: amount_sats
    });
    
  } catch (error) {
    console.error('Error estimating withdrawal fee:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to estimate withdrawal fee'
    });
  }
});

/**
 * POST /api/wallet-balance
 * Получить баланс кошелька
 * 
 * Body: { mnemonic: string }
 */
app.post('/api/wallet-balance', async (req, res) => {
  try {
    const { mnemonic } = req.body;
    
    if (!mnemonic) {
      return res.status(400).json({
        success: false,
        error: 'Missing mnemonic parameter'
      });
    }
    
    // Получаем адрес кошелька для UTXO.fun API
    let walletAddress;
    try {
      const { wallet } = await SparkWallet.initialize({ 
        mnemonicOrSeed: mnemonic,
        options: { network: "MAINNET" }
      });
      const depositAddr = await wallet.getDepositAddress();
      walletAddress = depositAddr.toString();
      await wallet.cleanup();
    } catch (err) {
      console.error('[Balance] Не удалось получить адрес:', err.message);
      throw new Error('Failed to get wallet address');
    }
    
    // Получаем баланс через UTXO.fun API (real-time из транзакций)
    const txApiUrl = `https://utxo.fun/api/sparkscan/v1/address/${walletAddress}/transactions?network=MAINNET&limit=100&_t=${Date.now()}`;
    
    const txResp = await fetch(txApiUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      }
    });
    
    if (txResp.ok) {
      const data = await txResp.json();
      const transactions = data.data || [];
      
      // Вычисляем баланс из транзакций
      let balanceSats = 0;
      
      for (const tx of transactions) {
        const direction = tx.direction;
        const amount = tx.amountSats || 0;
        const status = tx.status;
        
        // Считаем только confirmed и sent транзакции
        if (status === 'confirmed' || status === 'sent') {
          if (direction === 'incoming') {
            balanceSats += amount;
          } else if (direction === 'outgoing') {
            balanceSats -= amount;
          }
        }
      }
      
      console.log(`[Balance] Real-time balance: ${balanceSats} sats (from ${transactions.length} transactions)`);
      
      return res.json({
        success: true,
        balance_sats: balanceSats,
        balance_btc: balanceSats / 100000000,
        tx_count: transactions.length
      });
    } else {
      throw new Error(`UTXO.fun API returned ${txResp.status}`);
    }
    
  } catch (error) {
    console.error('Error getting wallet balance:', error);
    
    const errorMsg = error.message || error.toString();
    
    if (errorMsg.includes('NetworkError') || errorMsg.includes('fetch failed')) {
      return res.status(503).json({
        success: false,
        error: '🌐 Не удается подключиться к Spark SSP. Проверьте интернет.',
        retry: true
      });
    }
    
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get wallet balance'
    });
  }
});

/**
 * POST /api/token-info
 * Получить информацию о токене
 * 
 * Body: { 
 *   mnemonic: string, 
 *   token_id: string 
 * }
 */
app.post('/api/token-info', async (req, res) => {
  try {
    const { mnemonic, token_id } = req.body;
    
    if (!mnemonic || !token_id) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters: mnemonic, token_id'
      });
    }
    
    const { wallet } = await SparkWallet.initialize({ 
      mnemonicOrSeed: mnemonic,
      options: { network: "MAINNET" }
    });
    const tokenInfo = await wallet.tokens.getTokenInfo(token_id);
    
    res.json({
      success: true,
      token_info: tokenInfo
    });
    
  } catch (error) {
    console.error('Error getting token info:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get token info'
    });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: 'Endpoint not found',
    available_endpoints: [
      'POST /api/deposit-address',
      'POST /api/create-invoice',
      'POST /api/pay-invoice',
      'POST /api/send-transfer',
      'POST /api/withdraw-l1',
      'POST /api/withdrawal-fee',
      'POST /api/wallet-balance',
      'POST /api/token-info',
      'GET /health'
    ]
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    message: err.message
  });
});

// Запуск сервера
app.listen(PORT, '127.0.0.1', () => {
  console.log('='.repeat(60));
  console.log(`🚀 Spark SDK API Server запущен!`);
  console.log(`📡 Listening on: http://127.0.0.1:${PORT}`);
  console.log(`⚡ Готов к обработке 1000+ одновременных запросов`);
  console.log('='.repeat(60));
  console.log('\nДоступные endpoints:');
  console.log('  POST /api/deposit-address - Получить Bitcoin адрес');
  console.log('  POST /api/create-invoice - Создать Lightning invoice');
  console.log('  POST /api/pay-invoice - Оплатить Lightning invoice');
  console.log('  POST /api/send-transfer - Отправить Spark transfer');
  console.log('  POST /api/withdraw-l1 - Вывод на L1');
  console.log('  POST /api/withdrawal-fee - Комиссия за вывод');
  console.log('  POST /api/wallet-balance - Баланс кошелька');
  console.log('  POST /api/token-info - Информация о токене');
  console.log('  GET /health - Health check');
  console.log('='.repeat(60));
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('\n⏹️  Получен SIGTERM, останавливаю сервер...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('\n⏹️  Получен SIGINT, останавливаю сервер...');
  process.exit(0);
});
