"""
Lightspark GraphQL Client - Direct API Integration
Использует прямые GraphQL запросы вместо SDK
"""
import os
import requests
from typing import Dict, Any, Optional
import json


class LightsparkGraphQLClient:
    """Клиент для прямой работы с Lightspark GraphQL API"""
    
    def __init__(self, api_token: str, node_id: str):
        """
        Инициализация GraphQL клиента
        
        Args:
            api_token: Lightspark API token
            node_id: Lightning node ID
        """
        self.api_token = api_token
        self.node_id = node_id
        self.api_url = "https://api.lightspark.com/graphql/server/2023-04-04"
        
        # API Token authentication - try different header formats
        # Format 1: api-token:<token>
        self.headers = {
            "Authorization": f"api-token:{api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        print(f"[LIGHTSPARK] GraphQL client initialized")
        print(f"[LIGHTSPARK] API URL: {self.api_url}")
        print(f"[LIGHTSPARK] Node ID: {node_id}")
        print(f"[LIGHTSPARK] Auth header: api-token:{api_token[:16]}...")
    
    def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Выполнить GraphQL запрос
        
        Args:
            query: GraphQL query string
            variables: Query variables
        
        Returns:
            Response data
        """
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Проверяем статус
            if response.status_code != 200:
                print(f"[ERROR] HTTP {response.status_code}: {response.text}")
                return {
                    "errors": [{
                        "message": f"HTTP {response.status_code}",
                        "details": response.text
                    }]
                }
            
            result = response.json()
            
            # Проверяем GraphQL ошибки
            if "errors" in result:
                print(f"[ERROR] GraphQL errors: {result['errors']}")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Request failed: {e}")
            return {
                "errors": [{
                    "message": str(e)
                }]
            }
    
    def get_current_account(self) -> Dict[str, Any]:
        """Получить информацию о текущем аккаунте"""
        query = """
        query GetCurrentAccount {
          current_account {
            id
            name
            nodes {
              id
              display_name
              public_key
              color
              status
              balances {
                owned_balance { value }
                available_to_send_balance { value }
                available_to_withdraw_balance { value }
              }
            }
          }
        }
        """
        
        result = self._execute_query(query)
        
        if "errors" in result:
            return {
                "status": "error",
                "errors": result["errors"]
            }
        
        return {
            "status": "success",
            "data": result.get("data", {})
        }
    
    def get_node_balance(self) -> Dict[str, Any]:
        """Получить баланс ноды"""
        query = """
        query GetNode($node_id: ID!) {
          entity(id: $node_id) {
            ... on LightsparkNodeWithOSK {
              id
              display_name
              balances {
                owned_balance { value }
                available_to_send_balance { value }
                available_to_withdraw_balance { value }
              }
            }
          }
        }
        """
        
        variables = {"node_id": self.node_id}
        result = self._execute_query(query, variables)
        
        if "errors" in result:
            return {
                "status": "error",
                "errors": result["errors"]
            }
        
        entity = result.get("data", {}).get("entity", {})
        balances = entity.get("balances", {})
        
        if not balances:
            return {
                "status": "success",
                "total_balance_msats": 0,
                "available_balance_msats": 0
            }
        
        owned = balances.get("owned_balance", {}).get("value", 0)
        available = balances.get("available_to_send_balance", {}).get("value", 0)
        
        return {
            "status": "success",
            "total_balance_msats": owned,
            "available_balance_msats": available,
            "total_balance_sats": owned // 1000,
            "available_balance_sats": available // 1000,
            "total_balance_btc": owned / 100_000_000_000,
            "available_balance_btc": available / 100_000_000_000
        }
    
    def create_invoice(
        self,
        amount_msats: int,
        memo: Optional[str] = None,
        expiry_secs: int = 3600
    ) -> Dict[str, Any]:
        """
        Создать Lightning invoice
        
        Args:
            amount_msats: Сумма в миллисатоши
            memo: Описание invoice
            expiry_secs: Время жизни в секундах
        
        Returns:
            Информация о созданном invoice
        """
        mutation = """
        mutation CreateInvoice(
          $node_id: ID!
          $amount_msats: Long!
          $memo: String
          $expiry_secs: Int
        ) {
          create_invoice(input: {
            node_id: $node_id
            amount_msats: $amount_msats
            memo: $memo
            expiry_secs: $expiry_secs
          }) {
            invoice {
              id
              created_at
              data {
                encoded_payment_request
                bitcoin_network
                payment_hash
                amount {
                  original_value
                }
                expires_at
                memo
              }
            }
          }
        }
        """
        
        variables = {
            "node_id": self.node_id,
            "amount_msats": amount_msats,
            "memo": memo or "SPARK Bot deposit",
            "expiry_secs": expiry_secs
        }
        
        print(f"[LIGHTSPARK] Creating invoice: {amount_msats} msats")
        result = self._execute_query(mutation, variables)
        
        if "errors" in result:
            print(f"[ERROR] Failed to create invoice")
            return {
                "status": "error",
                "errors": result["errors"]
            }
        
        invoice = result.get("data", {}).get("create_invoice", {}).get("invoice", {})
        invoice_data = invoice.get("data", {})
        
        print(f"[LIGHTSPARK] ✅ Invoice created: {invoice.get('id')}")
        
        return {
            "status": "success",
            "invoice_id": invoice.get("id"),
            "encoded_payment_request": invoice_data.get("encoded_payment_request"),
            "payment_hash": invoice_data.get("payment_hash"),
            "amount_msats": amount_msats,
            "amount_sats": amount_msats // 1000,
            "amount_btc": amount_msats / 100_000_000_000,
            "memo": invoice_data.get("memo"),
            "expires_at": invoice_data.get("expires_at"),
            "created_at": invoice.get("created_at")
        }
    
    def pay_invoice(
        self,
        encoded_invoice: str,
        amount_msats: Optional[int] = None,
        timeout_secs: int = 60,
        max_fee_msats: int = 5000
    ) -> Dict[str, Any]:
        """
        Оплатить Lightning invoice
        
        Args:
            encoded_invoice: BOLT11 invoice (lnbc...)
            amount_msats: Сумма для zero-amount invoices
            timeout_secs: Таймаут
            max_fee_msats: Максимальная комиссия
        
        Returns:
            Результат оплаты
        """
        mutation = """
        mutation PayInvoice(
          $node_id: ID!
          $encoded_invoice: String!
          $timeout_secs: Int!
          $maximum_fees_msats: Long!
          $amount_msats: Long
        ) {
          pay_invoice(input: {
            node_id: $node_id
            encoded_invoice: $encoded_invoice
            timeout_secs: $timeout_secs
            maximum_fees_msats: $maximum_fees_msats
            amount_msats: $amount_msats
          }) {
            payment {
              id
              created_at
              status
              resolved_at
              amount {
                original_value
              }
              fees {
                original_value
              }
            }
          }
        }
        """
        
        variables = {
            "node_id": self.node_id,
            "encoded_invoice": encoded_invoice,
            "timeout_secs": timeout_secs,
            "maximum_fees_msats": max_fee_msats
        }
        
        if amount_msats:
            variables["amount_msats"] = amount_msats
        
        print(f"[LIGHTSPARK] Paying invoice...")
        result = self._execute_query(mutation, variables)
        
        if "errors" in result:
            print(f"[ERROR] Failed to pay invoice")
            return {
                "status": "error",
                "errors": result["errors"]
            }
        
        payment = result.get("data", {}).get("pay_invoice", {}).get("payment", {})
        
        print(f"[LIGHTSPARK] ✅ Payment sent: {payment.get('id')}")
        
        return {
            "status": "success",
            "payment_id": payment.get("id"),
            "payment_status": payment.get("status"),
            "amount_msats": payment.get("amount", {}).get("original_value"),
            "fees_msats": payment.get("fees", {}).get("original_value"),
            "created_at": payment.get("created_at"),
            "resolved_at": payment.get("resolved_at")
        }


# Singleton instance
_graphql_client: Optional[LightsparkGraphQLClient] = None


def get_lightspark_graphql_client() -> Optional[LightsparkGraphQLClient]:
    """Получить или создать GraphQL клиент"""
    global _graphql_client
    
    if _graphql_client is None:
        api_token = os.getenv("LIGHTSPARK_API_TOKEN")
        node_id = os.getenv("LIGHTSPARK_NODE_ID")
        
        if not api_token or not node_id:
            print("[WARNING] Lightspark credentials not found in .env")
            return None
        
        try:
            _graphql_client = LightsparkGraphQLClient(api_token, node_id)
            print("[LIGHTSPARK] GraphQL client initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to create GraphQL client: {e}")
            return None
    
    return _graphql_client
