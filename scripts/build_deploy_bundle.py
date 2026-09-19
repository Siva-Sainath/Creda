#!/usr/bin/env python3
"""Build a small, Lambda-friendly deploy bundle from local curated data."""
from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUR = ROOT / "data" / "curated"
OUT = ROOT / "deploy" / "bundle"
RETRIEVAL = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Official employer aliases for fast lookup at runtime
EMPLOYER_ALIASES = {
    "amazon": ["amazon", "amazon jobs", "amazon india"],
    "google": ["google", "alphabet"],
    "microsoft": ["microsoft", "msft", "microsoft india"],
    "kpmg": ["kpmg", "kpmg india"],
    "tcs": ["tcs", "tata consultancy services"],
    "infosys": ["infosys", "infosys limited"],
    "wipro": ["wipro"],
    "hcl": ["hcl", "hcltech", "hcl technologies"],
    "cognizant": ["cognizant", "cognizant india"],
    "tech_mahindra": ["tech mahindra", "techmahindra"],
    "accenture": ["accenture", "accenture india"],
    "capgemini": ["capgemini"],
    "ibm": ["ibm", "ibm india"],
    "oracle": ["oracle", "oracle india"],
    "flipkart": ["flipkart", "flipkart careers"],
    "razorpay": ["razorpay"],
    "freshworks": ["freshworks"],
    "zoho": ["zoho", "zoho corp"],
    "american express": ["amex", "american express"],
    "valero": ["valero"],
    "stripe": ["stripe"],
    "airbnb": ["airbnb"],
    "notion": ["notion"],
    "spotify": ["spotify"],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def slim_policy(row: dict) -> dict:
    text = row.get("normalized_text") or ""
    excerpt = text[:2500]
    employer = row.get("source_id", "").replace("_recruitment_fraud_policy", "").replace("_recruitment_scams_2025", "")
    no_fee = any(
        p in text.lower()
        for p in ("don't charge", "do not charge", "never charge", "never request money", "no fee", "does not charge")
    )
    return {
        "evidence_id": row.get("evidence_id"),
        "source_id": row.get("source_id"),
        "source_url": row.get("source_url"),
        "employer_key": employer,
        "evidence_tier": row.get("evidence_tier", "T1"),
        "no_fee_statement": no_fee,
        "official_domains": _domains_from_policy(row),
        "excerpt": excerpt,
        "scam_pattern_tags": row.get("scam_pattern_tags") or [],
    }


def _domains_from_policy(row: dict) -> list[str]:
    try:
        claims = json.loads(row.get("extracted_claims") or "{}")
        return claims.get("sender_domains") or []
    except Exception:
        return []


def slim_vacancy(row: dict) -> dict:
    return {
        "evidence_id": row.get("evidence_id"),
        "source_id": row.get("source_id"),
        "employer_claimed": row.get("employer_claimed") or row.get("source_id", "").replace("greenhouse_", "").replace("lever_", "").replace("_jobs", ""),
        "role_title": row.get("role_title") or row.get("title"),
        "canonical_url": row.get("canonical_url") or row.get("source_url"),
        "country": row.get("country"),
        "published_at": row.get("published_at"),
    }


def load_jsonl(path: Path) -> list[dict]:
    """Load valid JSONL records without silently treating malformed rows as data.

    Historical research captures occasionally contain a line-broken malformed
    record.  They are excluded from the runtime artifact rather than repaired or
    guessed at during a deploy build.
    """
    if not path.exists():
        return []
    rows = []
    skipped = 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                if isinstance(value, dict):
                    rows.append(value)
    if skipped:
        print(f"warning: skipped {skipped} malformed JSONL rows from {path}")
    return rows


def slim_pipeline_profile(row: dict) -> dict:
    fraud = row.get("fraud_policy") or {}
    return {
        "profile_id": row.get("profile_id"),
        "employer_key": row.get("employer_key"),
        "display_name": row.get("display_name"),
        "scam_target_priority": row.get("scam_target_priority"),
        "no_fee_statement": row.get("no_fee_statement", True),
        "official_domains": row.get("official_domains") or [],
        "forbidden_channels": row.get("forbidden_channels") or [],
        "forbidden_requests": row.get("forbidden_requests") or [],
        "tracks": row.get("tracks") or [],
        "fraud_policy": {
            "source_url": fraud.get("source_url"),
            "offer_verification_url": fraud.get("offer_verification_url"),
            "report_email": fraud.get("report_email"),
        },
        "india_careers_url": row.get("india_careers_url"),
        "official_process_steps": row.get("official_process_steps") or [],
        "pipeline_version": row.get("pipeline_version"),
    }


def build_demo_cases() -> list[dict]:
    return [
        {
            "demo_id": "amazon-fee-gmail",
            "title": "Amazon fee from Gmail mailbox",
            "input": {
                "text": "Congratulations! Amazon is hiring. Pay INR 3500 registration fee to hr.recruitment@gmail.com via UPI.",
                "senderEmail": "hr.recruitment@gmail.com",
                "employerHint": "Amazon",
                "locale": "en-IN",
            },
            "expected_verdict": "high_risk",
            "notes": "Free mailbox + fee contradicts Amazon no-fee policy",
        },
        {
            "demo_id": "kpmg-fee-training",
            "title": "KPMG training fee impersonation",
            "input": {
                "text": "KPMG India internship selected. Pay training fee INR 5000 to secure your slot. Interview on WhatsApp.",
                "senderEmail": "kpmg.careers@outlook.com",
                "employerHint": "KPMG",
                "locale": "en-IN",
            },
            "expected_verdict": "high_risk",
            "notes": "Fee + free mailbox + WhatsApp channel vs KPMG policy",
        },
        {
            "demo_id": "stripe-legitimate-style",
            "title": "Stripe-style remote role (no fee)",
            "input": {
                "text": "Stripe is hiring Software Engineer. Apply at https://stripe.com/jobs/listing/software-engineer. No fees required.",
                "senderEmail": "",
                "employerHint": "Stripe",
                "locale": "en-US",
            },
            "expected_verdict": "no_conflict_found",
            "notes": "No fee demand; official careers reference",
        },
        {
            "demo_id": "tcs-fee-whatsapp",
            "title": "TCS fee + WhatsApp interview scam",
            "input": {
                "text": "TCS selected you for campus hiring. Pay INR 5000 registration fee via UPI. Interview on WhatsApp only.",
                "senderEmail": "tcs.hr@gmail.com",
                "employerHint": "TCS",
                "locale": "en-IN",
            },
            "expected_verdict": "high_risk",
            "notes": "Fee + Gmail + WhatsApp vs TCS IPEP pipeline",
        },
        {
            "demo_id": "flipkart-internship-fee",
            "title": "Flipkart internship fee scam",
            "input": {
                "text": "Flipkart internship offer. Pay training fee INR 3000 to secure slot. Contact on Telegram.",
                "senderEmail": "flipkart.intern@gmail.com",
                "employerHint": "Flipkart",
                "locale": "en-IN",
            },
            "expected_verdict": "high_risk",
            "notes": "Common India internship impersonation pattern",
        },
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    policies_raw = load_jsonl(CUR / "employer_policies.jsonl")
    process_by_source = {r.get("source_id"): r for r in load_jsonl(CUR / "recruiting_process_patterns.jsonl")}
    policies = []
    for r in policies_raw:
        slim = slim_policy(r)
        proc = process_by_source.get(r.get("source_id"), {})
        slim["employer_key"] = proc.get("employer_key") or slim.get("employer_key")
        slim["display_name"] = proc.get("display_name") or slim.get("employer_key")
        slim["no_fee_statement"] = proc.get("no_fee_statement", slim.get("no_fee_statement"))
        slim["official_domains"] = proc.get("official_domains") or slim.get("official_domains")
        slim["forbidden_channels"] = proc.get("forbidden_channels") or []
        slim["official_process_steps"] = proc.get("official_process_steps") or []
        policies.append(slim)

    evidence = load_jsonl(CUR / "evidence.jsonl")
    # Keep every concrete public ATS listing.  The old 1,000-row prefix favored
    # the first fetched board (mostly Stripe) and discarded other employers.
    # Generic careers and API documentation pages are not vacancies.
    vacancies = [
        slim_vacancy(r)
        for r in evidence
        if r.get("record_type") == "official_vacancy" and r.get("evidence_tier") == "T1"
        and r.get("source_id", "").startswith(("greenhouse_", "lever_", "ashby_"))
        and r.get("source_id", "").endswith("_jobs")
        and r.get("canonical_url")
    ]

    channels = load_jsonl(CUR / "channel_patterns.jsonl")
    recruiting = load_jsonl(CUR / "recruiting_process_patterns.jsonl")
    hiring_pipelines = [slim_pipeline_profile(r) for r in load_jsonl(CUR / "hiring_pipeline_profiles.jsonl")]
    tactics = load_jsonl(CUR / "scam_tactics.jsonl")

    write_jsonl(OUT / "employer_policies.jsonl", policies)
    write_jsonl(OUT / "vacancy_index.jsonl", vacancies)
    write_jsonl(OUT / "channel_patterns.jsonl", channels)
    write_jsonl(OUT / "recruiting_process_patterns.jsonl", recruiting)
    write_jsonl(OUT / "hiring_pipeline_profiles.jsonl", hiring_pipelines)
    write_jsonl(OUT / "scam_tactics.jsonl", tactics)

    employer_index_path = CUR / "employer_index.json"
    if employer_index_path.exists():
        shutil.copy(employer_index_path, OUT / "employer_index.json")
    # This is an explicit allowlist, not a list inferred from user input. Runtime
    # refresh may contact only these public provider APIs.
    official_sources_path = ROOT / "data" / "official_ats_sources.json"
    if official_sources_path.exists():
        shutil.copy(official_sources_path, OUT / "official_ats_sources.json")

    demo_cases = build_demo_cases()
    (OUT / "demo_cases.json").write_text(json.dumps(demo_cases, indent=2), encoding="utf-8")

    alias_index = []
    emp_index = []
    if (OUT / "employer_index.json").exists():
        emp_index = json.loads((OUT / "employer_index.json").read_text())
    for emp in emp_index:
        alias_index.append({"employer_key": emp["employer_key"], "aliases": emp.get("aliases", [])})
    if not alias_index:
        for key, aliases in EMPLOYER_ALIASES.items():
            alias_index.append({"employer_key": key, "aliases": aliases})
    (OUT / "employer_aliases.json").write_text(json.dumps(alias_index, indent=2), encoding="utf-8")

    # A manifest cannot validate a hash of itself.  Remove a prior manifest
    # before inventorying the artifact, then write the new manifest afterward.
    manifest_path = OUT / "manifest.json"
    manifest_path.unlink(missing_ok=True)
    files = {}
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            rel = p.relative_to(OUT).as_posix()
            files[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}

    manifest = {
        "bundle_version": "creda-deploy-1.0",
        "retrieval_date": RETRIEVAL,
        "processing_version": "creda-preprocess-2.0",
        "counts": {
            "employer_policies": len(policies),
            "employers_in_registry": len(emp_index),
            "hiring_pipeline_profiles": len(hiring_pipelines),
            "vacancies": len(vacancies),
            "channel_patterns": len(channels),
            "recruiting_process_patterns": len(recruiting),
            "scam_tactics": len(tactics),
            "demo_cases": len(demo_cases),
        },
        "files": files,
        "s3_prefix": "curated/",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"bundle": str(OUT), "manifest": str(manifest_path), "counts": manifest["counts"]}, indent=2))


if __name__ == "__main__":
    main()
