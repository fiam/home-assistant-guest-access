import { readFile } from "node:fs/promises";
import { SourceTextModule } from "node:vm";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const assets = new URL(
  "../custom_components/guest_access/frontend/",
  import.meta.url,
);
export const linkA = "a".repeat(43);
export const linkB = "b".repeat(43);
export const activeState = () => ({
  name: "Synthetic guest",
  expires_at: new Date(Date.now() + 3600000).toISOString(),
  actions: [
    {
      id: "synthetic-action",
      label: "Apartment door",
      kind: "lock.open",
      available: true,
    },
  ],
});
export const response = (body, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => body,
});
export const flush = () => new Promise((resolve) => setImmediate(resolve));

export async function guestPage(handler, { uuid = true } = {}) {
  const html = await readFile(new URL("guest.html", assets), "utf8");
  const dom = new JSDOM(html, {
    url: `https://home.example.invalid/guest-access#${linkA}`,
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const { window } = dom;
  window.AbortSignal = AbortSignal;
  window.AbortController = AbortController;
  if (!uuid)
    Object.defineProperty(window.crypto, "randomUUID", { value: undefined });
  const calls = [],
    timers = new Map();
  window.fetch = async (url, options) => {
    const call = {
      operation: url.split("/").at(-1),
      body: JSON.parse(options.body),
      options,
    };
    calls.push(call);
    return handler(call);
  };
  window.setInterval = (fn, ms) => {
    timers.set(ms, fn);
    return ms;
  };
  window.setTimeout = (fn, ms) => {
    timers.set(ms, fn);
    return ms;
  };
  window.HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  window.HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
  await loadFrontend(dom, "guest.js");
  await flush();
  return {
    window,
    document: window.document,
    calls,
    timers,
    get: (id) => window.document.getElementById(id),
    tick: async (ms) => {
      timers.get(ms)?.();
      await flush();
    },
    close: () => window.close(),
  };
}

async function loadFrontend(dom, filename) {
  const context = dom.getInternalVMContext(),
    modules = new Map();
  async function moduleFor(url) {
    url = new URL(url);
    url.search = "";
    if (!modules.has(url.href))
      modules.set(
        url.href,
        new SourceTextModule(await readFile(fileURLToPath(url), "utf8"), {
          context,
          identifier: url.href,
        }),
      );
    return modules.get(url.href);
  }
  const entry = await moduleFor(new URL(filename, assets));
  await entry.link((specifier, parent) =>
    moduleFor(new URL(specifier, parent.identifier)),
  );
  await entry.evaluate();
}

export async function adminPage(data) {
  const dom = new JSDOM("<guest-access-panel></guest-access-panel>", {
    url: "https://home.example.invalid/guest-access-admin",
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  dom.window.HTMLElement.prototype.scrollIntoView = () => {};
  await loadFrontend(dom, "admin.js");
  const calls = [],
    panel = dom.window.document.querySelector("guest-access-panel");
  panel.hass = {
    callApi: async (method, path, payload) => {
      calls.push(structuredClone(payload));
      return structuredClone(data);
    },
  };
  await flush();
  return {
    window: dom.window,
    panel,
    root: panel.shadowRoot,
    calls,
    close: () => dom.window.close(),
  };
}
