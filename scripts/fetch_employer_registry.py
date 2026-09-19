#!/usr/bin/env python3
"""Fetch employer policies and ATS boards from data/employer_registry.yaml."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANUAL = ROOT / "data" / "manual_snapshots"
REGISTRY = ROOT / "data" / "employer_registry.yaml"
RETRIEVAL = datetime.now(timezone.utc).strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json,application/pdf,*/*;q=0.8",
}


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_bytes(dest: Path, content: bytes) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(content)
    tmp.replace(dest)
    return sha256_file(dest)


def write_meta(dest: Path, meta: dict[str, Any]) -> None:
    sidecar = dest.with_suffix(dest.suffix + ".meta.json")
    sidecar.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def fetch_url(url: str, timeout: int = 60) -> tuple[bytes | None, int, str]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return resp.content, resp.status_code, str(resp.url)
    except requests.RequestException as exc:
        return None, 0, str(exc)


def fetch_policy(emp: dict[str, Any], report: dict[str, Any]) -> None:
    policy = emp.get("policy") or {}
    fetch = policy.get("fetch") or {}
    source_id = policy.get("source_id")
    if not source_id:
        return
    filename = fetch.get("filename", "index.html")
    dest = RAW / source_id / RETRIEVAL / filename
    method = fetch.get("method", "direct")

    if method == "manual":
        manual_name = fetch.get("manual_file")
        src = MANUAL / manual_name
        if not src.exists():
            report["failed"].append({"source_id": source_id, "reason": f"missing manual file {manual_name}"})
            return
        content = src.read_bytes()
        checksum = write_bytes(dest, content)
        write_meta(
            dest,
            {
                "source_id": source_id,
                "source_url": policy.get("canonical_url", ""),
                "downloaded_at": RETRIEVAL,
                "method": "manual_verified_snapshot",
                "checksum_sha256": checksum,
                "bytes": len(content),
            },
        )
        report["downloaded"].append({"source_id": source_id, "method": "manual", "bytes": len(content)})
        return

    url = fetch.get("url", "")
    if not url:
        report["failed"].append({"source_id": source_id, "reason": "no fetch url"})
        return
    content, status, final = fetch_url(url, timeout=90)
    if not content or status >= 400 or len(content) < 200:
        report["failed"].append({"source_id": source_id, "http_status": status, "url": url, "detail": final})
        return
    checksum = write_bytes(dest, content)
    write_meta(
        dest,
        {
            "source_id": source_id,
            "source_url": policy.get("canonical_url", url),
            "canonical_url": final,
            "downloaded_at": RETRIEVAL,
            "method": method,
            "checksum_sha256": checksum,
            "bytes": len(content),
            "http_status": status,
        },
    )
    report["downloaded"].append({"source_id": source_id, "method": method, "bytes": len(content)})


def fetch_ats(emp: dict[str, Any], report: dict[str, Any]) -> None:
    ats = emp.get("ats") or {}
    ats_type = ats.get("type")
    source_id = ats.get("source_id")
    if not ats_type or not source_id:
        return
    dest = RAW / source_id / RETRIEVAL / "jobs.json"
    if dest.exists() and dest.stat().st_size > 500:
        report["skipped"].append({"source_id": source_id, "reason": "exists"})
        return

    url = ""
    if ats_type == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{ats['board']}/jobs"
    elif ats_type == "lever":
        url = f"https://api.lever.co/v0/postings/{ats['site']}?mode=json"
    elif ats_type == "ashby":
        url = f"https://api.ashbyhq.com/posting-api/job-board/{ats['board']}"
    else:
        return

    content, status, final = fetch_url(url, timeout=45)
    if not content or status != 200 or len(content) < 300:
        report["failed"].append({"source_id": source_id, "http_status": status, "url": url})
        return
    checksum = write_bytes(dest, content)
    write_meta(
        dest,
        {
            "source_id": source_id,
            "source_url": url,
            "downloaded_at": RETRIEVAL,
            "method": f"{ats_type}_api",
            "checksum_sha256": checksum,
            "bytes": len(content),
        },
    )
    report["downloaded"].append({"source_id": source_id, "method": ats_type, "bytes": len(content)})


def main() -> None:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    report: dict[str, Any] = {"retrieval_date": RETRIEVAL, "downloaded": [], "failed": [], "skipped": []}

    for emp in registry.get("employers", []):
        fetch_policy(emp, report)
        fetch_ats(emp, report)

    out = ROOT / "data" / "reports" / "employer_fetch_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"downloaded": len(report["downloaded"]), "failed": len(report["failed"]), "skipped": len(report["skipped"])}, indent=2))
    sys.exit(0 if report["downloaded"] else 1)


if __name__ == "__main__":
    main()
