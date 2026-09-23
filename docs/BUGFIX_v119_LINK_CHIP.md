# BUGFIX v119 — Duplicate URL in intake composer

**Date:** 2026-09-23 IST  
**Build:** `baseten-20260923-v119-linkchip`  
**Live:** https://main.d32sg54oqu2gcb.amplifyapp.com/  
**Amplify app:** `d32sg54oqu2gcb` · profile `creda-dev` · `ap-south-1`  
**Git:** `5680b20` on `main`

## Problem

Pasting a job or careers URL into the intake composer showed the same link twice:

1. As a parsed **link chip** above the textarea
2. Again as raw text inside the textarea

URL-only pastes also left a large empty textarea under the chip, so the composer looked broken and the dashed toolbar divider sat awkwardly in the middle of the field.

## Fix

- **`syncParsedLinksFromText`** — detected URLs are moved into chips and stripped from the visible textarea (message text stays)
- **`composerContentLength`** — Check stays enabled for link-only pastes (length counts chip URLs)
- **`buildPayload`** — link-only submissions still send `offerText` (joined URLs) plus `links[]`
- **`.composer-card.links-only`** — collapses the empty textarea when only chips are present
- **`deploy_amplify_frontend.sh`** — zip now includes `iso-anim.js` (required by `iso-loop.js`)

## Files

| File | Change |
|---|---|
| `frontend/app.js` | URL strip, chip-only layout state, payload/send-button logic |
| `frontend/styles.css` | `has-link-chips` / `links-only` composer styles |
| `frontend/index.html` | Build meta + cache-bust `v119-linkchip` |
| `scripts/deploy_amplify_frontend.sh` | Copy `iso-anim.js` into deploy zip |

## Deploy

```bash
/usr/local/bin/aws login --profile creda-dev   # if credentials expired
bash scripts/deploy_amplify_frontend.sh
```

Verify:

```bash
curl -sL https://main.d32sg54oqu2gcb.amplifyapp.com/ | grep creda-build
```

Expect: `baseten-20260923-v119-linkchip`

Amplify job **113** — SUCCEED (2026-09-23).

## Test

1. Hard-refresh the live app (Cmd+Shift+R).
2. Paste `https://luma.com/lossfunk?e=evt-…` into the composer.
3. URL appears **once** in the chip row; textarea stays empty (placeholder visible).
4. **Check** is enabled; submit works.
