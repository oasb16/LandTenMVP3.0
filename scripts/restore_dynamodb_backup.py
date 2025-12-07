"""Placeholder for restoring DynamoDB backups during rollback."""

import sys


def main() -> int:
    print("No automated DynamoDB backup restore is configured. Skipping.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
