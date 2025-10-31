#!/usr/bin/env python3
"""
Initialize DynamoDB Table for Chat Contexts

This script creates the `landtenmvp_{stage}_chat_contexts` table
required by the Context Manager for persistent conversational memory.

Usage:
    python scripts/init_context_table.py [--stage dev|prod] [--local]

Options:
    --stage: Environment stage (default: dev)
    --local: Use local DynamoDB endpoint (default: from env)
"""

import os
import sys
import argparse
import boto3
from botocore.exceptions import ClientError


def get_table_name(stage: str) -> str:
    """Get the table name for the given stage."""
    prefix = os.getenv("TABLE_PREFIX", "landtenmvp")
    return f"{prefix}_{stage}_chat_contexts"


def create_context_table(stage: str = "dev", local: bool = False):
    """
    Create the chat contexts DynamoDB table.

    Table Schema:
        - Partition Key: context_id (String) - Format: "user_id:channel_id"
        - TTL: expires_at (Number) - Unix timestamp for automatic expiration

    Global Secondary Indexes:
        - user_id-index: Allows querying all contexts for a user
        - channel_id-index: Allows querying all contexts in a channel
    """
    table_name = get_table_name(stage)

    # Determine endpoint
    if local or os.getenv("DYNAMO_ENDPOINT_URL"):
        endpoint_url = os.getenv("DYNAMO_ENDPOINT_URL", "http://localhost:8000")
        print(f"🔗 Using local DynamoDB endpoint: {endpoint_url}")
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url=endpoint_url,
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
    else:
        print(f"🌐 Using AWS DynamoDB in region: {os.getenv('AWS_REGION', 'us-east-1')}")
        dynamodb = boto3.client(
            'dynamodb',
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

    # Check if table already exists
    try:
        response = dynamodb.describe_table(TableName=table_name)
        print(f"✅ Table '{table_name}' already exists!")
        print(f"   Status: {response['Table']['TableStatus']}")
        print(f"   Items: {response['Table']['ItemCount']}")
        return
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            print(f"❌ Error checking table existence: {e}")
            sys.exit(1)

    # Create table
    print(f"📦 Creating table '{table_name}'...")

    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'context_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'context_id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'channel_id',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user_id-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'channel_id-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'channel_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Environment',
                    'Value': stage
                },
                {
                    'Key': 'Application',
                    'Value': 'PropertyAI-LandTen'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'Conversational Context Storage'
                }
            ]
        )

        print(f"✅ Table '{table_name}' created successfully!")
        print(f"   ARN: {table['TableDescription']['TableArn']}")
        print(f"   Status: {table['TableDescription']['TableStatus']}")

        # Wait for table to be active
        print("⏳ Waiting for table to become active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)

        print("✅ Table is now active!")

        # Enable TTL
        print("⏰ Enabling TTL on 'expires_at' attribute...")
        try:
            dynamodb.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': 'expires_at'
                }
            )
            print("✅ TTL enabled successfully!")
        except ClientError as e:
            print(f"⚠️  Warning: Could not enable TTL: {e}")
            print("   (TTL may not be supported on local DynamoDB)")

    except ClientError as e:
        print(f"❌ Error creating table: {e}")
        sys.exit(1)

    print("\n🎉 Context table initialization complete!")
    print(f"\n📊 Table Details:")
    print(f"   Name: {table_name}")
    print(f"   Partition Key: context_id (user_id:channel_id)")
    print(f"   GSI: user_id-index")
    print(f"   GSI: channel_id-index")
    print(f"   TTL: expires_at (automatic cleanup)")


def main():
    parser = argparse.ArgumentParser(
        description="Initialize DynamoDB table for chat contexts"
    )
    parser.add_argument(
        '--stage',
        type=str,
        default='dev',
        choices=['dev', 'prod'],
        help='Environment stage (default: dev)'
    )
    parser.add_argument(
        '--local',
        action='store_true',
        help='Use local DynamoDB endpoint'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  PropertyAI Context Table Initialization")
    print("=" * 60)
    print(f"Stage: {args.stage}")
    print(f"Local: {args.local}")
    print("=" * 60)
    print()

    create_context_table(stage=args.stage, local=args.local)


if __name__ == "__main__":
    main()
