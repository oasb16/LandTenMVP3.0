import os
import sys
from typing import Dict, List

REQUIRED_VARS: Dict[str, List[str]] = {
    "backend": [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
    ],
    "frontend": [
        "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY",
    ],
}


def validate_environment() -> bool:
    """Validate all required environment variables are set."""
    errors = []

    print("Checking backend environment variables...")
    for var in REQUIRED_VARS["backend"]:
        if not os.getenv(var):
            errors.append(f"Missing backend env var: {var}")
        else:
            print(f"  ✓ {var}")

    print("\nChecking frontend environment variables...")
    for var in REQUIRED_VARS["frontend"]:
        if not os.getenv(var):
            errors.append(f"Missing frontend env var: {var}")
        else:
            print(f"  ✓ {var}")

    if errors:
        print("\n❌ VALIDATION FAILED:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease set missing environment variables and try again.")
        return False

    print("\n✅ All environment variables are set!")
    return True


if __name__ == '__main__':
    success = validate_environment()
    sys.exit(0 if success else 1)
