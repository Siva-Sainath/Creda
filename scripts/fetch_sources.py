#!/usr/bin/env python3
"""Download and snapshot Creda source files with immutable raw-byte preservation."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RETRIEVAL = datetime.now(timezone.utc).strftime("%Y-%m-%d")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# source_id -> (url, relative_filename, optional_content_type_hint)
DOWNLOADS: dict[str, tuple[str, str, str | None]] = {
    "ftc_job_scams": (
        "https://consumer.ftc.gov/articles/job-scams",
        "index.html",
        "text/html",
    ),
    "google_recruitment_fraud_policy": (
        "https://careers.google.com/how-we-hire/recruitment-fraud/",
        "index.html",
        "text/html",
    ),
    "ic3_annual_report_2024": (
        "https://www.ic3.gov/Media/PDF/AnnualReport/2024_IC3Report.pdf",
        "report.pdf",
        "application/pdf",
    ),
    "ncsc_phishing_guidance": (
        "https://www.ncsc.gov.uk/collection/phishing-scams",
        "index.html",
        "text/html",
    ),
    "emigrate_portal": (
        "https://emigrate.gov.in/ext/home",
        "index.html",
        "text/html",
    ),
    "i4c_cybercrime_portal": (
        "https://cybercrime.gov.in",
        "index.html",
        "text/html",
    ),
    "greenhouse_stripe_jobs": (
        "https://boards-api.greenhouse.io/v1/boards/stripe/jobs",
        "jobs.json",
        "application/json",
    ),
    "greenhouse_airbnb_jobs": (
        "https://boards-api.greenhouse.io/v1/boards/airbnb/jobs",
        "jobs.json",
        "application/json",
    ),
    "greenhouse_discord_jobs": (
        "https://boards-api.greenhouse.io/v1/boards/discord/jobs",
        "jobs.json",
        "application/json",
    ),
    "ashby_notion_jobs": (
        "https://api.ashbyhq.com/posting-api/job-board/notion",
        "jobs.json",
        "application/json",
    ),
    "amazon_recruitment_fraud_policy": (
        "https://amazon.jobs/content/en/how-we-hire/fraud-alert-india",
        "index.html",
        "text/html",
    ),
    "amazon_jobs": (
        "https://www.amazon.jobs/",
        "index.html",
        "text/html",
    ),
    "yc_jobs": (
        "https://www.ycombinator.com/jobs/",
        "index.html",
        "text/html",
    ),
    "mea_overseas_employment": (
        "https://www.mea.gov.in/overseas-employment.htm",
        "index.html",
        "text/html",
    ),
    "greenhouse_job_board_api": (
        "https://developers.greenhouse.io/job-board.html",
        "index.html",
        "text/html",
    ),
    "lever_postings_api": (
        "https://github.com/lever/postings-api",
        "index.html",
        "text/html",
    ),
    "i4c_captcha_advisory_2025": (
        "https://cybercrime.gov.in/Webform/theme/resources/advisories/ADVISORY%20TAU-ADV-004_Captcha%20Filling%20Fraud_08.04.2025.pdf",
        "advisory.pdf",
        "application/pdf",
    ),
    "nasc_job_scam_fusion_report_2025": (
        "https://www.nasc.gov.au/system/files/nasc-job-scam-fusion-cell-final-report-2025.pdf",
        "report.pdf",
        "application/pdf",
    ),
    "i4c_fake_job_sms_advisory": (
        "https://cybercrime.gov.in/Webform/theme/resources/advisories/FraudsterssendingFakeJobOfferSMSstoperpetrateCybercrime.pdf",
        "advisory.pdf",
        "application/pdf",
    ),
    "i4c_handbook_2025": (
        "https://cdnbbsr.s3waas.gov.in/s303412aef4dcdee4f934f7bf599f89783/uploads/2025/07/20250701709992826.pdf",
        "handbook.pdf",
        "application/pdf",
    ),
    "cyberdost_job_fraud_tips": (
        "https://cytrain.ncrb.gov.in/staticpage/pdf/Cyber-security-tips-by-cyber-dost.pdf",
        "tips.pdf",
        "application/pdf",
    ),
    "mea_yangon_overseas_job_scam_2024": (
        "https://embassyofindiayangon.gov.in/public_files/assets/pdf/yangon_3july2024_popup.pdf",
        "advisory.pdf",
        "application/pdf",
    ),
    "ca_ag_job_scam_alert_2025": (
        "https://oag.ca.gov/news/press-releases/attorney-general-bonta-alerts-californians-job-recruitment-scams",
        "index.html",
        "text/html",
    ),
    "scamwatch_au_job_scams": (
        "https://www.scamwatch.gov.au/types-of-scams/jobs-and-employment-scams",
        "index.html",
        "text/html",
    ),
    "kpmg_recruitment_fraud_policy": (
        "https://kpmg.com/in/en/media/press-releases/2024/12/important-recruitment-fraud-alert.html",
        "index.html",
        "text/html",
    ),
    "netapp_recruitment_fraud_policy": (
        "https://www.netapp.com/responsibility/trust-center/security/recruitment-scam-warning-fraud-alert/",
        "index.html",
        "text/html",
    ),
    "amex_recruitment_fraud_policy": (
        "https://www.americanexpress.com/en-us/careers/recruitment-fraud/",
        "index.html",
        "text/html",
    ),
    "valero_recruitment_scams_2025": (
        "https://www.valero.com/sites/default/files/valero-documents/2025-10/Recruiting%20Scams_Careers%20Legal%20Document.pdf",
        "policy.pdf",
        "application/pdf",
    ),
    "greenhouse_shopify_jobs": (
        "https://boards-api.greenhouse.io/v1/boards/coinbase/jobs",
        "jobs.json",
        "application/json",
    ),
    "greenhouse_figma_jobs": (
        "https://boards-api.greenhouse.io/v1/boards/figma/jobs",
        "jobs.json",
        "application/json",
    ),
    "greenhouse_databricks_jobs": (
        "https://boards-api.greenhouse.io/v1/boards/databricks/jobs",
        "jobs.json",
        "application/json",
    ),
    "wipro_recruitment_fraud_policy": (
        "https://careers.wipro.com/content/Recruitment-Fraud-Alert/?locale=en_US",
        "index.html",
        "text/html",
    ),
    "lever_spotify_jobs": (
        "https://api.lever.co/v0/postings/spotify?mode=json",
        "jobs.json",
        "application/json",
    ),
    "smartrecruiters_api_docs": (
        "https://developers.smartrecruiters.com/docs/get-job-by-id",
        "index.html",
        "text/html",
    ),
    "linkedin_job_scam_guidance": (
        "https://www.linkedin.com/help/linkedin/answer/a1336384",
        "index.html",
        "text/html",
    ),
}

# Attempted but often blocked; recorded for registry status updates.
PROBE_ONLY = {
    "action_fraud_uk_jobs": "https://www.actionfraud.police.uk/a-z-of-fraud/fake-jobs-and-work-from-home-scams",
    "infosys_recruitment_fraud_policy": "https://www.infosys.com/careers/recruitment-fraud-alert.html",
    "tcs_recruitment_fraud_policy": "https://www.tcs.com/careers/india/recruitment-fraud-alert",
    "microsoft_recruitment_fraud_alert": "https://www.microsoft.com/en-us/trust-center/security/recruitment-fraud-alert",
    "wipro_recruitment_fraud_policy": "https://careers.wipro.com/content/Recruitment-Fraud-Alert/?locale=en_US",
    "ftc_job_scams_archive": "https://www.ftc.gov/news-events/data-visualizations/data-spotlight/2025/01/new-data-show-consumers-lost-12-billion-scams-2024",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_immutable(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(content)
    tmp.replace(path)
    return sha256_file(path)


def download_url(url: str, timeout: int = 60) -> tuple[bytes | None, int, str]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return resp.content, resp.status_code, str(resp.url)
    except requests.RequestException as exc:
        return None, 0, str(exc)


def refresh_cafc() -> dict[str, Any]:
    """Refresh CAFC open-government CSV if missing or stale."""
    dest_dir = RAW / "cafc_fraud_reports" / RETRIEVAL
    dest = dest_dir / "cafc.csv"
    meta_path = RAW / "cafc_fraud_reports" / "download_meta.json"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return {
            "source_id": "cafc_fraud_reports",
            "status": "skipped_existing",
            "path": str(dest.relative_to(ROOT)),
            "checksum": sha256_file(dest),
        }
    url = "https://open.canada.ca/data/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f/resource/7c0f6125-4ae7-4c44-9063-f2adcf1f3a81/download/cafc-fraud-reporting-system.csv"
    content, status, final = download_url(url, timeout=180)
    if not content or status != 200:
        return {"source_id": "cafc_fraud_reports", "status": "failed", "http_status": status, "detail": final}
    checksum = write_immutable(dest, content)
    meta_path.write_text(json.dumps({"url": url, "final_url": final, "checksum": checksum, "downloaded_at": RETRIEVAL}, indent=2))
    return {"source_id": "cafc_fraud_reports", "status": "downloaded", "path": str(dest.relative_to(ROOT)), "checksum": checksum}


def refresh_huggingface_difraud() -> dict[str, Any]:
    dest_dir = RAW / "difraud_job_scams" / RETRIEVAL
    if all((dest_dir / f"{split}.jsonl").exists() for split in ("train", "validation", "test")):
        return {"source_id": "difraud_job_scams", "status": "skipped_existing"}
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for split in ("train", "validation", "test"):
        url = f"https://huggingface.co/datasets/difraud/difraud/resolve/main/job_scams/{split}.jsonl"
        content, status, final = download_url(url, timeout=120)
        if not content or status != 200:
            results.append({"split": split, "status": "failed", "http_status": status})
            continue
        dest = dest_dir / f"{split}.jsonl"
        checksum = write_immutable(dest, content)
        results.append({"split": split, "status": "downloaded", "checksum": checksum})
    return {"source_id": "difraud_job_scams", "splits": results}


def refresh_emscad() -> dict[str, Any]:
    dest_dir = RAW / "emscad" / RETRIEVAL
    dest = dest_dir / "DataSet.csv"
    if dest.exists():
        return {"source_id": "emscad", "status": "skipped_existing", "checksum": sha256_file(dest)}
    try:
        import kaggle  # type: ignore
    except ImportError:
        return {"source_id": "emscad", "status": "skipped_no_kaggle", "note": "existing snapshot retained if present"}
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        kaggle.api.authenticate()
        kaggle.api.dataset_download_files("shivamb/real-or-fake-fake-jobposting-prediction", path=str(dest_dir), unzip=True)
    except Exception as exc:
        return {"source_id": "emscad", "status": "failed", "detail": str(exc)}
    csvs = list(dest_dir.glob("*.csv"))
    if not csvs:
        return {"source_id": "emscad", "status": "failed", "detail": "no csv after download"}
    if csvs[0].name != "DataSet.csv":
        csvs[0].replace(dest)
    return {"source_id": "emscad", "status": "downloaded", "checksum": sha256_file(dest)}


def refresh_scambench() -> dict[str, Any]:
    dest_dir = RAW / "scambench_employment" / RETRIEVAL
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for split, url in {
        "employment_scam": "https://huggingface.co/datasets/Shouninger/ScamBench/resolve/main/Scam/Employment.csv",
        "employment_nonscam": "https://huggingface.co/datasets/Shouninger/ScamBench/resolve/main/Non-scam/Employment.csv",
    }.items():
        dest = dest_dir / f"{split}.csv"
        if dest.exists() and dest.stat().st_size > 1000:
            results.append({"split": split, "status": "skipped_existing", "checksum": sha256_file(dest)})
            continue
        content, status, final = download_url(url, timeout=120)
        if not content or status != 200:
            results.append({"split": split, "status": "failed", "http_status": status, "detail": final})
            continue
        checksum = write_immutable(dest, content)
        results.append({"split": split, "status": "downloaded", "checksum": checksum})
    return {"source_id": "scambench_employment", "splits": results}


def refresh_kaggle_synthetic() -> dict[str, Any]:
    dest_dir = RAW / "kaggle_fake_vs_real_synthetic" / RETRIEVAL
    existing = list(dest_dir.glob("*.csv")) if dest_dir.exists() else []
    if existing:
        return {"source_id": "kaggle_fake_vs_real_synthetic", "status": "skipped_existing"}
    try:
        import kaggle  # type: ignore
    except ImportError:
        return {"source_id": "kaggle_fake_vs_real_synthetic", "status": "skipped_no_kaggle"}
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        kaggle.api.authenticate()
        kaggle.api.dataset_download_files(
            "khushikyad001/fake-vs-real-job-postings-synthetic-nlp-dataset",
            path=str(dest_dir),
            unzip=True,
        )
    except Exception as exc:
        return {"source_id": "kaggle_fake_vs_real_synthetic", "status": "failed", "detail": str(exc)}
    csvs = list(dest_dir.glob("*.csv"))
    return {
        "source_id": "kaggle_fake_vs_real_synthetic",
        "status": "downloaded" if csvs else "failed",
        "files": [c.name for c in csvs],
    }


def run_downloads() -> dict[str, Any]:
    report: dict[str, Any] = {"retrieval_date": RETRIEVAL, "downloaded": [], "failed": [], "probes": []}
    for source_id, (url, filename, _hint) in DOWNLOADS.items():
        dest = RAW / source_id / RETRIEVAL / filename
        content, status, final = download_url(url)
        if not content or status >= 400 or len(content) < 100:
            report["failed"].append(
                {"source_id": source_id, "url": url, "http_status": status, "detail": final, "bytes": len(content or b"")}
            )
            continue
        checksum = write_immutable(dest, content)
        sidecar = dest.with_suffix(dest.suffix + ".meta.json")
        sidecar.write_text(
            json.dumps(
                {
                    "source_id": source_id,
                    "source_url": url,
                    "canonical_url": final,
                    "downloaded_at": RETRIEVAL,
                    "checksum_sha256": checksum,
                    "bytes": len(content),
                    "http_status": status,
                },
                indent=2,
            )
        )
        report["downloaded"].append(
            {"source_id": source_id, "path": str(dest.relative_to(ROOT)), "checksum": checksum, "bytes": len(content)}
        )

    for source_id, url in PROBE_ONLY.items():
        content, status, final = download_url(url, timeout=20)
        report["probes"].append(
            {
                "source_id": source_id,
                "url": url,
                "http_status": status,
                "available": status == 200 and bool(content) and len(content or b"") > 500,
                "final_url": final,
            }
        )

    for fn in (refresh_cafc, refresh_huggingface_difraud, refresh_emscad, refresh_kaggle_synthetic, refresh_scambench):
        try:
            report.setdefault("bulk", []).append(fn())
        except Exception as exc:
            report.setdefault("bulk", []).append({"status": "error", "detail": str(exc)})

    manifest_lines = []
    for path in sorted(RAW.rglob("*")):
        if path.is_file() and not path.name.endswith(".tmp") and path.name != f"{RETRIEVAL}.sha256":
            rel = path.relative_to(ROOT)
            manifest_lines.append(f"{sha256_file(path)}  {rel.as_posix()}")
    manifest_path = RAW / f"{RETRIEVAL}.sha256"
    manifest_path.write_text("\n".join(manifest_lines) + "\n")
    report["checksum_manifest"] = str(manifest_path.relative_to(ROOT))
    report["checksum_count"] = len(manifest_lines)
    (ROOT / "data" / "reports" / "fetch_report.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    result = run_downloads()
    print(json.dumps({"downloaded": len(result["downloaded"]), "failed": len(result["failed"]), "checksum_count": result["checksum_count"]}, indent=2))
    sys.exit(1 if result["failed"] and not result["downloaded"] else 0)
