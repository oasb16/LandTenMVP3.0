"""
Test suite for StripeService payment methods.

Tests the three new Stripe Checkout methods:
- create_job_payment_session
- create_rent_payment_session
- create_platform_fee_session
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.stripe_service import StripeService


class TestStripeServiceJobPayment:
    """Tests for create_job_payment_session method."""

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_job_payment_session_new_customer(self, mock_customer_list, mock_session_create):
        """Test job payment session with new customer."""
        # Mock no existing customer
        mock_customer_list.return_value.data = []

        # Mock customer creation
        mock_customer = MagicMock()
        mock_customer.id = "cus_new_123"

        # Mock session creation
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session"
        mock_session.id = "cs_123"
        mock_session_create.return_value = mock_session

        # Create service and call method
        service = StripeService()
        result = service.create_job_payment_session(
            job_id="job_123",
            bid_id="bid_456",
            contractor_name="John Contractor",
            contractor_email="john@contractor.com",
            landlord_email="jane@landlord.com",
            amount=500.00,
            description="Plumbing repair"
        )

        # Assertions
        assert result["success"] is True
        assert result["checkoutUrl"] == "https://checkout.stripe.com/session"
        assert result["sessionId"] == "cs_123"
        mock_session_create.assert_called_once()

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_job_payment_session_existing_customer(self, mock_customer_list, mock_session_create):
        """Test job payment session with existing customer."""
        # Mock existing customer
        existing_customer = MagicMock()
        existing_customer.id = "cus_existing_123"
        mock_customer_list.return_value.data = [existing_customer]

        # Mock session creation
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session"
        mock_session.id = "cs_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        result = service.create_job_payment_session(
            job_id="job_123",
            bid_id="bid_456",
            contractor_name="John Contractor",
            contractor_email="john@contractor.com",
            landlord_email="jane@landlord.com",
            amount=500.00
        )

        assert result["success"] is True
        # Verify session was created with existing customer
        call_kwargs = mock_session_create.call_args[1]
        assert call_kwargs["customer"] == "cus_existing_123"

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_job_payment_session_amount_conversion(self, mock_customer_list, mock_session_create):
        """Test that amount is correctly converted to cents."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session"
        mock_session.id = "cs_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        service.create_job_payment_session(
            job_id="job_123",
            bid_id="bid_456",
            contractor_name="John",
            contractor_email="john@test.com",
            landlord_email="jane@test.com",
            amount=123.45  # Test decimal amount
        )

        call_kwargs = mock_session_create.call_args[1]
        line_item = call_kwargs["line_items"][0]
        # Amount should be converted to cents: 123.45 * 100 = 12345
        assert line_item["price_data"]["unit_amount"] == 12345

    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_job_payment_session_stripe_error(self, mock_customer_list):
        """Test handling of Stripe errors."""
        mock_customer_list.return_value.data = []

        with patch('backend.app.services.stripe_service.stripe.checkout.Session.create') as mock_session_create:
            mock_session_create.side_effect = Exception("Stripe API error")

            service = StripeService()
            result = service.create_job_payment_session(
                job_id="job_123",
                bid_id="bid_456",
                contractor_name="John",
                contractor_email="john@test.com",
                landlord_email="jane@test.com",
                amount=500.00
            )

            assert result["success"] is False
            assert "error" in result

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_job_payment_session_metadata(self, mock_customer_list, mock_session_create):
        """Test that correct metadata is included."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session"
        mock_session.id = "cs_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        service.create_job_payment_session(
            job_id="job_123",
            bid_id="bid_456",
            contractor_name="John",
            contractor_email="john@test.com",
            landlord_email="jane@test.com",
            amount=500.00
        )

        call_kwargs = mock_session_create.call_args[1]
        metadata = call_kwargs["metadata"]
        assert metadata["job_id"] == "job_123"
        assert metadata["bid_id"] == "bid_456"
        assert metadata["contractor_email"] == "john@test.com"
        assert metadata["payment_type"] == "job_completion"


class TestStripeServiceRentPayment:
    """Tests for create_rent_payment_session method."""

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_rent_payment_session_success(self, mock_customer_list, mock_customer_create, mock_session_create):
        """Test successful rent payment session creation."""
        mock_customer_list.return_value.data = []

        mock_customer = MagicMock()
        mock_customer.id = "cus_tenant_123"
        mock_customer_create.return_value = mock_customer

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/rent"
        mock_session.id = "cs_rent_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        result = service.create_rent_payment_session(
            property_id="prop_123",
            tenant_name="Alice Tenant",
            tenant_email="alice@tenant.com",
            landlord_email="bob@landlord.com",
            amount=1500.00,
            period="January 2024"
        )

        assert result["success"] is True
        assert result["checkoutUrl"] == "https://checkout.stripe.com/rent"
        assert result["sessionId"] == "cs_rent_123"

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_rent_payment_session_metadata(self, mock_customer_list, mock_session_create):
        """Test rent payment metadata."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/rent"
        mock_session.id = "cs_rent_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        service.create_rent_payment_session(
            property_id="prop_123",
            tenant_name="Alice",
            tenant_email="alice@test.com",
            landlord_email="bob@test.com",
            amount=1500.00,
            period="January 2024"
        )

        call_kwargs = mock_session_create.call_args[1]
        metadata = call_kwargs["metadata"]
        assert metadata["property_id"] == "prop_123"
        assert metadata["landlord_email"] == "bob@test.com"
        assert metadata["period"] == "January 2024"
        assert metadata["payment_type"] == "rent"


