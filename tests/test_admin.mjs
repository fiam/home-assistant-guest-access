import assert from "node:assert/strict";
import { test } from "node:test";
import { adminPage, flush } from "./frontend_harness.mjs";

const catalog = [
  ...["turn_on", "turn_off", "set_brightness"].map((action, i) => ({
    entity_id: "light.synthetic_room",
    name: "Room light",
    action,
    action_name: ["Turn on", "Turn off", "Set brightness"][i],
  })),
  ...["open", "lock", "unlock"].map((action, i) => ({
    entity_id: "lock.synthetic_door",
    name: "Front door",
    action,
    action_name: ["Open door", "Lock", "Unlock"][i],
  })),
];
const data = (links = []) => ({
  enabled: true,
  links,
  catalog,
  audit: [],
  base_url: "",
});
const button = (root, text) =>
  [...root.querySelectorAll("button")].find(
    (node) => node.textContent.trim() === text,
  );
const link = () => ({
  id: "synthetic-link",
  name: "Synthetic guest",
  enabled: true,
  version: 2,
  starts_at: new Date(Date.now() - 3600000).toISOString(),
  expires_at: new Date(Date.now() + 3600000).toISOString(),
  grants: [
    { entity_id: "lock.synthetic_door", action: "open", label: "Front door" },
  ],
});

test("selecting a device grants its supported controls without selecting other devices", async (t) => {
  const page = await adminPage(data());
  t.after(page.close);
  button(page.root, "New link").click();
  const form = page.root.querySelector("form");
  form.querySelector('input[maxlength="80"]').value = "Synthetic room guest";
  assert.equal(form.querySelector("select").value, "devices");
  const row = [...form.querySelectorAll(".choice")].find((node) =>
    node.textContent.includes("Room light"),
  );
  row.querySelector('input[type="checkbox"]').click();
  form.dispatchEvent(
    new page.window.Event("submit", { bubbles: true, cancelable: true }),
  );
  await flush();
  const saved = page.calls.find((call) => call.operation === "save");
  assert.equal(saved.link.enabled, false);
  assert.deepEqual(
    saved.link.grants.map((g) => g.action),
    ["turn_on", "turn_off", "set_brightness"],
  );
  assert.ok(
    saved.link.grants.every(
      (g) => g.entity_id === "light.synthetic_room" && g.label === "Room light",
    ),
  );
});

test("editing an open-door-only link preserves its narrow permissions and revision", async (t) => {
  const page = await adminPage(data([link()]));
  t.after(page.close);
  button(page.root, "Edit").click();
  const form = page.root.querySelector("form");
  const row = [...form.querySelectorAll(".choice")].find((node) =>
    node.textContent.includes("Front door"),
  );
  assert.equal(row.querySelector('input[type="checkbox"]').indeterminate, true);
  assert.match(row.textContent, /Selected: Open door/);
  const mode = form.querySelector("select");
  mode.value = "actions";
  mode.dispatchEvent(new page.window.Event("change"));
  assert.equal(
    form.querySelectorAll('.catalog input[type="checkbox"]:checked').length,
    1,
  );
  form.dispatchEvent(
    new page.window.Event("submit", { bubbles: true, cancelable: true }),
  );
  await flush();
  const saved = page.calls.find((call) => call.operation === "save");
  assert.equal(saved.version, 2);
  assert.deepEqual(saved.link.grants, link().grants);
});

test("Pause submits only a link ID and enabled flag", async (t) => {
  const page = await adminPage(data([link()]));
  t.after(page.close);
  button(page.root, "Pause").click();
  await flush();
  assert.deepEqual(page.calls.at(-1), {
    operation: "link_enabled",
    link_id: "synthetic-link",
    enabled: false,
  });
});
