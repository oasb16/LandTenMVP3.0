"""
Manual Integration Test Script for Stripe Checkout Payments

This script tests the complete flow of all three payment types:
1. Job payment (Landlord → Contractor)
2. Rent payment (Tenant → Landlord)
3. Platform fee (Landlord → Platform)

Run this script to manually test the payment flows.
Make sure your STRIPE_SECRET_KEY is set in environment variables.

Usage:
    python integration_test.py [--live]

Options:
    --live    Use live Stripe credentials (default: test mode)
"""

import sys
import os
import requests
import json
from datetime import datetime

# API base URL - adjust as needed
API_BASE_URL = os.getenv("BACKEND_URL", "https://landtenmvp3-55ce0053f28a.herokuapp.com/")


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def test_health_check():
    """Test the health check endpoint."""
    print_header("Testing Health Check")

    try:
        response = requests.get(f"{API_BASE_URL}/api/checkout/health")
        response.raise_for_status()

        data = response.json()
        print_success("Health check passed")
        print_info(f"Service: {data['service']}")
        print_info(f"Status: {data['status']}")
        print_info(f"Payment flows: {', '.join(data['payment_flows'])}")
        return True

    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_job_payment():
    """Test job payment session creation."""
    print_header("Testing Job Payment (Landlord → Contractor)")

    payload = {
        "job_id": f"test_job_{datetime.now().timestamp()}",
        "bid_id": f"test_bid_{datetime.now().timestamp()}",
        "contractor_name": "Test Contractor",
        "contractor_email": "contractor@test.com",
        "landlord_email": "landlord@test.com",
        "amount": 500.00,
        "description": "Integration test - Plumbing repair"
    }

    print_info(f"Creating job payment session for ${payload['amount']}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/checkout/job-payment",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        data = response.json()

        if data.get("success"):
            print_success("Job payment session created successfully")
            print_info(f"Session ID: {data['sessionId']}")
            print_info(f"Checkout URL: {data['checkoutUrl']}")
            print(f"\n{Colors.WARNING}To complete payment, visit:{Colors.ENDC}")
            print(f"{Colors.BOLD}{data['checkoutUrl']}{Colors.ENDC}\n")
            return True
        else:
            print_error(f"Failed to create session: {data.get('error')}")
            return False

    except Exception as e:
        print_error(f"Job payment test failed: {e}")
        return False


def test_rent_payment():
    """Test rent payment session creation."""
    print_header("Testing Rent Payment (Tenant → Landlord)")

    payload = {
        "property_id": f"test_prop_{datetime.now().timestamp()}",
        "tenant_name": "Test Tenant",
        "tenant_email": "tenant@test.com",
        "landlord_email": "landlord@test.com",
        "amount": 1500.00,
        "period": f"Test Month - {datetime.now().strftime('%B %Y')}"
    }

    print_info(f"Creating rent payment session for ${payload['amount']}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/checkout/rent-payment",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        data = response.json()

        if data.get("success"):
            print_success("Rent payment session created successfully")
            print_info(f"Session ID: {data['sessionId']}")
            print_info(f"Checkout URL: {data['checkoutUrl']}")
            print(f"\n{Colors.WARNING}To complete payment, visit:{Colors.ENDC}")
            print(f"{Colors.BOLD}{data['checkoutUrl']}{Colors.ENDC}\n")
            return True
        else:
            print_error(f"Failed to create session: {data.get('error')}")
            return False

    except Exception as e:
        print_error(f"Rent payment test failed: {e}")
        return False


def test_platform_fee():
    """Test platform fee session creation."""
    print_header("Testing Platform Fee (Landlord → Platform)")

    payload = {
        "landlord_id": f"test_landlord_{datetime.now().timestamp()}",
        "landlord_email": "landlord@test.com",
        "landlord_name": "Test Landlord",
        "amount": 49.99,
        "description": "Integration test - Monthly subscription"
    }

    print_info(f"Creating platform fee session for ${payload['amount']}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/checkout/platform-fee",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        data = response.json()

        if data.get("success"):
            print_success("Platform fee session created successfully")
            print_info(f"Session ID: {data['sessionId']}")
            print_info(f"Checkout URL: {data['checkoutUrl']}")
            print(f"\n{Colors.WARNING}To complete payment, visit:{Colors.ENDC}")
            print(f"{Colors.BOLD}{data['checkoutUrl']}{Colors.ENDC}\n")
            return True
        else:
            print_error(f"Failed to create session: {data.get('error')}")
            return False

    except Exception as e:
        print_error(f"Platform fee test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print_header("Stripe Checkout Integration Tests")

    if "--live" in sys.argv:
        print(f"{Colors.WARNING}⚠️  Running in LIVE mode - Real charges will occur!{Colors.ENDC}")
        confirmation = input("Type 'yes' to continue: ")
        if confirmation.lower() != 'yes':
            print("Aborted.")
            return
    else:
        print_info("Running in TEST mode (Stripe test credentials)")

    print_info(f"API Base URL: {API_BASE_URL}")

    # Run tests
    results = []

    results.append(("Health Check", test_health_check()))
    results.append(("Job Payment", test_job_payment()))
    results.append(("Rent Payment", test_rent_payment()))
    results.append(("Platform Fee", test_platform_fee()))

    # Summary
    print_header("Test Results Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.ENDC}")

    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}All tests passed! ✓{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}Some tests failed ✗{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
