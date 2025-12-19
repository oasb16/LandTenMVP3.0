"""
Elavon payment service for hotel terminal and mobile checkout.

This service handles:
- Elavon authentication (token retrieval)
- Pre-authorization for check-in
- Payment completion/capture for checkout
- Mobile checkout via Converge (Checkout.js)
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class ElavonService:
    """Service for handling Elavon payments."""

    def __init__(self):
        self.test_endpoint = "https://uat.pos.hpi.elavonaws.com"
        self.prod_endpoint = "https://pos.hpi.elavonaws.com"
        self.converge_test_endpoint = "https://api.demo.convergepay.com"
        self.converge_prod_endpoint = "https://api.convergepay.com"

    async def get_token(
        self,
        merchant_id: str,
        user_id: str,
        pin: str,
        api_endpoint: str
    ) -> Dict[str, Any]:
        """
        Get authentication token from Elavon.

        Args:
            merchant_id: Elavon merchant ID
            user_id: Elavon user ID
            pin: Elavon PIN
            api_endpoint: API endpoint URL

        Returns:
            Dict containing token and expiration
        """
        try:
            auth_request = {
                "merchantId": merchant_id,
                "userId": user_id,
                "pin": pin,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_endpoint}/api/v1/auth/token",
                    json=auth_request,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    timeout=30.0
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(f"Elavon auth error: {error_data}")
                    raise Exception(error_data.get("message", "Authentication failed"))

                data = response.json()

                # Token typically expires in 24 hours
                expires_at = datetime.utcnow() + timedelta(hours=24)

                return {
                    "token": data.get("token") or data.get("accessToken"),
                    "expiresAt": expires_at.isoformat(),
                }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in get_token: {e}")
            raise Exception(f"Failed to connect to Elavon: {str(e)}")
        except Exception as e:
            logger.error(f"Error in get_token: {e}")
            raise

    async def pre_authorize(
        self,
        token: str,
        amount: float,
        terminal_id: str,
        merchant_id: str,
        api_endpoint: str
    ) -> Dict[str, Any]:
        """
        Pre-authorize a payment (for check-in).

        Args:
            token: Elavon authentication token
            amount: Amount to pre-authorize in dollars
            terminal_id: Terminal ID
            merchant_id: Merchant ID
            api_endpoint: API endpoint URL

        Returns:
            Dict containing transaction ID and status
        """
        try:
            preauth_request = {
                "transactionType": "PREAUTH",
                "amount": int(round(amount * 100)),  # Convert dollars to cents
                "currency": "USD",
                "terminalId": terminal_id,
                "merchantId": merchant_id,
                "referenceNumber": f"PREAUTH-{datetime.utcnow().timestamp()}",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_endpoint}/api/v1/transactions",
                    json=preauth_request,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                    timeout=60.0
                )

                response_text = response.text
                logger.info(f"Elavon pre-auth response: {response_text}")

                # Try to parse as JSON
                try:
                    data = response.json()
                except:
                    # If not JSON, create response object
                    data = {
                        "transactionId": f"PREAUTH-{int(datetime.utcnow().timestamp())}",
                        "status": "APPROVED" if response.status_code == 200 else "DECLINED",
                        "message": response_text or ("Pre-authorization successful" if response.status_code == 200 else "Pre-authorization failed")
                    }

                if response.status_code != 200:
                    return {
                        "error": data.get("message", "Pre-authorization failed"),
                        "details": data,
                        "status": "DECLINED",
                        "transactionId": data.get("transactionId", ""),
                        "amount": amount,
                    }

                return {
                    "transactionId": data.get("transactionId", f"PREAUTH-{int(datetime.utcnow().timestamp())}"),
                    "status": data.get("status", "APPROVED"),
                    "amount": amount,
                }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in pre_authorize: {e}")
            raise Exception(f"Failed to connect to Elavon: {str(e)}")
        except Exception as e:
            logger.error(f"Error in pre_authorize: {e}")
            raise

    async def complete_payment(
        self,
        token: str,
        original_transaction_id: str,
        amount: float,
        terminal_id: str,
        merchant_id: str,
        api_endpoint: str
    ) -> Dict[str, Any]:
        """
        Complete/capture a pre-authorized payment (for checkout).

        Args:
            token: Elavon authentication token
            original_transaction_id: Original pre-auth transaction ID
            amount: Amount to capture in dollars
            terminal_id: Terminal ID
            merchant_id: Merchant ID
            api_endpoint: API endpoint URL

        Returns:
            Dict containing transaction ID and status
        """
        try:
            completion_request = {
                "transactionType": "COMPLETION",
                "originalTransactionId": original_transaction_id,
                "amount": int(round(amount * 100)),  # Convert dollars to cents
                "currency": "USD",
                "terminalId": terminal_id,
                "merchantId": merchant_id,
                "referenceNumber": f"COMP-{datetime.utcnow().timestamp()}",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_endpoint}/api/v1/transactions",
                    json=completion_request,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                    timeout=60.0
                )

                data = response.json()

                if response.status_code != 200:
                    return {
                        "error": data.get("message", "Completion failed"),
                        "status": "DECLINED",
                        "transactionId": data.get("transactionId", ""),
                        "amount": amount,
                    }

                return {
                    "transactionId": data.get("transactionId", f"COMP-{int(datetime.utcnow().timestamp())}"),
                    "status": data.get("status", "APPROVED"),
                    "amount": amount,
                }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in complete_payment: {e}")
            raise Exception(f"Failed to connect to Elavon: {str(e)}")
        except Exception as e:
            logger.error(f"Error in complete_payment: {e}")
            raise

    async def create_checkout_session(
        self,
        merchant_id: str,
        user_id: str,
        pin: str,
        amount: float,
        transaction_type: str = "ccsale",
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        invoice_number: str = "",
        is_test_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Create a mobile checkout session via Converge.

        Args:
            merchant_id: Converge merchant ID
            user_id: Converge user ID
            pin: Converge PIN
            amount: Amount in dollars
            transaction_type: Transaction type (default: ccsale)
            first_name: Guest first name
            last_name: Guest last name
            email: Guest email
            invoice_number: Invoice/reservation number
            is_test_mode: Use test endpoint

        Returns:
            Dict containing checkout URL and token
        """
        try:
            endpoint = self.converge_test_endpoint if is_test_mode else self.converge_prod_endpoint

            form_data = {
                "ssl_merchant_id": merchant_id,
                "ssl_user_id": user_id,
                "ssl_pin": pin,
                "ssl_transaction_type": transaction_type,
                "ssl_amount": f"{amount:.2f}",
                "ssl_first_name": first_name,
                "ssl_last_name": last_name,
                "ssl_email": email,
                "ssl_invoice_number": invoice_number,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{endpoint}/hosted-payments/transaction_token",
                    data=form_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    timeout=30.0
                )

                response_text = response.text
                logger.info(f"Converge response: {response_text}")

                # Parse response (usually in key=value format)
                parsed = {}
                for pair in response_text.split('&'):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        parsed[key] = value

                if parsed.get("errorCode") or parsed.get("ssl_result") != "0":
                    return {
                        "success": False,
                        "error": parsed.get("errorMessage", "Failed to create checkout session")
                    }

                token = parsed.get("ssl_token", "")
                checkout_url = f"{endpoint}/hosted-payments?ssl_txn_auth_token={token}"

                return {
                    "success": True,
                    "checkoutUrl": checkout_url,
                    "token": token,
                }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in create_checkout_session: {e}")
            return {
                "success": False,
                "error": f"Failed to connect to Converge: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error in create_checkout_session: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_elavon_service: Optional[ElavonService] = None


def get_elavon_service() -> ElavonService:
    """Get the singleton Elavon service instance."""
    global _elavon_service
    if _elavon_service is None:
        _elavon_service = ElavonService()
    return _elavon_service
