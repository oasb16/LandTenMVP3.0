"""
Test suite for Stripe Checkout payment routes.

Tests all three payment flows:
1. Job payment (Landlord → Contractor)
2. Rent payment (Tenant → Landlord)
3. Platform fee (Landlord → Platform)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.app.main import app

client = TestClient(app)


class TestJobPaymentRoute:
    """Tests for /api/checkout/job-payment endpoint."""

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_job_payment_session_success(self, mock_customer_list, mock_session_create):
        """Test successful job payment session creation."""
        # Mock Stripe customer
        mock_customer_list.return_value.data = []

        # Mock Stripe session creation
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test_session"
        mock_session.id = "cs_test_123"
        mock_session_create.return_value = mock_session

        # Request payload
        payload = {
            "job_id": "job_123",
            "bid_id": "bid_456",
            "contractor_name": "John Contractor",
            "contractor_email": "john@contractor.com",
            "landlord_email": "jane@landlord.com",
            "amount": 500.00,
            "description": "Plumbing repair"
        }

        # Make request
        response = client.post("/api/checkout/job-payment", json=payload)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["checkoutUrl"] == "https://checkout.stripe.com/test_session"
        assert data["sessionId"] == "cs_test_123"

    def test_create_job_payment_session_missing_fields(self):
        """Test job payment with missing required fields."""
        payload = {
            "job_id": "job_123",
            # Missing other required fields
        }

        response = client.post("/api/checkout/job-payment", json=payload)

        assert response.status_code == 422  # Validation error

    def test_create_job_payment_session_invalid_amount(self):
        """Test job payment with invalid amount."""
        payload = {
            "job_id": "job_123",
            "bid_id": "bid_456",
            "contractor_name": "John Contractor",
            "contractor_email": "john@contractor.com",
            "landlord_email": "jane@landlord.com",
            "amount": -100.00,  # Invalid negative amount
        }

        response = client.post("/api/checkout/job-payment", json=payload)

        assert response.status_code == 422

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_job_payment_session_stripe_error(self, mock_customer_list, mock_session_create):
        """Test handling of Stripe API errors."""
        mock_customer_list.return_value.data = []
        mock_session_create.side_effect = Exception("Stripe API error")

        payload = {
            "job_id": "job_123",
            "bid_id": "bid_456",
            "contractor_name": "John Contractor",
            "contractor_email": "john@contractor.com",
            "landlord_email": "jane@landlord.com",
            "amount": 500.00,
        }

        response = client.post("/api/checkout/job-payment", json=payload)

        assert response.status_code == 500


class TestRentPaymentRoute:
    """Tests for /api/checkout/rent-payment endpoint."""

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_rent_payment_session_success(self, mock_customer_list, mock_session_create):
        """Test successful rent payment session creation."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/rent_session"
        mock_session.id = "cs_rent_123"
        mock_session_create.return_value = mock_session

        payload = {
            "property_id": "prop_123",
            "tenant_name": "Alice Tenant",
            "tenant_email": "alice@tenant.com",
            "landlord_email": "bob@landlord.com",
            "amount": 1500.00,
            "period": "January 2024"
        }

        response = client.post("/api/checkout/rent-payment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["checkoutUrl"] == "https://checkout.stripe.com/rent_session"
        assert data["sessionId"] == "cs_rent_123"

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_rent_payment_with_existing_customer(self, mock_customer_list, mock_customer_create, mock_session_create):
        """Test rent payment with existing Stripe customer."""
        # Mock existing customer
        existing_customer = MagicMock()
        existing_customer.id = "cus_existing_123"
        mock_customer_list.return_value.data = [existing_customer]

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/rent_session"
        mock_session.id = "cs_rent_123"
        mock_session_create.return_value = mock_session

        payload = {
            "property_id": "prop_123",
            "tenant_name": "Alice Tenant",
            "tenant_email": "alice@tenant.com",
            "landlord_email": "bob@landlord.com",
            "amount": 1500.00,
        }

        response = client.post("/api/checkout/rent-payment", json=payload)

        assert response.status_code == 200
        # Verify existing customer was used (create not called)
        mock_customer_create.assert_not_called()


class TestPlatformFeeRoute:
    """Tests for /api/checkout/platform-fee endpoint."""

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_platform_fee_session_success(self, mock_customer_list, mock_session_create):
        """Test successful platform fee session creation."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/fee_session"
        mock_session.id = "cs_fee_123"
        mock_session_create.return_value = mock_session

        payload = {
            "landlord_id": "landlord_123",
            "landlord_email": "bob@landlord.com",
            "landlord_name": "Bob Landlord",
            "amount": 49.99,
            "description": "Monthly subscription"
        }

        response = client.post("/api/checkout/platform-fee", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["checkoutUrl"] == "https://checkout.stripe.com/fee_session"
        assert data["sessionId"] == "cs_fee_123"

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_create_platform_fee_with_custom_description(self, mock_customer_list, mock_session_create):
        """Test platform fee with custom description."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/fee_session"
        mock_session.id = "cs_fee_123"
        mock_session_create.return_value = mock_session

        payload = {
            "landlord_id": "landlord_123",
            "landlord_email": "bob@landlord.com",
            "landlord_name": "Bob Landlord",
            "amount": 99.99,
            "description": "Annual premium subscription"
        }

        response = client.post("/api/checkout/platform-fee", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestHealthCheck:
    """Tests for /api/checkout/health endpoint."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/checkout/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "LandTen Stripe Checkout Integration"
        assert "payment_flows" in data
        assert len(data["payment_flows"]) == 3
        assert "job_payment" in data["payment_flows"]
        assert "rent_payment" in data["payment_flows"]
        assert "platform_fee" in data["payment_flows"]


class TestIntegrationScenarios:
    """Integration tests for complete payment scenarios."""

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_complete_job_payment_flow(self, mock_customer_list, mock_session_create):
        """Test complete job payment flow from creation to redirect."""
        mock_customer_list.return_value.data = []

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test_session"
        mock_session.id = "cs_test_123"
        mock_session_create.return_value = mock_session

        # Step 1: Create payment session
        payload = {
            "job_id": "job_123",
            "bid_id": "bid_456",
            "contractor_name": "John Contractor",
            "contractor_email": "john@contractor.com",
            "landlord_email": "jane@landlord.com",
            "amount": 500.00,
            "description": "Plumbing repair",
            "success_url": "https://myapp.com/success",
            "cancel_url": "https://myapp.com/cancel"
        }

        response = client.post("/api/checkout/job-payment", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Step 2: Verify session data
        assert data["success"] is True
        assert data["checkoutUrl"].startswith("https://checkout.stripe.com/")
        assert data["sessionId"] is not None

        # Step 3: Verify Stripe was called with correct parameters
        mock_session_create.assert_called_once()
        call_kwargs = mock_session_create.call_args[1]
        assert call_kwargs["mode"] == "payment"
        assert call_kwargs["metadata"]["job_id"] == "job_123"
        assert call_kwargs["metadata"]["payment_type"] == "job_completion"

    @patch('backend.app.services.stripe_service.stripe.checkout.Session.create')
    @patch('backend.app.services.stripe_service.stripe.Customer.list')
    def test_multiple_payment_types_in_sequence(self, mock_customer_list, mock_session_create):
        """Test creating multiple different payment types in sequence."""
        mock_customer_list.return_value.data = []

        # Test job payment
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/job"
        mock_session.id = "cs_job"
        mock_session_create.return_value = mock_session

        job_payload = {
            "job_id": "job_123",
            "bid_id": "bid_456",
            "contractor_name": "John",
            "contractor_email": "john@test.com",
            "landlord_email": "jane@test.com",
            "amount": 500.00,
        }
        response = client.post("/api/checkout/job-payment", json=job_payload)
        assert response.status_code == 200

        # Test rent payment
        mock_session.url = "https://checkout.stripe.com/rent"
        mock_session.id = "cs_rent"

        rent_payload = {
            "property_id": "prop_123",
            "tenant_name": "Alice",
            "tenant_email": "alice@test.com",
            "landlord_email": "bob@test.com",
            "amount": 1500.00,
        }
        response = client.post("/api/checkout/rent-payment", json=rent_payload)
        assert response.status_code == 200

        # Test platform fee
        mock_session.url = "https://checkout.stripe.com/fee"
        mock_session.id = "cs_fee"

        fee_payload = {
            "landlord_id": "ll_123",
            "landlord_email": "bob@test.com",
            "landlord_name": "Bob",
            "amount": 49.99,
        }
        response = client.post("/api/checkout/platform-fee", json=fee_payload)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
