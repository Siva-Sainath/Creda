# COMPOSER — FORCE VISIBLE REDESIGN (updated after live retest)

**Modes:** `/architect` → `/poteto-mode`

Live: https://main.d32sg54oqu2gcb.amplifyapp.com/  
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com  
Edit + deploy `frontend/index.html` so Amplify **looks different** on hard-refresh. No PR unless asked.

## Latest Grok live retest (2026-09-19) — VERDICT: PARTIAL

### What improved
- Result/aftercare more case-file: RISK pill, E1–E4, Why/What expanders, Do not pay, Telegram `t.me/CredashieldBot`, Report missed scam
- Real API OK on create/poll
- Mobile stacks

### Still failing (must fix)
1. **Intake still marketing prototype** — “Check a job offer before you reply”, two-column hero, stock doc/magnifier/shield art, 1–2–3 steps. No case-file tool chrome on cold load. Telegram/report missing on intake.
2. **Wait stages don’t play** — Markup has folder/magnifier/slips/scan/stamp but run stays ~2s on folder “Opening your case…” then jumps to result. No magnifier, scan, stamp press, or mock-browser visible. Enforce **≥700ms dwell** per scene + compressed playlist when API is fast.
3. **“Stamp” on result is a RISK pill**, not a pressed ruling stamp. Exhibit “WHY WE TRUST THIS” lines empty.
4. **Follow-up CRITICAL BUG:** chip/send → “CREDA Thinking…” then **“Something went wrong / evidence is not defined”** (client JS ReferenceError). Pattern card may appear; **no Creda reply bubble**. Fix the undefined `evidence` reference; keep case token on every followup + poll.
5. Copy says “Hit +” but UI is paperclip — either add circular + or fix copy.
6. Step 3 on intake highlights when textarea fills, before Check — don’t mark complete early.
7. Second run with fee+Aadhaar still titled fee-only; transient better headline didn’t stick.

### Rejection criteria (task fails if any remain on live Amplify)
- Intake still looks like old marketing hero
- Wait never shows ≥2 distinct SVG scenes (folder→slips/magnifier→stamp or mock-browser)
- Follow-up throws or shows no assistant reply
- Result has empty “WHY WE TRUST THIS” / no real stamp language
- Hard-refresh still “same site”

---

## /architect then /poteto-mode

Visual system: paper `#F3F1EC`, ink, mono stamps, case-file intake (not marketing), wait storyboard with min dwell, result stamp→E1–E4→orders→aftercare, follow-up thread with token.

### P0 code fixes
- Find/fix `evidence is not defined` in follow-up render path.
- Always send `X-Case-Token` / access token on GET poll + POST followup.
- Render conversation bubbles after 202.
- Need-from-you vs Ask-Creda; Ask chips send.
- Wait: min 700ms/scene; playlist intake→evidence→(ocr)→stream mock-browser→stamp even if API returns in 2s.
- Implement real mock-browser chrome for stream (lukacho / 21st Safari hand-port).
- Result: SVG/CSS stamp press; fill provenance on exhibits or hide empty WHY lines.
- Intake: kill marketing hero energy; circular + or honest paperclip copy; optional Telegram on chrome.

### Resource → look (hand-port, no npm React)
| Process | FROM | LOOK |
|---------|------|------|
| Wait intake | CredaShieldArt / SVG Repo folder | Sheet into folder; tab pulse; ≥700ms |
| Wait evidence | animata bento + magnifier | Slips stagger; magnifier drift; checks |
| Wait OCR | scan-line | Loop only while OCR |
| Wait stream | lukacho / 21st Safari + kokonut shimmer | Browser chrome + URL; sheen on tokens |
| Wait/result stamp | stamp SVG | One press READY |
| Exhibits | animata bento + rechesoares flip | E1–E4; “Why we trust this” |
| Composer | 21st Input Bar | NL + circular attach + drop |

SKIP: unicorn WebGL, looping split-text, blank spinner.

Tokens: `--ink #0F2433; --muted #5F6D7A; --bg #F3F1EC; --panel #FFF; --line #D7E0E8; --blue #155EEF; --risk #B42318; --safe #087443; --warn #9A6700;`

## Done
Deploy Amplify. Hard-refresh. Reply with what **visually** changed + “Ready for Grok Bot test loop”. Do not claim SHIP.
