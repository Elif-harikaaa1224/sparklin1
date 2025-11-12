"""
Flashnet AMM интеграция для покупки/продажи мем-токенов
"""

import httpx
import asyncio
import json
import sys
from typing import Optional, Dict, Any
from datetime import datetime

# ← ДОБАВЛЕНО
from config import FLASHNET_INTEGRATOR_PUBLIC_KEY
from referral_service import get_total_integrator_fee_bps


class FlashnetSwapIntegration:
    def __init__(self, api_base: str = "https://api.amm.flashnet.xyz", timeout: int = 15):
        self.api_base = api_base
        self.timeout = timeout
        self.auth_token = None
        self.token_expiry = None
        self.use_mock = True  # Default to mock mode

    async def authenticate(self):
        """Authenticate with Flashnet AMM"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try to get challenge
                challenge_resp = await client.post(
                    f"{self.api_base}/v1/auth/challenge",
                    json={"publicKey": "mock_public_key"}
                )
                
                if challenge_resp.status_code == 200:
                    self.use_mock = False
                    print("[INFO] Flashnet is accessible, using REAL mode")
                else:
                    self.use_mock = True
                    print(f"[WARN] Flashnet returned {challenge_resp.status_code}, using MOCK mode")
                    
        except Exception as e:
            print(f"[WARN] Flashnet auth check failed: {e}, using MOCK mode")
            self.use_mock = True

    async def buy_token(
        self,
        token_address: str,
        amount_sats: int,
        wallet_name: str,
        slippage: float,
        tip_sats: int = 0,
        user_id: int | None = None,  # ← ДОБАВЛЕНО
    ) -> dict:
        """
        Покупка токена через Flashnet AMM
        """
        print(f"[INFO] Buy token via Flashnet AMM (mode: {'MOCK' if self.use_mock else 'REAL'})...")
        print(f"  Token: {token_address[:20]}...")
        print(f"  Amount: {amount_sats} sats")
        print(f"  Slippage: {slippage}%")
        
        if self.use_mock:
            return self._mock_buy(token_address, amount_sats, slippage)

        try:
            # ← ДОБАВЛЕНО: расчёт комиссий и слиппеджа
            total_fee_bps = get_total_integrator_fee_bps(int(user_id) if user_id is not None else 0)
            max_slippage_bps = int(round(float(slippage) * 100))  # % → bps

            # SIMULATE
            simulate_payload = {
                "poolId": "pool_123",
                "assetInAddress": "BTC",
                "assetOutAddress": token_address,
                "amountIn": int(amount_sats),
                "maxSlippageBps": max_slippage_bps,
                # ← ДОБАВЛЕНО: поля для комиссий
                "integratorPublicKey": FLASHNET_INTEGRATOR_PUBLIC_KEY,
                "totalIntegratorFeeRateBps": int(total_fee_bps),
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                sim_resp = await client.post(
                    f"{self.api_base}/v1/swaps/simulate",
                    json=simulate_payload,
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
                
                if sim_resp.status_code != 200:
                    print(f"[ERROR] Simulate failed: {sim_resp.status_code}")
                    return {"status": "error", "error": f"Simulate failed: {sim_resp.status_code}"}

            sim_data = sim_resp.json()
            print(f"[INFO] Simulate OK: {sim_data.get('amountOut', 0)} tokens out")

            # EXECUTE
            execute_payload = {
                "poolId": "pool_123",
                "assetInAddress": "BTC",
                "assetOutAddress": token_address,
                "amountIn": int(amount_sats),
                "maxSlippageBps": max_slippage_bps,
                "userPublicKey": "user_pubkey_placeholder",
                "assetInSparkTransferId": "transfer_id_placeholder",
                "nonce": "nonce_placeholder",
                "signature": "signature_placeholder",
                # ← ДОБАВЛЕНО: поля для комиссий
                "integratorPublicKey": FLASHNET_INTEGRATOR_PUBLIC_KEY,
                "totalIntegratorFeeRateBps": int(total_fee_bps),
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                exec_resp = await client.post(
                    f"{self.api_base}/v1/swaps/execute",
                    json=execute_payload,
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
                
                if exec_resp.status_code != 200:
                    print(f"[ERROR] Execute failed: {exec_resp.status_code}")
                    return {"status": "error", "error": f"Execute failed: {exec_resp.status_code}"}

            exec_data = exec_resp.json()
            txid = exec_data.get("txId", f"real_{datetime.now().timestamp()}")
            
            print(f"[SUCCESS] Buy executed: {txid}")
            return {
                "status": "success",
                "txid": txid,
                "amount_out": sim_data.get("amountOut", 0),
            }

        except Exception as e:
            print(f"[ERROR] Buy failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    async def sell_token(
        self,
        token_address: str,
        token_amount: int,
        wallet_name: str,
        slippage: float,
        user_id: int | None = None,  # ← ДОБАВЛЕНО
    ) -> dict:
        """
        Продажа токена через Flashnet AMM
        """
        print(f"[INFO] Sell token via Flashnet AMM (mode: {'MOCK' if self.use_mock else 'REAL'})...")
        print(f"  Token: {token_address[:20]}...")
        print(f"  Amount: {token_amount} tokens")
        print(f"  Slippage: {slippage}%")
        
        if self.use_mock:
            return self._mock_sell(token_address, token_amount, slippage)

        try:
            # ← ДОБАВЛЕНО: расчёт комиссий и слиппеджа
            total_fee_bps = get_total_integrator_fee_bps(int(user_id) if user_id is not None else 0)
            max_slippage_bps = int(round(float(slippage) * 100))  # % → bps

            # SIMULATE
            simulate_payload = {
                "poolId": "pool_123",
                "assetInAddress": token_address,
                "assetOutAddress": "BTC",
                "amountIn": int(token_amount),
                "maxSlippageBps": max_slippage_bps,
                # ← ДОБАВЛЕНО: поля для комиссий
                "integratorPublicKey": FLASHNET_INTEGRATOR_PUBLIC_KEY,
                "totalIntegratorFeeRateBps": int(total_fee_bps),
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                sim_resp = await client.post(
                    f"{self.api_base}/v1/swaps/simulate",
                    json=simulate_payload,
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
                
                if sim_resp.status_code != 200:
                    print(f"[ERROR] Simulate failed: {sim_resp.status_code}")
                    return {"status": "error", "error": f"Simulate failed: {sim_resp.status_code}"}

            sim_data = sim_resp.json()
            print(f"[INFO] Simulate OK: {sim_data.get('amountOut', 0)} sats out")

            # EXECUTE
            execute_payload = {
                "poolId": "pool_123",
                "assetInAddress": token_address,
                "assetOutAddress": "BTC",
                "amountIn": int(token_amount),
                "maxSlippageBps": max_slippage_bps,
                "userPublicKey": "user_pubkey_placeholder",
                "assetInSparkTransferId": "transfer_id_placeholder",
                "nonce": "nonce_placeholder",
                "signature": "signature_placeholder",
                # ← ДОБАВЛЕНО: поля для комиссий
                "integratorPublicKey": FLASHNET_INTEGRATOR_PUBLIC_KEY,
                "totalIntegratorFeeRateBps": int(total_fee_bps),
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                exec_resp = await client.post(
                    f"{self.api_base}/v1/swaps/execute",
                    json=execute_payload,
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
                
                if exec_resp.status_code != 200:
                    print(f"[ERROR] Execute failed: {exec_resp.status_code}")
                    return {"status": "error", "error": f"Execute failed: {exec_resp.status_code}"}

            exec_data = exec_resp.json()
            txid = exec_data.get("txId", f"real_{datetime.now().timestamp()}")
            
            print(f"[SUCCESS] Sell executed: {txid}")
            return {
                "status": "success",
                "txid": txid,
                "amount_out": sim_data.get("amountOut", 0),
            }

        except Exception as e:
            print(f"[ERROR] Sell failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    def _mock_buy(self, token_address: str, amount_sats: int, slippage: float) -> dict:
        """Mock покупка для тестирования"""
        token_amount = int(amount_sats / 1000)  # условно
        txid = f"mock_buy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"[MOCK] Bought {token_amount} tokens for {amount_sats} sats")
        return {
            "status": "success",
            "txid": txid,
            "amount_out": token_amount,
            "is_mock": True,
        }

    def _mock_sell(self, token_address: str, token_amount: int, slippage: float) -> dict:
        """Mock продажа для тестирования"""
        sats_out = token_amount * 1000  # условно
        txid = f"mock_sell_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"[MOCK] Sold {token_amount} tokens for {sats_out} sats")
        return {
            "status": "success",
            "txid": txid,
            "amount_out": sats_out,
            "is_mock": True,
        }
