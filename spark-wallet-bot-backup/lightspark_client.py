"""
Lightspark Client for Lightning Network Integration
Provides Lightning Network functionality via Lightspark API
"""
import os
from typing import Dict, Any, Optional
from lightspark import LightsparkSyncClient, InvoiceType
from lightspark.objects.CurrencyAmount import CurrencyAmount


class LightsparkManager:
    """Manager for Lightspark Lightning Network operations"""
    
    def __init__(self, api_token: str, node_id: str):
        """
        Initialize Lightspark client
        
        Args:
            api_token: Lightspark API token
            node_id: Lightning node ID
        """
        self.api_token = api_token
        self.node_id = node_id
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Lightspark SDK client"""
        try:
            # Load client secret from environment
            client_secret = os.getenv('LIGHTSPARK_CLIENT_SECRET')
            if not client_secret:
                raise ValueError("LIGHTSPARK_CLIENT_SECRET not found in environment")
            
            # API Token authentication with proper client secret
            self.client = LightsparkSyncClient(
                api_token_client_id=self.api_token,
                api_token_client_secret=client_secret
            )
            print(f"[LIGHTSPARK] Client initialized with token: {self.api_token[:16]}...")
            print(f"[LIGHTSPARK] Using client secret: {client_secret[:20]}...")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Lightspark client: {e}")
            raise
    
    def create_invoice(
        self,
        amount_msats: int,
        memo: Optional[str] = None,
        expiry_secs: int = 3600
    ) -> Dict[str, Any]:
        """
        Create Lightning invoice for receiving payment
        
        Args:
            amount_msats: Amount in millisatoshis
            memo: Optional invoice memo/description
            expiry_secs: Invoice expiry time in seconds (default 1 hour)
        
        Returns:
            Dictionary with invoice data including encoded_payment_request
        """
        try:
            print(f"[LIGHTSPARK] Creating invoice for {amount_msats} msats...")
            
            # Create invoice using Lightspark SDK
            invoice = self.client.create_invoice(
                node_id=self.node_id,
                amount_msats=amount_msats,
                memo=memo or "SPARK Bot deposit",
                invoice_type=InvoiceType.STANDARD,
                expiry_secs=expiry_secs
            )
            
            result = {
                "status": "success",
                "invoice_id": invoice.id,
                "encoded_payment_request": invoice.data.encoded_payment_request,
                "amount_msats": amount_msats,
                "amount_sats": amount_msats // 1000,
                "amount_btc": amount_msats / 100_000_000_000,
                "memo": memo,
                "expires_at": invoice.data.expires_at,
                "created_at": invoice.created_at
            }
            
            print(f"[LIGHTSPARK] ✅ Invoice created: {invoice.id}")
            print(f"[LIGHTSPARK]    Payment request: {invoice.data.encoded_payment_request[:50]}...")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to create invoice: {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "message": f"Failed to create invoice: {error_msg}"
            }
    
    def pay_invoice(
        self,
        encoded_invoice: str,
        amount_msats: Optional[int] = None,
        timeout_secs: int = 60,
        max_fee_msats: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Pay Lightning invoice
        
        Args:
            encoded_invoice: BOLT11 encoded invoice (lnbc...)
            amount_msats: Amount for zero-amount invoices
            timeout_secs: Payment timeout
            max_fee_msats: Maximum routing fee to pay
        
        Returns:
            Dictionary with payment result
        """
        try:
            print(f"[LIGHTSPARK] Paying invoice: {encoded_invoice[:50]}...")
            
            # Estimate fees first
            if max_fee_msats is None:
                fee_estimate = self.client.lightning_fee_estimate_for_invoice(
                    node_id=self.node_id,
                    encoded_payment_request=encoded_invoice,
                    amount_msats=amount_msats
                )
                max_fee_msats = fee_estimate.fee_estimate.fee_estimate_max.value
                print(f"[LIGHTSPARK] Estimated max fee: {max_fee_msats} msats")
            
            # Pay invoice
            payment = self.client.pay_invoice(
                node_id=self.node_id,
                encoded_invoice=encoded_invoice,
                timeout_secs=timeout_secs,
                maximum_fees_msats=max_fee_msats,
                amount_msats=amount_msats
            )
            
            result = {
                "status": "success",
                "payment_id": payment.id,
                "amount_msats": payment.amount.value if hasattr(payment, 'amount') else amount_msats,
                "fees_msats": payment.fees.value if hasattr(payment, 'fees') else 0,
                "payment_hash": payment.payment_request_hash if hasattr(payment, 'payment_request_hash') else None,
                "created_at": payment.created_at
            }
            
            print(f"[LIGHTSPARK] ✅ Payment successful: {payment.id}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to pay invoice: {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "message": f"Failed to pay invoice: {error_msg}"
            }
    
    def get_balance(self) -> Dict[str, Any]:
        """
        Get node balance
        
        Returns:
            Dictionary with balance information
        """
        try:
            # Get node info
            node = self.client.get_entity(self.node_id)
            
            if not node:
                return {
                    "status": "error",
                    "error": "Node not found"
                }
            
            # Get balances
            balances = node.balances if hasattr(node, 'balances') else None
            
            if not balances:
                return {
                    "status": "success",
                    "total_balance_msats": 0,
                    "available_balance_msats": 0,
                    "total_balance_sats": 0,
                    "available_balance_sats": 0
                }
            
            total_msats = balances.owned_balance.value if hasattr(balances, 'owned_balance') else 0
            available_msats = balances.available_to_send_balance.value if hasattr(balances, 'available_to_send_balance') else 0
            
            return {
                "status": "success",
                "total_balance_msats": total_msats,
                "available_balance_msats": available_msats,
                "total_balance_sats": total_msats // 1000,
                "available_balance_sats": available_msats // 1000,
                "total_balance_btc": total_msats / 100_000_000_000,
                "available_balance_btc": available_msats / 100_000_000_000
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to get balance: {error_msg}")
            return {
                "status": "error",
                "error": error_msg
            }
    
    def estimate_fee(
        self,
        encoded_invoice: str,
        amount_msats: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Estimate routing fee for paying an invoice
        
        Args:
            encoded_invoice: BOLT11 encoded invoice
            amount_msats: Amount for zero-amount invoices
        
        Returns:
            Dictionary with fee estimates
        """
        try:
            fee_estimate = self.client.lightning_fee_estimate_for_invoice(
                node_id=self.node_id,
                encoded_payment_request=encoded_invoice,
                amount_msats=amount_msats
            )
            
            return {
                "status": "success",
                "fee_estimate_min_msats": fee_estimate.fee_estimate.fee_estimate_min.value,
                "fee_estimate_max_msats": fee_estimate.fee_estimate.fee_estimate_max.value,
                "fee_estimate_min_sats": fee_estimate.fee_estimate.fee_estimate_min.value // 1000,
                "fee_estimate_max_sats": fee_estimate.fee_estimate.fee_estimate_max.value // 1000
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to estimate fee: {error_msg}")
            return {
                "status": "error",
                "error": error_msg
            }


# Singleton instance
_lightspark_manager: Optional[LightsparkManager] = None


def get_lightspark_manager() -> Optional[LightsparkManager]:
    """Get or create Lightspark manager instance"""
    global _lightspark_manager
    
    if _lightspark_manager is None:
        api_token = os.getenv("LIGHTSPARK_API_TOKEN")
        node_id = os.getenv("LIGHTSPARK_NODE_ID")
        
        if not api_token or not node_id:
            print("[WARNING] Lightspark credentials not found in .env")
            return None
        
        try:
            _lightspark_manager = LightsparkManager(api_token, node_id)
            print("[LIGHTSPARK] Manager initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to create Lightspark manager: {e}")
            return None
    
    return _lightspark_manager
