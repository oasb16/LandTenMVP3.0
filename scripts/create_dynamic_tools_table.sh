#!/bin/bash
# Create landten_dynamic_tools DynamoDB table
# Usage: ./scripts/create_dynamic_tools_table.sh [--stage prod]

STAGE=${1:-dev}
TABLE_NAME="landten_dynamic_tools"

echo "============================================================"
echo "Creating DynamoDB Table: $TABLE_NAME"
echo "Stage: $STAGE"
echo "============================================================"

aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
      AttributeName=tool_id,AttributeType=S \
      AttributeName=tool_name,AttributeType=S \
      AttributeName=category,AttributeType=S \
  --key-schema \
      AttributeName=tool_id,KeyType=HASH \
  --global-secondary-indexes \
      '[
        {
          "IndexName": "tool_name-index",
          "KeySchema": [{"AttributeName":"tool_name","KeyType":"HASH"}],
          "Projection": {"ProjectionType":"ALL"}
        },
        {
          "IndexName": "category-index",
          "KeySchema": [{"AttributeName":"category","KeyType":"HASH"}],
          "Projection": {"ProjectionType":"ALL"}
        }
      ]' \
  --billing-mode PAY_PER_REQUEST \
  --tags \
      Key=Environment,Value=$STAGE \
      Key=Application,Value=LandTenMVP \
      Key=Purpose,Value=DynamicToolPersistence \
  --region us-east-1

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✓ Table created successfully: $TABLE_NAME"
    echo "============================================================"
    echo ""
    echo "Waiting for table to become ACTIVE..."
    aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region us-east-1
    echo "✓ Table is now ACTIVE and ready to use"
else
    echo ""
    echo "============================================================"
    echo "✗ Failed to create table"
    echo "============================================================"
    echo ""
    echo "If the table already exists, this is expected."
    echo "Otherwise, check your AWS credentials and permissions."
fi
