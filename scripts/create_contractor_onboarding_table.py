#!/usr/bin/env python3
"""
Create DynamoDB table for contractor onboarding states.

This is the BILLION DOLLAR data model that ties everything together:
- contractor_id: Links to contractor record
- channel_id: Links to Stream Chat conversation
- token_id: Links to magic link token
- Stores all card submission data for rebuilding UI
"""

import boto3
import os
import sys

# Get environment
ENV = os.getenv("ENV", "dev")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

# Table name
TABLE_NAME = f"landten_{ENV}_contractor_onboarding_states"

def create_table():
    """Create the contractor onboarding states table."""
    dynamodb = boto3.client("dynamodb", region_name=AWS_REGION)

    try:
        response = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    "AttributeName": "state_id",
                    "KeyType": "HASH"  # Partition key
                }
            ],
            AttributeDefinitions=[
                {"AttributeName": "state_id", "AttributeType": "S"},
                {"AttributeName": "contractor_id", "AttributeType": "S"},
                {"AttributeName": "channel_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "contractor_id-index",
                    "KeySchema": [
                        {"AttributeName": "contractor_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                },
                {
                    "IndexName": "channel_id-index",
                    "KeySchema": [
                        {"AttributeName": "channel_id", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            },
            Tags=[
                {"Key": "Environment", "Value": ENV},
                {"Key": "Project", "Value": "LandTen"},
                {"Key": "Purpose", "Value": "ContractorOnboarding"}
            ]
        )

        print(f"✅ Table '{TABLE_NAME}' created successfully!")
        print(f"📊 Table ARN: {response['TableDescription']['TableArn']}")
        print(f"⏳ Waiting for table to become active...")

        # Wait for table to be active
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=TABLE_NAME)

        print(f"✅ Table '{TABLE_NAME}' is now active and ready!")
        print(f"\n🔍 Indexes created:")
        print(f"   - contractor_id-index (for querying by contractor)")
        print(f"   - channel_id-index (for querying by chat channel)")

        return True

    except dynamodb.exceptions.ResourceInUseException:
        print(f"ℹ️  Table '{TABLE_NAME}' already exists")
        return True

    except Exception as e:
        print(f"❌ Error creating table: {str(e)}")
        return False


def verify_table():
    """Verify the table exists and show its structure."""
    dynamodb = boto3.client("dynamodb", region_name=AWS_REGION)

    try:
        response = dynamodb.describe_table(TableName=TABLE_NAME)
        table = response["Table"]

        print(f"\n📋 Table Information:")
        print(f"   Name: {table['TableName']}")
        print(f"   Status: {table['TableStatus']}")
        print(f"   Item Count: {table['ItemCount']}")
        print(f"   Size: {table['TableSizeBytes']} bytes")

        print(f"\n🔑 Key Schema:")
        for key in table["KeySchema"]:
            print(f"   - {key['AttributeName']} ({key['KeyType']})")

        print(f"\n📊 Global Secondary Indexes:")
        for index in table.get("GlobalSecondaryIndexes", []):
            print(f"   - {index['IndexName']}")
            print(f"     Status: {index['IndexStatus']}")
            for key in index["KeySchema"]:
                print(f"     Key: {key['AttributeName']} ({key['KeyType']})")

        return True

    except dynamodb.exceptions.ResourceNotFoundException:
        print(f"❌ Table '{TABLE_NAME}' does not exist")
        return False

    except Exception as e:
        print(f"❌ Error verifying table: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Contractor Onboarding State Table Setup")
    print("=" * 60)
    print(f"Environment: {ENV}")
    print(f"AWS Region: {AWS_REGION}")
    print(f"Table Name: {TABLE_NAME}")
    print("=" * 60)

    # Create table
    if create_table():
        print("\n" + "=" * 60)
        verify_table()
        print("=" * 60)
        print("\n✅ Setup complete!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)
