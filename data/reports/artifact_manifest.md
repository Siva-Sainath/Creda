# Creda downloaded-data manifest

Retrieval date: 2026-09-17 (UTC)

Raw files are under `data/raw/<source_id>/2026-09-17/`. SHA-256 values for every raw file are in [`data/raw/2026-09-17.sha256`](../raw/2026-09-17.sha256).

Downloaded and accepted:

- EMSCAD Kaggle copy: `DataSet.csv` (17,880 rows; 17,014 legitimate and 866 historical fraudulent flags; 2012–2014).
- DiFrauD job-scams component: train/validation/test JSONL (14,295 rows total; MIT; provenance overlaps historical job-scam corpora).
- Kaggle fake-vs-real synthetic dataset: 3,000 rows, MIT; pattern exploration only and excluded from final evaluation.
- I4C fake CAPTCHA-filling advisory PDF.
- MEA overseas-employment guidance page.
- Amazon India recruitment-fraud policy and Amazon Jobs page.
- Y Combinator jobs page.
- Greenhouse Job Board API and Lever Postings API documentation.
- Canadian Anti-Fraud Centre CSV (350,361 de-identified complaint rows) plus 39-category aggregate summary.
- Australian National Anti-Scam Centre 2025 Job Scam Fusion Cell report PDF.

Unavailable or quarantined:

- FTC job-scams page: live download returned HTTP 403; web research captured the source identity and it remains registered as unavailable until a permitted snapshot is obtained.
- Srisai Hassanisetty fake-only Kaggle dataset: not downloaded because license/provenance could not be verified; remains quarantined.

Curated outputs:

- `data/curated/evidence.jsonl` and `evidence.parquet`: 35,179 canonical records.
- `data/curated/patterns.jsonl`: government guidance/advisory records.
- `data/curated/employer_policies.jsonl`: Amazon policy record.
- `data/curated/evaluation_cases.jsonl`: untouched source-grouped EMSCAD holdout cases.
- `data/curated/cafc_aggregate.jsonl`: aggregate context, kept separate from case evidence.
- `data/private/gmail_recruitment_candidates.jsonl`: 14 redacted inbox candidates, all `unverified`.
