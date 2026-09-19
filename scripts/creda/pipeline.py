"""Source ingestion, evaluation design, report generation, and pipeline orchestration."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import pandas as pd
import yaml

from .core import (
    FIELDS,
    PROCESSING_VERSION,
    assign_duplicate_groups,
    build_record,
    domain_from_url,
    normalize,
    parse_file_text,
    sha256_file,
    sha256_text,
)
from .employers import build_employer_index, build_process_profile, employer_lookup, load_registry
from .pipelines import build_hiring_pipeline_profiles
from .tactics import tactics_to_jsonl_rows

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CUR = ROOT / "data" / "curated"
REPORTS = ROOT / "data" / "reports"
QUARANTINE = ROOT / "data" / "quarantine"
PRIVATE = ROOT / "data" / "private"
SCHEMA = ROOT / "schemas" / "evidence.schema.json"
SNAPSHOTS = CUR / "source_snapshots"

SOURCE_META: dict[str, dict[str, str]] = {
    "emscad": {
        "source_url": "https://www.mdpi.com/1999-5903/9/1/6",
        "publisher": "University of the Aegean",
        "tier": "T3",
    },
    "difraud_job_scams": {
        "source_url": "https://huggingface.co/datasets/difraud/difraud/tree/main/job_scams",
        "publisher": "DiFrauD authors",
        "tier": "T3",
    },
    "kaggle_fake_vs_real_synthetic": {
        "source_url": "https://www.kaggle.com/datasets/khushikyad001/fake-vs-real-job-postings-synthetic-nlp-dataset",
        "publisher": "Kaggle contributor Khushi Yadav",
        "tier": "T3",
    },
    "i4c_captcha_advisory_2025": {
        "source_url": "https://cybercrime.gov.in/Webform/theme/resources/advisories/ADVISORY%20TAU-ADV-004_Captcha%20Filling%20Fraud_08.04.2025.pdf",
        "publisher": "Indian Cyber Crime Coordination Centre (I4C)",
        "tier": "T1",
    },
    "i4c_cybercrime_portal": {
        "source_url": "https://cybercrime.gov.in",
        "publisher": "I4C / MHA India",
        "tier": "T1",
    },
    "mea_overseas_employment": {
        "source_url": "https://www.mea.gov.in/overseas-employment.htm",
        "publisher": "Ministry of External Affairs, Government of India",
        "tier": "T1",
    },
    "emigrate_portal": {
        "source_url": "https://emigrate.gov.in/ext/home",
        "publisher": "Ministry of External Affairs, Government of India",
        "tier": "T1",
    },
    "ftc_job_scams": {
        "source_url": "https://consumer.ftc.gov/articles/job-scams",
        "publisher": "U.S. Federal Trade Commission",
        "tier": "T1",
    },
    "ic3_annual_report_2024": {
        "source_url": "https://www.ic3.gov/Media/PDF/AnnualReport/2024_IC3Report.pdf",
        "publisher": "FBI Internet Crime Complaint Center",
        "tier": "T1",
    },
    "ncsc_phishing_guidance": {
        "source_url": "https://www.ncsc.gov.uk/collection/phishing-scams",
        "publisher": "UK National Cyber Security Centre",
        "tier": "T1",
    },
    "nasc_job_scam_fusion_report_2025": {
        "source_url": "https://www.nasc.gov.au/system/files/nasc-job-scam-fusion-cell-final-report-2025.pdf",
        "publisher": "National Anti-Scam Centre (Australia)",
        "tier": "T1",
    },
    "cafc_fraud_reports": {
        "source_url": "https://open.canada.ca/data/en/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f",
        "publisher": "Canadian Anti-Fraud Centre / RCMP",
        "tier": "T1",
    },
    "amazon_recruitment_fraud_policy": {
        "source_url": "https://amazon.jobs/content/en/how-we-hire/fraud-alert-india",
        "publisher": "Amazon Jobs",
        "tier": "T1",
    },
    "google_recruitment_fraud_policy": {
        "source_url": "https://careers.google.com/how-we-hire/recruitment-fraud/",
        "publisher": "Google Careers",
        "tier": "T1",
    },
    "amazon_jobs": {
        "source_url": "https://www.amazon.jobs/",
        "publisher": "Amazon Jobs",
        "tier": "T1",
    },
    "yc_jobs": {
        "source_url": "https://www.ycombinator.com/jobs/",
        "publisher": "Y Combinator",
        "tier": "T1",
    },
    "greenhouse_job_board_api": {
        "source_url": "https://developers.greenhouse.io/job-board.html",
        "publisher": "Greenhouse",
        "tier": "T1",
    },
    "lever_postings_api": {
        "source_url": "https://github.com/lever/postings-api",
        "publisher": "Lever",
        "tier": "T1",
    },
    "greenhouse_stripe_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs",
        "publisher": "Stripe via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_airbnb_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/airbnb/jobs",
        "publisher": "Airbnb via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_discord_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/discord/jobs",
        "publisher": "Discord via Greenhouse",
        "tier": "T1",
    },
    "ashby_notion_jobs": {
        "source_url": "https://api.ashbyhq.com/posting-api/job-board/notion",
        "publisher": "Notion via Ashby",
        "tier": "T1",
    },
    "gmail_inbox_search": {
        "source_url": "private://gmail/inbox-search",
        "publisher": "User Gmail (private, redacted)",
        "tier": "T3",
    },
    "scambench_employment": {
        "source_url": "https://huggingface.co/datasets/Shouninger/ScamBench",
        "publisher": "ScamBench authors",
        "tier": "T3",
    },
    "i4c_fake_job_sms_advisory": {
        "source_url": "https://cybercrime.gov.in/Webform/theme/resources/advisories/FraudsterssendingFakeJobOfferSMSstoperpetrateCybercrime.pdf",
        "publisher": "I4C / MHA India",
        "tier": "T1",
    },
    "i4c_handbook_2025": {
        "source_url": "https://cdnbbsr.s3waas.gov.in/s303412aef4dcdee4f934f7bf599f89783/uploads/2025/07/20250701709992826.pdf",
        "publisher": "I4C / MHA India",
        "tier": "T1",
    },
    "cyberdost_job_fraud_tips": {
        "source_url": "https://cytrain.ncrb.gov.in/staticpage/pdf/Cyber-security-tips-by-cyber-dost.pdf",
        "publisher": "CyberDost / NCRB India",
        "tier": "T1",
    },
    "mea_yangon_overseas_job_scam_2024": {
        "source_url": "https://embassyofindiayangon.gov.in/public_files/assets/pdf/yangon_3july2024_popup.pdf",
        "publisher": "Embassy of India, Yangon",
        "tier": "T1",
    },
    "ca_ag_job_scam_alert_2025": {
        "source_url": "https://oag.ca.gov/news/press-releases/attorney-general-bonta-alerts-californians-job-recruitment-scams",
        "publisher": "California Attorney General",
        "tier": "T1",
    },
    "scamwatch_au_job_scams": {
        "source_url": "https://www.scamwatch.gov.au/types-of-scams/jobs-and-employment-scams",
        "publisher": "ACCC Scamwatch (Australia)",
        "tier": "T1",
    },
    "kpmg_recruitment_fraud_policy": {
        "source_url": "https://kpmg.com/in/en/media/press-releases/2024/12/important-recruitment-fraud-alert.html",
        "publisher": "KPMG India",
        "tier": "T1",
    },
    "netapp_recruitment_fraud_policy": {
        "source_url": "https://www.netapp.com/responsibility/trust-center/security/recruitment-scam-warning-fraud-alert/",
        "publisher": "NetApp",
        "tier": "T1",
    },
    "amex_recruitment_fraud_policy": {
        "source_url": "https://www.americanexpress.com/en-us/careers/recruitment-fraud/",
        "publisher": "American Express",
        "tier": "T1",
    },
    "valero_recruitment_scams_2025": {
        "source_url": "https://www.valero.com/sites/default/files/valero-documents/2025-10/Recruiting%20Scams_Careers%20Legal%20Document.pdf",
        "publisher": "Valero Energy Corporation",
        "tier": "T1",
    },
    "greenhouse_shopify_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/coinbase/jobs",
        "publisher": "Coinbase via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_figma_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/figma/jobs",
        "publisher": "Figma via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_databricks_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/databricks/jobs",
        "publisher": "Databricks via Greenhouse",
        "tier": "T1",
    },
    "wipro_recruitment_fraud_policy": {
        "source_url": "https://careers.wipro.com/content/Recruitment-Fraud-Alert/?locale=en_US",
        "publisher": "Wipro Limited",
        "tier": "T1",
    },
    "lever_spotify_jobs": {
        "source_url": "https://api.lever.co/v0/postings/spotify?mode=json",
        "publisher": "Spotify via Lever",
        "tier": "T1",
    },
    "smartrecruiters_api_docs": {
        "source_url": "https://developers.smartrecruiters.com/docs/get-job-by-id",
        "publisher": "SmartRecruiters",
        "tier": "T1",
    },
    "tcs_recruitment_fraud_policy": {
        "source_url": "https://www.tcs.com/careers/india/recruitment-fraud-alert",
        "publisher": "Tata Consultancy Services",
        "tier": "T1",
    },
    "infosys_recruitment_fraud_policy": {
        "source_url": "https://www.infosys.com/careers/recruitment-fraud-alert.html",
        "publisher": "Infosys Limited",
        "tier": "T1",
    },
    "microsoft_recruitment_fraud_alert": {
        "source_url": "https://careers.microsoft.com/",
        "publisher": "Microsoft",
        "tier": "T1",
    },
    "hcl_recruitment_fraud_policy": {
        "source_url": "https://www.hcltech.com/careers/recruitment-fraud-alert",
        "publisher": "HCLTech",
        "tier": "T1",
    },
    "cognizant_recruitment_fraud_policy": {
        "source_url": "https://careers.cognizant.com/global/en/recruitment-fraud-alert",
        "publisher": "Cognizant",
        "tier": "T1",
    },
    "tech_mahindra_recruitment_fraud_policy": {
        "source_url": "https://www.techmahindra.com/en-in/careers/recruitment-fraud-alert/",
        "publisher": "Tech Mahindra",
        "tier": "T1",
    },
    "accenture_recruitment_fraud_policy": {
        "source_url": "https://www.accenture.com/us-en/careers/recruitment-fraud-alert",
        "publisher": "Accenture",
        "tier": "T1",
    },
    "capgemini_recruitment_fraud_policy": {
        "source_url": "https://www.capgemini.com/in-en/careers/recruitment-fraud-alert/",
        "publisher": "Capgemini",
        "tier": "T1",
    },
    "ibm_recruitment_fraud_policy": {
        "source_url": "https://www.ibm.com/careers/us-en/fraud-alert/",
        "publisher": "IBM",
        "tier": "T1",
    },
    "oracle_recruitment_fraud_policy": {
        "source_url": "https://www.oracle.com/corporate/security-alert/recruitment-fraud/",
        "publisher": "Oracle",
        "tier": "T1",
    },
    "flipkart_recruitment_fraud_policy": {
        "source_url": "https://www.flipkartcareers.com/",
        "publisher": "Flipkart",
        "tier": "T1",
    },
    "razorpay_recruitment_fraud_policy": {
        "source_url": "https://razorpay.com/jobs/",
        "publisher": "Razorpay",
        "tier": "T1",
    },
    "freshworks_recruitment_fraud_policy": {
        "source_url": "https://www.freshworks.com/company/careers/",
        "publisher": "Freshworks",
        "tier": "T1",
    },
    "zoho_recruitment_fraud_policy": {
        "source_url": "https://www.zoho.com/careers/",
        "publisher": "Zoho",
        "tier": "T1",
    },
    "linkedin_job_scam_guidance": {
        "source_url": "https://www.linkedin.com/help/linkedin/answer/a1336384",
        "publisher": "LinkedIn",
        "tier": "T1",
    },
    "greenhouse_coinbase_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/coinbase/jobs",
        "publisher": "Coinbase via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_anthropic_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs",
        "publisher": "Anthropic via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_datadog_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/datadog/jobs",
        "publisher": "Datadog via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_mongodb_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/mongodb/jobs",
        "publisher": "MongoDB via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_cloudflare_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs",
        "publisher": "Cloudflare via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_vercel_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/vercel/jobs",
        "publisher": "Vercel via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_reddit_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/reddit/jobs",
        "publisher": "Reddit via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_twilio_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/twilio/jobs",
        "publisher": "Twilio via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_lyft_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/lyft/jobs",
        "publisher": "Lyft via Greenhouse",
        "tier": "T1",
    },
    "greenhouse_instacart_jobs": {
        "source_url": "https://boards-api.greenhouse.io/v1/boards/instacart/jobs",
        "publisher": "Instacart via Greenhouse",
        "tier": "T1",
    },
}


def latest_retrieval() -> str:
    manifests = sorted(RAW.glob("*.sha256"))
    if manifests:
        return manifests[-1].stem
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def meta(source_id: str) -> dict[str, str]:
    return SOURCE_META.get(source_id, {"source_url": "", "publisher": "", "tier": "T3"})


def ingest_emscad(retrieval: str, observed_at: str) -> list[dict[str, Any]]:
    path = RAW / "emscad" / retrieval / "DataSet.csv"
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            text = "\n".join(str(row.get(k, "")) for k in ["title", "company_profile", "description", "requirements", "benefits"])
            label = "suspicious_pattern" if row.get("fraudulent") == "t" else "legitimate"
            rec = build_record(
                evidence_id=f"emscad-{i:05d}",
                record_type="job_posting",
                source_id="emscad",
                source_url=meta("emscad")["source_url"],
                publisher=meta("emscad")["publisher"],
                evidence_tier="T3",
                text=text,
                label=label,
                label_provenance="EMSCAD manual annotation 2012-2014; historical baseline only; never upgraded to confirmed_scam",
                label_confidence="low",
                title=row.get("title", ""),
                country=row.get("location", ""),
                employment_type=row.get("employment_type", ""),
                salary_text=row.get("salary_range", ""),
                observed_at=observed_at,
                evaluation_eligible=False,
                raw_uri=f"s3://creda-data/raw/emscad/{retrieval}/DataSet.csv",
            )
            out.append(rec)
    return out


def ingest_difraud(retrieval: str, observed_at: str) -> list[dict[str, Any]]:
    out = []
    base_dir = RAW / "difraud_job_scams" / retrieval
    for fp in sorted(base_dir.glob("*.jsonl")):
        split = fp.stem
        with fp.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                row = json.loads(line)
                text = row.get("text", "")
                label = "suspicious_pattern" if int(row.get("label", 0)) == 1 else "legitimate"
                out.append(
                    build_record(
                        evidence_id=f"difraud-{split}-{i:05d}",
                        record_type="job_posting",
                        source_id="difraud_job_scams",
                        source_url=meta("difraud_job_scams")["source_url"],
                        publisher=meta("difraud_job_scams")["publisher"],
                        evidence_tier="T3",
                        text=text,
                        label=label,
                        label_provenance="DiFrauD MIT label; overlaps EMSCAD-era corpora; not live verdict evidence",
                        label_confidence="low",
                        observed_at=observed_at,
                        evaluation_eligible=False,
                        raw_uri=f"s3://creda-data/raw/difraud_job_scams/{retrieval}/{fp.name}",
                    )
                )
    return out


def ingest_synthetic(retrieval: str, observed_at: str) -> list[dict[str, Any]]:
    out = []
    syn_dir = RAW / "kaggle_fake_vs_real_synthetic" / retrieval
    for fp in syn_dir.glob("*.csv") if syn_dir.exists() else []:
        df = pd.read_csv(fp).fillna("")
        for i, row in enumerate(df.to_dict(orient="records")):
            text = " ".join(str(v) for v in row.values())
            is_fake = str(row.get("is_fake", row.get("label", ""))).lower() in {"1", "true", "fake"}
            label = "suspicious_pattern" if is_fake else "legitimate"
            out.append(
                build_record(
                    evidence_id=f"synthetic-{i:05d}",
                    record_type="job_posting",
                    source_id="kaggle_fake_vs_real_synthetic",
                    source_url=meta("kaggle_fake_vs_real_synthetic")["source_url"],
                    publisher=meta("kaggle_fake_vs_real_synthetic")["publisher"],
                    evidence_tier="T3",
                    text=text,
                    label=label,
                    label_provenance="Synthetic MIT dataset; pattern exploration only; excluded from evaluation",
                    label_confidence="low",
                    title=str(row.get("job_title", "")),
                    country=str(row.get("location", "")),
                    employer_claimed=str(row.get("company_name", "")),
                    published_at=str(row.get("posting_date", "")) or None,
                    observed_at=observed_at,
                    evaluation_eligible=False,
                    raw_uri=f"s3://creda-data/raw/kaggle_fake_vs_real_synthetic/{retrieval}/{fp.name}",
                )
            )
    return out


def ingest_document(
    source_id: str,
    record_type: str,
    filename: str,
    retrieval: str,
    observed_at: str,
    label: str = "unverified",
    evaluation_eligible: bool = True,
    published_at: str | None = None,
) -> dict[str, Any] | None:
    path = RAW / source_id / retrieval / filename
    if not path.exists():
        return None
    text = parse_file_text(path)
    m = meta(source_id)
    rec = build_record(
        evidence_id=f"{source_id}-{sha256_text(normalize(text))[:12]}",
        record_type=record_type,
        source_id=source_id,
        source_url=m["source_url"],
        publisher=m["publisher"],
        evidence_tier=m["tier"],
        text=text,
        label=label,
        label_provenance="Official source content; pattern/policy evidence only; no individual case verdict",
        label_confidence="high" if m["tier"] == "T1" else "medium",
        title=source_id.replace("_", " "),
        published_at=published_at,
        observed_at=observed_at,
        evaluation_eligible=evaluation_eligible,
        raw_uri=f"s3://creda-data/raw/{source_id}/{retrieval}/{filename}",
    )
    return rec


def ingest_greenhouse_jobs(source_id: str, retrieval: str, observed_at: str) -> list[dict[str, Any]]:
    path = RAW / source_id / retrieval / "jobs.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs = data.get("jobs", [])
    employer = source_id.replace("greenhouse_", "").replace("_jobs", "")
    out = []
    for job in jobs:
        text = normalize(f"{job.get('title','')} {job.get('content','')} {job.get('location',{}).get('name','')}")
        updated = job.get("updated_at") or job.get("first_published")
        rec = build_record(
            evidence_id=f"{source_id}-{job.get('id', sha256_text(text)[:8])}",
            record_type="official_vacancy",
            source_id=source_id,
            source_url=job.get("absolute_url") or meta(source_id)["source_url"],
            publisher=meta(source_id)["publisher"],
            evidence_tier="T1",
            text=text,
            label="legitimate",
            label_provenance="Live public Greenhouse board vacancy; employer-controlled ATS record",
            label_confidence="high",
            title=job.get("title", ""),
            canonical_url=job.get("absolute_url"),
            country=str((job.get("location") or {}).get("name", "")),
            employer_claimed=employer.title(),
            employer_domain=domain_from_url(job.get("absolute_url", "")),
            role_title=job.get("title", ""),
            published_at=str(updated)[:10] if updated else None,
            observed_at=observed_at,
            evaluation_eligible=True,
            raw_uri=f"s3://creda-data/raw/{source_id}/{retrieval}/jobs.json",
        )
        out.append(rec)
    return out


def ingest_ashby_jobs(source_id: str, retrieval: str, observed_at: str) -> list[dict[str, Any]]:
    path = RAW / source_id / retrieval / "jobs.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs = data.get("jobs", data if isinstance(data, list) else [])
    out = []
    for job in jobs:
        text = normalize(
            f"{job.get('title','')} {job.get('descriptionPlain','')} {job.get('descriptionHtml','')} {job.get('location','')}"
        )
        rec = build_record(
            evidence_id=f"{source_id}-{job.get('id', sha256_text(text)[:8])}",
            record_type="official_vacancy",
            source_id=source_id,
            source_url=job.get("jobUrl") or job.get("applyUrl") or meta(source_id)["source_url"],
            publisher=meta(source_id)["publisher"],
            evidence_tier="T1",
            text=text,
            label="legitimate",
            label_provenance="Live public Ashby board vacancy; employer-controlled ATS record",
            label_confidence="high",
            title=job.get("title", ""),
            canonical_url=job.get("jobUrl") or job.get("applyUrl"),
            country=str(job.get("location", "")),
            employer_claimed="Notion",
            employer_domain=domain_from_url(job.get("jobUrl", "")),
            role_title=job.get("title", ""),
            published_at=str(job.get("publishedAt", ""))[:10] or None,
            observed_at=observed_at,
            evaluation_eligible=True,
            raw_uri=f"s3://creda-data/raw/{source_id}/{retrieval}/jobs.json",
        )
        out.append(rec)
    return out


def ingest_scambench(retrieval: str, observed_at: str) -> list[dict[str, Any]]:
    """ScamBench employment messages — best public message-level scam corpus with employer names."""
    base = RAW / "scambench_employment" / retrieval
    if not base.exists():
        return []
    out = []
    for fname, label, rtype in [
        ("employment_scam.csv", "suspicious_pattern", "community_report"),
        ("employment_nonscam.csv", "legitimate", "offer_message"),
    ]:
        path = base / fname
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as f:
            for i, row in enumerate(csv.DictReader(f)):
                text = str(row.get("description") or row.get("rewrite_description") or "")
                if not text.strip():
                    continue
                employer = str(row.get("business_name_used") or "")
                rec = build_record(
                    evidence_id=f"scambench-{path.stem}-{i:04d}",
                    record_type=rtype,
                    source_id="scambench_employment",
                    source_url=meta("scambench_employment")["source_url"],
                    publisher=meta("scambench_employment")["publisher"],
                    evidence_tier="T3",
                    text=text,
                    label=label if label != "suspicious_pattern" else "suspicious_pattern",
                    label_provenance="ScamBench victim-reported employment message (CC BY-NC 4.0); not upgraded to confirmed_scam",
                    label_confidence="medium",
                    title=employer or "employment message",
                    employer_claimed=employer,
                    country=str(row.get("location") or ""),
                    published_at=str(row.get("date_reported") or "")[:10] or None,
                    observed_at=observed_at,
                    evaluation_eligible=True,
                    raw_uri=f"s3://creda-data/raw/scambench_employment/{retrieval}/{path.name}",
                )
                claims = json.loads(rec["extracted_claims"])
                channels = claims.get("contact_channels") or []
                rec["recruiter_contact_channel"] = ",".join(channels)
                if row.get("dollars_lost"):
                    rec["payment_amount"] = str(row.get("dollars_lost"))
                out.append(rec)
    return out


def ingest_lever_jobs(source_id: str, retrieval: str, observed_at: str) -> list[dict[str, Any]]:
    path = RAW / source_id / retrieval / "jobs.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs = data if isinstance(data, list) else data.get("jobs", [])
    employer = source_id.replace("lever_", "").replace("_jobs", "")
    out = []
    for job in jobs:
        text = normalize(
            f"{job.get('text','')} {job.get('title','')} {job.get('descriptionPlain','')} {job.get('categories',{}).get('location','')}"
        )
        hosted = job.get("hostedUrl") or job.get("applyUrl") or ""
        rec = build_record(
            evidence_id=f"{source_id}-{job.get('id', sha256_text(text)[:8])}",
            record_type="official_vacancy",
            source_id=source_id,
            source_url=hosted or meta(source_id)["source_url"],
            publisher=meta(source_id)["publisher"],
            evidence_tier="T1",
            text=text,
            label="legitimate",
            label_provenance="Live public Lever board vacancy; employer-controlled ATS record",
            label_confidence="high",
            title=str(job.get("text") or job.get("title") or ""),
            canonical_url=hosted,
            country=str((job.get("categories") or {}).get("location", "")),
            employer_claimed=employer.title(),
            employer_domain=domain_from_url(hosted),
            role_title=str(job.get("text") or job.get("title") or ""),
            published_at=str(job.get("createdAt", ""))[:10] or None,
            observed_at=observed_at,
            evaluation_eligible=True,
            raw_uri=f"s3://creda-data/raw/{source_id}/{retrieval}/jobs.json",
        )
        out.append(rec)
    return out


def build_recruiting_process_patterns(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rich employer process profiles for contradiction checks."""
    lookup = employer_lookup()
    by_source = {emp.get("policy", {}).get("source_id"): emp for emp in load_registry().get("employers", []) if emp.get("policy")}
    patterns = []
    for rec in policies:
        emp = by_source.get(rec["source_id"])
        profile = build_process_profile(rec, emp)
        profile["pattern_id"] = f"recruiting-process-{rec['source_id']}"
        profile["label"] = "legitimate"
        profile["note"] = "Employer-published hiring process; use for contradiction checks against scam offers"
        patterns.append(profile)
    return patterns


