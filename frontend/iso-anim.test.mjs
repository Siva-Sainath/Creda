import fs from "node:fs";
import assert from "node:assert/strict";
import test from "node:test";
import { followU, snapBox } from "./iso-anim.js";

test("followU does not lerp backward across the 0-1 wrap (the flicker)", () => {
  const lerped = 0.98 + (0.02 - 0.98) * 0.12;
  assert.ok(lerped > 0.8, "documents the old lerp flying backward");
  assert.equal(followU(0.98, 0.02, 0.12), 0.02);
});

test("followU still eases forward between stations", () => {
  const next = followU(0.2, 0.4, 0.12);
  assert.ok(next > 0.2 && next < 0.4);
});

test("snapBox rounds fractional portal CSS pixels", () => {
  assert.deepEqual(snapBox(577.078, 279.564, 266.4, 260.2), {
    left: 577,
    top: 280,
    width: 266,
    height: 260,
  });
});

test("iso-loop idle packet follows wrap-safe followU, not raw lerp", () => {
  const src = fs.readFileSync(new URL("./iso-loop.js", import.meta.url), "utf8");
  assert.match(src, /packetU = followU\(packetU, targetU/);
  assert.doesNotMatch(src, /packetU = lerp\(packetU, targetU, 0\.12\)/);
});

test("iso-loop does not portal the canvas onto document.body", () => {
  const src = fs.readFileSync(new URL("./iso-loop.js", import.meta.url), "utf8");
  assert.doesNotMatch(src, /document\.body\.appendChild\(host\)/);
  assert.doesNotMatch(src, /iso-portal/);
});
