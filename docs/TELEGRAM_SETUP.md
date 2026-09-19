# CredaShield on Telegram

Production bot: **[@CredashieldBot](https://t.me/CredashieldBot)**  
Web UI: https://main.d32sg54oqu2gcb.amplifyapp.com  
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com  

Telegram uses the **same Mumbai case pipeline** as the Amplify site (create case → worker evidence → Qwen judge → verdict).

---

## For job seekers (how to use the bot)

1. Open Telegram and search **@CredashieldBot**.
2. Tap **Start** so you are in a **private chat** with the bot.  
   **Groups do not work** — the bot only reads direct messages.
3. Send `/start` or `/help` for a short onboarding message.
4. Paste the recruiter message **or** send a **screenshot with a caption** (at least 12 characters of text total).
5. Wait **30–90 seconds**. The bot replies with:
   - Verdict (`High risk`, `Unverified`, `No conflict found`)
   - A short headline / reasoning
   - **Full report:** link to the Amplify site with `?case=` and `token=` so you can read exhibits and follow up on the web.

### What works today

| Input | Supported |
|-------|-----------|
| Plain text offer / DM paste | Yes |
| Photo + caption | Yes (OCR + multimodal judge path) |
| `/start`, `/help` | Yes |
| Deep link to web case | Yes |
| Private DM | Yes |
| Group chats | **No** (message ignored) |
| PDF documents | **No** (not yet) |

### Common “bot doesn’t work” causes

| Symptom | Fix |
|---------|-----|
| No reply in a **group** | Open **@CredashieldBot** in a **private chat** |
| “Forward the recruitment message…” | Paste more text (12+ chars) or add a caption to a photo |
| Long wait then timeout | Mumbai judge may be slow; retry or use the web UI |
| Full report link 403 | Link expired or wrong chat; start a new check |

---

## For operators (deploy CredaShield Telegram)

Backend code: `creda-aws-backend/src/telegram_bot.py` (deployed via SAM stack `creda-mumbai`).  
Scripts in this repo: `scripts/deploy_telegram.sh`, `scripts/setup_telegram_webhook.sh`, `scripts/test_telegram_webhook.sh`.

The `/telegram/webhook` route is **disabled** until the stack is deployed with both `TelegramBotToken` and `TelegramWebhookSecret`.

### Architecture

```
Telegram → API Gateway POST /telegram/webhook
         → Lambda (webhook) → SQS (optional) → Lambda (telegram-worker)
         → create case (DynamoDB + worker queue)
         → poll until READY
         → sendMessage with verdict + Amplify deep link
```

Webhook auth: Telegram sends `X-Telegram-Bot-Api-Secret-Token`; Lambda compares with `hmac.compare_digest`.

### 1. Create the bot (@BotFather)

1. Open [@BotFather](https://t.me/BotFather).
2. `/newbot` → pick display name and username (must end in `bot`).
3. Copy the **HTTP API token** (`123456789:ABC…`). Store in env only — **never commit**.

### 2. Generate a webhook secret

```bash
export TELEGRAM_WEBHOOK_SECRET=$(openssl rand -hex 32)
```

Do not reuse `creda-telegram-webhook` or any default string.

### 3. Deploy (one command)

```bash
export TELEGRAM_BOT_TOKEN='...'   # from @BotFather
export TELEGRAM_WEBHOOK_SECRET=$(openssl rand -hex 32)
bash scripts/deploy_telegram.sh
```

This runs `sam deploy` on stack `creda-mumbai` with:

- `TelegramBotToken`
- `TelegramWebhookSecret`
- `PublicApiUrl` → Mumbai API
- `PublicUiUrl` → Amplify URL (used in “Full report” links)

Then registers the webhook and runs `test_telegram_webhook.sh`.

### 4. Manual webhook register (if needed)

```bash
export TELEGRAM_BOT_TOKEN='...'
export TELEGRAM_WEBHOOK_SECRET='...'
bash scripts/setup_telegram_webhook.sh
```

Webhook URL: `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com/telegram/webhook`

### 5. Verify

```bash
bash scripts/test_telegram_webhook.sh          # expect 401 without secret, not 404
export TELEGRAM_WEBHOOK_SECRET='...'
bash scripts/test_telegram_webhook.sh          # expect HTTP 200
```

Live bot smoke test:

1. DM **@CredashieldBot** → `/start`
2. Paste a fee-scam style message (see `docs/TEST_PROMPTS.md`)
3. Confirm interim “checking…” then verdict + **Full report** link
4. Open link → Amplify loads case with exhibits

Check webhook health:

```bash
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" | jq .
```

Expect `url` pointing at Mumbai `/telegram/webhook`, `last_error_date` empty.

### Troubleshooting (operators)

| Symptom | Fix |
|---------|-----|
| Webhook `404` | Telegram Lambdas not deployed — run `deploy_telegram.sh` with token + secret |
| Webhook `401` | Secret mismatch — redeploy stack and re-run `setup_telegram_webhook.sh` |
| Webhook `503` | Empty `TelegramWebhookSecret` in stack |
| Bot silent | CloudWatch log group `creda-mumbai-telegram-worker` (or webhook Lambda) |
| Empty Full report URL | Redeploy with `PublicUiUrl=https://main.d32sg54oqu2gcb.amplifyapp.com` |
| Friend sees nothing in group | Expected — only private chats; document in UI |

### Security notes

- Webhook secret required on every POST (constant-time compare).
- Case access tokens are hashed in DynamoDB; Telegram replies include the raw token only in the private DM.
- Bot does not fetch arbitrary URLs from user messages.

### Not implemented yet

- PDF `message.document` intake
- `update_id` dedup for webhook retries
- Reply when poll exceeds 140s (async message)
- Helpful reply when user messages from a **group** (currently silent ignore)

### References

- Hackathons Playbook (Notion): https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd  
- Web test prompts: `docs/TEST_PROMPTS.md`  
- UI copy: intake **Telegram** card on https://main.d32sg54oqu2gcb.amplifyapp.com
