# Creda WorkOffer Shield — product map (Gate 1)

## User

Job seeker in India receiving recruiter messages (email, WhatsApp, DM). Non-expert, often on phone, one-time or occasional use. Job: decide whether to reply, pay, or share documents.

## Entities

| Entity | Key fields | States |
|---|---|---|
| Case | caseId, token, offerText, attachments | queued → running → completed |
| Evidence | check, outcome, tier, excerpt, sourceUrl | per-check outcome |
| Verdict | verdict, headline, confidence, agentReasoning | high_risk / no_conflict_found / unverified / pending |
| Report | reportText, linkedCaseId | submitted |

## Actions → endpoints

| Action | Endpoint | Reversible |
|---|---|---|
| Check offer | POST /cases | yes (new case) |
| Poll status | GET /cases/{id} | — |
| Follow-up | POST /cases/{id}/followup | yes |
| Attach file | POST /upload-url | yes |
| Report scam | POST /reports/scam | no |
| Health | GET /health | — |

## Flows

1. **Check offer:** Paste/drop → POST /cases → wait stream → ruling + exhibits → follow-up optional
2. **Demo:** Chip fills + submits → same as 1
3. **Report missed scam:** Footer panel → POST /reports/scam → confirmation
4. **Resume:** sessionStorage case → GET /cases/{id} → result if ready else wait

## State matrix

| Screen | Loading | Empty | Success | Error |
|---|---|---|---|---|
| Intake | health pill | composer placeholder | — | error card + Fix it / Try again |
| Wait | shimmer + branch stream | live exhibits empty state | stream + exhibits | stream error card + Try again / Go back |
| Result | — | no evidence dock message | ruling + flip exhibits | error card + Got it / Check another |
| Report | send disabled | validation | "Report sent" | error card + Try again |

Async: judge runs on ECS/SageMaker; UI polls every 2s, max 5 min, then partial result + timeout message.
