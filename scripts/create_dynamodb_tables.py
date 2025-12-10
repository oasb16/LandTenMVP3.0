#!/usr/bin/env python3
"""
Create DynamoDB tables for property management workflow system.

Creates 6 tables:
1. incidents - Tenant-reported incidents
2. jobs - Contractor job postings
3. bids - Contractor bids on jobs
4. contractors - Contractor profiles
5. payments - Payment transactions
6. conversation_mappings - Slack channel to OpenAI Conversation ID mappings

All tables use PAY_PER_REQUEST billing for cost efficiency.
Script is idempotent - safe to run multiple times.

Usage:
    python scripts/create_dynamodb_tables.py
    python scripts/create_dynamodb_tables.py --stage prod
    python scripts/create_dynamodb_tables.py --local
"""

import argparse
import os
import sys
from typing import Dict, Any, List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def get_table_prefix(stage: str) -> str:
    """Get table name prefix based on stage."""
    prefix = os.getenv("TABLE_PREFIX", "landten")
    return f"{prefix}_{stage}" if stage else prefix


def get_dynamodb_client(local: bool = False):
    """Get DynamoDB client with proper configuration."""
    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    endpoint_url = "http://localhost:8000" if local else os.getenv("DYNAMO_ENDPOINT_URL")

    cfg = Config(
        retries={"max_attempts": 3, "mode": "standard"},
        region_name=region
    )

    return boto3.client(
        "dynamodb",
        region_name=region,
        endpoint_url=endpoint_url,
        config=cfg
    )