def employer_policy_doc_specs(retrieval: str) -> list[tuple[str, str, str, str | None]]:
    specs: list[tuple[str, str, str, str | None]] = []
    seen: set[str] = set()
    for emp in load_registry().get("employers", []):
        policy = emp.get("policy") or {}
        source_id = policy.get("source_id")
        if not source_id or source_id in seen:
            continue
        fetch = policy.get("fetch") or {}
        filename = fetch.get("filename", "index.html")
        path = RAW / source_id / retrieval / filename
        if path.exists():
            specs.append((source_id, "employer_policy", filename, policy.get("published_at")))
            seen.add(source_id)
    return specs


def build_channel_patterns(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Government-reported scam channel tactics for SMS/WhatsApp/email impersonation."""
    channel_docs = []
    for rec in docs:
        claims = json.loads(rec.get("extracted_claims") or "{}")
        channels = claims.get("contact_channels") or []
        if not channels and not rec.get("scam_pattern_tags"):
            continue
        channel_docs.append(
            {
                "pattern_id": f"channel-{rec['source_id']}",
                "source_id": rec["source_id"],
                "reported_channels": channels,
                "scam_pattern_tags": rec.get("scam_pattern_tags") or [],
                "evidence_id": rec["evidence_id"],
                "source_url": rec["source_url"],
                "evidence_tier": rec["evidence_tier"],
                "label": "unverified",
                "note": "Government or registry-reported channel tactics; pattern evidence only",
            }
        )
    return channel_docs


def ingest_gmail_private(observed_at: str) -> list[dict[str, Any]]:
    path = PRIVATE / "gmail_recruitment_candidates.jsonl"
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            text = f"{row.get('subject','')} {row.get('snippet_redacted','')} sender:{row.get('sender_display','')}"
            rec = build_record(
                evidence_id=row.get("record_id", f"gmail-{sha256_text(text)[:8]}"),
                record_type="offer_message",
                source_id="gmail_inbox_search",
                source_url="private://gmail/inbox-search",
                publisher="User Gmail (private, redacted)",
                evidence_tier="T3",
                text=text,
                label="unverified",
                label_provenance=row.get("label_provenance", "user Gmail message; no verdict assigned"),
                label_confidence="low",
                title=row.get("subject", ""),
                published_at=row.get("date_display"),
                observed_at=observed_at,
                evaluation_eligible=True,
                raw_uri="s3://creda-data/private/gmail_recruitment_candidates.jsonl",
            )
            rec["scam_pattern_tags"] = row.get("scam_pattern_tags", rec["scam_pattern_tags"])
            rec["pii_redaction_status"] = "redacted_snippet_only"
            rec["lifecycle_status"] = "active"
            rec["evaluation_partition"] = "recent_private_unverified"
            out.append(rec)
    return out


def build_evaluation_cases(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eval_rows: list[dict[str, Any]] = []
    recent_sources = {
        "greenhouse_stripe_jobs",
        "greenhouse_airbnb_jobs",
        "greenhouse_discord_jobs",
        "greenhouse_shopify_jobs",
        "greenhouse_figma_jobs",
        "greenhouse_databricks_jobs",
        "lever_spotify_jobs",
        "ashby_notion_jobs",
        "google_recruitment_fraud_policy",
        "amazon_recruitment_fraud_policy",
        "kpmg_recruitment_fraud_policy",
        "nasc_job_scam_fusion_report_2025",
        "i4c_captcha_advisory_2025",
        "i4c_fake_job_sms_advisory",
        "ic3_annual_report_2024",
        "scambench_employment",
        "gmail_inbox_search",
    }
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        if rec.get("evaluation_eligible") and rec["source_id"] in recent_sources:
            by_source[rec["source_id"]].append(rec)

    slice_defs = [
        ("india_domestic", "gmail_inbox_search", {"internship_or_apprenticeship", "fee_or_deposit_request", "impersonation_signal"}, 8),
        ("overseas_relocation", "mea_overseas_employment", set(), 0),
        ("international_remote", "greenhouse_stripe_jobs", {"remote_work"}, 5),
        ("startup_impersonation", "greenhouse_discord_jobs", set(), 3),
        ("large_company_impersonation", "gmail_inbox_search", {"impersonation_signal"}, 4),
        ("fee_scams", "gmail_inbox_search", {"fee_or_deposit_request"}, 3),
        ("equipment_scams", "ic3_annual_report_2024", {"equipment_purchase"}, 1),
        ("fake_check_scams", "ic3_annual_report_2024", {"fake_check_or_reimbursement"}, 1),
        ("task_scams", "i4c_captcha_advisory_2025", {"task_or_boosting"}, 1),
        ("identity_document_requests", "gmail_inbox_search", {"identity_or_banking_request"}, 2),
        ("no_fee_legitimate", "google_recruitment_fraud_policy", {"no_fee_statement"}, 2),
        ("official_vacancy_control", "ashby_notion_jobs", set(), 5),
        ("employer_policy_control", "amazon_recruitment_fraud_policy", {"no_fee_statement"}, 1),
        ("sms_whatsapp_channel", "i4c_fake_job_sms_advisory", {"sms", "whatsapp"}, 1),
        ("scambench_employer_impersonation", "scambench_employment", {"fee_or_deposit_request", "impersonation_signal"}, 10),
        ("kpmg_india_policy", "kpmg_recruitment_fraud_policy", {"no_fee_statement"}, 1),
        ("official_vacancy_shopify", "greenhouse_shopify_jobs", set(), 3),
        ("government_pattern_2025", "nasc_job_scam_fusion_report_2025", set(), 1),
    ]

    used: set[str] = set()
    for slice_name, source_id, required_tags, limit in slice_defs:
        pool = by_source.get(source_id, [])
        if source_id == "mea_overseas_employment":
            pool = [r for r in records if r["source_id"] == source_id]
        picked = 0
        for rec in pool:
            if rec["evidence_id"] in used:
                continue
            tags = set(rec.get("scam_pattern_tags") or [])
            if required_tags and not (tags & required_tags):
                continue
            partition = f"recent_{slice_name}__{rec['source_id']}__{rec.get('campaign_group','na')}"
            eval_rows.append(
                {
                    "evaluation_id": f"eval-{len(eval_rows):04d}",
                    "evidence_id": rec["evidence_id"],
                    "source_id": rec["source_id"],
                    "employer_claimed": rec.get("employer_claimed", ""),
                    "campaign_group": rec.get("campaign_group", ""),
                    "published_at": rec.get("published_at"),
                    "label": rec["label"],
                    "evaluation_slice": slice_name,
                    "partition": partition,
                    "split": "recent_holdout_2023_2026",
                    "reason": f"Recent-source grouped holdout for {slice_name}; weak labels remain unverified/suspicious_pattern",
                }
            )
            used.add(rec["evidence_id"])
            picked += 1
            if picked >= limit:
                break

    emscad_pool = [r for r in records if r["source_id"] == "emscad" and r["label"] in {"legitimate", "suspicious_pattern"}]
    for rec in emscad_pool[:20]:
        if rec["evidence_id"] in used:
            continue
        eval_rows.append(
            {
                "evaluation_id": f"eval-{len(eval_rows):04d}",
                "evidence_id": rec["evidence_id"],
                "source_id": rec["source_id"],
                "employer_claimed": rec.get("employer_claimed", ""),
                "campaign_group": rec.get("campaign_group", ""),
                "published_at": rec.get("published_at"),
                "label": rec["label"],
                "evaluation_slice": "historical_baseline",
                "partition": f"historical_emscad__{rec.get('campaign_group','na')}",
                "split": "historical_holdout_2012_2014",
                "reason": "Historical EMSCAD holdout; not used as current-truth evaluation",
            }
        )
    return eval_rows


def validate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for i, rec in enumerate(records):
        for err in validator.iter_errors(rec):
            errors.append({"index": i, "evidence_id": rec.get("evidence_id"), "message": err.message})
            if len(errors) >= 100:
                break
        if len(errors) >= 100:
            break
    return {"valid_count": len(records) - len({e["index"] for e in errors}), "error_count": len(errors), "errors": errors[:20]}


def write_parquet(records: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    df = pd.DataFrame(records).reindex(columns=FIELDS)
    for col in ["scam_pattern_tags"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)
    df.to_parquet(path, index=False)
    return {"rows": len(df), "columns": len(df.columns), "path": str(path.relative_to(ROOT))}


def build_cafc_aggregate(retrieval: str) -> tuple[list[dict[str, Any]], str]:
    cafc = RAW / "cafc_fraud_reports" / retrieval / "cafc.csv"
    if not cafc.exists():
        return [], ""
    df = pd.read_csv(
        cafc,
        usecols=["Fraud and Cybercrime Thematic Categories", "Number of Victims / Nombre de victimes", "Dollar Loss /pertes financières"],
        low_memory=False,
    )
    summary = (
        df.groupby("Fraud and Cybercrime Thematic Categories", dropna=False)
        .agg(reports=("Fraud and Cybercrime Thematic Categories", "size"), victims=("Number of Victims / Nombre de victimes", "sum"))
        .reset_index()
    )
    rows = []
    for _, r in summary.iterrows():
        rows.append(
            {
                "source_id": "cafc_fraud_reports",
                "category": str(r.iloc[0]),
                "reports": int(r.iloc[1]),
                "victims": int(r.iloc[2]),
                "label": "unverified",
                "evidence_tier": "T1",
                "note": "aggregate context only; no individual verdict",
            }
        )
    note = f"CAFC raw rows: {len(df)}; categories: {len(summary)}"
    return rows, note


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def generate_reports(
    records: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    dup_stats: dict[str, Any],
    validation: dict[str, Any],
    parquet_info: dict[str, Any],
    retrieval: str,
    observed_at: str,
    cafc_note: str,
) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    counts_by_source = Counter(r["source_id"] for r in records)
    counts_by_label = Counter(r["label"] for r in records)
    recent_records = [r for r in records if r.get("evaluation_eligible")]

    (REPORTS / "data_quality_report.md").write_text(
        f"""# Creda data quality report

Generated: {observed_at}
Processing version: {PROCESSING_VERSION}

## Summary

- Canonical evidence records: {len(records)}
- Recent evaluation-eligible records (2023-2026 sources): {len(recent_records)}
- Evaluation cases: {len(eval_rows)}
- Exact duplicate rows grouped: {dup_stats.get('exact_duplicate_rows', 0)}
- Derived EMSCAD copies flagged: {dup_stats.get('derived_from_emscad', 0)}
- Unique content hashes: {dup_stats.get('unique_content_hashes', 0)}
- Schema validation errors: {validation.get('error_count', 0)}

## Counts by source

""" + "\n".join(f"- `{k}`: {v}" for k, v in sorted(counts_by_source.items())) + """

## Counts by label

""" + "\n".join(f"- `{k}`: {v}" for k, v in sorted(counts_by_label.items())) + """

Historical and synthetic labels are pattern-discovery metadata only. They cannot independently create a Creda fraud verdict.
"""
    )

    (REPORTS / "source_coverage_report.md").write_text(
        f"""# Creda source coverage

Generated: {observed_at}

| Slice | Status |
|---|---|
| India domestic / campus | Gmail private candidates + I4C 2025 CAPTCHA advisory + MEA/emigrate guidance |
| Overseas relocation / visa | MEA + emigrate.gov.in registry guidance ingested |
| International remote | Greenhouse Stripe/Airbnb/Discord + Ashby Notion vacancies |
| Startup impersonation | YC directory + Discord Greenhouse board |
| Large-company impersonation | Gmail Tata/TCS/IBM/Cisco candidates (unverified) |
| Fee / equipment / fake-check / task / crypto | I4C advisory, NASC 2025 report, IC3 2024 report, deterministic tag extraction |
| Official no-fee policies | Amazon India + Google Careers recruitment fraud pages |
| Hindi / Hinglish | gap — no activated message-level corpus |
| Confirmed scam message labels (2023-2026) | gap — no public licensed message-level ground truth |

## Recent source inventory

""" + "\n".join(
            f"- `{sid}`: {counts_by_source.get(sid, 0)} records"
            for sid in [
                "greenhouse_stripe_jobs",
                "greenhouse_airbnb_jobs",
                "greenhouse_discord_jobs",
                "ashby_notion_jobs",
                "google_recruitment_fraud_policy",
                "ic3_annual_report_2024",
                "nasc_job_scam_fusion_report_2025",
                "i4c_captcha_advisory_2025",
                "gmail_inbox_search",
            ]
        ) + f"""

{cafc_note}

Gmail: 14 redacted candidate records under `data/private/`; all labeled `unverified`.
"""
    )

    (REPORTS / "license_report.md").write_text(
        """# License and provenance report

| Source | License | Permitted use | Notes |
|---|---|---|---|
| EMSCAD | CC0 (Kaggle card) | Historical baseline only | 2012-2014; not current truth |
| DiFrauD job_scams | MIT | Pattern discovery | Derived overlap with EMSCAD-era corpora |
| Kaggle synthetic | MIT | Pattern exploration only | Excluded from evaluation |
| I4C advisories / portal | Government publication | Pattern evidence | Verify redistribution terms |
| MEA / emigrate.gov.in | Government publication | Overseas verification guidance | Registry adapter pending |
| CAFC CSV | Open Government Licence - Canada | Aggregate context only | Individual rows not in evidence corpus |
| NASC 2025 report | AU government publication | Pattern evidence | Case studies not individual verdicts |
| IC3 2024 report | US government publication | Pattern evidence | FBI public report |
| NCSC UK phishing guidance | Open Government Licence | Pattern evidence | Not job-specific alone |
| Greenhouse / Ashby APIs | Employer public boards | Vacancy verification | Official ATS endpoints |
| Google / Amazon policies | Employer pages | Current policy evidence | Quote with attribution |
| Gmail private | User-owned private data | Evaluation leads only | Never publish raw bodies |
| Srisai Kaggle fake-only | unknown | quarantined | Not downloaded |
| FTC job scams page | US gov | blocked at fetch (403) | Registered unavailable |
"""
    )

    (REPORTS / "duplication_report.md").write_text(
        f"""# Duplication report

Generated: {observed_at}

- Exact duplicate content rows: {dup_stats.get('exact_duplicate_rows', 0)}
- Unique normalized hashes: {dup_stats.get('unique_content_hashes', 0)}
- Rows flagged `derived_from_emscad`: {dup_stats.get('derived_from_emscad', 0)}
- Near-duplicate pairs sampled: {len(dup_stats.get('near_duplicate_pairs_sample', []))}

## Sample near-duplicate pairs

""" + "\n".join(
            f"- `{a}` ~ `{b}` (score {score})" for a, b, score in dup_stats.get("near_duplicate_pairs_sample", [])[:15]
        ) + """

DiFrauD and EMSCAD overlap is expected. Synthetic dataset duplicates are excluded from evaluation partitions.
"""
    )

    (REPORTS / "freshness_report.md").write_text(
        f"""# Freshness report

Generated: {observed_at}
Retrieval snapshot: {retrieval}

| Source | Date range | Freshness policy | Status |
|---|---|---|---|
| EMSCAD / DiFrauD | 2012-2014 | immutable historical | baseline only |
| Synthetic Kaggle | 2023-2025 generated | immutable | pattern only |
| I4C CAPTCHA advisory | 2025-04-08 | recheck 30d | current |
| NASC fusion report | 2025 | recheck 30d | current |
| IC3 annual report | 2024 | recheck 90d | current |
| Greenhouse / Ashby boards | live API snapshot | recheck 24h | current |
| Employer policies | live pages | recheck 7d | current |
| Gmail candidates | 2026-06 to 2026-09 | private intake | unverified |
| FTC job scams | current page | recheck 30d | unavailable (403) |

Recent labeled scam messages remain the largest gap for precision/recall measurement.
"""
    )

    manifest_records = []
    for sid, count in sorted(counts_by_source.items()):
        raw_dir = RAW / sid / retrieval
        checksum = None
        if raw_dir.exists():
            files = [p for p in raw_dir.iterdir() if p.is_file() and not p.name.endswith(".meta.json")]
            if files:
                checksum = sha256_file(files[0])
        manifest_records.append(
            {
                "source_id": sid,
                "record_count": count,
                "raw_checksum_sample": checksum,
                "permissions": "public" if not sid.startswith("gmail") else "private",
            }
        )

    (REPORTS / "aws_ingestion_manifest.md").write_text(
        f"""# AWS ingestion manifest (documentation only — no resources deployed)

Generated: {observed_at}
Processing version: {PROCESSING_VERSION}

## S3 prefix layout

```
s3://creda-data/
  raw/{{source_id}}/{{retrieval_date}}/          # immutable bytes + sidecar metadata
  curated/evidence/{{evidence_id}}.json          # canonical records
  curated/evidence.parquet                       # Glue/Bedrock-friendly table
  curated/patterns.jsonl
  curated/employer_policies.jsonl
  curated/evaluation_cases.jsonl
  curated/source_snapshots/{{retrieval_date}}/
  quarantine/{{source_id}}/
  private/gmail/                                 # never public ACL
  manifests/{{retrieval_date}}/ingestion.json
  bedrock/documents/{{evidence_id}}.json       # metadata adjacent to source refs
```

## Record manifest

| source_id | records | sample_checksum | permissions |
|---|---:|---|---|
""" + "\n".join(
            f"| `{m['source_id']}` | {m['record_count']} | `{m['raw_checksum_sample'] or 'n/a'}` | {m['permissions']} |"
            for m in manifest_records
        ) + f"""

## Parquet

- Path: `data/curated/evidence.parquet`
- Rows: {parquet_info.get('rows', 0)}
- Columns: {parquet_info.get('columns', 0)}

## Glue

Use `schemas/glue_evidence_table.json` (generated) with partition key `source_id`.

## Bedrock Knowledge Base

Store document bodies in S3; keep metadata JSON adjacent. Do **not** store full bodies in DynamoDB.

## Estimated monthly cost (if deployed — requires approval)

| Service | Assumption | Est. USD/month |
|---|---|---|
| S3 Standard | ~500 MB curated + 120 MB raw | $0.02 |
| Glue Crawler | weekly on curated prefix | $1-3 |
| Athena | 10 GB scanned / month | $0.05 |
| Bedrock KB sync | 50k docs, monthly refresh | $5-15 |
| **Total** | dev/staging footprint | **~$6-20** |

No AWS resources are created by this pipeline run.
"""
    )

    eval_metrics = {
        "precision": "not_computable_without_confirmed_recent_labels",
        "recall": "not_computable_without_confirmed_recent_labels",
        "false_positive_rate": "pending_human_review_on_unverified_routes",
        "false_negative_cases": "unknown_without_ground_truth",
        "unverified_routing_rate": round(
            sum(1 for r in records if r["label"] == "unverified") / max(len(records), 1), 4
        ),
        "evaluation_cases": len(eval_rows),
        "recent_holdout_cases": sum(1 for e in eval_rows if e.get("split", "").startswith("recent")),
    }
    (REPORTS / "evaluation_design.json").write_text(json.dumps(eval_metrics, indent=2))

    (REPORTS / "source_quality_ranking.md").write_text(
        f"""# Source quality ranking for Creda

Generated: {observed_at}

This ranks sources by usefulness for **current** recruitment-offer verification — not raw row count.

## Tier A — use for live verdict evidence (T1)

| Source | Why it is high quality | Gap it fills |
|---|---|---|
| Greenhouse/Ashby/Lever live boards | Employer-controlled ATS JSON with canonical URLs | Official vacancy match, startup + large-company coverage |
| Employer fraud policies (Amazon, Google, KPMG, Amex, NetApp, Valero) | Published no-fee rules, official email domains, interview process | Contradiction checks against fee demands and free-mailbox offers |
| I4C advisories + handbook (2025) | India-specific SMS/WhatsApp/CAPTCHA/task scam tactics | Channel + fee patterns for Indian applicants |
| NASC Job Scam Fusion report (2025) | Recent AU government case analysis: WhatsApp, Telegram, crypto wallets | Modern channel tactics and impersonation targets |
| IC3 2024 report | US BEC/fake-job loss trends | Equipment, fake-check, crypto patterns |
| MEA + eMigrate + Yangon advisory | Overseas agent registry + trafficking warnings | Overseas relocation verification |
| CA AG + Scamwatch AU | Current government alerts on recruitment channels | Multi-country guidance |

## Tier B — pattern discovery + evaluation only (T3, never standalone verdict)

| Source | Why it is useful | Limitation |
|---|---|---|
| **ScamBench Employment** | Best public **message-level** corpus with `business_name_used`, dates, losses | CC BY-NC 4.0; victim reports → `suspicious_pattern` only |
| Gmail private candidates (14) | Real 2026 India internship/fee/impersonation leads | Redacted snippets; all `unverified` |
| EMSCAD (2012–2014) | Historical baseline for posting-level ML | Not current tactics |
| DiFrauD | Overlaps EMSCAD; useful for duplicate detection | Not independent |
| Kaggle synthetic | Pattern exploration | Excluded from evaluation |

## Tier C — rejected / quarantined / unavailable

| Source | Status | Reason |
|---|---|---|
| FTC job-scams page | unavailable (403) | Need alternate snapshot or FTC data spotlight |
| Infosys/TCS/Wipro/Microsoft policies | blocked (403/404) | Manual fetch or employer partnership needed |
| Srisai Kaggle fake-only | quarantined | Unknown license/provenance |
| Fraud-R1 / adversarial Kaggle | not ingested | Partially synthetic; pattern-only |

## What Creda still lacks (honest gaps)

1. **Confirmed 2023–2026 message-level labels** tied to employer verification outcomes — no public licensed dataset exists at scale.
2. **Indian large-employer policy pages** (TCS, Infosys, Wipro) — blocked to automated fetch; critical for campus impersonation cases.
3. **Full Gmail message bodies** — connector needed for sender-domain and URL extraction.
4. **Hindi/Hinglish** recruitment scam messages — no activated corpus yet.
5. **RDAP/DNS T2 signals** — not in this dataset layer; computed at verification runtime.

## Recommended priority for agentic pipeline

1. Resolve employer → official domain (Wikidata + careers page)
2. Compare against ingested **employer_policies.jsonl** + live ATS vacancy
3. Extract fee/channel claims from user paste; match **channel_patterns.jsonl** + **recruiting_process_patterns.jsonl**
4. Route to **Unverified** when T1 evidence missing — never guess from ScamBench/Gmail alone
"""
    )


def update_registry_checksums(retrieval: str) -> None:
    registry_path = ROOT / "data" / "source_registry.yaml"
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    for src in data.get("sources", []):
        sid = src.get("source_id")
        raw_dir = RAW / sid / retrieval
        if raw_dir.exists():
            files = sorted(p for p in raw_dir.rglob("*") if p.is_file() and not p.name.endswith(".meta.json"))
            if files:
                src["checksum"] = sha256_file(files[0])
                src["local_path"] = f"data/raw/{sid}/"
                src["downloaded_at"] = retrieval
        src.setdefault("duplicate_provenance_notes", src.get("duplicate_provenance_notes", ""))
    registry_path.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True))


def run_pipeline(retrieval: str | None = None) -> dict[str, Any]:
    retrieval = retrieval or latest_retrieval()
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    CUR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    QUARANTINE.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    records.extend(ingest_emscad(retrieval, observed_at))
    records.extend(ingest_difraud(retrieval, observed_at))
    records.extend(ingest_synthetic(retrieval, observed_at))
    records.extend(ingest_scambench(retrieval, observed_at))
    records.extend(ingest_gmail_private(observed_at))

    doc_specs = [
        ("i4c_captcha_advisory_2025", "government_advisory", "advisory.pdf", "2025-04-08"),
        ("i4c_fake_job_sms_advisory", "government_advisory", "advisory.pdf", None),
        ("i4c_handbook_2025", "government_advisory", "handbook.pdf", "2025"),
        ("cyberdost_job_fraud_tips", "government_guidance", "tips.pdf", None),
        ("mea_yangon_overseas_job_scam_2024", "government_advisory", "advisory.pdf", "2024-07-03"),
        ("ca_ag_job_scam_alert_2025", "government_advisory", "index.html", "2025"),
        ("scamwatch_au_job_scams", "government_guidance", "index.html", None),
        ("linkedin_job_scam_guidance", "government_guidance", "index.html", None),
        ("ftc_job_scams", "government_guidance", "index.html", None),
        ("i4c_cybercrime_portal", "government_advisory", "index.html", None),
        ("mea_overseas_employment", "government_guidance", "index.html", None),
        ("emigrate_portal", "registry_record", "index.html", None),
        ("nasc_job_scam_fusion_report_2025", "government_advisory", "report.pdf", "2025"),
        ("ic3_annual_report_2024", "government_advisory", "report.pdf", "2024"),
        ("ncsc_phishing_guidance", "government_advisory", "index.html", None),
        ("amazon_jobs", "official_vacancy", "index.html", None),
        ("yc_jobs", "official_vacancy", "index.html", None),
        ("greenhouse_job_board_api", "registry_record", "index.html", None),
        ("lever_postings_api", "registry_record", "index.html", None),
        ("smartrecruiters_api_docs", "registry_record", "index.html", None),
    ]
    doc_specs.extend(employer_policy_doc_specs(retrieval))
    docs = []
    for sid, rtype, fn, pub in doc_specs:
        rec = ingest_document(sid, rtype, fn, retrieval, observed_at, published_at=pub)
        if rec:
            docs.append(rec)
            records.append(rec)

    for sid in [
        "greenhouse_stripe_jobs",
        "greenhouse_airbnb_jobs",
        "greenhouse_discord_jobs",
        "greenhouse_coinbase_jobs",
        "greenhouse_figma_jobs",
        "greenhouse_databricks_jobs",
        "greenhouse_anthropic_jobs",
        "greenhouse_datadog_jobs",
        "greenhouse_mongodb_jobs",
        "greenhouse_cloudflare_jobs",
        "greenhouse_vercel_jobs",
        "greenhouse_reddit_jobs",
        "greenhouse_twilio_jobs",
        "greenhouse_lyft_jobs",
        "greenhouse_instacart_jobs",
    ]:
        records.extend(ingest_greenhouse_jobs(sid, retrieval, observed_at))
    records.extend(ingest_ashby_jobs("ashby_notion_jobs", retrieval, observed_at))
    records.extend(ingest_lever_jobs("lever_spotify_jobs", retrieval, observed_at))

    dup_stats = assign_duplicate_groups(records)
    eval_rows = build_evaluation_cases(records)

    cafc_rows, cafc_note = build_cafc_aggregate(retrieval)
    write_jsonl(CUR / "cafc_aggregate.jsonl", cafc_rows)

    write_jsonl(CUR / "evidence.jsonl", records)
    patterns = [r for r in docs if r["record_type"] in {"government_advisory", "government_guidance", "government_report"}]
    policies = [r for r in docs if r["record_type"] == "employer_policy"]
    write_jsonl(CUR / "patterns.jsonl", patterns)
    write_jsonl(CUR / "employer_policies.jsonl", policies)
    write_jsonl(CUR / "recruiting_process_patterns.jsonl", build_recruiting_process_patterns(policies))
    write_jsonl(CUR / "hiring_pipeline_profiles.jsonl", build_hiring_pipeline_profiles(policies))
    write_jsonl(CUR / "channel_patterns.jsonl", build_channel_patterns(docs))
    write_jsonl(CUR / "evaluation_cases.jsonl", eval_rows)
    write_jsonl(CUR / "scam_tactics.jsonl", tactics_to_jsonl_rows())
    (CUR / "employer_index.json").write_text(json.dumps(build_employer_index(), indent=2), encoding="utf-8")

    parquet_info = write_parquet(records, CUR / "evidence.parquet")
    validation = validate_records(records)

    snapshot = {
        "retrieval_date": retrieval,
        "record_count": len(records),
        "sources": dict(Counter(r["source_id"] for r in records)),
        "labels": dict(Counter(r["label"] for r in records)),
        "processing_version": PROCESSING_VERSION,
    }
    write_jsonl(SNAPSHOTS / f"{retrieval}.jsonl", [snapshot])

    glue_schema = {
        "Table": {
            "Name": "creda_evidence",
            "StorageDescriptor": {
                "Columns": [{"Name": c, "Type": "string"} for c in FIELDS],
                "Location": f"s3://creda-data/curated/evidence.parquet",
                "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            },
            "PartitionKeys": [{"Name": "source_id", "Type": "string"}],
        }
    }
    (ROOT / "schemas" / "glue_evidence_table.json").write_text(json.dumps(glue_schema, indent=2))

    generate_reports(records, eval_rows, dup_stats, validation, parquet_info, retrieval, observed_at, cafc_note)
    update_registry_checksums(retrieval)

    samples = {}
    for rtype in ["official_vacancy", "employer_policy", "government_advisory", "offer_message", "job_posting"]:
        for rec in records:
            if rec["record_type"] == rtype:
                samples[rtype] = {
                    "evidence_id": rec["evidence_id"],
                    "source_id": rec["source_id"],
                    "label": rec["label"],
                    "title": rec.get("title", "")[:120],
                    "tags": rec.get("scam_pattern_tags", [])[:5],
                }
                break

    return {
        "records": len(records),
        "evaluation_cases": len(eval_rows),
        "duplicates": dup_stats,
        "validation": validation,
        "parquet": parquet_info,
        "counts_by_source": dict(Counter(r["source_id"] for r in records)),
        "counts_by_label": dict(Counter(r["label"] for r in records)),
        "samples": samples,
        "retrieval": retrieval,
    }
