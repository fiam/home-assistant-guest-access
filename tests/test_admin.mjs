import assert from "node:assert/strict";
import { test } from "node:test";
import { adminPage, flush } from "./frontend_harness.mjs";

const catalog = [
  ...["turn_on", "turn_off", "set_brightness"].map((action, i) => ({
    entity_id: "light.synthetic_room",
    name: "Room light",
    device_id: "light-device",
    device_name: "Room light",
    area: "Guest room",
    action,
    action_name: ["Turn on", "Turn off", "Set brightness"][i],
  })),
  ...["open", "lock", "unlock"].map((action, i) => ({
    entity_id: "lock.synthetic_door",
    name: "Front door",
    device_id: "door-device",
    device_name: "Front door",
    area: "Entrance",
    action,
    action_name: ["Open door", "Lock", "Unlock"][i],
  })),
  {
    entity_id: "button.synthetic_identify",
    name: "Identify",
    device_id: "door-device",
    device_name: "Front door",
    area: "Entrance",
    action: "press",
    action_name: "Press",
    maintenance: true,
  },
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
const submit = async (page) => {
  page.root
    .querySelector("form")
    .dispatchEvent(
      new page.window.Event("submit", { bubbles: true, cancelable: true }),
    );
  await flush();
  return page.calls.find((call) => call.operation === "save");
};
const dialog = (page) => page.root.querySelector("dialog");
const openDevice = (page, device) => {
  button(page.root, "Add device").click();
  dialog(page).querySelector(`[data-device="device:${device}"]`).click();
};

test("the main form shows shared devices only; adding a device saves explicit controls", async (t) => {
  const page = await adminPage(data());
  t.after(page.close);
  button(page.root, "New link").click();
  page.root.querySelector('form input[maxlength="80"]').value =
    "Synthetic room guest";
  assert.equal(page.root.querySelectorAll("select").length, 0);
  assert.equal(page.root.querySelectorAll(".shared-device").length, 0);
  assert.equal(page.root.querySelectorAll(".device-result").length, 0);
  openDevice(page, "light-device");
  button(dialog(page), "Share all 3 controls").click();
  assert.equal(page.root.querySelectorAll(".shared-device").length, 0);
  button(dialog(page), "Done").click();
  assert.equal(page.root.querySelectorAll(".shared-device").length, 1);
  assert.equal(page.calls.length, 1);
  const saved = await submit(page);
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

test("Cancel and Escape discard device changes and return focus", async (t) => {
  const page = await adminPage(data([link()]));
  t.after(page.close);
  button(page.root, "Edit").click();
  const edit = page.root.querySelector(".device-edit");
  edit.click();
  button(dialog(page), "Share all 3 controls").click();
  button(dialog(page), "Cancel").click();
  assert.equal(page.root.activeElement, edit);
  edit.click();
  assert.equal(
    dialog(page).querySelectorAll('input[type="checkbox"]:checked').length,
    1,
  );
  button(dialog(page), "Clear selection").click();
  dialog(page).dispatchEvent(
    new page.window.Event("cancel", { cancelable: true }),
  );
  assert.equal(dialog(page).open, false);
  const saved = await submit(page);
  assert.equal(saved.version, 2);
  assert.deepEqual(saved.link.grants, link().grants);
});

test("the lock and its Identify entity form one device; Share all excludes maintenance", async (t) => {
  const page = await adminPage(data([link()]));
  t.after(page.close);
  button(page.root, "Edit").click();
  button(page.root, "Add device").click();
  assert.equal(dialog(page).querySelectorAll(".device-result").length, 2);
  dialog(page).querySelector('[data-device="device:door-device"]').click();
  button(dialog(page), "Share all 3 controls").click();
  assert.equal(
    dialog(page).querySelector(
      '[data-action="button.synthetic_identify:press"]',
    ).checked,
    false,
  );
  button(dialog(page), "Done").click();
  assert.equal(page.root.querySelectorAll(".shared-device").length, 1);
  const saved = await submit(page);
  assert.deepEqual(
    saved.link.grants.map((g) => g.action),
    ["open", "lock", "unlock"],
  );
});

test("Done preserves distinct existing labels and unavailable grants", async (t) => {
  const original = link();
  original.grants.push({
    entity_id: "lock.synthetic_door",
    action: "unlock",
    label: "Release latch",
  });
  const input = data([original]);
  input.catalog = catalog.map((c) =>
    c.action === "unlock" ? { ...c, available: false, selectable: false } : c,
  );
  const page = await adminPage(input);
  t.after(page.close);
  button(page.root, "Edit").click();
  page.root.querySelector(".device-edit").click();
  assert.equal(dialog(page).querySelectorAll(".action-name").length, 3);
  assert.match(dialog(page).textContent, /Currently unavailable/);
  button(dialog(page), "Done").click();
  const saved = await submit(page);
  assert.deepEqual(saved.link.grants, original.grants);
});

test("search and Back preserve a link draft without accepting dialog edits", async (t) => {
  const page = await adminPage(data([link()]));
  t.after(page.close);
  button(page.root, "Edit").click();
  button(page.root, "Add device").click();
  const search = dialog(page).querySelector('input[type="search"]');
  search.value = "guest room";
  search.dispatchEvent(new page.window.Event("input"));
  assert.equal(dialog(page).querySelectorAll(".device-result").length, 1);
  dialog(page).querySelector(".device-result").click();
  button(dialog(page), "Share all 3 controls").click();
  assert.equal(await submit(page), undefined);
  button(dialog(page), "Back to devices").click();
  assert.equal(
    dialog(page).querySelector('input[type="search"]').value,
    "guest room",
  );
  button(dialog(page), "Cancel").click();
  const saved = await submit(page);
  assert.deepEqual(saved.link.grants, link().grants);
});

test("a shared device can be removed from the draft without saving other changes", async (t) => {
  const original = link();
  original.grants.push({
    entity_id: "light.synthetic_room",
    action: "turn_on",
    label: "Room lamp",
  });
  const page = await adminPage(data([original]));
  t.after(page.close);
  button(page.root, "Edit").click();
  page.root
    .querySelector('[data-device="device:door-device"] .device-remove')
    .click();
  assert.equal(page.calls.length, 1);
  const saved = await submit(page);
  assert.deepEqual(saved.link.grants, [original.grants[1]]);
});

test("maintenance-only devices need an explicit selection", async (t) => {
  const input = data();
  input.catalog = [
    ...catalog,
    {
      entity_id: "button.synthetic_sensor_identify",
      device_id: "sensor-device",
      device_name: "Room sensor",
      name: "Identify",
      action: "press",
      action_name: "Press",
      maintenance: true,
    },
  ];
  const page = await adminPage(input);
  t.after(page.close);
  button(page.root, "New link").click();
  button(page.root, "Add device").click();
  assert.equal(dialog(page).querySelectorAll(".device-result").length, 2);
  button(dialog(page), "Show maintenance devices").click();
  assert.equal(dialog(page).querySelectorAll(".device-result").length, 3);
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
