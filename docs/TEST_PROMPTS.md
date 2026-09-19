# Creda test prompts (live regression catalog)

All scenarios live in **`scripts/test_cases.json`** — no UI demo chips, no hardcoded verdict tuning. Re-run anytime against prod.

## Quick start

```bash
# Full API catalog (21 cases + follow-ups + OCR + intake guards) — ~25–40 min
bash scripts/run_test_catalog.sh

# Same via legacy name
bash scripts/test_prompt_rotation.sh

# Everything: API catalog + vacancy unit tests + browser UI (if Playwright installed)
bash scripts/test_live_suite.sh

# Browser only (first 6 ui-tagged cases from catalog)
bash scripts/test_ui_journey.sh
```

Env overrides:

| Variable | Default |
|----------|---------|
| `CREDA_API_URL` | `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com` |
| `CREDA_UI_URL` | `https://main.d32sg54oqu2gcb.amplifyapp.com` |
| `CREDA_TEST_CHANNEL` | `api` (use `ui` to filter catalog) |
| `CREDA_UI_MAX_CASES` | `6` |

## Manual website testing

Open the live UI, paste each **offerText** below, add **links** if listed, submit, then ask the **follow-ups**.

### High-risk patterns (often `high_risk`)

| ID | Paste this |
|----|------------|
| `anthropic-laptop-deposit` | Hi, Anthropic AI Safety team here. You passed the screen. Transfer $450 laptop security deposit to anthropic-onboarding@proton.me before we ship equipment. Interview was on Telegram @AnthropicHire. |
| `flipkart-whatsapp-kit` | Flipkart hiring for WFH catalog tagging. Salary 35k/month. Buy starter kit Rs 2499 on PhonePe to hr.flipkart.wfh@gmail.com. Training on WhatsApp group only. |
| `tcs-registration-fee` | TCS campus offer letter attached. Pay Rs 8500 document verification and background check to tcs-onboarding@yahoo.com via UPI before joining Chennai office. |
| `infosys-laptop-security` | Infosys selected you for Java Developer. Laptop security deposit Rs 12000 refundable after 6 months. Pay to infosys.hr.recruit@gmail.com. Interview completed on Telegram. |
| `meta-gift-card-equipment` | Meta Reality Labs offer. Purchase $500 Apple gift cards for home office equipment reimbursement — send codes to meta-onboarding@icloud.com before equipment ships. |
| `deloitte-form-bitly` | Deloitte USI campus shortlist. Register: https://bit.ly/deloitte-usi-2026 then fill Google Form. Pay Rs 999 background verification to deloitte.hr@gmail.com |
| `airbnb-fee-scam` | Airbnb Trust & Safety analyst role. Pay $299 background check fee to airbnb.hr.verify@gmail.com before access badge is issued. |

### India / channel-specific

| ID | Notes |
|----|-------|
| `hcl-telegram-interview` | Add link: `https://t.me/hcl_fasthire` |
| `razorpay-fake-offer` | PAN/Aadhaar to Outlook sender |
| `whatsapp-protonmail-data-entry` | WhatsApp-origin vague offer |

### EU / remote scams

| ID | Paste this |
|----|------------|
| `revolut-eu-remote-scam` | Revolut Operations Associate — 100% remote from Bucharest. €90/hour paid in Bitcoin. Buy €200 onboarding voucher before contract signing. |
| `nl-data-entry-wire` | Amsterdam Logistics BV — remote data entry, €65/hour. Wire €350 equipment insurance to IBAN before first shift. |

### Typosquat / KYC / identity

| ID | Notes |
|----|-------|
| `coinbase-typosquat-crypto` | Link: `https://coinbase-careers-verify.net/form` |
| `passport-upfront-kyc` | Passport + SSN before interview |

### Legit ATS probes (expect `unverified` or `no_conflict_found`)

| ID | Links to add |
|----|----------------|
| `anthropic-official-greenhouse` | `https://job-boards.greenhouse.io/anthropic/jobs/4461450008` |
| `figma-greenhouse-legit` | `https://job-boards.greenhouse.io/figma/jobs/5630673004` |
| `coinbase-greenhouse-legit` | `https://boards.greenhouse.io/coinbase/jobs/8175363` |
| `mongodb-greenhouse` | `https://boards.greenhouse.io/mongodb/jobs/6205599` |
| `spotify-gmail-mismatch` | `https://jobs.lever.co/spotify` + Gmail sender |

### Vague / LinkedIn

| ID | Paste this |
|----|------------|
| `notion-linkedin-vague` | LinkedIn InMail from Notion Talent: We loved your profile for a remote PM role. Reply with salary expectation — interview tomorrow on Google Meet. |

### Multimodal (screenshot)

Upload **`scripts/fixtures/ocr_scam_offer.png`** with caption: `Screenshot of suspicious job message attached.`

## Follow-up questions (pick 2 per case)

**Sender / channel**
- Is a free Gmail sender normal for this employer?
- Would official HR use ProtonMail or WhatsApp for hiring?

**Payment**
- Should I ever pay a registration or training fee before joining?
- Is it normal to pay via UPI, gift card, or crypto for a job?

**Links**
- Should I click a bit.ly link from a recruiter?
- Why is a Google Form a warning sign for employer hiring?
- Is a Telegram interview invite trustworthy?

**Verify**
- What is the safest way to verify this offer?
- What should I screenshot before reporting this?

**ATS**
- Does this job ID appear on the employer official careers feed?
- What else should I verify before I apply?

## What to verify

| Check | Pass criteria |
|-------|----------------|
| `agentSource` | `creda` or `creda-vlm` (not `fallback`) |
| Verdict | Renders within ~90s; stamp visible |
| Follow-up | "Creda answer" bubble after each question |
| Links panel | Google Form / bit.ly / t.me exhibits when links added |
| Report scam | Prefill from last ruling (UI) or `POST /reports/scam` → `PENDING_REVIEW` |

## Should reject (no case created)

```
hi
```

## Telegram (@CredashieldBot)

Use the same bodies as the table above. Send `/start` first. Photo path: upload `ocr_scam_offer.png` with caption `Please check this offer screenshot`.
