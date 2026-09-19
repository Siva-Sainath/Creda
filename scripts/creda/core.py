"""Normalization, redaction, claim extraction, parsing, and deduplication."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from rapidfuzz import fuzz

PROCESSING_VERSION = "creda-preprocess-2.0"

FIELDS = [
    "evidence_id",
    "record_type",
    "source_id",
    "source_url",
    "canonical_url",
    "source_domain",
    "publisher",
    "evidence_tier",
    "country",
    "applicant_country",
    "employment_country",
    "remote_scope",
    "language",
    "title",
    "employer_claimed",
    "employer_canonical_domain",
    "recruiter_name_claimed",
    "recruiter_contact_channel",
    "sender_domain",
    "role_title",
    "employment_type",
    "salary_text",
    "payment_requested",
    "payment_amount",
    "payment_currency",
    "payment_method",
    "requested_documents",
    "urgency_claims",
    "equipment_purchase_claim",
    "visa_or_relocation_claim",
    "extracted_claims",
    "scam_pattern_tags",
    "original_text",
    "normalized_text",
    "label",
    "label_provenance",
    "label_confidence",
    "human_review_status",
    "content_hash",
    "near_duplicate_group",
    "campaign_group",
    "derived_from_emscad",
    "published_at",
    "observed_at",
    "last_verified_at",
    "next_verification_at",
    "expires_at",
    "verification_status",
    "lifecycle_status",
    "supersedes_evidence_id",
    "raw_s3_uri",
    "curated_s3_uri",
    "pii_redaction_status",
    "processing_version",
    "evaluation_eligible",
    "evaluation_partition",
]

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4,6}(?!\d)"
)
ACCOUNT_RE = re.compile(r"\b(?:account|a/c|acct)\s*(?:no\.?|number|#)?\s*[:#]?\s*[\d-]{6,}\b", re.I)
ID_RE = re.compile(
    r"\b(?:aadhaar|aadhar|pan|passport|ssn|sin|nino|dl|driving licence|driving license)\s*(?:no\.?|number|#)?\s*[:#]?\s*[\dA-Z-]{4,}\b",
    re.I,
)
UPI_RE = re.compile(r"\b[\w.-]+@[\w.-]+\b")
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:com|org|net|in|co|io|gov|edu|uk|au|ca)\b", re.I)
CURRENCY_AMOUNT_RE = re.compile(
    r"(?:₹|inr|usd|\$|€|£|cad|aud)\s?[\d,]+(?:\.\d+)?|\b[\d,]+(?:\.\d+)?\s?(?:lakh|lakhs|crore|k|million|bn)\b",
    re.I,
)
RECIPIENT_LIST_RE = re.compile(r"(?:to:|cc:|bcc:)\s*[^\n]{20,500}", re.I)

SCAM_TAG_RULES = {
    "fee_or_deposit_request": r"\b(fee|fees|deposit|registration charge|security deposit|pay upfront|training fee|processing fee)\b",
    "equipment_purchase": r"\b(equipment|laptop|workstation|vendor|purchase.*laptop|buy.*equipment)\b",
    "fake_check_or_reimbursement": r"\b(check|cheque|reimburse|send back|return part|overpayment|mobile deposit)\b",
    "task_or_boosting": r"\b(task scam|product boosting|optimization scam|commission task|click task|captcha filling)\b",
    "crypto_or_gift_card": r"\b(crypto|bitcoin|usdt|ethereum|gift card|steam card|google play card)\b",
    "identity_or_banking_request": r"\b(passport|aadhaar|aadhar|pan card|bank account|account number|otp|ifsc|routing number)\b",
    "urgency": r"\b(immediately|urgent|final call|only \d+ day|apply fast|limited slots|act now|deadline today)\b",
    "high_salary_claim": CURRENCY_AMOUNT_RE.pattern,
    "remote_work": r"\b(remote|work from home|wfh|work-from-home)\b",
    "visa_or_relocation": r"\b(visa sponsorship|work permit|relocation package|overseas placement|abroad job)\b",
    "internship_or_apprenticeship": r"\b(internship|apprentice|placement|ppo|ppi|campus hiring)\b",
    "claimed_affiliation": r"\b(official partner|authorized recruiter|on behalf of|representing)\b",
    "no_fee_statement": r"\b(no fee|never charge|do not ask for money|free of cost|no registration fee)\b",
    "impersonation_signal": r"\b(tata group|tcs group|amazon hr|google careers|microsoft hiring|infosys careers)\b",
    "upi_payment": r"\b(upi|paytm|phonepe|gpay|google pay)\b",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", html.unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def domain_from_url(url: str) -> str:
    m = re.search(r"https?://([^/?#]+)", url or "", re.I)
    return m.group(1).lower() if m else ""


def redact_pii(text: str) -> tuple[str, str]:
    redacted = text
    redacted = EMAIL_RE.sub(r"[REDACTED_EMAIL]@\1", redacted)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = ACCOUNT_RE.sub("[REDACTED_ACCOUNT]", redacted)
    redacted = ID_RE.sub("[REDACTED_ID]", redacted)
    redacted = RECIPIENT_LIST_RE.sub("[REDACTED_RECIPIENTS]", redacted)
    redacted = re.sub(
        r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
        "[REDACTED_NAME]",
        redacted,
    )
    status = "redacted" if redacted != text else "not_applicable"
    return redacted, status


def extract_domains(text: str) -> list[str]:
    domains = set()
    for url in URL_RE.findall(text):
        d = domain_from_url(url)
        if d:
            domains.add(d)
    for d in DOMAIN_RE.findall(text):
        domains.add(d.lower())
    return sorted(domains)


def scam_pattern_tags(text: str) -> list[str]:
    t = text.lower()
    return [name for name, pat in SCAM_TAG_RULES.items() if re.search(pat, t, re.I)]


def extract_claims(text: str) -> dict[str, Any]:
    n = normalize(text)
    lower = n.lower()
    amounts = CURRENCY_AMOUNT_RE.findall(n)
    domains = extract_domains(n)
    urls = URL_RE.findall(n)
    return {
        "fees_requested": bool(re.search(SCAM_TAG_RULES["fee_or_deposit_request"], lower)),
        "deposit_requested": "deposit" in lower,
        "equipment_purchase": bool(re.search(SCAM_TAG_RULES["equipment_purchase"], lower)),
        "fake_check_or_reimbursement": bool(re.search(SCAM_TAG_RULES["fake_check_or_reimbursement"], lower)),
        "crypto_or_gift_card": bool(re.search(SCAM_TAG_RULES["crypto_or_gift_card"], lower)),
        "document_requests": bool(re.search(SCAM_TAG_RULES["identity_or_banking_request"], lower)),
        "urgency": bool(re.search(SCAM_TAG_RULES["urgency"], lower)),
        "salary_amounts": amounts[:5],
        "remote_work": bool(re.search(SCAM_TAG_RULES["remote_work"], lower)),
        "visa_or_relocation": bool(re.search(SCAM_TAG_RULES["visa_or_relocation"], lower)),
        "recruiter_identity_claimed": bool(re.search(r"\b(recruiter|talent acquisition|hr manager|hiring manager)\b", lower)),
        "sender_domains": domains[:10],
        "official_vacancy_urls": [u for u in urls if any(x in u.lower() for x in ("jobs", "careers", "greenhouse", "lever", "ashby"))][:5],
        "upi_or_wallet": bool(re.search(SCAM_TAG_RULES["upi_payment"], lower)),
        "no_fee_statement": bool(re.search(SCAM_TAG_RULES["no_fee_statement"], lower)),
        "contact_channels": detect_contact_channels(n),
        "scam_pattern_tags": scam_pattern_tags(n),
    }


def detect_contact_channels(text: str) -> list[str]:
    lower = text.lower()
    channels = []
    rules = {
        "email": r"\b(email|inbox|mail@|@gmail|@outlook|@yahoo|@rediff|@proton)\b",
        "sms": r"\b(sms|text message|otp sms|sms-header)\b",
        "whatsapp": r"\b(whatsapp|wa\.me|whats app)\b",
        "telegram": r"\b(telegram|t\.me/)\b",
        "signal": r"\b(signal messenger|signal app)\b",
        "linkedin": r"\b(linkedin|inmail)\b",
        "phone_call": r"\b(phone call|call back|mobile number)\b",
        "social_media": r"\b(facebook|instagram|telegram channel|social media ad)\b",
        "job_portal": r"\b(job portal|naukri|indeed|linkedin jobs|job board)\b",
    }
    for name, pat in rules.items():
        if re.search(pat, lower):
            channels.append(name)
    return channels


def parse_file_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            try:
                import subprocess

                return subprocess.check_output(
                    ["pdftotext", "-layout", str(path), "-"], text=True, errors="replace"
                )
            except Exception:
                return path.read_text(errors="replace")
    if suffix in {".html", ".htm"}:
        raw = path.read_text(errors="replace")
        soup = BeautifulSoup(raw, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.find("body")
        text = (main or soup).get_text(" ")
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 400 and "recruitment" in raw.lower():
            # SPA pages may hide content; keep visible strings from raw HTML
            stripped = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
            stripped = re.sub(r"<[^>]+>", " ", stripped)
            stripped = re.sub(r"\s+", " ", html.unescape(stripped)).strip()
            if len(stripped) > len(text):
                text = stripped
        return text
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(data, ensure_ascii=False)
    if suffix == ".jsonl":
        lines = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    lines.append(line.strip())
        return "\n".join(lines)
    if suffix == ".csv":
        rows = []
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rows.append(" ".join(str(v) for v in row.values() if v))
        return "\n".join(rows)
    return path.read_text(errors="replace")


def build_record(
    *,
    evidence_id: str,
    record_type: str,
    source_id: str,
    source_url: str,
    publisher: str,
    evidence_tier: str,
    text: str,
    label: str,
    label_provenance: str,
    label_confidence: str = "low",
    title: str = "",
    published_at: str | None = None,
    raw_uri: str = "",
    canonical_url: str | None = None,
    country: str = "",
    employer_claimed: str = "",
    employer_domain: str = "",
    role_title: str = "",
    employment_type: str = "",
    salary_text: str = "",
    observed_at: str,
    evaluation_eligible: bool = False,
    derived_from_emscad: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    original, pii_status = redact_pii(text)
    normalized = normalize(original)
    claims = extract_claims(normalized)
    tags = claims["scam_pattern_tags"]
    rec = {
        "evidence_id": evidence_id,
        "record_type": record_type,
        "source_id": source_id,
        "source_url": source_url,
        "canonical_url": canonical_url or source_url,
        "source_domain": domain_from_url(canonical_url or source_url),
        "publisher": publisher,
        "evidence_tier": evidence_tier,
        "country": country,
        "applicant_country": "",
        "employment_country": country,
        "remote_scope": "remote" if claims["remote_work"] else "",
        "language": "en",
        "title": title,
        "employer_claimed": employer_claimed,
        "employer_canonical_domain": employer_domain,
        "recruiter_name_claimed": "",
        "recruiter_contact_channel": "",
        "sender_domain": employer_domain,
        "role_title": role_title or title,
        "employment_type": employment_type,
        "salary_text": salary_text,
        "payment_requested": claims["fees_requested"] or claims["deposit_requested"],
        "payment_amount": claims["salary_amounts"][0] if claims["salary_amounts"] else "",
        "payment_currency": "",
        "payment_method": "upi" if claims["upi_or_wallet"] else "",
        "requested_documents": "identity_or_banking" if claims["document_requests"] else "",
        "urgency_claims": "present" if claims["urgency"] else "",
        "equipment_purchase_claim": claims["equipment_purchase"],
        "visa_or_relocation_claim": claims["visa_or_relocation"],
        "extracted_claims": json.dumps(claims, ensure_ascii=False),
        "scam_pattern_tags": tags,
        "original_text": original,
        "normalized_text": normalized,
        "label": label,
        "label_provenance": label_provenance,
        "label_confidence": label_confidence,
        "human_review_status": "unreviewed",
        "content_hash": sha256_text(normalized),
        "near_duplicate_group": sha256_text(normalized)[:16],
        "campaign_group": sha256_text(normalized)[:12],
        "derived_from_emscad": derived_from_emscad,
        "published_at": published_at,
        "observed_at": observed_at,
        "last_verified_at": None,
        "next_verification_at": None,
        "expires_at": None,
        "verification_status": "not_reverified",
        "lifecycle_status": "active",
        "supersedes_evidence_id": None,
        "raw_s3_uri": raw_uri,
        "curated_s3_uri": f"s3://creda-data/curated/evidence/{evidence_id}.json",
        "pii_redaction_status": pii_status,
        "processing_version": PROCESSING_VERSION,
        "evaluation_eligible": evaluation_eligible,
        "evaluation_partition": "",
    }
    if extra:
        rec.update(extra)
    return rec


def assign_duplicate_groups(records: list[dict[str, Any]], near_threshold: int = 92) -> dict[str, Any]:
    hash_groups: dict[str, list[int]] = defaultdict(list)
    for i, rec in enumerate(records):
        hash_groups[rec["content_hash"]].append(i)

    exact_dupes = sum(len(idxs) - 1 for idxs in hash_groups.values() if len(idxs) > 1)
    for idxs in hash_groups.values():
        group_id = records[idxs[0]]["content_hash"][:16]
        campaign = records[idxs[0]]["content_hash"][:12]
        for i in idxs:
            records[i]["near_duplicate_group"] = group_id
            records[i]["campaign_group"] = campaign

    emscad_hashes = {
        r["content_hash"]
        for r in records
        if r["source_id"] == "emscad" and r.get("normalized_text")
    }
    derived_count = 0
    for rec in records:
        if rec["source_id"] != "emscad" and rec["content_hash"] in emscad_hashes:
            rec["derived_from_emscad"] = True
            derived_count += 1

    # Near-duplicate fuzzy matching only on message-level / recent sources (not 30k+ job postings).
    near_sources = {
        "scambench_employment",
        "gmail_inbox_search",
        "i4c_fake_job_sms_advisory",
        "nasc_job_scam_fusion_report_2025",
        "ic3_annual_report_2024",
    }
    block_map: dict[str, list[tuple[int, str]]] = defaultdict(list)
    near_pairs: list[tuple[str, str, int]] = []
    for i, rec in enumerate(records):
        if rec["source_id"] not in near_sources and rec.get("record_type") not in {"offer_message", "community_report"}:
            continue
        text = rec.get("normalized_text") or ""
        if len(text) < 80:
            continue
        block = text[:48]
        matched = False
        for rep_idx, rep_text in block_map[block]:
            score = fuzz.token_set_ratio(text[:3000], rep_text[:3000])
            if score >= near_threshold:
                rec["near_duplicate_group"] = records[rep_idx]["near_duplicate_group"]
                rec["campaign_group"] = records[rep_idx]["campaign_group"]
                near_pairs.append((rec["evidence_id"], records[rep_idx]["evidence_id"], score))
                matched = True
                break
        if not matched:
            block_map[block].append((i, text))

    return {
        "exact_duplicate_rows": exact_dupes,
        "derived_from_emscad": derived_count,
        "near_duplicate_pairs_sample": near_pairs[:50],
        "unique_content_hashes": len(hash_groups),
    }
