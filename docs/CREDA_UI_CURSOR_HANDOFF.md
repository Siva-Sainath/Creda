# Creda UI handoff

The frontend is a static, vanilla HTML/CSS/JS build designed for AWS Amplify.

## Files

- `frontend/index.html` — source UI, live API client, responsive design system, Ruling + Exhibits renderer, follow-up flow, report flow.
- `frontend/dist/index.html` — generated deploy artifact for the current Mumbai API.
- `frontend/amplify.yml` — fail-closed build; requires `VITE_API_URL` and replaces `__CREDA_API_URL__`.

## Live contract

The UI calls only:

`https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`

It uses `GET /health`, `POST /cases`, `GET /cases/{caseId}` with `X-Case-Token`, `POST /cases/{caseId}/followup`, and `POST /reports/scam`. Case tokens stay in memory and `sessionStorage`; they are never placed in URLs or logs.

## Design language

Creda is presented as a calm case file: a warm paper background, navy ink, blue evidence controls, and a clear verdict stamp. The result is ordered as ruling → exhibits → orders → follow-up → evidence timeline. Risk, uncertainty, and consistency use both color and text. The layout is mobile-first, keyboard-friendly, and honors `prefers-reduced-motion`.

## Local build check

```bash
cd /Users/siva/Documents/first_commit_hack/frontend
VITE_API_URL=https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
test -n "$VITE_API_URL" || exit 1
mkdir -p dist
sed "s|__CREDA_API_URL__|$VITE_API_URL|g" index.html > dist/index.html
test -z "$(rg '__CREDA_API_URL__' dist/index.html || true)"
```

Before deploying, run the live acceptance flow: open the dist file or Amplify URL, confirm the live health badge, submit the fee-request demo, wait for real evidence and ruling data, send a follow-up, and submit a report. Keep the UI wording honest when the backend returns a fallback or `unverified` result.

The current backend health response reports `judgeMode: creda`, `agentQueueConfigured: true`, 18 ATS sources, 47 indexed employers, daily vacancy refresh, OCR upload support, and no open-web search per request. The current ECS judge still has a structured-output parsing issue documented in `LLM-JUDGE-LIVE-VERIFICATION-2026-09-18.md`; the UI renders the returned fallback honestly and does not fabricate a Qwen result.
