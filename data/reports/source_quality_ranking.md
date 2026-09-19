# Source quality ranking for Creda

Generated: 2026-09-17

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
