"""
Stripe payment service for LandTen platform.

This service handles:
- Creating Stripe Connect accounts for contractors
- Adding external bank accounts
- Landlord → Contractor payments (job completion)
- Tenant → Landlord payments (rent/fees)
- Landlord → Platform payments (platform fees)
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
    def create_job_payment_session(
        job_id: str,
        bid_id: str,
        contractor_name: str,
        contractor_email: str,
        landlord_email: str,
        amount: float,
        description: str = "",
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for landlord paying contractor.

        Args:
            job_id: Job ID
            bid_id: Winning bid ID
            contractor_name: Contractor name
            contractor_email: Contractor email
            landlord_email: Landlord email (payer)
            amount: Amount in dollars
            description: Job description
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL

        Returns:
            Dict containing checkout URL and session ID
        """
        try:
            # Find or create customer for landlord
            customer = None
            if landlord_email:
                existing_customers = stripe.Customer.list(
                    email=landlord_email,
                    limit=1
                )

                if existing_customers.data:
                    customer = existing_customers.data[0]
                else:
                    customer = stripe.Customer.create(
                        email=landlord_email,
                    )

            # Create checkout session
            session_params = {
                "mode": "payment",
                "line_items": [
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Job Payment - {contractor_name}",
                                "description": description or "Payment for completed work",
                            },
                            "unit_amount": int(round(amount * 100)),  # Convert to cents
                        },
                        "quantity": 1,
                    },
                ],
                "metadata": {
                    "job_id": job_id,
                    "bid_id": bid_id,
                    "contractor_email": contractor_email,
                    "payment_type": "job_completion",
                },
                "success_url": success_url or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/landlord/jobs/{job_id}?payment=success",
                "cancel_url": cancel_url or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/landlord/jobs/{job_id}?payment=cancelled",
            }

            if customer:
                session_params["customer"] = customer.id
            else:
                session_params["customer_email"] = landlord_email

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

    @staticmethod
    def create_rent_payment_session(
        property_id: str,
        tenant_name: str,
        tenant_email: str,
        landlord_email: str,
        amount: float,
        period: str = "",
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for tenant paying rent.

        Args:
            property_id: Property ID
            tenant_name: Tenant name
            tenant_email: Tenant email (payer)
            landlord_email: Landlord email (receiver)
            amount: Rent amount in dollars
            period: Rent period (e.g., "January 2024")
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL

        Returns:
            Dict containing checkout URL and session ID
        """
        try:
            # Find or create customer for tenant
            customer = None
            if tenant_email:
                existing_customers = stripe.Customer.list(
                    email=tenant_email,
                    limit=1
                )

                if existing_customers.data:
                    customer = existing_customers.data[0]
                else:
                    customer = stripe.Customer.create(
                        email=tenant_email,
                        name=tenant_name,
                    )

            # Create checkout session
            session_params = {
                "mode": "payment",
                "line_items": [
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Rent Payment{' - ' + period if period else ''}",
                                "description": f"Property: {property_id}",
                            },
                            "unit_amount": int(round(amount * 100)),
                        },
                        "quantity": 1,
                    },
                ],
                "metadata": {
                    "property_id": property_id,
                    "landlord_email": landlord_email,
                    "period": period or "",
                    "payment_type": "rent",
                },
                "success_url": success_url or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/tenant/payments?status=success",
                "cancel_url": cancel_url or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/tenant/payments?status=cancelled",
            }

            if customer:
                session_params["customer"] = customer.id
            else:
                session_params["customer_email"] = tenant_email

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

    @staticmethod
    def create_platform_fee_session(
        landlord_id: str,
        landlord_email: str,
        landlord_name: str,
        amount: float,
        description: str = "Platform subscription fee",
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for landlord paying platform fees.

        Args:
            landlord_id: Landlord ID
            landlord_email: Landlord email (payer)
            landlord_name: Landlord name
            amount: Fee amount in dollars
            description: Fee description
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL

        Returns:
            Dict containing checkout URL and session ID
        """
        try:
            # Find or create customer for landlord
            customer = None
            if landlord_email:
                existing_customers = stripe.Customer.list(
                    email=landlord_email,
                    limit=1
                )

                if existing_customers.data:
                    customer = existing_customers.data[0]
                else:
                    customer = stripe.Customer.create(
                        email=landlord_email,
                        name=landlord_name,
                    )

            # Create checkout session
            session_params = {
                "mode": "payment",
                "line_items": [
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": "LandTen Platform Fee",
                                "description": description,
                            },
                            "unit_amount": int(round(amount * 100)),
                        },
                        "quantity": 1,
                    },
                ],
                "metadata": {
                    "landlord_id": landlord_id,
                    "payment_type": "platform_fee",
                },
                "success_url": success_url or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/landlord/billing?status=success",
                "cancel_url": cancel_url or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/landlord/billing?status=cancelled",
            }

            if customer:
                session_params["customer"] = customer.id
            else:
                session_params["customer_email"] = landlord_email

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