def table_exists(client, table_name: str) -> bool:
    """Check if a table already exists."""
    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def create_incidents_table(client, table_name: str) -> None:
    """
    Create incidents table.

    Primary Key: incident_id (HASH)
    GSIs:
    - tenant_id-index: Query all incidents for a tenant
    - landlord_id-status-index: Query landlord's incidents by status
    - property_id-index: Query all incidents for a property
    - job_id-index: Find incident by job_id
    """
    print(f"Creating table: {table_name}")

    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "incident_id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "incident_id", "AttributeType": "S"},
                {"AttributeName": "tenant_id", "AttributeType": "S"},
                {"AttributeName": "landlord_id", "AttributeType": "S"},
                {"AttributeName": "property_id", "AttributeType": "S"},
                {"AttributeName": "job_id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "tenant_id-index",
                    "KeySchema": [
                        {"AttributeName": "tenant_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "landlord_id-status-index",
                    "KeySchema": [
                        {"AttributeName": "landlord_id", "KeyType": "HASH"},
                        {"AttributeName": "status", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "property_id-index",
                    "KeySchema": [
                        {"AttributeName": "property_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "job_id-index",
                    "KeySchema": [
                        {"AttributeName": "job_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Environment", "Value": os.getenv("STAGE", "dev")},
                {"Key": "Application", "Value": "LandTenMVP"},
                {"Key": "Purpose", "Value": "IncidentManagement"}
            ]
        )

        print(f"✓ Table {table_name} created successfully")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"⚠ Table {table_name} already exists")
        else:
            raise


def create_jobs_table(client, table_name: str) -> None:
    """
    Create jobs table.

    Primary Key: job_id (HASH)
    GSIs:
    - incident_id-index: Find job by incident
    - landlord_id-status-index: Query landlord's jobs by status
    - property_id-index: Query all jobs for a property
    - awarded_contractor_id-index: Query contractor's awarded jobs
    - stripe_payment_intent_id-index: Find job by Stripe payment
    """
    print(f"Creating table: {table_name}")

    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "job_id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "job_id", "AttributeType": "S"},
                {"AttributeName": "incident_id", "AttributeType": "S"},
                {"AttributeName": "landlord_id", "AttributeType": "S"},
                {"AttributeName": "property_id", "AttributeType": "S"},
                {"AttributeName": "awarded_contractor_id", "AttributeType": "S"},
                {"AttributeName": "stripe_payment_intent_id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "incident_id-index",
                    "KeySchema": [
                        {"AttributeName": "incident_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "landlord_id-status-index",
                    "KeySchema": [
                        {"AttributeName": "landlord_id", "KeyType": "HASH"},
                        {"AttributeName": "status", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "property_id-index",
                    "KeySchema": [
                        {"AttributeName": "property_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "awarded_contractor_id-index",
                    "KeySchema": [
                        {"AttributeName": "awarded_contractor_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "stripe_payment_intent_id-index",
                    "KeySchema": [
                        {"AttributeName": "stripe_payment_intent_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Environment", "Value": os.getenv("STAGE", "dev")},
                {"Key": "Application", "Value": "LandTenMVP"},
                {"Key": "Purpose", "Value": "JobManagement"}
            ]
        )

        print(f"✓ Table {table_name} created successfully")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"⚠ Table {table_name} already exists")
        else:
            raise


def create_bids_table(client, table_name: str) -> None:
    """
    Create bids table.

    Primary Key: bid_id (HASH)
    GSIs:
    - job_id-index: Query all bids for a job
    - contractor_id-index: Query all bids by a contractor
    - job_id-status-index: Query bids by job and status (e.g., submitted bids)
    """
    print(f"Creating table: {table_name}")

    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "bid_id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "bid_id", "AttributeType": "S"},
                {"AttributeName": "job_id", "AttributeType": "S"},
                {"AttributeName": "contractor_id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "job_id-index",
                    "KeySchema": [
                        {"AttributeName": "job_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "contractor_id-index",
                    "KeySchema": [
                        {"AttributeName": "contractor_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "job_id-status-index",
                    "KeySchema": [
                        {"AttributeName": "job_id", "KeyType": "HASH"},
                        {"AttributeName": "status", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Environment", "Value": os.getenv("STAGE", "dev")},
                {"Key": "Application", "Value": "LandTenMVP"},
                {"Key": "Purpose", "Value": "BidManagement"}
            ]
        )

        print(f"✓ Table {table_name} created successfully")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"⚠ Table {table_name} already exists")
        else:
            raise


def create_contractors_table(client, table_name: str) -> None:
    """
    Create contractors table.

    Primary Key: contractor_id (HASH)
    GSIs:
    - user_id-index: Find contractor profile by user_id
    - stripe_account_id-index: Find contractor by Stripe account
    """
    print(f"Creating table: {table_name}")

    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "contractor_id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "contractor_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "stripe_account_id", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "user_id-index",
                    "KeySchema": [
                        {"AttributeName": "user_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "stripe_account_id-index",
                    "KeySchema": [
                        {"AttributeName": "stripe_account_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Environment", "Value": os.getenv("STAGE", "dev")},
                {"Key": "Application", "Value": "LandTenMVP"},
                {"Key": "Purpose", "Value": "ContractorManagement"}
            ]
        )

        print(f"✓ Table {table_name} created successfully")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"⚠ Table {table_name} already exists")
        else:
            raise


def create_payments_table(client, table_name: str) -> None:
    """
    Create payments table.

    Primary Key: payment_id (HASH)
    GSIs:
    - job_id-index: Find payment by job
    - landlord_id-index: Query all payments by a landlord
    - contractor_id-index: Query all payments to a contractor
    - stripe_payment_intent_id-index: Find payment by Stripe PaymentIntent
    """
    print(f"Creating table: {table_name}")

    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "payment_id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "payment_id", "AttributeType": "S"},
                {"AttributeName": "job_id", "AttributeType": "S"},
                {"AttributeName": "landlord_id", "AttributeType": "S"},
                {"AttributeName": "contractor_id", "AttributeType": "S"},
                {"AttributeName": "stripe_payment_intent_id", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "job_id-index",
                    "KeySchema": [
                        {"AttributeName": "job_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "landlord_id-index",
                    "KeySchema": [
                        {"AttributeName": "landlord_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "contractor_id-index",
                    "KeySchema": [
                        {"AttributeName": "contractor_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "stripe_payment_intent_id-index",
                    "KeySchema": [
                        {"AttributeName": "stripe_payment_intent_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Environment", "Value": os.getenv("STAGE", "dev")},
                {"Key": "Application", "Value": "LandTenMVP"},
                {"Key": "Purpose", "Value": "PaymentProcessing"}
            ]
        )

        print(f"✓ Table {table_name} created successfully")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"⚠ Table {table_name} already exists")
        else:
            raise


def create_conversation_mappings_table(client, table_name: str) -> None:
    """
    Create conversation_mappings table.

    Maps Slack channels to OpenAI Conversation IDs for context persistence.
    Used by ResponseHandler/ConversationManager for Responses API integration.

    Primary Key: channel_id (HASH)
    No GSIs needed - simple key-value mapping
    """
    print(f"Creating table: {table_name}")

    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "channel_id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "channel_id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Environment", "Value": os.getenv("STAGE", "dev")},
                {"Key": "Application", "Value": "LandTenMVP"},
                {"Key": "Purpose", "Value": "ConversationPersistence"}
            ]
        )

        print(f"✓ Table {table_name} created successfully")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"⚠ Table {table_name} already exists")
        else:
            raise


def wait_for_table(client, table_name: str, max_attempts: int = 30) -> bool:
    """Wait for table to become active."""
    print(f"Waiting for {table_name} to become active...")

    for attempt in range(max_attempts):
        try:
            response = client.describe_table(TableName=table_name)
            status = response["Table"]["TableStatus"]

            if status == "ACTIVE":
                print(f"✓ {table_name} is ACTIVE")
                return True

            if attempt % 5 == 0:
                print(f"  Status: {status} (attempt {attempt + 1}/{max_attempts})")

            import time
            time.sleep(2)

        except ClientError as e:
            print(f"✗ Error checking table status: {e}")
            return False

    print(f"✗ Timeout waiting for {table_name}")
    return False


def verify_table(client, table_name: str) -> Dict[str, Any]:
    """Verify table creation and return details."""
    try:
        response = client.describe_table(TableName=table_name)
        table = response["Table"]

        gsi_count = len(table.get("GlobalSecondaryIndexes", []))
        item_count = table.get("ItemCount", 0)

        print(f"\n{'='*60}")
        print(f"Table: {table_name}")
        print(f"{'='*60}")
        print(f"Status: {table['TableStatus']}")
        print(f"Item Count: {item_count}")
        print(f"Global Secondary Indexes: {gsi_count}")

        if gsi_count > 0:
            print("\nGSIs:")
            for gsi in table["GlobalSecondaryIndexes"]:
                print(f"  - {gsi['IndexName']}")
                keys = " + ".join([k["AttributeName"] for k in gsi["KeySchema"]])
                print(f"    Keys: {keys}")

        return {
            "name": table_name,
            "status": table["TableStatus"],
            "gsi_count": gsi_count,
            "item_count": item_count
        }

    except ClientError as e:
        print(f"✗ Error verifying table {table_name}: {e}")
        return {"name": table_name, "status": "ERROR", "error": str(e)}


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Create DynamoDB tables for property management system"
    )
    parser.add_argument(
        "--stage",
        default=os.getenv("STAGE", "dev"),
        help="Deployment stage (dev, staging, prod)"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local DynamoDB (http://localhost:8000)"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"DynamoDB Table Creation - Stage: {args.stage}")
    print(f"{'='*60}\n")

    # Get DynamoDB client
    client = get_dynamodb_client(local=args.local)

    # Define tables to create
    tables = [
        ("incidents", create_incidents_table),
        ("jobs", create_jobs_table),
        ("bids", create_bids_table),
        ("contractors", create_contractors_table),
        ("payments", create_payments_table),
        ("conversation_mappings", create_conversation_mappings_table)
    ]

    # Create tables
    created_tables = []
    for base_name, create_func in tables:
        table_name = f"{get_table_prefix(args.stage)}_{base_name}"

        if table_exists(client, table_name):
            print(f"⚠ Table {table_name} already exists, skipping creation")
        else:
            create_func(client, table_name)
            created_tables.append(table_name)

    # Wait for tables to become active
    if created_tables:
        print(f"\n{'='*60}")
        print("Waiting for tables to become active...")
        print(f"{'='*60}\n")

        for table_name in created_tables:
            wait_for_table(client, table_name)

    # Verify all tables
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")

    results = []
    for base_name, _ in tables:
        table_name = f"{get_table_prefix(args.stage)}_{base_name}"
        result = verify_table(client, table_name)
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total tables: {len(results)}")
    active_count = sum(1 for r in results if r.get("status") == "ACTIVE")
    print(f"Active tables: {active_count}")

    if active_count == len(results):
        print("\n✓ All tables created and verified successfully!")
        return 0
    else:
        print("\n✗ Some tables failed to create or verify")
        return 1


if __name__ == "__main__":
    sys.exit(main())
