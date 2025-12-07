#!/usr/bin/env python3
"""Production infrastructure automation for LandTen MVP 3.0.

Idempotently provisions DynamoDB tables, S3 buckets, and generates
production environment templates. Designed to run in CI/CD with no manual
steps required.
"""

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Reuse existing table definitions to stay consistent with the app schema
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

try:
    from create_dynamodb_tables import (
        create_bids_table,
        create_contractors_table,
        create_incidents_table,
        create_jobs_table,
        create_payments_table,
    )
except Exception:  # pragma: no cover - fallback if import fails
    print("❌ Unable to import table definitions from create_dynamodb_tables.py")
    sys.exit(1)


@dataclass
class TableDefinition:
    name: str
    creator: Callable


class ProductionSetup:
    def __init__(self) -> None:
        self.region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        self.stage = os.getenv("STAGE", "prod")
        self.table_prefix = os.getenv("TABLE_PREFIX", "landten")
        self.production_frontend = "https://land-ten-mvp-3-0.vercel.app"
        self.production_backend = "https://landtenmvp3-55ce0053f28a.herokuapp.com"

        cfg = Config(retries={"max_attempts": 5, "mode": "standard"}, region_name=self.region)
        self.dynamodb = boto3.client("dynamodb", region_name=self.region, config=cfg)
        self.s3 = boto3.client("s3", region_name=self.region, config=cfg)

        self.buckets = [
            "landten-incident-photos-prod",
            "landten-job-completion-photos-prod",
        ]
        self.table_definitions: List[TableDefinition] = [
            TableDefinition("incidents", create_incidents_table),
            TableDefinition("jobs", create_jobs_table),
            TableDefinition("bids", create_bids_table),
            TableDefinition("contractors", create_contractors_table),
            TableDefinition("payments", create_payments_table),
        ]

    # ---------------- DynamoDB -----------------
    def full_table_name(self, base_name: str) -> str:
        return f"{self.table_prefix}_{self.stage}_{base_name}"

    def ensure_dynamodb_tables(self) -> List[str]:
        """Create production DynamoDB tables if missing and wait for ACTIVE."""
        print("\n=== DynamoDB Setup ===")
        created: List[str] = []

        for definition in self.table_definitions:
            table_name = self.full_table_name(definition.name)
            if self._table_exists(table_name):
                print(f"✓ {table_name} already exists")
                continue

            print(f"Creating table: {table_name}")
            # Ensure tags show prod
            os.environ.setdefault("STAGE", self.stage)
            try:
                definition.creator(self.dynamodb, table_name)
                created.append(table_name)
            except ClientError as exc:
                print(f"❌ Failed to create {table_name}: {exc}")
                continue

        for table_name in created:
            self._wait_for_active(table_name)

        arns = self._collect_table_arns()
        print("\nDynamoDB table ARNs:")
        for name, arn in arns.items():
            print(f"  - {name}: {arn}")
        return created

    def _table_exists(self, table_name: str) -> bool:
        try:
            self.dynamodb.describe_table(TableName=table_name)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            raise

    def _wait_for_active(self, table_name: str, timeout: int = 300) -> None:
        print(f"Waiting for {table_name} to become ACTIVE...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = self.dynamodb.describe_table(TableName=table_name)
                status = resp["Table"]["TableStatus"]
                if status == "ACTIVE":
                    print(f"✓ {table_name} is ACTIVE")
                    return
                time.sleep(5)
            except ClientError as exc:
                print(f"⚠️  Error polling {table_name}: {exc}")
                time.sleep(5)
        print(f"❌ Timeout waiting for {table_name} to become ACTIVE")

    def _collect_table_arns(self) -> Dict[str, str]:
        arns: Dict[str, str] = {}
        for definition in self.table_definitions:
            table_name = self.full_table_name(definition.name)
            try:
                resp = self.dynamodb.describe_table(TableName=table_name)
                arns[table_name] = resp["Table"].get("TableArn", "<unknown>")
            except ClientError as exc:
                arns[table_name] = f"error: {exc}"  # pragma: no cover - telemetry only
        return arns

    # ---------------- S3 -----------------
    def ensure_buckets(self) -> None:
        print("\n=== S3 Setup ===")
        for bucket in self.buckets:
            exists = self._bucket_exists(bucket)
            if not exists:
                self._create_bucket(bucket)
            self._enable_versioning(bucket)
            self._apply_lifecycle(bucket)
            self._apply_cors(bucket)
            self._apply_bucket_policy(bucket)
            print(f"✓ Bucket ready: s3://{bucket}")

        print("\nBucket URLs:")
        for bucket in self.buckets:
            print(f"  - https://{bucket}.s3.amazonaws.com")

    def _bucket_exists(self, bucket: str) -> bool:
        try:
            self.s3.head_bucket(Bucket=bucket)
            print(f"✓ Bucket exists: {bucket}")
            return True
        except ClientError:
            print(f"ℹ️  Bucket missing, will create: {bucket}")
            return False

    def _create_bucket(self, bucket: str) -> None:
        params = {"Bucket": bucket}
        if self.region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": self.region}
        self.s3.create_bucket(**params)
        print(f"✅ Created bucket: {bucket}")

    def _enable_versioning(self, bucket: str) -> None:
        self.s3.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )

    def _apply_lifecycle(self, bucket: str) -> None:
        rules = {
            "Rules": [
                {
                    "ID": "auto-delete-90-days",
                    "Prefix": "",
                    "Status": "Enabled",
                    "Expiration": {"Days": 90},
                    "NoncurrentVersionExpiration": {"NoncurrentDays": 90},
                }
            ]
        }
        self.s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration=rules)

    def _apply_cors(self, bucket: str) -> None:
        allowed_origins = [self.production_frontend, self.production_backend]
        cors = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
                    "AllowedOrigins": allowed_origins,
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3000,
                }
            ]
        }
        self.s3.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors)

    def _apply_bucket_policy(self, bucket: str) -> None:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "EnforceTLS",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
                    "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                },
                {
                    "Sid": "AllowPresigned",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject", "s3:PutObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                },
            ],
        }
        self.s3.put_bucket_policy(Bucket=bucket, Policy=json_dumps(policy))

    # ---------------- Environment -----------------
    def generate_env_template(self) -> None:
        template_path = Path(".env.production.template")
        content = f"""# LandTen MVP 3.0 Production Environment
# Fill in the values and load them into CI/CD secrets (do not commit real secrets).

# --- AWS ---
AWS_ACCESS_KEY_ID=<your_aws_access_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>
AWS_REGION={self.region}
TABLE_PREFIX={self.table_prefix}
STAGE={self.stage}

# --- STRIPE ---
STRIPE_SECRET_KEY=<sk_live_...>
STRIPE_WEBHOOK_SECRET=<filled_automatically_by_setup_script>
STRIPE_CONNECT_CLIENT_ID=<ca_xxx>
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=<pk_live_...>

# --- BACKEND ---
BACKEND_URL={self.production_backend}
FRONTEND_URL={self.production_frontend}
S3_INCIDENT_BUCKET=landten-incident-photos-prod
S3_COMPLETION_BUCKET=landten-job-completion-photos-prod

# --- STREAM (optional) ---
STREAM_CHAT_API_KEY=<stream_key>
STREAM_CHAT_API_SECRET=<stream_secret>
STREAM_WEBHOOK_URL={self.production_backend}/ai/stream-webhook

# --- OBSERVABILITY ---
SENTRY_DSN=<sentry_dsn_optional>
"""
        template_path.write_text(content)
        print(f"✓ Wrote env template to {template_path}")

    # ---------------- Verification -----------------
    def verify_setup(self) -> None:
        print("\n=== Verification ===")
        try:
            tables = self.dynamodb.list_tables().get("TableNames", [])
            prod_tables = [t for t in tables if t.startswith(f"{self.table_prefix}_{self.stage}")]
            print(f"DynamoDB tables present: {len(prod_tables)} -> {', '.join(prod_tables)}")
        except Exception as exc:  # pragma: no cover - network/runtime guard
            print(f"⚠️  Could not list DynamoDB tables: {exc}")

        try:
            buckets = [b["Name"] for b in self.s3.list_buckets().get("Buckets", [])]
            for bucket in self.buckets:
                status = "present" if bucket in buckets else "missing"
                print(f"Bucket {bucket}: {status}")
        except Exception as exc:  # pragma: no cover
            print(f"⚠️  Could not list buckets: {exc}")


def json_dumps(data: Dict) -> str:
    import json

    return json.dumps(data)


def ensure_aws_credentials() -> None:
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("❌ AWS credentials are required in the environment")
        sys.exit(1)


def main() -> int:
    ensure_aws_credentials()
    setup = ProductionSetup()

    setup.ensure_dynamodb_tables()
    setup.ensure_buckets()
    setup.generate_env_template()
    setup.verify_setup()

    print("\n✅ Production infrastructure setup complete")
    print("Use scripts/setup_stripe_webhook.py to register Stripe webhook.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
