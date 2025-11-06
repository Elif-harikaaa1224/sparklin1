#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spark Withdrawal Manager
Управление выводом средств из Spark wallet
"""

import subprocess
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class SparkWithdrawalManager:
    """Менеджер вывода средств из Spark"""
    
    def __init__(self, nodejs_dir: str = "./nodejs"):
        """
        Инициализация менеджера вывода
        
        Args:
            nodejs_dir: Директория с Node.js скриптами для Spark SDK
        """
        # Используем абсолютный путь!
        if not Path(nodejs_dir).is_absolute():
            # Путь относительно файла spark_withdrawal.py
            self.nodejs_dir = Path(__file__).parent / nodejs_dir
        else:
            self.nodejs_dir = Path(nodejs_dir)
        
        self.nodejs_dir = self.nodejs_dir.resolve()  # Делаем абсолютным
        self.nodejs_dir.mkdir(parents=True, exist_ok=True)
    
    def get_deposit_address(self, mnemonic: str) -> Dict[str, Any]:
        """
        Получить Bitcoin адрес для пополнения с биржи
        
        Args:
            mnemonic: Mnemonic фраза кошелька
        
        Returns:
            Dict с Bitcoin адресом для депозита
        """
        script = self.nodejs_dir / "get_deposit_address.js"
        
        if not script.exists():
            self._create_deposit_address_script()
        
        cmd = [
            "node",
            str(script),
            mnemonic
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            return {
                "success": False,
                "error": f"Failed to get deposit address: {error_msg}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting deposit address: {str(e)}"
            }
    
    def create_lightning_invoice(
        self, 
        mnemonic: str, 
        amount_sats: int,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создать Lightning invoice через Spark SDK (MAINNET!)
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            amount_sats: Сумма в satoshi
            memo: Описание платежа (опционально)
        
        Returns:
            Dict с encoded invoice
        """
        script = self.nodejs_dir / "create_lightning_invoice.js"
        
        cmd = [
            "node",
            str(script),
            mnemonic,
            str(amount_sats),
            memo or "SPARK Wallet Payment"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60  # Увеличен timeout до 60 секунд
            )
            data = json.loads(result.stdout)
            
            if data.get('success'):
                # Извлекаем encoded invoice из ответа Spark SDK
                invoice_data = data.get('invoice', {})
                if isinstance(invoice_data, dict):
                    encoded_invoice = invoice_data.get('invoice', {}).get('encodedInvoice')
                else:
                    encoded_invoice = invoice_data
                
                return {
                    "success": True,
                    "invoice": encoded_invoice,
                    "amount_sats": amount_sats,
                    "memo": memo,
                    "full_data": invoice_data
                }
            else:
                return data
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            return {
                "success": False,
                "error": f"Failed to create Lightning invoice: {error_msg}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating Lightning invoice: {str(e)}"
            }
    
    async def send_spark_transfer(
        self,
        mnemonic: str,
        receiver_address: str,
        amount_sats: int
    ) -> Dict[str, Any]:
        """
        Отправить Spark transfer на указанный адрес (работает с spark1... адресами!)
        
        Args:
            mnemonic: Mnemonic фраза кошелька отправителя
            receiver_address: Spark address получателя (spark1...)
            amount_sats: Сумма в satoshi
        
        Returns:
            Dict с результатом transfer
        """
        script_name = "send_transfer_simple.js"
        
        cmd = [
            "node",
            script_name,  # Только имя файла, т.к. используем cwd
            mnemonic,
            receiver_address,
            str(amount_sats)
        ]
        
        # ИСПОЛЬЗУЕМ ASYNC SUBPROCESS - КАК В get_wallet_balance (который работает!)
        import asyncio
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.nodejs_dir)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result = json.loads(stdout.decode('utf-8'))
                return result
            else:
                error_msg = stderr.decode('utf-8', errors='replace')
                
                # Парсим ошибку
                if "RESOURCE_EXHAUSTED" in error_msg or "UNIMPLEMENTED" in error_msg or "unavailable" in error_msg:
                    return {
                        "success": False,
                        "error": "⏳ Spark SSP перегружен или на обслуживании. Попробуйте через 1-2 минуты."
                    }
                
                return {
                    "success": False,
                    "error": f"Transfer failed: {error_msg[:300]}"
                }
                
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "⏳ Transfer timeout. Попробуйте через 1-2 минуты."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }
    
    def pay_lightning_invoice(
        self,
        mnemonic: str,
        invoice: str,
        max_fee_sats: int = 100
    ) -> Dict[str, Any]:
        """
        Оплатить Lightning invoice
        
        Args:
            mnemonic: Mnemonic фраза кошелька плательщика
            invoice: Закодированный Lightning invoice (lnbc...)
            max_fee_sats: Максимальная комиссия в satoshi
        
        Returns:
            Dict с результатом платежа
        """
        script = self.nodejs_dir / "pay_lightning_invoice.js"
        
        if not script.exists():
            self._create_pay_lightning_script()
        
        cmd = [
            "node",
            str(script),
            mnemonic,
            invoice,
            str(max_fee_sats)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            return {
                "success": False,
                "error": f"Failed to pay Lightning invoice: {error_msg}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error paying Lightning invoice: {str(e)}"
            }
    
    def withdraw_to_l1(
        self,
        mnemonic: str,
        btc_address: str,
        amount_sats: int,
        speed: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """
        Вывести средства на Bitcoin L1 адрес
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            btc_address: Bitcoin адрес получателя (bc1... или bcrt1...)
            amount_sats: Сумма в satoshi
            speed: Скорость транзакции ("SLOW", "MEDIUM", "FAST")
        
        Returns:
            Dict с результатом вывода
        """
        script = self.nodejs_dir / "withdraw_to_l1.js"
        
        if not script.exists():
            self._create_withdraw_script()
        
        cmd = [
            "node",
            str(script),
            mnemonic,
            btc_address,
            str(amount_sats),
            speed
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            return {
                "success": False,
                "error": f"Failed to withdraw to L1: {error_msg}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error withdrawing to L1: {str(e)}"
            }
    
    def get_withdrawal_fee(
        self,
        mnemonic: str,
        btc_address: str,
        amount_sats: int
    ) -> Dict[str, Any]:
        """
        Получить стоимость комиссии за вывод
        
        Args:
            mnemonic: Mnemonic фраза кошелька
            btc_address: Bitcoin адрес получателя
            amount_sats: Сумма в satoshi
        
        Returns:
            Dict с комиссиями для разных скоростей
        """
        script = self.nodejs_dir / "get_withdrawal_fee.js"
        
        if not script.exists():
            self._create_get_fee_script()
        
        cmd = [
            "node",
            str(script),
            mnemonic,
            btc_address,
            str(amount_sats)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            return {
                "success": False,
                "error": f"Failed to get withdrawal fee: {error_msg}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting withdrawal fee: {str(e)}"
            }
    
    def _create_lightning_invoice_script(self):
        """Создать Node.js скрипт для создания Lightning invoice"""
        script_content = """/**
 * Create Lightning Invoice using Spark SDK
 * Usage: node create_lightning_invoice.js <mnemonic> <amount_sats> <memo>
 */

const mnemonic = process.argv[2];
const amountSats = parseInt(process.argv[3]);
const memo = process.argv[4] || "";

async function createInvoice() {
    try {
        // TODO: Реализовать через Spark SDK
        // const { SparkWallet } = await import('@buildonspark/spark-sdk');
        // const wallet = await SparkWallet.initialize({ mnemonic });
        // const invoice = await wallet.createSatsInvoice({ amount: amountSats, memo });
        
        console.log(JSON.stringify({
            success: false,
            error: "Spark SDK integration not yet implemented. Install @buildonspark/spark-sdk"
        }));
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message
        }));
        process.exit(1);
    }
}

createInvoice();
"""
        script_path = self.nodejs_dir / "create_lightning_invoice.js"
        script_path.write_text(script_content)
    
    def _create_pay_lightning_script(self):
        """Создать Node.js скрипт для оплаты Lightning invoice"""
        script_content = """/**
 * Pay Lightning Invoice using Spark SDK
 * Usage: node pay_lightning_invoice.js <mnemonic> <invoice> <max_fee_sats>
 */

const mnemonic = process.argv[2];
const invoice = process.argv[3];
const maxFeeSats = parseInt(process.argv[4]);

async function payInvoice() {
    try {
        // TODO: Реализовать через Spark SDK
        // const { SparkWallet } = await import('@buildonspark/spark-sdk');
        // const wallet = await SparkWallet.initialize({ mnemonic });
        // const result = await wallet.payLightningInvoice({ invoice, maxFeeSats });
        
        console.log(JSON.stringify({
            success: false,
            error: "Spark SDK integration not yet implemented. Install @buildonspark/spark-sdk"
        }));
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message
        }));
        process.exit(1);
    }
}

payInvoice();
"""
        script_path = self.nodejs_dir / "pay_lightning_invoice.js"
        script_path.write_text(script_content)
    
    def _create_withdraw_script(self):
        """Создать Node.js скрипт для вывода на L1"""
        script_content = """/**
 * Withdraw to Bitcoin L1 using Spark SDK
 * Usage: node withdraw_to_l1.js <mnemonic> <btc_address> <amount_sats> <speed>
 */

const mnemonic = process.argv[2];
const btcAddress = process.argv[3];
const amountSats = parseInt(process.argv[4]);
const speed = process.argv[5] || "MEDIUM";

async function withdraw() {
    try {
        // TODO: Реализовать через Spark SDK
        // const { SparkWallet } = await import('@buildonspark/spark-sdk');
        // const wallet = await SparkWallet.initialize({ mnemonic });
        // const result = await wallet.withdraw({
        //     onchainAddress: btcAddress,
        //     amountSats: amountSats,
        //     exitSpeed: speed
        // });
        
        console.log(JSON.stringify({
            success: false,
            error: "Spark SDK integration not yet implemented. Install @buildonspark/spark-sdk"
        }));
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message
        }));
        process.exit(1);
    }
}

withdraw();
"""
        script_path = self.nodejs_dir / "withdraw_to_l1.js"
        script_path.write_text(script_content)
    
    def _create_get_fee_script(self):
        """Создать Node.js скрипт для получения комиссии"""
        script_content = """/**
 * Get withdrawal fee using Spark SDK
 * Usage: node get_withdrawal_fee.js <mnemonic> <btc_address> <amount_sats>
 */

const mnemonic = process.argv[2];
const btcAddress = process.argv[3];
const amountSats = parseInt(process.argv[4]);

async function getFee() {
    try {
        // TODO: Реализовать через Spark SDK
        // const { SparkWallet } = await import('@buildonspark/spark-sdk');
        // const wallet = await SparkWallet.initialize({ mnemonic });
        // const feeQuote = await wallet.getWithdrawalFeeQuote({
        //     onchainAddress: btcAddress,
        //     amountSats: amountSats
        // });
        
        console.log(JSON.stringify({
            success: false,
            error: "Spark SDK integration not yet implemented. Install @buildonspark/spark-sdk"
        }));
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message
        }));
        process.exit(1);
    }
}

getFee();
"""
        script_path = self.nodejs_dir / "get_withdrawal_fee.js"
        script_path.write_text(script_content)
    
    def _create_spark_transfer_script(self):
        """Создать Node.js скрипт для Spark transfer"""
        script_content = """/**
 * Send Spark Transfer using Spark SDK
 * Usage: node send_spark_transfer.js <mnemonic> <receiver_address> <amount_sats>
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2];
const receiverAddress = process.argv[3];
const amountSats = parseInt(process.argv[4]);

async function sendTransfer() {
    try {
        if (!mnemonic) {
            throw new Error("Mnemonic is required");
        }
        
        if (!receiverAddress || !receiverAddress.startsWith('spark1')) {
            throw new Error("Valid Spark address is required (spark1...)");
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
        
        // Send transfer
        const result = await wallet.transfer({
            receiverSparkAddress: receiverAddress,
            amountSats: amountSats
        });
        
        console.log(JSON.stringify({
            success: true,
            transfer_id: result.id || 'N/A',
            amount_sats: amountSats,
            receiver: receiverAddress,
            message: "Transfer completed successfully"
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

sendTransfer();
"""
        script_path = self.nodejs_dir / "send_spark_transfer.js"
        script_path.write_text(script_content)
    
    def _create_deposit_address_script(self):
        """Создать Node.js скрипт для получения deposit address"""
        script_content = """/**
 * Get Bitcoin Deposit Address using Spark SDK
 * Usage: node get_deposit_address.js <mnemonic>
 */

import { SparkWallet } from '@buildonspark/spark-sdk';

const mnemonic = process.argv[2];

async function getDepositAddress() {
    try {
        if (!mnemonic) {
            throw new Error("Mnemonic is required");
        }
        
        // Initialize Spark Wallet
        const { wallet } = await SparkWallet.initialize({ 
            mnemonic,
            options: { 
                network: "MAINNET"
            }
        });
        
        // Get static deposit address (permanent, can be reused)
        const depositAddress = await wallet.getStaticDepositAddress();
        
        console.log(JSON.stringify({
            success: true,
            address: depositAddress,
            type: "static",
            network: "bitcoin",
            message: "Use this address to deposit Bitcoin from exchanges"
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

getDepositAddress();
"""
        script_path = self.nodejs_dir / "get_deposit_address.js"
        script_path.write_text(script_content)

