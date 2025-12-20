#!/usr/bin/env python3
"""
Script to create the magic-links DynamoDB table for contractor onboarding.
Run this once to set up the table.
"""
import os
import boto3
from botocore.exceptions import ClientError

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def create_magic_links_table():
    """Create the magic-links DynamoDB table."""

    # Get configuration from environment
    region = os.getenv("AWS_REGION", "us-east-1")
    table_prefix = os.getenv("TABLE_PREFIX", "landten")
    table_name = f"{table_prefix}-magic-links"

    print(f"Creating DynamoDB table: {table_name}")
    print(f"Region: {region}")

    # Initialize DynamoDB client
    dynamodb = boto3.client("dynamodb", region_name=region)

    try:
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName=table_name)
            print(f"✓ Table {table_name} already exists!")
            print(f"  Status: {response['Table']['TableStatus']}")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise

        # Create the table
        print(f"Creating table {table_name}...")
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'token_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'token_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )

        print(f"✓ Table {table_name} created successfully!")
        print(f"  ARN: {response['TableDescription']['TableArn']}")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        print("\nWaiting for table to become active...")

        # Wait for table to be active
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)

        print(f"✓ Table {table_name} is now active and ready to use!")

    except ClientError as e:
        print(f"✗ Error creating table: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        raise

if __name__ == "__main__":
    create_magic_links_table()
