import assert from "node:assert/strict";
import { test } from "node:test";
import {
  guestPage,
  activeState,
  response,
  flush,
  linkA,
  linkB,
} from "./frontend_harness.mjs";

test("remembered guests recover from a pause without signing in again", async (t) => {
  let paused = false;
  const page = await guestPage(() =>
    paused
      ? response({ error: "access_paused" }, 403)
      : response(activeState()),
  );
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
  const page = await guestPage(() =>
    expired
      ? response({ error: "outside_window" }, 403)
      : response(activeState()),
  );
  t.after(page.close);
  assert.equal(page.get("login").hidden, true);
  expired = false;
  await page.tick(15000);
  assert.equal(page.get("actions").children.length, 1);
  assert.equal(page.get("message").textContent, "");
});

test("a late status response cannot sign the page back in after logout", async (t) => {
  let resolveStatus,
    delay = false;
  const page = await guestPage(({ operation }) =>
    operation === "status" && delay
      ? new Promise((resolve) => {
          resolveStatus = resolve;
        })
      : response(activeState()),
  );
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

test("actions work without the secure-context-only randomUUID API", async (t) => {
  const page = await guestPage(
    ({ operation }) =>
      response(operation === "action" ? { requested: true } : activeState()),
    { uuid: false },
  );
  t.after(page.close);
  page.get("actions").querySelector("button").click();
  assert.equal(page.get("confirm").open, true);
  page.get("send").click();
  await flush();
  const action = page.calls.find((call) => call.operation === "action");
  assert.ok(action);
  assert.match(action.body.request_id, /^[0-9a-f]{32}$/);
  assert.equal(page.get("message").textContent, "Request sent.");
});

test("fragment navigation replaces the link and ignores an old in-flight response", async (t) => {
  let delayed,
    delay = false;
  const page = await guestPage((call) => {
    if (delay && call.options.headers["X-Guest-Link"] === linkA)
      return new Promise((resolve) => {
        delayed = resolve;
      });
    return response({
      ...activeState(),
      name:
        call.options.headers["X-Guest-Link"] === linkB
          ? "Second guest"
          : "First guest",
    });
  });
  t.after(page.close);
  delay = true;
  await page.tick(15000);
  const oldRequest = page.calls.at(-1);
  page.window.location.hash = `#${linkB}`;
  // Dispatch explicitly so the test does not depend on jsdom's navigation timer.
  page.window.dispatchEvent(new page.window.HashChangeEvent("hashchange"));
  await flush();
  assert.equal(oldRequest.options.signal.aborted, true);
  assert.equal(page.calls.at(-1).options.headers["X-Guest-Link"], linkB);
  delayed(response({ ...activeState(), name: "First guest" }));
  await flush();
  assert.equal(page.get("intro").textContent, "Second guest");
  page.get("actions").querySelector("button").click();
  page.get("send").click();
  await flush();
  assert.equal(
    page.calls.find((call) => call.operation === "action").options.headers[
      "X-Guest-Link"
    ],
    linkB,
  );
});

test("navigating to an invalid fragment clears old controls", async (t) => {
  const page = await guestPage(() => response(activeState()));
  t.after(page.close);
  page.window.location.hash = "#invalid";
  page.window.dispatchEvent(new page.window.HashChangeEvent("hashchange"));
  await flush();
  assert.equal(page.get("controls").hidden, true);
  assert.equal(page.get("actions").children.length, 0);
  assert.match(page.get("message").textContent, /not valid/);
});

const roomState = () => ({
  ...activeState(),
  actions: [
    {
      id: "light-on",
      device_id: "synthetic-light",
      label: "Room light",
      kind: "light.turn_on",
      available: true,
      state: "on",
      value: 50,
    },
    {
      id: "light-off",
      device_id: "synthetic-light",
      label: "Room light",
      kind: "light.turn_off",
      available: true,
      state: "on",
      value: 50,
    },
    {
      id: "light-brightness",
      device_id: "synthetic-light",
      label: "Room light",
      kind: "light.set_brightness",
      available: true,
      state: "on",
      value: 50,
    },
  ],
});

test("a light is one card with only its granted controls", async (t) => {
  const page = await guestPage(() => response(roomState()));
  t.after(page.close);
  assert.equal(page.get("actions").children.length, 1);
  assert.equal(page.document.querySelectorAll(".device-button").length, 2);
  assert.equal(page.document.querySelectorAll('input[type="range"]').length, 1);
  page.document.querySelectorAll(".device-button")[1].click();
  assert.equal(page.get("confirm").open, true);
  page.get("send").click();
  await flush();
  const call = page.calls.find((c) => c.operation === "action");
  assert.equal(call.body.action_id, "light-off");
  assert.equal(Object.hasOwn(call.body, "value"), false);
});

test("slider drafts survive polling and send a value only after Apply and confirmation", async (t) => {
  const page = await guestPage(() => response(roomState()));
  t.after(page.close);
  const range = page.document.querySelector('input[type="range"]');
  range.focus();
  range.value = "35";
  range.dispatchEvent(new page.window.Event("input", { bubbles: true }));
  await page.tick(15000);
  assert.equal(page.document.activeElement, range);
  assert.equal(range.value, "35");
  assert.equal(page.calls.filter((c) => c.operation === "action").length, 0);
  page.document.querySelector(".slider-apply").click();
  assert.match(page.get("confirm-body").textContent, /35%/);
  assert.equal(page.calls.filter((c) => c.operation === "action").length, 0);
  page.get("send").click();
  await flush();
  const call = page.calls.find((c) => c.operation === "action");
  assert.equal(call.body.action_id, "light-brightness");
  assert.equal(call.body.value, 35);
});

test("cover controls show open, close, stop and position in one card", async (t) => {
  const data = {
    ...activeState(),
    actions: [
      "open_cover",
      "close_cover",
      "stop_cover",
      "set_cover_position",
    ].map((action) => ({
      id: action,
      device_id: "synthetic-blind",
      label: "Room blind",
      kind: `cover.${action}`,
      available: true,
      state: "open",
      value: 25,
    })),
  };
  const page = await guestPage(() => response(data));
  t.after(page.close);
  assert.equal(page.get("actions").children.length, 1);
  assert.equal(page.document.querySelectorAll(".device-button").length, 3);
  assert.equal(page.document.querySelector('input[type="range"]').value, "25");
  for (const action of data.actions) action.available = false;
  await page.tick(15000);
  assert.ok(
    [...page.get("actions").querySelectorAll("button, input")].every(
      (control) => control.disabled,
    ),
  );
});

test("refresh keeps button focus and closes a revoked confirmation", async (t) => {
  const data = activeState();
  const page = await guestPage(() => response(data));
  t.after(page.close);
  const button = page.get("actions").querySelector("button");
  button.focus();
  await page.tick(15000);
  assert.equal(page.document.activeElement, button);
  button.click();
  assert.equal(page.get("confirm").open, true);
  data.actions = [];
  await page.tick(15000);
  assert.equal(page.get("confirm").open, false);
  page.get("send").click();
  await flush();
  assert.equal(page.calls.filter((c) => c.operation === "action").length, 0);
});

test("a status refresh cannot clear an unconfirmed command warning", async (t) => {
  const page = await guestPage(({ operation }) => {
    if (operation === "action") throw new Error("connection lost");
    return response(activeState());
  });
  t.after(page.close);
  page.get("actions").querySelector("button").click();
  page.get("send").click();
  await flush();
  const warning = page.get("message").textContent;
  assert.match(warning, /could not be confirmed/i);
  await page.tick(3200);
  await page.tick(15000);
  assert.equal(page.get("message").textContent, warning);
  assert.equal(page.calls.filter((c) => c.operation === "action").length, 1);
});
