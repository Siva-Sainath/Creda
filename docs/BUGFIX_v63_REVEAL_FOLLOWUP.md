# BUGFIX v63 — Reveal ghosting + follow-up answers

**Date:** 2026-09-19 IST  
**Build:** `baseten-20260919-v63-reveal-followup`  
**Base:** Local `baseten-20260919-v62-glass-vectors` (ahead of live `v62b-controls`)  
**Live:** https://main.d32sg54oqu2gcb.amplifyapp.com/  
**Amplify app:** `d32sg54oqu2gcb` · profile `creda-dev` · `ap-south-1`

## P0 fixed

### P0-1 — Stamp / tiles ghosted after result render
After 2nd/3rd case, GSAP `from`/`autoAlpha` leave stamp, headline, chips, and tiles at opacity ~0.14–0.43.

**Fix:**
- `CredaMotion.forceRevealVisible()` — kill prior reveal TL, `gsap.set` / `clearProps`, force `opacity:1` / `visibility:visible`
- `resultReveal` uses `fromTo` → explicit end `autoAlpha:1`, `onComplete` force-clears inline props
- Every `renderResult` resets opacity/visibility before animating; `skipReveal` still force-visible
- `prefers-reduced-motion`: show fully visible, no stuck autoAlpha (JS early-return + CSS `!important`)

### P0-2 — Follow-up never answers
Domain follow-ups left the chat bubble on interim copy (“…Creda is writing the explanation”). Board wipe stayed OK.

**Fix:**
- `isInterimText` / `extractFollowupAnswer` — never treat interim headlines as the chat answer
- `followupReplyComplete` — READY with only interim / no real `agentReply`/`followupReply`/assistant turn → **keep polling**
- On READY with a real answer → replace placeholder with headline/agent answer via `ensureFollowupAssistantTurn`
- On poll timeout → honest **“I couldn't verify that domain yet”**, keep prior ruling (snapshot merge unchanged)
- Pending bubble copy: “Creda is checking that domain…” (never interim headline)

## P1 while touching same files

- Thin / overlay pane scrollbars; outer panes `overflow:hidden`; inner scroller only when needed
- Check in-flight: `setIntakeBusy` disables Check; health pill shows **CHECKING** (not stuck READY)
- Stamp `pointer-events: none` + toolbar z-index so **Check another** stays clickable
- `#judgment-host` / `.why-collapsed` cleared below tactics so **Why Creda ruled** does not overlap tiles

## Deploy

```bash
cd frontend
mkdir -p dist && cp index.html styles.css app.js dist/
zip -qr deploy.zip -C dist .
AWS_PROFILE=creda-dev ./deploy_amplify_v62.sh   # or create-deployment flow
```

Verify: `curl -sL https://main.d32sg54oqu2gcb.amplifyapp.com/ | grep creda-build`  
Expect: `baseten-20260919-v63-reveal-followup`

## Out of scope

No PRs. No multimodal claims.
