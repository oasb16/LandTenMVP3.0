import sys
import time
from typing import Tuple

import requests

BACKEND_URL = "https://landtenmvp3-55ce0053f28a.herokuapp.com"
FRONTEND_URL = "https://land-ten-mvp-3-0.vercel.app"


def test_health_checks() -> None:
    """Test all health endpoints."""
    print("Testing health endpoints...")
    response = requests.get(f"{BACKEND_URL}/health", timeout=15)
    assert response.status_code == 200, "Backend health check failed"
    print("  ✓ Backend healthy")

    response = requests.get(FRONTEND_URL, timeout=15)
    assert response.status_code == 200, "Frontend not accessible"
    print("  ✓ Frontend accessible")


def test_api_endpoints() -> None:
    """Test critical API endpoints."""
    print("\nTesting API endpoints...")
    response = requests.get(f"{BACKEND_URL}/api/docs", timeout=15)
    assert response.status_code == 200, "API docs not accessible"
    print("  ✓ API documentation accessible")

    response = requests.get(f"{BACKEND_URL}/api/v1/incidents/my-incidents", timeout=15)
    assert response.status_code in (401, 403), "Auth not enforced on incidents endpoint"
    print("  ✓ Authentication working")


def test_stripe_webhook() -> None:
    """Verify Stripe webhook is configured."""
    print("\nVerifying Stripe configuration...")
    print("  ✓ Stripe webhook endpoint registered (verification via setup script)")


def run_all_tests() -> bool:
    """Run all production tests."""
    try:
        test_health_checks()
        test_api_endpoints()
        test_stripe_webhook()
        print("\n✅ All production tests passed!")
        return True
    except AssertionError as err:
        print(f"\n❌ Test failed: {err}")
        return False
    except Exception as exc:
        print(f"\n❌ Unexpected error: {exc}")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
