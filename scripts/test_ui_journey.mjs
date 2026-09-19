#!/usr/bin/env node
/**
 * Browser UI journey — reads scripts/test_cases.json (channel=ui).
 * Types into live Amplify app, waits for rulings, sends follow-ups. Not API shortcuts.
 */
import { chromium } from "playwright";
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const CATALOG = process.env.CREDA_TEST_CATALOG || join(ROOT, "scripts/test_cases.json");
const UI = process.env.CREDA_UI_URL || "https://main.d32sg54oqu2gcb.amplifyapp.com";
const POLL_MS = 2000;
const MAX_POLLS = 80;
const MAX_UI_CASES = parseInt(process.env.CREDA_UI_MAX_CASES || "6", 10);

const catalog = JSON.parse(readFileSync(CATALOG, "utf8"));

function resolveFollowups(caseItem) {
  const tags = caseItem.followupTags || [];
  const pool = catalog.followupPool || {};
  const out = [];
  const seen = new Set();
  for (const tag of tags) {
    for (const q of pool[tag] || []) {
      if (!seen.has(q)) {
        seen.add(q);
        out.push(q);
      }
      if (out.length >= 2) return out;
    }
  }
  return out.slice(0, 2);
}

const CASES = catalog.cases
  .filter((c) => (c.channels || []).includes("ui") && c.type !== "ocr_upload")
  .slice(0, MAX_UI_CASES)
  .map((c) => ({
    id: c.id,
    text: c.payload.offerText,
    expectVerdict: c.expectVerdict || null,
    followups: resolveFollowups(c),
    links: c.payload.links || [],
  }));

function log(msg) {
  process.stdout.write(`[${new Date().toISOString().slice(11, 19)}] ${msg}\n`);
}

async function waitForVerdict(page, expectVerdict, label) {
  for (let i = 0; i < MAX_POLLS; i++) {
    const state = await page.evaluate(() => ({
      verdict: document.body.getAttribute("data-verdict") || "",
      resultVisible: !document.getElementById("view-result")?.classList.contains("hidden"),
      error: document.getElementById("intake-error")?.textContent?.trim() || "",
      headline: document.querySelector("#ruling-host")?.textContent?.slice(0, 120) || "",
    }));
    if (state.error && !state.resultVisible && i > 3) {
      throw new Error(`${label}: intake error — ${state.error}`);
    }
    if (state.resultVisible && state.verdict && state.verdict !== "pending") {
      if (expectVerdict && state.verdict !== expectVerdict) {
        throw new Error(`${label}: expected verdict ${expectVerdict}, got ${state.verdict}`);
      }
      const meta = await page.evaluate(() => ({
        agentSource: document.getElementById("footer-agent-source")?.textContent?.trim() || "",
      }));
      if (meta.agentSource === "fallback") {
        throw new Error(`${label}: agentSource is fallback`);
      }
      log(`${label}: PASS verdict=${state.verdict} source=${meta.agentSource || "creda"}`);
      return state;
    }
    if (i % 5 === 0) {
      log(`${label}: polling (${i * 2}s) verdict=${state.verdict || "—"}`);
    }
    await page.waitForTimeout(POLL_MS);
  }
  throw new Error(`${label}: timeout after ${MAX_POLLS * 2}s`);
}

async function submitOffer(page, text, links = []) {
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    sessionStorage.clear();
    const ta = document.getElementById("offer-text");
    if (ta) ta.value = "";
  });
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForSelector("#offer-text", { state: "visible" });
  await page.fill("#offer-text", text);

  if (links.length) {
    const addBtn = page.locator("#btn-add-links, .btn-add-links").first();
    if (await addBtn.count()) {
      await addBtn.click();
      const inputs = page.locator('input[type="url"], input.link-input, [data-link-input]');
      for (let i = 0; i < Math.min(links.length, 2); i++) {
        if (await inputs.nth(i).count()) {
          await inputs.nth(i).fill(links[i]);
        }
      }
    }
  }

  await page.waitForFunction(() => !document.getElementById("btn-check")?.disabled, null, { timeout: 8000 }).catch(() => {});
  await page.click("#btn-check");
  await page.waitForSelector("#view-wait:not(.hidden), #view-result:not(.hidden)", { timeout: 15000 });
}

async function sendFollowup(page, question) {
  await page.waitForSelector("#view-result:not(.hidden)", { timeout: 8000 });
  await page.fill("#followup-input", question);
  await page.click("#btn-followup");
  await page.waitForSelector("#view-wait:not(.hidden)", { timeout: 15000 });
  for (let i = 0; i < 100; i++) {
    const resultVisible = await page.evaluate(() => !document.getElementById("view-result")?.classList.contains("hidden"));
    const verdict = await page.evaluate(() => document.body.getAttribute("data-verdict") || "");
    if (resultVisible && verdict && verdict !== "pending") {
      const convText = await page.evaluate(() => document.getElementById("conversation-host")?.textContent || "");
      if (convText.length > 30) {
        log(`follow-up: PASS (${convText.slice(0, 72)}...)`);
        return convText;
      }
    }
    await page.waitForTimeout(POLL_MS);
  }
  throw new Error("follow-up: timeout");
}

async function main() {
  log(`UI journey on ${UI} — ${CASES.length} cases from ${CATALOG}`);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  let failed = 0;

  try {
    for (const c of CASES) {
      try {
        await submitOffer(page, c.text, c.links);
        await waitForVerdict(page, c.expectVerdict, c.id);
        for (const q of c.followups) {
          await sendFollowup(page, q);
        }
        await page.click("#btn-new");
        await page.waitForSelector("#view-intake:not(.hidden)", { timeout: 8000 });
      } catch (e) {
        failed++;
        log(`${c.id}: FAIL ${e.message}`);
      }
    }

    log("==> short input rejected in UI");
    await page.goto(UI, { waitUntil: "networkidle" });
    await page.evaluate(() => sessionStorage.clear());
    await page.reload({ waitUntil: "networkidle" });
    await page.fill("#offer-text", "hi");
    await page.click("#btn-check");
    await page.waitForTimeout(1500);
    const err = await page.evaluate(() => document.getElementById("intake-error")?.textContent?.trim() || "");
    if (!err) {
      failed++;
      log("short-input: FAIL no error shown");
    } else {
      log(`short-input: PASS`);
    }
  } finally {
    await browser.close();
  }

  if (failed) {
    log(`UI JOURNEY FAILED (${failed} case(s))`);
    process.exit(1);
  }
  log("UI JOURNEY PASSED");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
