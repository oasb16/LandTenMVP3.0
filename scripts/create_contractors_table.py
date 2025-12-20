#!/usr/bin/env python3
"""
Create the contractors table in DynamoDB.

This table stores contractor profiles and registration information.
"""

import boto3
import os
import sys
from botocore.exceptions import ClientError

# Add parent directory to path to import from backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def get_table_name(base_name: str) -> str:
    """Get table name with environment prefix."""
    env = os.getenv("ENVIRONMENT", "dev")
    return f"landten-{base_name}" if env == "prod" else f"landten-{env}-{base_name}"

def create_contractors_table():
    """Create the contractors table in DynamoDB."""

    # Get AWS region
    region = os.getenv("AWS_REGION", "us-east-1")

    # Initialize DynamoDB client
    dynamodb = boto3.client('dynamodb', region_name=region)

    table_name = get_table_name("contractors")

    print(f"Creating DynamoDB table: {table_name}")
    print(f"Region: {region}")

    try:
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName=table_name)
            print(f"✓ Table already exists: {table_name}")
            print(f"  Status: {response['Table']['TableStatus']}")
            print(f"  Items: {response['Table']['ItemCount']}")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
            # Table doesn't exist, continue to create it

        # Create table
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'contractor_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'contractor_id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'  # String
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'email-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'email',
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
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Environment',
                    'Value': os.getenv('ENVIRONMENT', 'dev')
                },
                {
                    'Key': 'Application',
                    'Value': 'LandTen'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'Contractor profiles and registration'
                }
            ]
        )

        print(f"✓ Table creation initiated: {table_name}")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        print(f"\nWaiting for table to become active...")

        # Wait for table to be created
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(
            TableName=table_name,
            WaiterConfig={
                'Delay': 2,
                'MaxAttempts': 30
            }
        )

        print(f"✓ Table is now active: {table_name}")

        # Describe the final table
        response = dynamodb.describe_table(TableName=table_name)
        print(f"\nTable Details:")
        print(f"  ARN: {response['Table']['TableArn']}")
        print(f"  Status: {response['Table']['TableStatus']}")
        print(f"  Partition Key: contractor_id (String)")
        print(f"  GSI: email-index (for looking up contractors by email)")

    except ClientError as e:
        print(f"✗ Error creating table: {e.response['Error']['Message']}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Contractor Table Setup")
    print("=" * 60)
    print()

    create_contractors_table()

    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
