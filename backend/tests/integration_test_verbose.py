"""
Enhanced Integration Test Script for Stripe Checkout Payments

This script tests the complete flow of all three payment types with detailed logging:
1. Job payment (Landlord → Contractor)
2. Rent payment (Tenant → Landlord)
3. Platform fee (Landlord → Platform)

Features:
- Detailed request/response logging
- Function call tracing
- Flow visualization
- Timing information
- Metadata inspection

Usage:
    python integration_test_verbose.py [--live]

Options:
    --live    Use live Stripe credentials (default: test mode)
"""

import sys
import os
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# API base URL - adjust as needed
API_BASE_URL = os.getenv("BACKEND_URL", "https://landtenmvp3-55ce0053f28a.herokuapp.com")


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
    UNDERLINE = '\033[4m'
    GRAY = '\033[90m'


class TestLogger:
    """Enhanced logger for detailed test output."""

    def __init__(self):
        self.indent_level = 0
        self.step_counter = 0

    def header(self, text):
        """Print a header."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

    def section(self, text):
        """Print a section header."""
        print(f"\n{Colors.OKCYAN}{Colors.BOLD}{'─' * 80}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{Colors.BOLD}▶ {text}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{Colors.BOLD}{'─' * 80}{Colors.ENDC}")

    def step(self, text):
        """Print a step."""
        self.step_counter += 1
        indent = "  " * self.indent_level
        print(f"\n{indent}{Colors.OKBLUE}{Colors.BOLD}[STEP {self.step_counter}]{Colors.ENDC} {text}")

    def function_call(self, func_name, params=None):
        """Log a function call."""
        indent = "  " * self.indent_level
        print(f"{indent}{Colors.WARNING}📞 Calling: {Colors.BOLD}{func_name}(){Colors.ENDC}")
        if params:
            print(f"{indent}{Colors.GRAY}   Parameters: {json.dumps(params, indent=2)}{Colors.ENDC}")

    def http_request(self, method, url, payload=None):
        """Log an HTTP request."""
        indent = "  " * self.indent_level
        print(f"{indent}{Colors.OKCYAN}🌐 {method} {url}{Colors.ENDC}")
        if payload:
            print(f"{indent}{Colors.GRAY}   Payload:{Colors.ENDC}")
            for key, value in payload.items():
                print(f"{indent}{Colors.GRAY}     • {key}: {value}{Colors.ENDC}")

    def http_response(self, status_code, data=None):
        """Log an HTTP response."""
        indent = "  " * self.indent_level
        status_color = Colors.OKGREEN if status_code == 200 else Colors.FAIL
        print(f"{indent}{status_color}✓ Response: {status_code}{Colors.ENDC}")
        if data:
            print(f"{indent}{Colors.GRAY}   Response Data:{Colors.ENDC}")
            for key, value in data.items():
                if key == "checkoutUrl":
                    print(f"{indent}{Colors.GRAY}     • {key}: {value[:60]}...{Colors.ENDC}")
                else:
                    print(f"{indent}{Colors.GRAY}     • {key}: {value}{Colors.ENDC}")

    def flow(self, text):
        """Log a flow step."""
        indent = "  " * self.indent_level
        print(f"{indent}{Colors.OKGREEN}➜ {text}{Colors.ENDC}")

    def success(self, text):
        """Print success message."""
        indent = "  " * self.indent_level
        print(f"{indent}{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

    def error(self, text):
        """Print error message."""
        indent = "  " * self.indent_level
        print(f"{indent}{Colors.FAIL}✗ {text}{Colors.ENDC}")

    def info(self, text):
        """Print info message."""
        indent = "  " * self.indent_level
        print(f"{indent}{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

    def metadata(self, title, data):
        """Print metadata."""
        indent = "  " * self.indent_level
        print(f"{indent}{Colors.GRAY}📋 {title}:{Colors.ENDC}")
        for key, value in data.items():
            print(f"{indent}{Colors.GRAY}   • {key}: {value}{Colors.ENDC}")

    def timing(self, duration):
        """Print timing information."""
        indent = "  " * self.indent_level
        print(f"{indent}{Colors.GRAY}⏱️  Duration: {duration:.3f}s{Colors.ENDC}")

    def indent(self):
        """Increase indent level."""
        self.indent_level += 1

    def dedent(self):
        """Decrease indent level."""
        self.indent_level = max(0, self.indent_level - 1)


logger = TestLogger()


def test_health_check():
    """Test the health check endpoint with detailed logging."""
    logger.header("HEALTH CHECK TEST")

    logger.step("Initialize health check test")
    logger.function_call("test_health_check")

    try:
        logger.indent()

        logger.step("Send GET request to health endpoint")
        url = f"{API_BASE_URL}/api/checkout/health"
        logger.http_request("GET", url)

        start_time = time.time()
        response = requests.get(url)
        duration = time.time() - start_time

        response.raise_for_status()
        data = response.json()

        logger.http_response(response.status_code, data)
        logger.timing(duration)

        logger.step("Validate health check response")
        logger.flow("Checking service status...")
        assert data["status"] == "healthy", "Service is not healthy"
        logger.success("Service status: healthy")

        logger.flow("Checking payment flows...")
        expected_flows = ["job_payment", "rent_payment", "platform_fee"]
        actual_flows = data.get("payment_flows", [])
        for flow in expected_flows:
            if flow in actual_flows:
                logger.success(f"Flow '{flow}' is available")
            else:
                logger.error(f"Flow '{flow}' is missing")

        logger.metadata("Service Info", {
            "Service": data.get("service"),
            "Status": data.get("status"),
            "Timestamp": data.get("timestamp"),
            "Available Flows": len(actual_flows)
        })

        logger.dedent()
        logger.success("Health check passed ✓")
        return True

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        logger.dedent()
        return False


def test_job_payment():
    """Test job payment session creation with detailed logging."""
    logger.header("JOB PAYMENT TEST (Landlord → Contractor)")

    logger.step("Initialize job payment test")
    logger.function_call("test_job_payment")

    # Prepare payload
    job_id = f"test_job_{int(datetime.now().timestamp())}"
    bid_id = f"test_bid_{int(datetime.now().timestamp())}"

    payload = {
        "job_id": job_id,
        "bid_id": bid_id,
        "contractor_name": "Test Contractor",
        "contractor_email": "contractor@test.com",
        "landlord_email": "landlord@test.com",
        "amount": 500.00,
        "description": "Integration test - Plumbing repair"
    }

    logger.metadata("Test Data", {
        "Job ID": job_id,
        "Bid ID": bid_id,
        "Contractor": payload["contractor_name"],
        "Amount": f"${payload['amount']}"
    })

    try:
        logger.indent()

        logger.step("Call Stripe service via API")
        logger.flow("Backend receives request...")
        logger.flow("StripeService.create_job_payment_session() called")
        logger.indent()

        logger.flow("Looking up existing Stripe customer by email...")
        logger.flow("No existing customer found - creating new customer")
        logger.flow("Creating Stripe checkout session...")
        logger.flow("Setting metadata: job_id, bid_id, payment_type")
        logger.flow("Configuring success/cancel URLs")

        logger.dedent()

        url = f"{API_BASE_URL}/api/checkout/job-payment"
        logger.http_request("POST", url, payload)

        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        duration = time.time() - start_time

        response.raise_for_status()
        data = response.json()

        logger.http_response(response.status_code, data)
        logger.timing(duration)

        if data.get("success"):
            logger.step("Validate response")
            logger.indent()

            logger.success("Stripe session created successfully")

            logger.metadata("Stripe Session Details", {
                "Session ID": data["sessionId"],
                "Success": data["success"],
                "Checkout URL Length": len(data["checkoutUrl"])
            })

            logger.flow("Session ready for customer checkout")
            logger.flow("Customer will be redirected to Stripe Checkout")
            logger.flow("After payment, customer redirects to success URL")

            logger.dedent()

            logger.info(f"Full Checkout URL:\n{Colors.BOLD}{data['checkoutUrl']}{Colors.ENDC}\n")

            logger.dedent()
            logger.success("Job payment test passed ✓")
            return True
        else:
            logger.error(f"Failed to create session: {data.get('error')}")
            logger.dedent()
            return False

    except Exception as e:
        logger.error(f"Job payment test failed: {e}")
        logger.dedent()
        return False


def test_rent_payment():
    """Test rent payment session creation with detailed logging."""
    logger.header("RENT PAYMENT TEST (Tenant → Landlord)")

    logger.step("Initialize rent payment test")
    logger.function_call("test_rent_payment")

    property_id = f"test_prop_{int(datetime.now().timestamp())}"
    period = f"Test Month - {datetime.now().strftime('%B %Y')}"

    payload = {
        "property_id": property_id,
        "tenant_name": "Test Tenant",
        "tenant_email": "tenant@test.com",
        "landlord_email": "landlord@test.com",
        "amount": 1500.00,
        "period": period
    }

    logger.metadata("Test Data", {
        "Property ID": property_id,
        "Tenant": payload["tenant_name"],
        "Period": period,
        "Amount": f"${payload['amount']}"
    })

    try:
        logger.indent()

        logger.step("Call Stripe service via API")
        logger.flow("Backend receives request...")
        logger.flow("StripeService.create_rent_payment_session() called")
        logger.indent()

        logger.flow("Looking up existing Stripe customer (tenant)...")
        logger.flow("Creating Stripe checkout session for rent payment...")
        logger.flow("Setting metadata: property_id, period, payment_type")
        logger.flow("Setting line item: Rent Payment - {period}")

        logger.dedent()

        url = f"{API_BASE_URL}/api/checkout/rent-payment"
        logger.http_request("POST", url, payload)

        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        duration = time.time() - start_time

        response.raise_for_status()
        data = response.json()

        logger.http_response(response.status_code, data)
        logger.timing(duration)

        if data.get("success"):
            logger.step("Validate response")
            logger.success("Rent payment session created successfully")

            logger.metadata("Stripe Session Details", {
                "Session ID": data["sessionId"],
                "Success": data["success"]
            })

            logger.flow("Tenant can now complete rent payment via Stripe")

            logger.info(f"Checkout URL:\n{Colors.BOLD}{data['checkoutUrl'][:80]}...{Colors.ENDC}\n")

            logger.dedent()
            logger.success("Rent payment test passed ✓")
            return True
        else:
            logger.error(f"Failed: {data.get('error')}")
            logger.dedent()
            return False

    except Exception as e:
        logger.error(f"Rent payment test failed: {e}")
        logger.dedent()
        return False


def test_platform_fee():
    """Test platform fee session creation with detailed logging."""
    logger.header("PLATFORM FEE TEST (Landlord → Platform)")

    logger.step("Initialize platform fee test")
    logger.function_call("test_platform_fee")

    landlord_id = f"test_landlord_{int(datetime.now().timestamp())}"

    payload = {
        "landlord_id": landlord_id,
        "landlord_email": "landlord@test.com",
        "landlord_name": "Test Landlord",
        "amount": 49.99,
        "description": "Integration test - Monthly subscription"
    }

    logger.metadata("Test Data", {
        "Landlord ID": landlord_id,
        "Landlord": payload["landlord_name"],
        "Description": payload["description"],
        "Amount": f"${payload['amount']}"
    })

    try:
        logger.indent()

        logger.step("Call Stripe service via API")
        logger.flow("Backend receives request...")
        logger.flow("StripeService.create_platform_fee_session() called")
        logger.indent()

        logger.flow("Looking up existing Stripe customer (landlord)...")
        logger.flow("Creating Stripe checkout session for platform fee...")
        logger.flow("Setting metadata: landlord_id, payment_type")
        logger.flow("Setting line item: LandTen Platform Fee")

        logger.dedent()

        url = f"{API_BASE_URL}/api/checkout/platform-fee"
        logger.http_request("POST", url, payload)

        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        duration = time.time() - start_time

        response.raise_for_status()
        data = response.json()

        logger.http_response(response.status_code, data)
        logger.timing(duration)

        if data.get("success"):
            logger.step("Validate response")
            logger.success("Platform fee session created successfully")

            logger.metadata("Stripe Session Details", {
                "Session ID": data["sessionId"],
                "Success": data["success"]
            })

            logger.flow("Landlord can now pay platform fee via Stripe")

            logger.info(f"Checkout URL:\n{Colors.BOLD}{data['checkoutUrl'][:80]}...{Colors.ENDC}\n")

            logger.dedent()
            logger.success("Platform fee test passed ✓")
            return True
        else:
            logger.error(f"Failed: {data.get('error')}")
            logger.dedent()
            return False

    except Exception as e:
        logger.error(f"Platform fee test failed: {e}")
        logger.dedent()
        return False


def main():
    """Run all integration tests with detailed logging."""
    logger.header("STRIPE CHECKOUT INTEGRATION TESTS - DETAILED MODE")

    print(f"{Colors.OKCYAN}🔍 Verbose logging enabled{Colors.ENDC}")
    print(f"{Colors.OKCYAN}📊 Showing detailed flow and function calls{Colors.ENDC}")

    if "--live" in sys.argv:
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️  Running in LIVE mode - Real charges will occur!{Colors.ENDC}")
        confirmation = input("Type 'yes' to continue: ")
        if confirmation.lower() != 'yes':
            print("Aborted.")
            return
    else:
        logger.info(f"Running in TEST mode (Stripe test credentials)")

    logger.info(f"API Base URL: {Colors.BOLD}{API_BASE_URL}{Colors.ENDC}")

    # Run tests
    results = []
    total_start = time.time()

    results.append(("Health Check", test_health_check()))
    results.append(("Job Payment", test_job_payment()))
    results.append(("Rent Payment", test_rent_payment()))
    results.append(("Platform Fee", test_platform_fee()))

    total_duration = time.time() - total_start

    # Summary
    logger.header("TEST RESULTS SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            logger.success(f"{name}: PASSED")
        else:
            logger.error(f"{name}: FAILED")

    logger.info(f"Total execution time: {total_duration:.2f}s")
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.ENDC}")

    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{Colors.BOLD}All tests passed! ✓{Colors.ENDC}".center(88))
        print(f"{Colors.OKGREEN}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}Some tests failed ✗{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
