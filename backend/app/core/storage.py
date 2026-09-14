"""Object storage backed by S3/MinIO.

Provides random object keys (uuid, tenant/claim scoped) and 5-minute
pre-signed download URLs. The client is created lazily so importing the app
never requires the storage service to be reachable.
"""

from __future__ import annotations

import re
import uuid
from typing import Protocol
from uuid import UUID

from app.config import settings

_EXT_RE = re.compile(r"[^a-z0-9]")


def sanitize_extension(filename: str) -> str:
    """Lowercase alphanumeric extension from a filename, defaulting to 'bin'."""
    lower = filename.lower()
    if "." not in lower:
        return "bin"
    base = lower.rsplit(".", 1)[1]
    cleaned = _EXT_RE.sub("", base)[:8]
    return cleaned or "bin"


def random_object_key(tenant_id: UUID, claim_id: UUID, filename: str) -> str:
    """Unpredictable, scoped object key: tenants/{tenant}/claims/{claim}/attachments/{uuid}.{ext}."""
    return (
        f"tenants/{tenant_id}/claims/{claim_id}/attachments/"
        f"{uuid.uuid4().hex}.{sanitize_extension(filename)}"
    )


class ObjectStorage(Protocol):
    def put_object(self, key: str, data: bytes, content_type: str) -> None: ...
    def presign_download_url(self, key: str, expires_in: int) -> str: ...


class S3ObjectStorage:
    def __init__(self) -> None:
        import boto3

        self._bucket = settings.S3_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )

    def _ensure_bucket(self) -> None:
        existing = {b["Name"] for b in self._client.list_buckets().get("Buckets", [])}
        if self._bucket not in existing:
            self._client.create_bucket(Bucket=self._bucket)

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def presign_download_url(self, key: str, expires_in: int) -> str:
        return str(
            self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        )


object_storage: ObjectStorage = S3ObjectStorage()
