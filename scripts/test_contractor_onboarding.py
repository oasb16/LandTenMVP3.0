#!/usr/bin/env python3
"""
Test script for contractor onboarding flow.

This script helps you test the complete magic link contractor onboarding system:
1. Create a magic link for a contractor
2. Verify the magic link
3. Test contractor registration
4. Test dashboard data retrieval

Usage:
    python scripts/test_contractor_onboarding.py
"""
import os
import requests
import json
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Colors for terminal output
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ {text}{RESET}")

def print_json(data):
    print(json.dumps(data, indent=2))


class ContractorOnboardingTester:
    """Test the contractor onboarding flow."""

    def __init__(self):
        self.backend_url = BACKEND_URL
        self.frontend_url = FRONTEND_URL
        self.magic_link_token = None
        self.magic_link_url = None
        self.contractor_id = None

    def test_1_create_magic_link(self):
        """Test creating a magic link for contractor invitation."""
        print_header("TEST 1: Create Magic Link")

        # Sample data - you can modify these
        payload = {
            "email": "testcontractor@example.com",
            "job_id": "job_test123",
            "landlord_id": "landlord_test456",
            "property_id": "prop_test789",
            "tenant_id": "tenant_test012"
        }

        print_info(f"Creating magic link for: {payload['email']}")
        print_info(f"Job ID: {payload['job_id']}")

        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/magic-links/create",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                self.magic_link_token = data['token']
                self.magic_link_url = data['magic_link_url']

                print_success("Magic link created successfully!")
                print(f"\nMagic Link URL:\n{self.magic_link_url}\n")
                print(f"Token: {self.magic_link_token}")
                print(f"Expires at: {data['expires_at']}")

                return True
            else:
                print_error(f"Failed to create magic link: {response.status_code}")
                print_json(response.json())
                return False

        except Exception as e:
            print_error(f"Error: {str(e)}")
            return False

    def test_2_verify_magic_link(self):
        """Test verifying a magic link token."""
        print_header("TEST 2: Verify Magic Link")

        if not self.magic_link_token:
            print_error("No magic link token available. Run test 1 first.")
            return False

        payload = {
            "token": self.magic_link_token
        }

        print_info(f"Verifying token: {self.magic_link_token[:20]}...")

        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/magic-links/verify",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()

                if data['valid']:
                    print_success("Token is valid!")
                    print(f"Email: {data['email']}")
                    print(f"Job ID: {data['job_id']}")
                    print(f"Message: {data['message']}")

                    if data.get('contractor_id'):
                        self.contractor_id = data['contractor_id']
                        print(f"Existing Contractor ID: {self.contractor_id}")
                    else:
                        print_info("New contractor - registration required")

                    return True
                else:
                    print_error(f"Token is invalid: {data['message']}")
                    return False
            else:
                print_error(f"Failed to verify token: {response.status_code}")
                print_json(response.json())
                return False

        except Exception as e:
            print_error(f"Error: {str(e)}")
            return False

    def test_3_register_contractor(self):
        """Test registering a new contractor."""
        print_header("TEST 3: Register New Contractor")

        if self.contractor_id:
            print_info("Contractor already exists, skipping registration")
            return True

        # Sample contractor data
        payload = {
            "business_name": "Test Plumbing Services",
            "email": "testcontractor@example.com",
            "phone": "(555) 123-4567",
            "categories": json.dumps(["plumbing", "hvac"]),
            "service_zip_codes": json.dumps(["10001", "10002", "10003"]),
            "license_number": "LIC-TEST-12345"
        }

        print_info(f"Registering contractor: {payload['business_name']}")

        try:
            # Note: This endpoint requires authentication in production
            # For testing, you may need to modify auth requirements
            response = requests.post(
                f"{self.backend_url}/api/v1/contractors/register",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    contractor_data = data['contractor']
                    self.contractor_id = contractor_data['contractor_id']

                    print_success("Contractor registered successfully!")
                    print(f"Contractor ID: {self.contractor_id}")
                    print(f"Business Name: {contractor_data['business_name']}")
                    print(f"Email: {contractor_data['email']}")
                    print(f"Status: {contractor_data['status']}")

                    # Mark magic link as used
                    self.mark_magic_link_used()

                    return True
                else:
                    print_error("Registration failed")
                    print_json(data)
                    return False
            else:
                print_error(f"Failed to register contractor: {response.status_code}")
                print(response.text)
                return False

        except Exception as e:
            print_error(f"Error: {str(e)}")
            return False

    def mark_magic_link_used(self):
        """Mark the magic link as used after registration."""
        if not self.magic_link_token or not self.contractor_id:
            return

        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/magic-links/mark-used/{self.magic_link_token}",
                params={"contractor_id": self.contractor_id}
            )

            if response.status_code == 200:
                print_success("Magic link marked as used")
            else:
                print_error(f"Failed to mark link as used: {response.status_code}")

        except Exception as e:
            print_error(f"Error marking link as used: {str(e)}")

    def test_4_get_dashboard_data(self):
        """Test retrieving contractor dashboard data."""
        print_header("TEST 4: Get Dashboard Data")

        if not self.contractor_id:
            print_error("No contractor ID available. Run previous tests first.")
            return False

        print_info(f"Fetching dashboard for contractor: {self.contractor_id}")

        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/magic-links/onboarding-dashboard/{self.contractor_id}"
            )

            if response.status_code == 200:
                data = response.json()

                print_success("Dashboard data retrieved successfully!")

                # Display contractor profile
                if data.get('contractor'):
                    print(f"\n{YELLOW}Contractor Profile:{RESET}")
                    contractor = data['contractor']
                    print(f"  Business Name: {contractor['business_name']}")
                    print(f"  Email: {contractor['email']}")
                    print(f"  Phone: {contractor['phone']}")
                    print(f"  Status: {contractor['status']}")
                    print(f"  Total Jobs: {contractor.get('total_jobs', 0)}")
                    print(f"  Completed Jobs: {contractor.get('completed_jobs', 0)}")

                # Display jobs summary
                if data.get('jobs'):
                    jobs = data['jobs']
                    print(f"\n{YELLOW}Jobs Summary:{RESET}")
                    print(f"  Available Jobs: {jobs['total_available']}")
                    print(f"  Active Jobs: {jobs['total_active']}")
                    print(f"  Completed Jobs: {jobs['total_completed']}")

                # Display bids summary
                if data.get('bids'):
                    bids = data['bids']
                    print(f"\n{YELLOW}Bids Summary:{RESET}")
                    print(f"  Total Bids Submitted: {bids['total']}")

                # Display payments summary
                if data.get('payments'):
                    payments = data['payments']
                    print(f"\n{YELLOW}Payments Summary:{RESET}")
                    print(f"  Total Earnings: ${payments['total_earnings']:.2f}")
                    print(f"  Pending Payments: ${payments['pending']:.2f}")
                    print(f"  Completed Payments: ${payments['completed']:.2f}")

                return True
            else:
                print_error(f"Failed to get dashboard data: {response.status_code}")
                print_json(response.json())
                return False

        except Exception as e:
            print_error(f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence."""
        print_header(f"Testing Contractor Onboarding Flow")
        print_info(f"Backend URL: {self.backend_url}")
        print_info(f"Frontend URL: {self.frontend_url}")

        results = []

        # Run tests in sequence
        results.append(("Create Magic Link", self.test_1_create_magic_link()))
        results.append(("Verify Magic Link", self.test_2_verify_magic_link()))
        results.append(("Register Contractor", self.test_3_register_contractor()))
        results.append(("Get Dashboard Data", self.test_4_get_dashboard_data()))

        # Print summary
        print_header("Test Results Summary")

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            if result:
                print_success(f"{test_name}")
            else:
                print_error(f"{test_name}")

        print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}\n")

        # Print next steps
        if passed == total:
            print_header("Next Steps - Manual Testing")
            print(f"1. Open the magic link in a browser:")
            print(f"   {self.magic_link_url}\n")
            print(f"2. You should see the contractor onboarding page")
            print(f"3. If contractor exists: Dashboard should load")
            print(f"4. If new contractor: Registration form should appear\n")

        return passed == total


def main():
    """Main test runner."""
    print(f"\n{BLUE}╔{'═'*58}╗{RESET}")
    print(f"{BLUE}║{' '*15}Contractor Onboarding Tester{' '*15}║{RESET}")
    print(f"{BLUE}╚{'═'*58}╝{RESET}")

    tester = ContractorOnboardingTester()
    success = tester.run_all_tests()

    exit(0 if success else 1)


if __name__ == "__main__":
    main()