class TestStripeServicePlatformFee:
    """Tests for create_platform_fee_session method."""

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_platform_fee_session_success(self, mock_customer_list, mock_customer_create, mock_session_create):
        """Test successful platform fee session creation."""
        mock_customer_list.return_value.data = []

        mock_customer = MagicMock()
        mock_customer.id = "cus_landlord_123"
        mock_customer_create.return_value = mock_customer

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/fee"
        mock_session.id = "cs_fee_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        result = service.create_platform_fee_session(
            landlord_id="landlord_123",
            landlord_email="bob@landlord.com",
            landlord_name="Bob Landlord",
            amount=49.99,
            description="Monthly subscription"
        )

        assert result["success"] is True
        assert result["checkoutUrl"] == "https://checkout.stripe.com/fee"
        assert result["sessionId"] == "cs_fee_123"

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_platform_fee_session_default_description(self, mock_customer_list, mock_session_create):
        """Test platform fee with default description."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/fee"
        mock_session.id = "cs_fee_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        service.create_platform_fee_session(
            landlord_id="landlord_123",
            landlord_email="bob@test.com",
            landlord_name="Bob",
            amount=49.99
            # No description provided
        )

        call_kwargs = mock_session_create.call_args[1]
        line_item = call_kwargs["line_items"][0]
        # Should use default description
        assert "Platform" in line_item["price_data"]["product_data"]["description"]

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_platform_fee_session_metadata(self, mock_customer_list, mock_session_create):
        """Test platform fee metadata."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/fee"
        mock_session.id = "cs_fee_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        service.create_platform_fee_session(
            landlord_id="landlord_123",
            landlord_email="bob@test.com",
            landlord_name="Bob",
            amount=49.99
        )

        call_kwargs = mock_session_create.call_args[1]
        metadata = call_kwargs["metadata"]
        assert metadata["landlord_id"] == "landlord_123"
        assert metadata["payment_type"] == "platform_fee"


class TestStripeServiceEdgeCases:
    """Test edge cases and error handling."""

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_zero_decimal_amount_conversion(self, mock_customer_list, mock_session_create):
        """Test amount conversion for whole dollar amounts."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session"
        mock_session.id = "cs_123"
        mock_session_create.return_value = mock_session

        service = StripeService()
        service.create_job_payment_session(
            job_id="job_123",
            bid_id="bid_456",
            contractor_name="John",
            contractor_email="john@test.com",
            landlord_email="jane@test.com",
            amount=100.00  # Whole dollar amount
        )

        call_kwargs = mock_session_create.call_args[1]
        line_item = call_kwargs["line_items"][0]
        assert line_item["price_data"]["unit_amount"] == 10000

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_custom_success_url(self, mock_customer_list, mock_session_create):
        """Test custom success URL is used."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session"
        mock_session.id = "cs_123"
        mock_session_create.return_value = mock_session

        custom_success_url = "https://myapp.com/payment-success"
        custom_cancel_url = "https://myapp.com/payment-cancelled"

        service = StripeService()
        service.create_job_payment_session(
            job_id="job_123",
            bid_id="bid_456",
            contractor_name="John",
            contractor_email="john@test.com",
            landlord_email="jane@test.com",
            amount=500.00,
            success_url=custom_success_url,
            cancel_url=custom_cancel_url
        )

        call_kwargs = mock_session_create.call_args[1]
        assert call_kwargs["success_url"] == custom_success_url
        assert call_kwargs["cancel_url"] == custom_cancel_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
