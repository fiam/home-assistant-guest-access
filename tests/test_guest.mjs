import assert from "node:assert/strict";
import { test } from "node:test";
import { guestPage, activeState, response, flush } from "./frontend_harness.mjs";

test("remembered guests recover from a pause without signing in again", async (t) => {
  let paused = false;
  const page = await guestPage(() => paused ? response({ error: "access_paused" }, 403) : response(activeState()));
  t.after(page.close);
  assert.equal(page.get("login").hidden, true);
  paused = true;
  await page.tick(15000);
  assert.equal(page.get("login").hidden, true);
  assert.equal(page.get("controls").hidden, false);
  assert.equal(page.get("actions").children.length, 0);
  assert.match(page.get("message").textContent, /paused/);
  paused = false;
  await page.tick(15000);
  assert.equal(page.get("actions").children.length, 1);
  assert.equal(page.get("message").textContent, "");
});

test("a remembered browser outside the window keeps checking for an extension", async (t) => {
  let expired = true;
  const page = await guestPage(() => expired ? response({ error: "outside_window" }, 403) : response(activeState()));
  t.after(page.close);
  assert.equal(page.get("login").hidden, true);
  expired = false;
  await page.tick(15000);
  assert.equal(page.get("actions").children.length, 1);
  assert.equal(page.get("message").textContent, "");
});

test("a late status response cannot sign the page back in after logout", async (t) => {
  let resolveStatus, delay = false;
  const page = await guestPage(({ operation }) => operation === "status" && delay
    ? new Promise(resolve => { resolveStatus = resolve; }) : response(activeState()));
  t.after(page.close);
  delay = true;
  await page.tick(15000);
  page.get("logout").click();
  await flush();
  resolveStatus(response(activeState()));
  await flush();
  assert.equal(page.get("login").hidden, false);
  assert.equal(page.get("controls").hidden, true);
});

test("invalid credentials require login; pause recovery does not bypass authentication", async (t) => {
  const page = await guestPage(() => response({ error: "sign_in" }, 401));
  t.after(page.close);
  assert.equal(page.get("login").hidden, false);
  assert.equal(page.get("controls").hidden, true);
});
