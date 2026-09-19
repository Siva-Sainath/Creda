"""SageMaker JumpStart streaming inference for the Creda judge."""
from __future__ import annotations

import json
import logging
from typing import Callable

import boto3

LOG = logging.getLogger(__name__)


def _build_prompt(system: str, user: str) -> str:
    return (
        f"<|im_start|>system\n{system}\n"
        f"<|im_start|>user\n{user}\n"
        f"<|im_start|>assistant\n"
    )


def stream_sagemaker_judge(
    endpoint_name: str,
    region: str,
    system: str,
    user_payload: str,
    on_chunk: Callable[[str], None],
    max_tokens: int = 200,
) -> str:
    """Stream tokens from a JumpStart HuggingFace LLM endpoint."""
    client = boto3.client("sagemaker-runtime", region_name=region)
    prompt = _build_prompt(system, user_payload)
    body = json.dumps(
        {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.0,
                "top_p": 0.9,
                "return_full_text": False,
                "stop": [""],
            },
        }
    ).encode("utf-8")
    text_parts: list[str] = []
    response = client.invoke_endpoint_with_response_stream(
        EndpointName=endpoint_name,
        Body=body,
        ContentType="application/json",
    )
    for event in response["Body"]:
        if "PayloadPart" not in event:
            continue
        chunk = event["PayloadPart"]["Bytes"].decode("utf-8", errors="replace")
        for line in chunk.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            token = payload.get("token", {}).get("text") if isinstance(payload.get("token"), dict) else None
            if not token:
                token = payload.get("generated_text") or payload.get("outputs") or ""
                if isinstance(token, list):
                    token = token[0] if token else ""
            if not token:
                continue
            text_parts.append(str(token))
            on_chunk("".join(text_parts))
    return "".join(text_parts)
