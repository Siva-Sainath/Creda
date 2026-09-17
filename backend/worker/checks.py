"""
Creda — Deterministic sender checks.

None of these need an API key, a partner agreement, or a model.
Together they produce most of the high-risk verdicts you will demo,
they run in well under a second, and they work identically for a
company nobody has ever heard of.

Checks:
  1. Domain match         sender apex vs official domain          T1
  2. Free mailbox         gmail / outlook / yahoo / rediff        T2
  3. Lookalike domain     Levenshtein + confusable characters     T2
  4. Domain age           RDAP registration date                  T2
  5. Mail posture         MX / SPF / DMARC via DNS                T2
  6. Payment demand       UPI / bank / crypto / gift card regex   T1
  7. Link destinations    shorteners, IPs, domain mismatches      T2

Rule: NEVER fetch a suspicious URL. Parse it as a string, check
reputation lists, show the user where it goes.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import requests

from shared.models import (
    EvidenceRecord, EmployerProfile, EvidenceTier, EvidenceOutcome,
    CheckType, ChecksResult, Claim
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TWO_PART_TLDS = {
    ".co.uk", ".co.in", ".com.au", ".com.br", ".net.in", ".org.in",
    ".ac.in", ".gov.in", ".co.nz", ".co.za", ".co.jp",
}


def extract_apex_domain(value: str) -> str | None:
    """Extract the registrable (apex) domain from an email or URL."""
    if not value:
        return None
    try:
        value = value.strip().lower()
        if "@" in value:
            domain = value.split("@")[-1]
        elif "://" in value:
            domain = urlparse(value).netloc.split(":")[0]
        else:
            domain = value.split("/")[0].split(":")[0]

        parts = domain.split(".")
        if len(parts) < 2:
            return domain or None
        last_two = f".{parts[-2]}.{parts[-1]}"
        if last_two in TWO_PART_TLDS and len(parts) > 2:
            return f"{parts[-3]}.{parts[-2]}.{parts[-1]}"
        return f"{parts[-2]}.{parts[-1]}"
    except Exception:
        return None


def extract_email_domain(email: str) -> str | None:
    """Full domain part of an email (not just apex)."""
    if not email or "@" not in email:
        return None
    return email.split("@")[-1].strip().lower()


def extract_urls_from_text(text: str) -> list[str]:
    """Pull all http/https URLs from free text."""
    return re.findall(r"https?://[^\s\"'<>)\]]+", text)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Classic DP Levenshtein — no external dependency."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]


# ---------------------------------------------------------------------------
# Main checker
# ---------------------------------------------------------------------------

class DeterministicChecker:
    """Runs all deterministic sender checks against one offer."""

    # -- Known sets ----------------------------------------------------------

    KNOWN_ATS_DOMAINS = {
        "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com",
        "smartrecruiters.com", "recruitee.com", "myworkday.com",
        "icims.com", "taleo.net",
    }

    FREE_MAILBOXES = {
        "gmail.com", "googlemail.com", "outlook.com", "hotmail.com",
        "live.com", "yahoo.com", "yahoo.co.in", "rediffmail.com",
        "protonmail.com", "proton.me", "ymail.com", "aol.com",
        "mail.com", "zoho.com", "icloud.com", "gmx.com", "tutanota.com",
    }

    UPI_HANDLES = {
        "upi", "paytm", "ybl", "okaxis", "okhdfcbank", "oksbi",
        "apl", "ibl", "axl", "oksbi", "okicici", "axisbank",
    }

    SHORTENERS = {
        "bit.ly", "tinyurl.com", "t.co", "goo.gl",
        "is.gd", "rb.gy", "shorturl.at",
    }

    CONFUSABLES: dict[str, str] = {
        "0": "o", "1": "l", "l": "1", "rn": "m",
        "vv": "w", "5": "s",
    }

    SCAM_SUFFIXES = ["-careers", "-jobs", "-hr", "-india", "-hiring", "-recruit"]

    # -----------------------------------------------------------------------
    # 1. Domain match (T1)
    # -----------------------------------------------------------------------

    def check_domain_match(
        self, sender_email: str | None, employer: EmployerProfile | None,
    ) -> EvidenceRecord:
        """Compare sender apex domain to official employer domain."""
        sender_apex = extract_apex_domain(sender_email) if sender_email else None
        if not sender_apex:
            return EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check=CheckType.DOMAIN_MATCH,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={"error": "No sender email to check"},
            )

        official = employer.official_domain if employer else None
        official_apex = extract_apex_domain(official) if official else None

        if not official_apex:
            return EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check=CheckType.DOMAIN_MATCH,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={"sender_apex": sender_apex, "note": "No official domain to compare"},
            )

        if sender_apex == official_apex or sender_apex in self.KNOWN_ATS_DOMAINS:
            return EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check=CheckType.DOMAIN_MATCH,
                outcome=EvidenceOutcome.CONFIRMED,
                details={
                    "sender_apex": sender_apex,
                    "official_apex": official_apex,
                    "is_ats": sender_apex in self.KNOWN_ATS_DOMAINS,
                },
            )

        # Mismatch — downgrading to T2 so legitimate recruiting agencies don't auto-trigger HIGH RISK without a fee demand
        return EvidenceRecord(
            tier=EvidenceTier.T2_TECHNICAL,
            check=CheckType.DOMAIN_MATCH,
            outcome=EvidenceOutcome.CONFLICT,
            details={
                "sender_apex": sender_apex,
                "official_apex": official_apex,
                "note": "Sender domain differs from employer's official domain",
            },
        )

    # -----------------------------------------------------------------------
    # 2. Free mailbox (T2)
    # -----------------------------------------------------------------------

    def check_free_mailbox(
        self, sender_email: str | None, offer_text: str,
    ) -> EvidenceRecord:
        """Detect personal mailbox + fee language combination."""
        domain = extract_email_domain(sender_email) if sender_email else None
        if not domain:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.FREE_MAILBOX,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={"error": "No sender email"},
            )

        if domain not in self.FREE_MAILBOXES:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.FREE_MAILBOX,
                outcome=EvidenceOutcome.CONFIRMED,
                details={"sender_domain": domain, "note": "Not a free mailbox"},
            )

        # Is there also a fee demand in the text?
        fee_re = re.compile(
            r"\b(fee|deposit|payment|pay\s+us|processing\s+fee|"
            r"security\s+deposit|refundable\s+deposit|registration\s+fee)\b",
            re.IGNORECASE,
        )
        has_fee = bool(fee_re.search(offer_text))

        if has_fee:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.FREE_MAILBOX,
                outcome=EvidenceOutcome.CONFLICT,
                details={"sender_domain": domain, "note": "Free mailbox + fee demand in text"},
            )

        return EvidenceRecord(
            tier=EvidenceTier.T2_TECHNICAL,
            check=CheckType.FREE_MAILBOX,
            outcome=EvidenceOutcome.UNRESOLVED,
            details={"sender_domain": domain, "note": "Free mailbox but no explicit fee"},
        )

    # -----------------------------------------------------------------------
    # 3. Lookalike domain (T2)
    # -----------------------------------------------------------------------

    def check_lookalike_domain(
        self, sender_email: str | None, employer: EmployerProfile | None,
    ) -> EvidenceRecord:
        """Levenshtein + confusable-character check against official domain."""
        sender_apex = extract_apex_domain(sender_email) if sender_email else None
        official_apex = extract_apex_domain(employer.official_domain) if employer and employer.official_domain else None

        if not sender_apex or not official_apex:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.LOOKALIKE_DOMAIN,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={"reason": "Missing sender or official domain"},
            )

        if sender_apex == official_apex:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.LOOKALIKE_DOMAIN,
                outcome=EvidenceOutcome.CONFIRMED,
                details={"sender_apex": sender_apex, "note": "Exact match"},
            )

        dist = levenshtein_distance(sender_apex, official_apex)

        # Check confusable substitutions
        subs_found: list[str] = []
        for orig, confuse in self.CONFUSABLES.items():
            if orig in sender_apex and confuse in official_apex:
                subs_found.append(f"{orig}↔{confuse}")

        # Check scam suffixes
        sender_name = sender_apex.split(".")[0]
        official_name = official_apex.split(".")[0]
        has_suffix = any(sender_name.endswith(s) for s in self.SCAM_SUFFIXES)
        starts_with_official = sender_name.startswith(official_name)

        is_lookalike = (0 < dist <= 3) or (has_suffix and starts_with_official) or bool(subs_found)

        if is_lookalike:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.LOOKALIKE_DOMAIN,
                outcome=EvidenceOutcome.CONFLICT,
                details={
                    "sender_apex": sender_apex,
                    "official_apex": official_apex,
                    "distance": dist,
                    "substitutions": subs_found,
                    "has_scam_suffix": has_suffix,
                },
            )

        return EvidenceRecord(
            tier=EvidenceTier.T2_TECHNICAL,
            check=CheckType.LOOKALIKE_DOMAIN,
            outcome=EvidenceOutcome.UNRESOLVED,
            details={"distance": dist, "sender_apex": sender_apex, "official_apex": official_apex},
        )

    # -----------------------------------------------------------------------
    # 4. Domain age via RDAP (T2)
    # -----------------------------------------------------------------------

    def check_domain_age(self, sender_email: str | None) -> EvidenceRecord:
        """RDAP lookup for sender domain registration date."""
        sender_apex = extract_apex_domain(sender_email) if sender_email else None
        if not sender_apex:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.DOMAIN_AGE,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={"error": "No sender domain"},
            )

        # Skip well-known domains
        sender_domain = extract_email_domain(sender_email) if sender_email else None
        if sender_domain in self.FREE_MAILBOXES or sender_apex in self.KNOWN_ATS_DOMAINS:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.DOMAIN_AGE,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={"note": "Skipping age check for well-known domain"},
            )

        try:
            resp = requests.get(f"https://rdap.org/domain/{sender_apex}", timeout=5)
            if resp.status_code != 200:
                raise ValueError(f"RDAP returned {resp.status_code}")

            events = resp.json().get("events", [])
            reg_date_str = None
            for ev in events:
                if ev.get("eventAction") == "registration":
                    reg_date_str = ev.get("eventDate")
                    break

            if not reg_date_str:
                return EvidenceRecord(
                    tier=EvidenceTier.T2_TECHNICAL,
                    check=CheckType.DOMAIN_AGE,
                    outcome=EvidenceOutcome.UNAVAILABLE,
                    source_url=f"https://rdap.org/domain/{sender_apex}",
                    details={"reason": "No registration event in RDAP response"},
                )

            # Parse ISO date
            if reg_date_str.endswith("Z"):
                reg_date_str = reg_date_str[:-1] + "+00:00"
            reg_date = datetime.fromisoformat(reg_date_str)
            age_days = (datetime.now(timezone.utc) - reg_date).days

            if age_days < 30:
                outcome = EvidenceOutcome.CONFLICT
            elif age_days < 90:
                outcome = EvidenceOutcome.UNRESOLVED
            else:
                outcome = EvidenceOutcome.CONFIRMED

            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.DOMAIN_AGE,
                outcome=outcome,
                source_url=f"https://rdap.org/domain/{sender_apex}",
                details={"age_days": age_days, "registration_date": reg_date.isoformat()},
            )

        except Exception as exc:
            logger.warning("RDAP lookup failed for %s: %s", sender_apex, exc)
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.DOMAIN_AGE,
                outcome=EvidenceOutcome.UNAVAILABLE,
                details={"error": str(exc)},
            )

    # -----------------------------------------------------------------------
    # 5. Mail posture via DNS (T2)
    # -----------------------------------------------------------------------

    def check_mail_posture(self, sender_email: str | None) -> EvidenceRecord:
        """Check MX, SPF, and DMARC records for the sender domain."""
        domain = extract_email_domain(sender_email) if sender_email else None
        if not domain:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.MAIL_POSTURE,
                outcome=EvidenceOutcome.UNAVAILABLE,
                details={"error": "No sender domain"},
            )

        if domain in self.FREE_MAILBOXES:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.MAIL_POSTURE,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={"note": "Skipping posture check for free mailbox"},
            )

        has_mx = False
        has_spf = False
        has_dmarc = False

        try:
            import dns.resolver
            res = dns.resolver.Resolver()
            res.timeout = 5
            res.lifetime = 5

            try:
                if res.resolve(domain, "MX"):
                    has_mx = True
            except Exception:
                pass

            try:
                for rdata in res.resolve(domain, "TXT"):
                    txt = b"".join(rdata.strings).decode("utf-8", errors="ignore").lower()
                    if txt.startswith("v=spf1"):
                        has_spf = True
                        break
            except Exception:
                pass

            try:
                for rdata in res.resolve(f"_dmarc.{domain}", "TXT"):
                    txt = b"".join(rdata.strings).decode("utf-8", errors="ignore").lower()
                    if txt.startswith("v=dmarc1"):
                        has_dmarc = True
                        break
            except Exception:
                pass

        except ImportError:
            # Fallback: Cloudflare DNS-over-HTTPS
            return self._mail_posture_doh(domain)
        except Exception as exc:
            # If there was a timeout or network failure, we cannot say they explicitly LACK records (conflict)
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.MAIL_POSTURE,
                outcome=EvidenceOutcome.UNAVAILABLE,
                details={"error": f"DNS resolution failed: {exc}"},
            )

        details = {"has_mx": has_mx, "has_spf": has_spf, "has_dmarc": has_dmarc}

        if not has_mx and not has_spf:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.MAIL_POSTURE,
                outcome=EvidenceOutcome.CONFLICT,
                details={**details, "note": "No MX and no SPF — domain has no mail infrastructure"},
            )

        if has_mx and has_spf and has_dmarc:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.MAIL_POSTURE,
                outcome=EvidenceOutcome.CONFIRMED,
                details={**details, "note": "Solid mail posture"},
            )

        return EvidenceRecord(
            tier=EvidenceTier.T2_TECHNICAL,
            check=CheckType.MAIL_POSTURE,
            outcome=EvidenceOutcome.UNRESOLVED,
            details={**details, "note": "Partial mail configuration"},
        )

    def _mail_posture_doh(self, domain: str) -> EvidenceRecord:
        """Fallback: use Cloudflare DoH when dnspython is unavailable."""
        has_mx = False
        has_spf = False
        headers = {"Accept": "application/dns-json"}
        try:
            r = requests.get(f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX", headers=headers, timeout=5)
            if r.status_code == 200 and r.json().get("Answer"):
                has_mx = True
        except Exception:
            pass
        try:
            r = requests.get(f"https://cloudflare-dns.com/dns-query?name={domain}&type=TXT", headers=headers, timeout=5)
            if r.status_code == 200:
                for ans in r.json().get("Answer", []):
                    if "v=spf1" in ans.get("data", "").lower():
                        has_spf = True
                        break
        except Exception:
            pass

        details = {"has_mx": has_mx, "has_spf": has_spf, "method": "cloudflare_doh"}
        if not has_mx and not has_spf:
            outcome = EvidenceOutcome.CONFLICT
        elif has_mx and has_spf:
            outcome = EvidenceOutcome.CONFIRMED
        else:
            outcome = EvidenceOutcome.UNRESOLVED

        return EvidenceRecord(
            tier=EvidenceTier.T2_TECHNICAL,
            check=CheckType.MAIL_POSTURE,
            outcome=outcome,
            details=details,
        )

    # -----------------------------------------------------------------------
    # 6. Payment demand extraction (T1)
    # -----------------------------------------------------------------------

    def check_payment_demand(self, offer_text: str) -> EvidenceRecord:
        """Regex extraction of UPI IDs, bank accounts, crypto, amounts, urgency."""
        details: dict = {}
        found = False

        # UPI IDs — distinguish from email by checking handle
        upi_re = re.compile(r"([a-zA-Z0-9.\-_]+@[a-zA-Z]+)")
        for m in upi_re.finditer(offer_text):
            handle = m.group(1).split("@")[-1].lower()
            if handle in self.UPI_HANDLES:
                details.setdefault("upi_id", []).append(m.group(1))
                found = True

        # Bank account numbers
        acct_re = re.compile(r"(?i)(?:account|a/c|acct)[\s:#\-]?(\d{9,18})")
        for m in acct_re.finditer(offer_text):
            details.setdefault("bank_account", []).append(m.group(1))
            found = True

        # IFSC codes
        ifsc_re = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
        for m in ifsc_re.finditer(offer_text):
            details.setdefault("ifsc", []).append(m.group(0))
            found = True

        # Amounts (₹, Rs, INR)
        amt_re = re.compile(r"(?i)(?:fee|deposit|pay|charge|cost|transfer|registration).{0,30}(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{1,2})?)")
        for m in amt_re.finditer(offer_text):
            details.setdefault("amount", []).append(m.group(1).replace(",", ""))
            found = True

        # Crypto wallets
        btc_re = re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|\bbc1[ac-hj-np-z02-9]{11,71}\b")
        eth_re = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
        for m in list(btc_re.finditer(offer_text)) + list(eth_re.finditer(offer_text)):
            details.setdefault("crypto_address", []).append(m.group(0))
            found = True

        # Gift cards
        gift_re = re.compile(r"(?i)\b(gift\s+card|voucher|amazon\s+pay|itunes)\b")
        for m in gift_re.finditer(offer_text):
            details.setdefault("gift_card", []).append(m.group(1))
            found = True

        # Urgency / deadline
        urgency_re = re.compile(
            r"(?i)\b(within 24 hours|immediate(?:ly)?|today only|last date|"
            r"expires?|deadline|urgent|limited time)\b"
        )
        for m in urgency_re.finditer(offer_text):
            details.setdefault("deadline", []).append(m.group(1))

        if found:
            return EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check=CheckType.PAYMENT_DEMAND,
                outcome=EvidenceOutcome.CONFIRMED,
                details=details,
            )

        return EvidenceRecord(
            tier=EvidenceTier.T1_AUTHORITATIVE,
            check=CheckType.PAYMENT_DEMAND,
            outcome=EvidenceOutcome.UNRESOLVED,
            details={"note": "No explicit payment demands found"},
        )

    # -----------------------------------------------------------------------
    # 7. Link destination analysis (T2)
    # -----------------------------------------------------------------------

    def check_link_destinations(
        self, offer_text: str, links: list[str], employer: EmployerProfile | None,
    ) -> EvidenceRecord:
        """Parse URLs — check for shorteners, IPs, domain mismatches. Never fetch."""
        all_urls = list(set(extract_urls_from_text(offer_text) + (links or [])))
        if not all_urls:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.LINK_DESTINATION,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={"note": "No links found"},
            )

        official_apex = extract_apex_domain(employer.official_domain) if employer and employer.official_domain else None
        ip_re = re.compile(r"https?://\d+\.\d+\.\d+\.\d+")

        shortener_hits: list[str] = []
        ip_hits: list[str] = []
        mismatch_hits: list[str] = []

        for url in all_urls:
            domain = extract_apex_domain(url)
            if not domain:
                continue
            if domain in self.SHORTENERS:
                shortener_hits.append(url)
            if ip_re.match(url):
                ip_hits.append(url)
            if official_apex and domain != official_apex and domain not in self.KNOWN_ATS_DOMAINS:
                mismatch_hits.append(url)

        details = {
            "total_links": len(all_urls),
            "shorteners": shortener_hits,
            "ip_links": ip_hits,
            "mismatched_links": mismatch_hits,
        }

        if ip_hits or shortener_hits:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.LINK_DESTINATION,
                outcome=EvidenceOutcome.CONFLICT,
                details={**details, "note": "Suspicious link format (IP address or URL shortener)"},
            )

        if not mismatch_hits:
            return EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.LINK_DESTINATION,
                outcome=EvidenceOutcome.CONFIRMED,
                details={**details, "note": "All links point to official or known ATS domains"},
            )

        return EvidenceRecord(
            tier=EvidenceTier.T2_TECHNICAL,
            check=CheckType.LINK_DESTINATION,
            outcome=EvidenceOutcome.UNRESOLVED,
            details={**details, "note": "Some links point to third-party domains"},
        )

    # -----------------------------------------------------------------------
    # Run all checks
    # -----------------------------------------------------------------------

    def run_all_checks(
        self,
        offer_text: str,
        sender_email: str | None = None,
        links: list[str] | None = None,
        employer: EmployerProfile | None = None,
    ) -> ChecksResult:
        """Execute every deterministic check and return aggregated results."""
        evidence: list[EvidenceRecord] = []
        claims: list[Claim] = []

        evidence.append(self.check_domain_match(sender_email, employer))
        evidence.append(self.check_free_mailbox(sender_email, offer_text))
        evidence.append(self.check_lookalike_domain(sender_email, employer))
        evidence.append(self.check_domain_age(sender_email))
        evidence.append(self.check_mail_posture(sender_email))

        payment_ev = self.check_payment_demand(offer_text)
        evidence.append(payment_ev)
        # If payment was found, create a Claim for it
        if payment_ev.outcome == EvidenceOutcome.CONFIRMED:
            amt = payment_ev.details.get("amount", ["unknown"])[0] if payment_ev.details.get("amount") else "unknown"
            upi = payment_ev.details.get("upi_id", [None])[0] if payment_ev.details.get("upi_id") else None
            claims.append(Claim(
                type="payment_demand",
                value=f"INR {amt}" if amt != "unknown" else "Payment requested",
                quote=f"UPI: {upi}" if upi else None,
            ))

        evidence.append(self.check_link_destinations(offer_text, links or [], employer))

        return ChecksResult(evidence=evidence, claims_extracted=claims)
