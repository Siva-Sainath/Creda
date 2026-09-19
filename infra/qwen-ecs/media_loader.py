"""Load user-uploaded case images from S3 for multimodal judge calls."""
from __future__ import annotations

import base64
import logging
import os

import boto3

LOG = logging.getLogger(__name__)
MAX_IMAGES = 2
MAX_BYTES = 4 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/webp"}


def load_case_images(item: dict) -> list[dict]:
    bucket = os.environ.get("EVIDENCE_BUCKET", "")
    if not bucket:
        return []
    client = boto3.client("s3")
    images: list[dict] = []
    for attachment in (item.get("attachments") or [])[:MAX_IMAGES]:
        if not isinstance(attachment, dict):
            continue
        key = (attachment.get("s3Key") or attachment.get("key") or "").strip()
        content_type = (attachment.get("contentType") or "image/jpeg").strip().lower()
        if not key.startswith("cases/uploads/") or content_type not in ALLOWED:
            continue
        try:
            head = client.head_object(Bucket=bucket, Key=key)
            size = int(head.get("ContentLength") or 0)
            if size <= 0 or size > MAX_BYTES:
                continue
            body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
            images.append({
                "name": attachment.get("name") or "screenshot",
                "contentType": content_type,
                "base64": base64.b64encode(body).decode("ascii"),
            })
        except Exception:
            LOG.exception("Failed to load attachment key=%s", key)
    return images
