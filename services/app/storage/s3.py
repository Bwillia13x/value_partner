import json
import os
from datetime import datetime
from typing import Any, Dict

import boto3  # type: ignore

__all__ = ["put_json", "generate_key"]


def _client():
    """Return a cached boto3 S3 client using env credentials."""
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


BUCKET_NAME = os.getenv("RAW_DATA_BUCKET", "value-partner-raw")


def generate_key(symbol: str, provider_name: str, timestamp: str | None = None) -> str:
    """Convenience helper to build S3 object key path."""
    ts = timestamp or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"{symbol}/{provider_name}/{ts}.json"


def put_json(key: str, data: Dict[str, Any]) -> str:
    """Upload the given dict as JSON to S3 and return the s3:// URI."""
    body = json.dumps(data).encode()
    _client().put_object(Bucket=BUCKET_NAME, Key=key, Body=body)
    return f"s3://{BUCKET_NAME}/{key}"