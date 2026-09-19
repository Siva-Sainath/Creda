#!/usr/bin/env python3
"""Minimal SageMaker VLM smoke test for creda-qwen-judge."""
from __future__ import annotations

import argparse
import json
import os
import sys

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=os.environ.get("CREDA_SM_ENDPOINT", "creda-qwen-judge"))
    args = parser.parse_args()
    region = os.environ.get("AWS_REGION", "ap-south-1")
    client = boto3.client("sagemaker-runtime", region_name=region)
    body = json.dumps({
        "messages": [
            {"role": "system", "content": "Reply with JSON only: {\"ok\":true}"},
            {"role": "user", "content": "Say ok in JSON."},
        ],
        "max_tokens": 32,
        "temperature": 0.0,
    }).encode("utf-8")
    response = client.invoke_endpoint(
        EndpointName=args.endpoint,
        Body=body,
        ContentType="application/json",
        Accept="application/json",
    )
    payload = response["Body"].read().decode("utf-8", errors="replace")
    print(payload[:500])
    if not payload.strip():
        sys.exit("empty response")
    print("SMOKE_OK")


if __name__ == "__main__":
    main()
