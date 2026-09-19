# CURSOR — ECS is the real judge · near–SageMaker speed · paste links · ATS/EventBridge · easy scam report

**Modes (mandatory):** `/architect` then `/poteto-mode`

Live UI: https://main.d32sg54oqu2gcb.amplifyapp.com/  
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com  
AWS profile: `creda-dev` · region `ap-south-1`  
Repo: `/Users/siva/Documents/first_commit_hack`

**Why this brief exists**
1. Always-on SageMaker `ml.g5.xlarge` (`creda-qwen-judge`) burns ~$1.4/hr ≈ **$1k/mo**. User has **~$250 credits** — not enough for a month of SM.  
2. Live worker today: ECS `creda-qwen-cpu:23` with **`JUDGE_BACKEND=sagemaker`**. Flip so **ECS/llama is the true production path**.  
3. Users paste **job URLs + mail links** (Google Forms, “Click to Enroll”, Corizo/IBM-style bait) and expect Creda to **use** those hyperlinks — not ignore them.  
4. Health already reports `searcher.atsSources: 18`, `employersIndexed: 47`, `vacancyRefresh: daily`, but `forumIngestion: false` — verify ATS works end-to-end and wire EventBridge for scam/forum intel.  
5. Reporting a new scam must be a **first-class, easy** aftercare action (`POST /reports/scam`).

Do **not** open a PR unless asked. Deploy Amplify + required AWS stacks. Report blockers honestly.

---

## Part A — `/architect` (write first, then implement)

Deliver a short plan covering:
1. **Cutover:** SageMaker → ECS-primary (`JUDGE_BACKEND=llama`), when to delete/stop `creda-qwen-judge`.  
2. **Latency budget:** target p50 / p95 case judgment time on ECS vs current SM.  
3. **Link intake:** how paste detects URLs (job ATS, careers, mailto, Google Forms, bit.ly) and what is fetched vs string-analyzed (SSRF rules).  
4. **Searcher:** which ATS APIs (Greenhouse / Lever / Ashby) are hit live vs index-only.  
5. **EventBridge:** daily ingest + optional forum/advisory schedule; keep T3 forums **non-verdict**.  
6. **Report scam UX:** one-tap from result aftercare; receipt; storage.  
7. **Acceptance tests** (table at bottom).

Then `/poteto-mode`.

---

# P0 — ECS is the true backend (stop SageMaker burn)

## Current verified state (re-check yourself)
```bash
aws --profile creda-dev --region ap-south-1 sagemaker describe-endpoint \
  --endpoint-name creda-qwen-judge --query EndpointStatus
# expect: InService  → this is the cost bleed

aws --profile creda-dev --region ap-south-1 ecs describe-task-definition \
  --task-definition creda-qwen-cpu:23 \
  --query 'taskDefinition.containerDefinitions[].environment[?name==`JUDGE_BACKEND` || name==`SAGEMAKER_ENDPOINT_NAME` || name==`LLAMA_URL`]'
# today: JUDGE_BACKEND=sagemaker
```

## Required cutover
1. Redeploy ECS with **`CREDA_JUDGE_BACKEND=llama`** (see `scripts/deploy_qwen_ecs.sh`; template default may still say sagemaker — **override**).  
2. Confirm new task def env: `JUDGE_BACKEND=llama`, llama-server sidecar healthy, worker logs `Creda judge worker ready (llama.cpp backend)`.  
3. Run one live case; confirm judgment completes with `agentSource` / logs showing **llama**, not `InvokeEndpoint`.  
4. **Delete or stop** SageMaker endpoint `creda-qwen-judge` (and endpoint config if unused) so credits stop burning. Confirm status `Failed`/`OutOfService`/absent.  
5. Update `/health` (or docs) so operators see judge backend honestly if a field exists; do not claim SageMaker while on llama.

## Make ECS inference *near* SageMaker (same product feel)

SageMaker quality today = GPU `ml.g5.xlarge` + vLLM + Qwen3.5-4B VLM.  
CPU llama on Fargate will never fully match GPU TTFT — close the **gap users feel**:

### A1 — Same model family + tight outputs (do first)
- Keep **Qwen3 / Qwen3.5 4B-class** GGUF on llama.cpp (match SM model family; don’t silently switch to a tiny toy model).  
- Cap completions: `QWEN_MAX_TOKENS` ≤ **180–220** for judge JSON; **disable thinking** / hidden chain-of-thought if the build still emits it.  
- Keep the **tiny fixed JSON schema** (verdict, headline, short why, exhibit titles) — frontend owns chrome.  
- Warm the model: llama-server stays up in the task; hit a tiny health completion on boot so first user case isn’t cold-load.

