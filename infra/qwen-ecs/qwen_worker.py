"""Creda judge worker — gather-then-judge (Lambda tools, SageMaker VLM or local llama)."""
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from decimal import Decimal

import boto3
import httpx
from botocore.config import Config

from judge import JUDGE_SYSTEM_PROMPT, fallback_judgment, judge_packet, parse_judge_response
from media_loader import load_case_images
from vlm_inference import stream_vlm_judge
from vllm_local import stream_vllm_judge, vllm_healthy

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
SDK_CONFIG = Config(retries={"total_max_attempts": 2, "mode": "adaptive"}, connect_timeout=3, read_timeout=120)
SQS = boto3.client("sqs", config=SDK_CONFIG)
DDB = boto3.resource("dynamodb", config=SDK_CONFIG)
JUDGE_BACKEND = os.environ.get("JUDGE_BACKEND", "llama").strip().lower()
SAGEMAKER_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
LLAMA_URL = os.environ.get("LLAMA_URL", "http://127.0.0.1:8080/v1/chat/completions")
MAX_TOKENS = int(os.environ.get("QWEN_MAX_TOKENS", "256"))
INFER_TIMEOUT_S = int(os.environ.get("QWEN_INFER_TIMEOUT_S", "120"))
STREAM_FLUSH_CHARS = int(os.environ.get("QWEN_STREAM_FLUSH_CHARS", "28"))


def stream_llama_judge(packet: dict, item: dict, on_chunk) -> str:
    body = {
        "model": "qwen",
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False, separators=(",", ":"))},
        ],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "stream": True,
        "stop": ["\n\n\n"],
        "chat_template_kwargs": {"enable_thinking": False},
    }
    text_parts: list[str] = []
    last_flush = 0.0
    with httpx.stream("POST", LLAMA_URL, json=body, timeout=INFER_TIMEOUT_S) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if payload == "[DONE]":
                break
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            delta = event.get("choices", [{}])[0].get("delta", {}).get("content") or ""
            if not delta:
                continue
            text_parts.append(delta)
            joined = "".join(text_parts)
            now = time.time()
            if len(joined) - last_flush >= STREAM_FLUSH_CHARS or now - getattr(on_chunk, "_last_ts", 0) > 0.4:
                on_chunk(joined)
                on_chunk._last_ts = now
                last_flush = len(joined)
            if '"reasoning"' in joined and joined.count("{") and joined.rfind("}") > joined.find("{"):
                try:
                    parse_judge_response(joined, item)
                    break
                except (ValueError, json.JSONDecodeError):
                    pass
    return "".join(text_parts)


def stream_judge(packet: dict, item: dict, images: list[dict], on_chunk) -> str:
    if JUDGE_BACKEND == "vllm":
        if not vllm_healthy():
            raise RuntimeError("vLLM sidecar unhealthy")
        return stream_vllm_judge(
            JUDGE_SYSTEM_PROMPT,
            packet,
            images,
            on_chunk,
            max_tokens=MAX_TOKENS,
        )
    if JUDGE_BACKEND == "sagemaker":
        if not SAGEMAKER_ENDPOINT:
            raise RuntimeError("SAGEMAKER_ENDPOINT_NAME is required for sagemaker backend")
        return stream_vlm_judge(
            SAGEMAKER_ENDPOINT,
            AWS_REGION,
            JUDGE_SYSTEM_PROMPT,
            packet,
            images,
            on_chunk,
            max_tokens=MAX_TOKENS,
        )
    return stream_llama_judge(packet, item, on_chunk)


def _public_progress(stream_text: str, has_images: bool) -> str:
    if has_images and '"reasoning"' not in stream_text:
        return "Creda is reading your screenshot and official evidence"
    if '"reasoning"' in stream_text:
        return "Creda is writing your explanation from the evidence packet"
    if '"citedEvidenceIds"' in stream_text or '"headline"' in stream_text:
        return "Creda is citing official evidence in plain language"
    return "Creda is preparing your case explanation"


def write_stream(table, case_id: str, stream_text: str, has_images: bool) -> None:
    clipped = (stream_text or "")[-3500:]
    table.update_item(
        Key={"caseId": case_id},
        UpdateExpression=(
            "SET agentStatus = :streaming, agentProgress = :progress, "
            "agentStreamText = :stream, agentUpdatedAt = :now"
        ),
        ExpressionAttributeValues={
            ":streaming": "STREAMING",
            ":progress": _public_progress(stream_text, has_images),
            ":stream": clipped,
            ":now": int(time.time()),
        },
    )


