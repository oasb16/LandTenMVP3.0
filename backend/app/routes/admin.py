"""
Admin endpoints for database setup and management.

These endpoints help set up and manage DynamoDB tables.
"""

from fastapi import APIRouter, HTTPException
from botocore.exceptions import ClientError
import os
import logging

from ..deps.dynamo import get_dynamo_resource

# Configure router
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# Configure logging
logger = logging.getLogger(__name__)

def get_table_name(base_name: str) -> str:
    """Get table name with environment prefix."""
    env = os.getenv("ENVIRONMENT", "prod")
    return f"landten-{base_name}" if env == "prod" else f"landten-{env}-{base_name}"


@router.post("/setup/contractors-table")
async def create_contractors_table():
    """
    Create the contractors table in DynamoDB.

    This endpoint creates the contractors table with the following schema:
    - Primary Key: contractor_id (String)
    - GSI: email-index for looking up contractors by email

    Returns:
        Success message and table details
    """
    try:
        dynamodb = get_dynamo_resource()
        table_name = get_table_name("contractors")

        logger.info(f"[admin] Creating contractors table: {table_name}")

        # Check if table already exists
        try:
            existing_table = dynamodb.Table(table_name)
            existing_table.load()
            return {
                "status": "already_exists",
                "message": f"Table {table_name} already exists",
                "table_name": table_name,
                "table_status": existing_table.table_status
            }
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise

        # Create table
        table = dynamodb.create_table(
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
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
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
            }
        )

        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)

        logger.info(f"[admin] ✅ Table created successfully: {table_name}")

        return {
            "status": "created",
            "message": f"Table {table_name} created successfully",
            "table_name": table_name,
            "table_arn": table.table_arn,
            "table_status": table.table_status
        }

    except ClientError as e:
        logger.error(f"[admin] ❌ Failed to create table: {e.response['Error']['Message']}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create table: {e.response['Error']['Message']}"
        )
    except Exception as e:
        logger.error(f"[admin] ❌ Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/tables/status")
async def get_tables_status():
    """
    Get the status of all DynamoDB tables.

    Returns:
        Status information for each table
    """
    try:
        dynamodb = get_dynamo_resource()

        tables_to_check = ["contractors", "magic-links", "jobs", "bids"]
        status = {}

        for base_name in tables_to_check:
            table_name = get_table_name(base_name)
            try:
                table = dynamodb.Table(table_name)
                table.load()
                status[base_name] = {
                    "exists": True,
                    "table_name": table_name,
                    "status": table.table_status,
                    "item_count": table.item_count
                }
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    status[base_name] = {
                        "exists": False,
                        "table_name": table_name
                    }
                else:
                    status[base_name] = {
                        "exists": "unknown",
                        "error": e.response['Error']['Message']
                    }

        return {
            "environment": os.getenv("ENVIRONMENT", "prod"),
            "tables": status
        }

    except Exception as e:
        logger.error(f"[admin] ❌ Error checking tables: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking tables: {str(e)}"
        )
