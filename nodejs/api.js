/**
 * Simple Express API for Spark Wallet Operations
 * 
 * Endpoints:
 * POST /api/create-invoice - Create a Lightning invoice
 * POST /api/get-deposit-address - Get a deposit address
 * POST /api/send-transfer - Send a transfer
 */

import express from 'express';
import { createInvoice } from './api/create_lightning_invoice.js';
import { getDepositAddress } from './api/get_deposit_address.js';
import { sendTransfer } from './api/send_transfer_simple.js';

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware to parse JSON bodies
app.use(express.json());

// Health check endpoint
app.get('/', (req, res) => {
    res.json({
        status: 'ok',
        message: 'Spark Wallet API is running',
        endpoints: [
            'POST /api/create-invoice',
            'POST /api/get-deposit-address',
            'POST /api/send-transfer'
        ]
    });
});

/**
 * POST /api/create-invoice
 * Body: { mnemonic, amountSats, memo }
 */
app.post('/api/create-invoice', async (req, res) => {
    try {
        const { mnemonic, amountSats, memo } = req.body;

        // Validate required fields
        if (!mnemonic) {
            return res.status(400).json({
                success: false,
                error: 'Mnemonic is required'
            });
        }

        if (!amountSats || isNaN(amountSats) || amountSats <= 0) {
            return res.status(400).json({
                success: false,
                error: 'Valid amount in sats is required'
            });
        }

        // Create invoice
        const result = await createInvoice(mnemonic, parseInt(amountSats), memo || '');

        if (result && result.success) {
            res.json(result);
        } else {
            res.status(500).json({
                success: false,
                error: 'Failed to create invoice'
            });
        }
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message || 'Internal server error'
        });
    }
});

/**
 * POST /api/get-deposit-address
 * Body: { mnemonic }
 */
app.post('/api/get-deposit-address', async (req, res) => {
    try {
        const { mnemonic } = req.body;

        // Validate required fields
        if (!mnemonic) {
            return res.status(400).json({
                success: false,
                error: 'Mnemonic is required'
            });
        }

        // Get deposit address
        const result = await getDepositAddress(mnemonic);

        if (result && result.success) {
            res.json(result);
        } else {
            res.status(500).json({
                success: false,
                error: 'Failed to get deposit address'
            });
        }
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message || 'Internal server error'
        });
    }
});

/**
 * POST /api/send-transfer
 * Body: { mnemonic, receiverAddress, amountSats }
 */
app.post('/api/send-transfer', async (req, res) => {
    try {
        const { mnemonic, receiverAddress, amountSats } = req.body;

        // Validate required fields
        if (!mnemonic) {
            return res.status(400).json({
                success: false,
                error: 'Mnemonic is required'
            });
        }

        if (!receiverAddress) {
            return res.status(400).json({
                success: false,
                error: 'Receiver address is required'
            });
        }

        if (!amountSats || isNaN(amountSats) || amountSats <= 0) {
            return res.status(400).json({
                success: false,
                error: 'Valid amount in sats is required'
            });
        }

        // Send transfer
        const result = await sendTransfer(mnemonic, receiverAddress, parseInt(amountSats));

        if (result && result.success) {
            res.json(result);
        } else {
            res.status(500).json({
                success: false,
                error: 'Failed to send transfer'
            });
        }
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message || 'Internal server error'
        });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Error:', err);
    res.status(500).json({
        success: false,
        error: 'Internal server error'
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Spark Wallet API server running on http://localhost:${PORT}`);
    console.log(`\nAvailable endpoints:`);
    console.log(`  GET  /                        - Health check`);
    console.log(`  POST /api/create-invoice      - Create Lightning invoice`);
    console.log(`  POST /api/get-deposit-address - Get deposit address`);
    console.log(`  POST /api/send-transfer       - Send transfer`);
});

export default app;