def write_judgment(table, case_id: str, result: dict) -> None:
    presentation = result["presentation"]
    source = result.get("agentSource") or "creda"
    table.update_item(
        Key={"caseId": case_id},
        UpdateExpression=(
            "SET verdict = :verdict, headline = :headline, nextActions = :actions, "
            "agentStatus = :ready, agentSummary = :summary, agentFollowups = :followups, "
            "agentPresentation = :presentation, agentReasoning = :reasoning, "
            "agentConfidence = :confidence, agentCitedEvidence = :cited, "
            "agentGuardrailNote = :guardrail, agentSource = :source, agentUpdatedAt = :now, stage = :stage, "
            "agentProgress = :progress "
            "REMOVE agentStreamText"
        ),
        ExpressionAttributeValues={
            ":verdict": result["verdict"],
            ":headline": result["headline"],
            ":actions": result.get("nextActions") or [],
            ":ready": "READY",
            ":summary": presentation.get("explanation", {}).get("text", ""),
            ":followups": result.get("followUpQuestions") or [],
            ":presentation": presentation,
            ":reasoning": result.get("reasoning") or "",
            ":confidence": Decimal(str(result.get("confidence", 0.5))),
            ":cited": result.get("citedEvidenceIds") or [],
            ":guardrail": result.get("guardrailNote") or "",
            ":source": source,
            ":now": int(time.time()),
            ":stage": "complete",
            ":progress": "Judgment complete",
        },
    )


def process(case_id: str) -> None:
    table = DDB.Table(os.environ["CASES_TABLE_NAME"])
    item = table.get_item(Key={"caseId": case_id}, ConsistentRead=True).get("Item")
    if not item or item.get("status") != "COMPLETED":
        return
    images = load_case_images(item)
    table.update_item(
        Key={"caseId": case_id},
        UpdateExpression="SET agentStatus = :running, agentProgress = :progress REMOVE agentStreamText",
        ExpressionAttributeValues={
            ":running": "RUNNING",
            ":progress": "Creda started judgment" + (" with screenshot(s)" if images else ""),
        },
    )
    packet = judge_packet(item)
    if images:
        packet["userImageCount"] = len(images)

    def _judge() -> dict:
        def on_chunk(text: str) -> None:
            write_stream(table, case_id, text, bool(images))

        raw = stream_judge(packet, item, images, on_chunk)
        result = parse_judge_response(raw, item)
        if images and JUDGE_BACKEND in ("sagemaker", "vllm"):
            result["agentSource"] = "creda-vlm"
        elif JUDGE_BACKEND == "vllm":
            result["agentSource"] = "creda"
        return result

    try:
        LOG.info(
            "Judge start caseId=%s backend=%s images=%s packetBytes=%s",
            case_id,
            JUDGE_BACKEND,
            len(images),
            len(json.dumps(packet)),
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(_judge).result(timeout=INFER_TIMEOUT_S + 30)
    except (FuturesTimeout, Exception):
        LOG.exception("Judge failed caseId=%s; rule fallback", case_id)
        result = fallback_judgment(item)
    write_judgment(table, case_id, result)
    LOG.info("Judge done caseId=%s verdict=%s blocks=%s", case_id, result["verdict"], len(result["presentation"].get("blocks", [])))


def _wait_for_llama() -> None:
    for _ in range(120):
        try:
            if httpx.get("http://127.0.0.1:8080/health", timeout=5).is_success:
                return
        except httpx.HTTPError:
            pass
        time.sleep(5)
    raise RuntimeError("Qwen server did not become ready")


def _wait_for_vllm() -> None:
    for _ in range(180):
        if vllm_healthy():
            return
        time.sleep(5)
    raise RuntimeError("vLLM sidecar did not become healthy")


def main():
    if JUDGE_BACKEND == "llama":
        _wait_for_llama()
        LOG.info("Creda judge worker ready (llama.cpp backend)")
    elif JUDGE_BACKEND == "vllm":
        _wait_for_vllm()
        LOG.info("Creda judge worker ready (vLLM GPU backend)")
    else:
        LOG.info("Creda judge worker ready (SageMaker VLM backend endpoint=%s)", SAGEMAKER_ENDPOINT)
    while True:
        response = SQS.receive_message(
            QueueUrl=os.environ["QWEN_QUEUE_URL"],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=300,
        )
        for message in response.get("Messages", []):
            try:
                process(json.loads(message["Body"])["caseId"])
            except Exception:
                LOG.exception("Failed processing SQS message")
            finally:
                SQS.delete_message(
                    QueueUrl=os.environ["QWEN_QUEUE_URL"],
                    ReceiptHandle=message["ReceiptHandle"],
                )


if __name__ == "__main__":
    main()
