# Creda

## You get a job offer. 30 seconds to tell if it's real.

Every month, thousands of students in India see a WhatsApp message with a company logo, a salary, and a bank account. "Send Rs 2,500 for the kit and you're hired." It's never real.

**Creda checks if a job offer is a scam** — paste the text, get a verdict in 30 seconds. No login. Same check on the web, Telegram, or Chrome.

**[Open the app](https://main.d32sg54oqu2gcb.amplifyapp.com/)** · **[Telegram @CredashieldBot](https://t.me/CredashieldBot)**

![Creda checks your offer against real employer data](docs/architecture.png)

## What you get

**Three honest verdicts.** We don't scare you just to scare you.

- **High risk**: They ask for money upfront, fake email, or known scammer tactics.
- **Unverified**: Real company, but something doesn't add up (vague role, no clear hiring process).
- **No conflict found**: The company is hiring, this looks real, go for it.

**Works with what you already have.** Paste the actual WhatsApp text the scammer sent. Copy a screenshot. Drop a job URL. We'll check it.

**Answers in 30 seconds.** We compare your offer against official employer careers pages, ATS indexes, and a database of known scam fee structures. It's fast because we cache the evidence overnight.

**Runs where you are.** Amplify web app in India. Telegram for anyone. No account, no tracking.

## Try it

**Definitely a scam:**

```
Flipkart hiring for WFH catalog tagging. Salary 35k/month. 
Buy starter kit Rs 2499 on PhonePe to hr.flipkart.wfh@gmail.com. 
Training on WhatsApp group only.
```

**Suspicious but not proof:**

```
LinkedIn InMail from Notion Talent: We loved your profile for a remote PM role. 
Reply with your salary expectation. Interview tomorrow on Google Meet, no prep needed.
```

**Probably real:** a direct link to Flipkart Careers or LinkedIn from a verified account, no upfront fee.

## Why we built this

A student who pays Rs 2,499 (USD 3) for a fake "starter kit" loses two weeks of part-time income. If Creda takes 30 seconds to save one student a month, it pays for itself. We built it because scam offers keep changing but the pattern doesn't.

## How it works (the short version)

You paste an offer → we check it against real employer websites → we look for fee tactics (UPI requests, "kit" payments, registration fees) → we tell you what we found.

If you send a screenshot, we can read it with image AI. If you're not sure what service to trust, we tell you honestly: we couldn't verify, so be careful.

## The stack

We run it cheap so students can use it free. Here's what you need to know:

- **Web:** Amplify (static hosting)
- **API:** Lambda functions that check employers and scam patterns
- **Database:** DynamoDB (stores your cases so you can follow up)
- **Search:** Overnight batch job that refreshes employer data from ATS indexes
- **Judge:** Small Qwen model on Fargate (decides if it's a scam)
- **Optional:** GPU when you upload a screenshot (usually off, costs almost nothing at this scale)

**What it costs:**

| Scenario | Cost |
|----------|------|
| 1,000 students checking offers per month (text only) | under USD 5 |
| Keep the judge warm 24/7 | ~USD 5/day |
| GPU for screenshot reading (when used) | ~USD 0.58/hour |

One fake deposit that doesn't work out costs way more than a month of Creda.

## Set it up

**For you (try it live right now):**

[Open app](https://main.d32sg54oqu2gcb.amplifyapp.com/)

**For Telegram:**

Message [@CredashieldBot](https://t.me/CredashieldBot), paste an offer, get a verdict.

**For developers (run it yourself):**

```bash
# Set up Python
python -m venv .venv
source .venv/bin/activate

# Install and run
pip install -r requirements.txt
bash scripts/serve_frontend.sh
```

```bash
# Check the API is alive
curl -s https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com/health | jq .
```

**Full setup:** See `DEPLOY.md` and `docs/TELEGRAM_SETUP.md`.

**Telegram hardening:** See `docs/TELEGRAM_BOT_HARDENING.md`.

## Structure

```
backend/           Lambda functions that do the checking
frontend/          The web app (Amplify)
infra/             Deployment templates (SAM, ECS)
scripts/           Deploy, tests, and GPU scaling
docs/              Setup guides, architecture notes
deploy/bundle/     Employer evidence (built offline)
extension/         Chrome helper
```

## For your own domain

The app lives at `*.amplifyapp.com` and you can't rename that. To use your own domain:

1. Buy a domain in Route 53 (e.g., `creda.in`)
2. In the Amplify console, go to **Hosting** → **Custom domains**
3. Map your domain to the `main` branch

That's it. You'll have your own URL in a few minutes.

## Next

- **Run it locally:** `DEPLOY.md`
- **Set up Telegram:** `docs/TELEGRAM_SETUP.md`
- **How we check:** `docs/MVP-HARDENED-ARCHITECTURE.md`
- **Report a bug:** [GitHub Issues](https://github.com/Siva-Sainath/Creda/issues)
