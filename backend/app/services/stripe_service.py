"""
Stripe payment service for contractor payouts and hotel checkout.

This service handles:
- Creating Stripe Connect accounts for contractors
- Adding external bank accounts
- Making payouts from landlord to contractor
- Hotel checkout sessions
"""

import os
import logging
from typing import Dict, Any, Optional
import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
logger = logging.getLogger(__name__)


class StripeService:
    """Service for handling Stripe payments and payouts."""

    @staticmethod
    def create_express_account(
        email: str,
        contractor_id: str,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Express account for a contractor.

        Args:
            email: Contractor's email address
            contractor_id: Internal contractor ID
            name: Contractor's name (optional)

        Returns:
            Dict containing account_id and other account details
        """
        account = stripe.Account.create(
            type="express",
            email=email,
            metadata={
                "contractor_id": contractor_id
            },
            business_type="individual",
            capabilities={
                "transfers": {"requested": True},
            }
        )

        return {
            "account_id": account.id,
            "email": account.email,
            "details_submitted": account.details_submitted,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled
        }

    @staticmethod
    def add_external_bank_account(
        account_id: str,
        account_number: str,
        routing_number: str,
        account_holder_name: str,
        account_holder_type: str = "individual"
    ) -> Dict[str, Any]:
        """
        Add an external bank account to a Stripe Connect account.

        Args:
            account_id: Stripe account ID
            account_number: Bank account number
            routing_number: Bank routing number
            account_holder_name: Name on the bank account
            account_holder_type: Type of account holder (individual or company)

        Returns:
            Dict containing bank account details
        """
        # Create a bank account token
        token = stripe.Token.create(
            bank_account={
                "country": "US",
                "currency": "usd",
                "account_holder_name": account_holder_name,
                "account_holder_type": account_holder_type,
                "routing_number": routing_number,
                "account_number": account_number,
            }
        )

        # Add the bank account to the Connect account
        bank_account = stripe.Account.create_external_account(
            account_id,
            external_account=token.id,
        )

        return {
            "bank_account_id": bank_account.id,
            "last4": bank_account.last4,
            "bank_name": bank_account.bank_name,
            "routing_number": bank_account.routing_number,
            "status": bank_account.status
        }

    @staticmethod
    def create_payout(
        destination_account_id: str,
        amount_cents: int,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a transfer to a contractor's Stripe Connect account.

        Args:
            destination_account_id: Stripe account ID of the contractor
            amount_cents: Amount in cents (e.g., 10000 = $100.00)
            description: Description of the payment
            metadata: Optional metadata to attach to the transfer

        Returns:
            Dict containing transfer details
        """
        transfer = stripe.Transfer.create(
            amount=amount_cents,
            currency="usd",
            destination=destination_account_id,
            description=description,
            metadata=metadata or {}
        )

        return {
            "transfer_id": transfer.id,
            "amount": transfer.amount,
            "currency": transfer.currency,
            "destination": transfer.destination,
            "created": transfer.created,
            "status": "pending"
        }

    @staticmethod
    def get_account_balance(account_id: str) -> Dict[str, Any]:
        """
        Get the balance of a Stripe Connect account.

        Args:
            account_id: Stripe account ID

        Returns:
            Dict containing balance information
        """
        balance = stripe.Balance.retrieve(
            stripe_account=account_id
        )

        return {
            "available": balance.available,
            "pending": balance.pending
        }

    @staticmethod
    def create_account_link(
        account_id: str,
        refresh_url: str,
        return_url: str
    ) -> str:
        """
        Create an account link for contractor onboarding.

        Args:
            account_id: Stripe account ID
            refresh_url: URL to redirect if the link expires
            return_url: URL to redirect after onboarding completion

        Returns:
            URL for the account link
        """
        account_link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )

        return account_link.url

    @staticmethod
    def retrieve_account(account_id: str) -> Dict[str, Any]:
        """
        Retrieve details about a Stripe Connect account.

        Args:
            account_id: Stripe account ID

        Returns:
            Dict containing account details
        """
        account = stripe.Account.retrieve(account_id)

        return {
            "account_id": account.id,
            "email": account.email,
            "details_submitted": account.details_submitted,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,
            "requirements": account.requirements
        }

    @staticmethod
    def create_hotel_checkout_session(
        amount: float,
        guest_name: str,
        guest_email: str,
        guest_phone: Optional[str],
        reservation_id: str,
        hotel_name: str = "Hotel",
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for hotel payment.

        Args:
            amount: Amount in dollars
            guest_name: Guest name
            guest_email: Guest email
            guest_phone: Guest phone (optional)
            reservation_id: Reservation ID
            hotel_name: Hotel name
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL

        Returns:
            Dict containing checkout URL and session ID
        """
        try:
            # Find or create customer
            customer = None
            if guest_email:
                existing_customers = stripe.Customer.list(
                    email=guest_email,
                    limit=1
                )

                if existing_customers.data:
                    customer = existing_customers.data[0]
                else:
                    customer = stripe.Customer.create(
                        email=guest_email,
                        name=guest_name,
                        phone=guest_phone,
                    )

            # Create checkout session
            session_params = {
                "mode": "payment",
                "line_items": [
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Hotel Stay - {hotel_name}",
                                "description": f"Reservation for {guest_name}",
                            },
                            "unit_amount": int(round(amount * 100)),  # Convert to cents
                        },
                        "quantity": 1,
                    },
                ],
                "metadata": {
                    "reservation_id": reservation_id,
                    "guest_name": guest_name,
                    "guest_phone": guest_phone or "",
                },
                "success_url": success_url or "https://yourdomain.com/checkout-success?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": cancel_url or "https://yourdomain.com/checkout-cancel",
            }

            if customer:
                session_params["customer"] = customer.id
            else:
                session_params["customer_email"] = guest_email

            session = stripe.checkout.Session.create(**session_params)

            return {
                "success": True,
                "checkoutUrl": session.url,
                "sessionId": session.id,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            return {
                "success": False,
                "error": str(e)
            }
