# UI PACK 0 — Commit v64 baseline (run first)

**Role:** Cursor Composer  
**Branch:** `creda/mvp-g4dn-ship`  
**Repo:** `/Users/siva/Documents/first_commit_hack`  
**Do NOT open a PR.**

---

## Why this pack exists

`frontend/index.html`, `frontend/styles.css`, and `frontend/app.js` are modified but **uncommitted**. Last commit is `0f0978e` (v60 two-pane). Live Amplify serves `baseten-20260919-v64-intake-clean` from local uncommitted work. Commit the baseline **before** UI-1 through UI-5 so the rewrite is revertible.

---

## Global rules (all packs)

- Vanilla Amplify frontend only: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`. No React, no npm UI kits.
- AWS profile `creda-dev`, region `ap-south-1`.
- No PRs unless the human explicitly asks.
- No flip-cards. No 720px postcard shell regressions.
- Do not claim multimodal / screenshot / PDF upload unless GPU Path C is live (out of scope for UI packs).

---

## Steps

### 1. Confirm branch and dirty state

```bash
cd /Users/siva/Documents/first_commit_hack
git branch --show-current
git status --short frontend/
```

**Expect:** branch `creda/mvp-g4dn-ship`; three modified files under `frontend/`.

### 2. Inspect diff (do not skip)

```bash
git diff --stat frontend/
git diff frontend/index.html | head -80
grep 'creda-build' frontend/index.html
```

**Expect:** meta `baseten-20260919-v64-intake-clean` (or similar v64 tag).

### 3. Stage only frontend baseline

```bash
git add frontend/index.html frontend/styles.css frontend/app.js
git status --short
```

**Do NOT** stage `frontend/deploy.zip`, `frontend/dist/`, or unrelated docs unless the human asked.

### 4. Commit

```bash
git commit -m "$(cat <<'EOF'
feat(ui): commit v64 intake-clean baseline before UI rewrite

Preserves uncommitted two-pane workspace, glass vectors, reveal/follow-up
fixes, and compact Telegram chip so UI PACK 1–5 can rewrite from a known point.
EOF
)"
```

### 5. Verify

```bash
git log -1 --oneline
git status --short frontend/
```

**Pass if:**
- New commit exists on `creda/mvp-g4dn-ship`.
- `frontend/index.html`, `styles.css`, `app.js` are clean (no unstaged changes).
- `grep creda-build frontend/index.html` still shows a v64 build tag.

**Fail if:** commit hook rejects — fix hook issues and create a **new** commit (do not amend unless hook auto-modified staged files).

---

## Hard-fail

- Do not proceed to UI PACK 1 with uncommitted frontend changes.
- Do not rewrite CSS/JS/HTML in this pack — commit only.

---

## Next pack

→ [UI_PACK_1_html_restructure.md](./UI_PACK_1_html_restructure.md)
