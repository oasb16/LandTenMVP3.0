import os
import boto3
from botocore.config import Config


def get_dynamo_resource():
    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    endpoint_url = os.getenv("DYNAMO_ENDPOINT_URL")  # allow local dynamodb
    cfg = Config(retries={"max_attempts": 3, "mode": "standard"})
    return boto3.resource("dynamodb", region_name=region, endpoint_url=endpoint_url, config=cfg)


def table_name(base: str) -> str:
    prefix = os.getenv("TABLE_PREFIX", "landtenmvp")
    stage = os.getenv("STAGE", "dev")
    return f"{prefix}_{stage}_{base}"