### A2 — Hardware path to “near SM” without $1k/mo
Pick **one** and implement (prefer in order for $250 credits):

| Option | What | When |
|--------|------|------|
| **H1 (default always-on)** | Fargate CPU llama, optimized prompts/quant (Q4_K_M or Q5), 2–4 vCPU / 8–16GB if template allows | Always on — fits credits |
| **H2 (demo turbo)** | ECS **EC2 capacity provider** on **g5.xlarge** (or g4dn) running **same vLLM image** as SM used, scheduled **only demo hours** via EventBridge start/stop of ASG desired=0/1 | Hackathon / judging windows |
| **H3 (optional)** | Spot GPU EC2 + ECS — cheaper turbo, expect reclaim | If Spot available in ap-south-1 |

**Do not** run SM + GPU ECS + idle CPU triple-billing. One always-on path only.

### A3 — Product UX so ECS “feels” like SM
- Wait choreography still ≥700ms/scene but **total** wait tracks real poll; don’t fake 8s if ready in 3s.  
- Stream tokens from llama if available (same mock-browser sheen as SM path).  
- If llama slower, show honest stage copy (“Reading ATS boards…”, “Writing ruling…”) — never a blank spinner.  
- Multimodal: OCR/screenshot path must still work when backend is llama (CPU may skip VLM images — if so, **say so in UI** and still use OCR text in packet; don’t hang on SM-only image branch).

### A4 — Acceptance for Part A
- [ ] `JUDGE_BACKEND=llama` on running task  
- [ ] SageMaker endpoint deleted/stopped (no InService)  
- [ ] Fee-scam demo still `high_risk` with exhibits  
- [ ] Stripe/clean ATS demo still honest (vacancy match, not “authenticated”)  
- [ ] p50 judgment (evidence→ready) measured and reported in your reply  
- [ ] Credit posture: only one GPU path if any; default CPU always-on

---

# P1 — Paste job links + mail links (hyperlinks that actually get used)

## User problem (from WhatsApp / Corizo-style mail)
Copy-paste often **drops hyperlinks**. Victims only see “Click to Enroll Now” while the real URL is a **Google Form** / phishing enroll link / fake IBM×NSDC landing. Creda must:
1. Accept **raw URLs** pasted alone or inside message text.  
2. Accept **mailto:** and visible “From / Subject / body” email pastes.  
3. Prefer an explicit **Links** field (multi-URL) so users can paste hrefs they copied separately.  
4. Extract URLs with a robust regex + HTML `href` if they paste a fragment.  
5. Classify each URL: `ats_job` | `careers` | `google_form` | `shortener` | `mailto` | `telegram` | `unknown`.

## Security (non-negotiable — from build brief)
- **Never SSRF-fetch arbitrary phishing URLs from the worker.**  
- **Allowlist fetch only:** known ATS JSON APIs, resolved official employer careers hosts, allowlisted gov/advisory feeds.  
- For suspicious links: **parse as strings**, expand redirect metadata if safely available via reputation/string checks, show “where this claims to go”, add exhibit — do **not** execute the enroll form.

## UI (intake)
- Composer still primary; add compact **“Add links”** chip → opens chips/inputs for 1–5 URLs.  
- Channel chip **Email** already hints to paste From/Subject/body — also prompt “Paste every link from the mail.”  
- On submit, client sends `offerText` plus optional `links: string[]` (add API field if missing; mirror into case packet).  
- During wait: stage copy when a Google Form / enroll CTA is detected (“Checking enrollment link pattern…”).

## Backend
- URL extractor in gather packet.  
- Signals: fee+enroll CTA, Google Form, lookalike careers domain, ATS board token if URL matches Greenhouse/Lever/Ashby patterns → vacancy tool.  
- Exhibits must cite the **link class** (E.g. “Enrollment Google Form — not an official careers apply URL”).

### Acceptance
- [ ] Paste only a Greenhouse job URL → vacancy check runs (or clear “board not in index”).  
- [ ] Paste mail body + Google Form URL → form flagged; no SSRF to the form.  
- [ ] Paste Corizo/IBM-style enroll CTA text + link → high_risk or unverified with tactic exhibits, never “safe because IBM mentioned”.

---

# P2 — Verify searcher + ATS APIs (make them real)

Live health:
```json
"searcher": {
  "atsSources": 18,
  "employersIndexed": 47,
  "vacancyRefresh": "daily",
  "openWebPerRequest": false,
  "forumIngestion": false
}
```

## Required verification (run and paste results)
1. `GET /health` — searcher block present.  
2. `scripts/test_ats_pipeline.sh` (or equivalent) against **live API**:
   - Stripe + official Greenhouse link → vacancy evidence.  
   - Fake “Stripe HR” WhatsApp fee → high_risk, no false vacancy blessing.  
3. Confirm daily ingest: EventBridge rule `CredaDailyIngest` (see `infra/template.yaml` `DailyIngestSchedule`) invokes ingest Lambda; last success in CloudWatch/S3 freshness.  
4. If ATS live HTTP is broken (index stale only), fix allowlisted clients for:
   - Greenhouse `boards-api.greenhouse.io/v1/boards/{token}/jobs`
   - Lever `api.lever.co/v0/postings/{site}?mode=json`
   - Ashby `api.ashbyhq.com/posting-api/job-board/{name}`
5. Surface in UI when vacancy matched: exhibit “Official board snapshot · observed &lt;date&gt;” (T1 supporting).

### Acceptance
- [ ] ATS script green on live API  
- [ ] Health `atsSources` / `employersIndexed` match reality  
- [ ] One matched + one deliberately unmatched employer demo documented

---

# P3 — EventBridge for forums / new scam intel (T3 discovery only)

Today `forumIngestion: false`. Implement **safely**:

1. **EventBridge schedule** (e.g. every 6–24h) → ingest Lambda/job that pulls **allowlisted** advisory/forum sources already in Creda’s source policy (I4C / CERT-In style advisories, curated scam reports — **not** random open web).  
2. Write into the existing S3/data lake as **T3 discovery** tactics / IOCs (domains, fee phrases, channel patterns).  
3. **Hard rule:** T3 never alone sets `high_risk`. Verdict still needs T1/T2 signals (fee policy, domain, ATS, etc.).  
4. Flip health `forumIngestion: true` only when the pipeline actually runs.  
5. Optional: EventBridge rule on “new report accepted” → light enrichment (dedupe domains into review queue) — **no auto-ban without review**.

Do **not** build a scrapers free-for-all. Prefer the sources already ranked in `data/reports/source_quality_ranking.md`.

### Acceptance
- [ ] Schedule visible in EventBridge  
- [ ] One successful ingest log + artifact timestamp  
- [ ] Health flag honest  
- [ ] Unit/integration: T3-only packet cannot become high_risk

---

# P4 — Make “report a new scam” easy

Existing: `POST /reports/scam` with `{ reportText, employerHint?, contactConsent? }` · UI has a Report control that was previously buried.

## UX
1. On **result aftercare** (not orphan footer): primary-adjacent ghost **“Report a missed scam”**.  
2. One-click expand: textarea prefilled with **current case headline + key links + verdict** (editable).  
3. Optional employer hint; consent checkbox if contact stored.  
4. Submit → real receipt id/message; disable double-submit.  
5. From intake (no case): still allow report via same panel with empty prefills.  
6. Telegram: short line “Or tip @CredashieldBot” — compact chip, not a fat banner.

## Backend
- Confirm API stores report (Dynamo/S3) with timestamp, optional `caseId`, `links[]`.  
- Emit EventBridge event `creda.scam_report.created` for Part P3 enrichment (optional).  
- Rate-limit / size-cap abuse.

### Acceptance
- [ ] Report from result aftercare succeeds on live API  
- [ ] Prefill includes links from the case  
- [ ] Receipt shown; error path honest

---

# P5 — Do not regress UI craft (while you touch intake/results)
- Fix blank stamp if still present: `.stampInkPress` must **not** drive fill to opacity 1 over same-color text (split `.stamp-fill` / `.stamp-text`).  
- Keep glass + no cream construction grid.  
- Vector tactic tiles preferred over text walls (fee, Telegram, enroll form, domain mismatch).

---

# Done checklist (reply with all)
1. `/architect` plan summary  
2. Proof: `JUDGE_BACKEND=llama` + SageMaker endpoint **not** InService  
3. Measured ECS judgment latency (p50/p95) vs prior SM if known  
4. Link paste: ATS URL demo + Google Form demo results  
5. ATS pipeline script output  
6. EventBridge ingest: rule name + last run evidence  
7. Report scam: screenshot + receipt  
8. Amplify hard-refresh note  
9. “Ready for Grok Bot test loop”

## Hard fail
- Still calling SageMaker while claiming ECS primary  
- SM endpoint left InService burning credits  
- Fetching arbitrary user links (SSRF)  
- Forums alone forcing high_risk  
- Report still orphan-only / broken API  
- Blank stamp still solid with invisible text
