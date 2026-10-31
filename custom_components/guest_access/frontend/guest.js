/* Sign-in is an HttpOnly cookie. Never store passwords or retry commands. */
import { icon, actionIcon } from "./icons.js?v=0.3.1";
import {
  translations,
  languageFor,
  actionName,
  labelFor,
} from "./translations.js?v=0.3.1";
(() => {
  const { lang, locale } = languageFor(
    navigator.languages?.length ? navigator.languages : [navigator.language],
  );
  const strings = translations[lang];
  document.documentElement.lang = lang;
  document.title = strings.title;
  for (const node of document.querySelectorAll("[data-i18n]"))
    node.textContent = strings[node.dataset.i18n];
  for (const node of document.querySelectorAll("[data-icon]"))
    node.replaceChildren(icon(node.dataset.icon));
  const $ = (id) => document.getElementById(id);
  let link = location.hash.slice(1);
  const pendingRequests = new Set();
  let signedIn = false,
    busy = false,
    selected = null,
    expires = 0,
    epoch = 0,
    statusSequence = 0,
    messageSource = "";
  const messages = strings.errors;
  function message(text, error = false, source = "") {
    messageSource = source;
    $("message").textContent = text;
    $("message").className = error ? "error" : "";
  }
  function forget() {
    epoch += 1;
    busy = false;
    $("login").querySelector("button").disabled = false;
    signedIn = false;
    expires = 0;
    selected = null;
    $("confirm").close();
    $("actions").replaceChildren();
    $("controls").hidden = true;
    $("login").hidden = false;
    $("login-note").hidden = false;
    $("intro").textContent = strings.intro;
  }
  function requestId() {
    // getRandomValues also works on LAN HTTP origins; randomUUID requires HTTPS.
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(
      "",
    );
  }
  async function api(operation, data = {}) {
    let response, result;
    const controller = new AbortController();
    pendingRequests.add(controller);
    try {
      response = await fetch(`/api/guest_access/${operation}`, {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        redirect: "error",
        headers: {
          "Content-Type": "application/json",
          "X-Guest-Link": link,
        },
        body: JSON.stringify(data),
        signal: AbortSignal.any([
          controller.signal,
          AbortSignal.timeout(25000),
        ]),
      });
      result = await response.json();
    } catch {
      throw new Error(
        operation === "action" ? strings.errors.unconfirmed : strings.failure,
      );
    } finally {
      pendingRequests.delete(controller);
    }
    if (!response.ok) {
      const error = new Error(messages[result.error] || strings.failure);
      error.status = response.status;
      error.code = result.error;
      throw error;
    }
    return result;
  }
  function suspendAccess() {
    signedIn = true;
    expires = 0;
    selected = null;
    $("confirm").close();
    $("actions").replaceChildren();
    $("login").hidden = true;
    $("login-note").hidden = true;
    $("controls").hidden = false;
    $("expiry").parentElement.hidden = true;
    if ($("intro").textContent === strings.intro) $("intro").textContent = "";
  }
  function handleError(error, policy = true) {
    if (error.status === 401) forget();
    else if (policy && ["access_paused", "outside_window"].includes(error.code))
      suspendAccess();
  }
  function choose(action, value, onSent) {
    if (busy || !action.available || expires <= Date.now()) return;
    selected = { ...action, value, onSent };
    $("confirm-title").textContent = labelFor(action.label, strings);
    $("confirm-body").textContent =
      `${actionName(action.kind, strings)}${value === undefined ? "" : `: ${value}%`}?`;
    $("confirm-icon").replaceChildren(icon(actionIcon(action.kind)));
    $("confirm").showModal();
    $("cancel").focus();
  }
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function singleAction() {
    const button = element("button", "action-card");
    button.type = "button";
    const badge = element("span", "action-icon"),
      copy = element("span", "action-copy");
    const title = element("span", "action-title"),
      caption = element("span", "action-caption");
    copy.append(title, caption);
    button.append(badge, copy, icon("chevron", "action-arrow"));
    let current;
    button.addEventListener("click", () => choose(current));
    button.update = ([action]) => {
      current = action;
      title.textContent = labelFor(action.label, strings);
      caption.textContent = action.available
        ? actionName(action.kind, strings)
        : strings.unavailableLabel;
      badge.replaceChildren(icon(actionIcon(action.kind)));
      button.disabled = busy || !action.available || expires <= Date.now();
    };
    return button;
  }
  function deviceCard(actions) {
    const card = element("article", "device-card card");
    const heading = element("div", "device-header"),
      badge = element("span", "action-icon");
    const copy = element("div", "action-copy"),
      title = element("h2", "action-title");
    const state = element("p", "action-caption");
    title.id = `device-${actions[0].id}`;
    card.setAttribute("aria-labelledby", title.id);
    badge.append(icon(actionIcon(actions[0].kind)));
    copy.append(title, state);
    heading.append(badge, copy);
    card.append(heading);
    const quick = element("div", "device-buttons"),
      controls = new Map();
    for (const action of actions) {
      if (
        action.kind.endsWith(".set_brightness") ||
        action.kind.endsWith(".set_cover_position")
      )
        continue;
      const button = element(
        "button",
        "device-button secondary",
        actionName(action.kind, strings),
      );
      button.type = "button";
      button.addEventListener("click", () =>
        choose(controls.get(action.id).action),
      );
      controls.set(action.id, { button, action });
      quick.append(button);
    }
    if (quick.children.length) card.append(quick);
    const sliders = new Map();
    for (const action of actions.filter((a) =>
      /\.(set_brightness|set_cover_position)$/.test(a.kind),
    )) {
      const block = element("div", "device-slider");
      const row = element("div", "slider-heading"),
        label = element(
          "label",
          "",
          action.kind.startsWith("light.")
            ? strings.brightness
            : strings.position,
        );
      const output = element("output"),
        range = element("input");
      range.type = "range";
      range.min = "0";
      range.max = "100";
      range.step = "1";
      range.id = `value-${action.id}`;
      label.htmlFor = range.id;
      output.htmlFor = range.id;
      const apply = element("button", "slider-apply secondary", strings.apply);
      apply.type = "button";
      apply.setAttribute(
        "aria-label",
        `${strings.apply}: ${labelFor(action.label, strings)} · ${label.textContent}`,
      );
      const control = { range, output, apply, action, dirty: false };
      sliders.set(action.id, control);
      range.addEventListener("input", () => {
        control.dirty = true;
        output.textContent = `${range.value}%`;
        apply.disabled =
          busy || !control.action.available || expires <= Date.now();
      });
      apply.addEventListener("click", () =>
        choose(control.action, Number(range.value), () => {
          control.dirty = false;
        }),
      );
      const ends = element("div", "slider-ends");
      ends.append(
        element(
          "span",
          "",
          action.kind.startsWith("cover.") ? strings.closed : "0%",
        ),
        element(
          "span",
          "",
          action.kind.startsWith("cover.") ? strings.open : "100%",
        ),
      );
      row.append(label, output, apply);
      block.append(row, range, ends);
      card.append(block);
    }
    card.update = (current) => {
      title.textContent = labelFor(current[0].label, strings);
      state.textContent = current.some((a) => a.available)
        ? strings.states[current[0].state] || ""
        : strings.unavailableLabel;
      for (const action of current) {
        const disabled = busy || !action.available || expires <= Date.now();
        if (controls.has(action.id)) {
          const control = controls.get(action.id);
          control.action = action;
          control.button.disabled = disabled;
          if (/\.(turn_on|turn_off)$/.test(action.kind))
            control.button.setAttribute(
              "aria-pressed",
              String(
                action.state ===
                  (action.kind.endsWith("turn_on") ? "on" : "off"),
              ),
            );
        }
        if (sliders.has(action.id)) {
          const control = sliders.get(action.id);
          control.action = action;
          control.range.disabled = disabled;
          control.apply.disabled = disabled || !control.dirty;
          if (!control.dirty && document.activeElement !== control.range) {
            control.range.value = action.value ?? 50;
            control.output.textContent =
              action.value == null ? "—" : `${action.value}%`;
          }
        }
      }
    };
    return card;
  }
  function renderActions(actions) {
    const groups = new Map();
    for (const action of actions) {
      const key = action.device_id
        ? `device:${action.device_id}:${action.label}`
        : `action:${action.id}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(action);
    }
    const existing = new Map(
      [...$("actions").children].map((node) => [node.dataset.key, node]),
    );
    const keep = new Set();
    let index = 0;
    for (const [group, items] of groups) {
      const key = `${group}:${items.map((a) => a.id).join(",")}`;
      const node =
        existing.get(key) ||
        (items[0].device_id ? deviceCard(items) : singleAction());
      node.dataset.key = key;
      node.update(items);
      keep.add(node);
      // Keep nodes in place during polling so focus and slider drafts survive.
      if ($("actions").children[index] !== node)
        $("actions").insertBefore(node, $("actions").children[index] || null);
      index += 1;
    }
    for (const node of [...$("actions").children])
      if (!keep.has(node)) node.remove();
    if (selected && !actions.some((a) => a.id === selected.id && a.available)) {
      selected = null;
      $("confirm").close();
    }
  }
  function render(data) {
    signedIn = true;
    $("login-note").hidden = true;
    expires = new Date(data.expires_at).getTime();
    $("intro").textContent = data.name;
    $("login").hidden = true;
    $("controls").hidden = false;
    $("expiry").parentElement.hidden = false;
    $("expiry").textContent = strings.until.replace(
      "{date}",
      new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(data.expires_at)),
    );
    renderActions(data.actions);
  }
  async function refresh(silent = false) {
    if (busy || !/^[A-Za-z0-9_-]{43}$/.test(link)) return;
    const started = epoch,
      sequence = ++statusSequence;
    try {
      const data = await api("status");
      if (started !== epoch || sequence !== statusSequence || busy) return;
      render(data);
      if (messageSource === "status") message("");
    } catch (error) {
      if (started !== epoch || sequence !== statusSequence || busy) return;
      handleError(error);
      if (!(silent && error.status === 401))
        message(error.message, true, "status");
      $("actions")
        .querySelectorAll("button, input")
        .forEach((b) => (b.disabled = true));
    }
  }
  $("login").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    const started = ++epoch;
    busy = true;
    $("login").querySelector("button").disabled = true;
    message(strings.checking);
    const password = $("password").value;
    $("password").value = "";
    try {
      const data = await api("login", {
        link,
        password,
        remember: $("remember").checked,
      });
      if (started !== epoch) return;
      busy = false;
      render(data);
      message("");
    } catch (error) {
      if (started !== epoch) return;
      handleError(error, false);
      message(error.message, true);
    } finally {
      if (started === epoch) {
        busy = false;
        $("login").querySelector("button").disabled = false;
      }
    }
  });
  $("cancel").addEventListener("click", () => {
    selected = null;
    $("confirm").close();
  });
  $("send").addEventListener("click", async () => {
    if (busy || !selected) return;
    const started = ++epoch,
      action = selected;
    selected = null;
    $("confirm").close();
    busy = true;
    $("actions")
      .querySelectorAll("button, input")
      .forEach((b) => (b.disabled = true));
    message(strings.sending);
    try {
      await api("action", {
        action_id: action.id,
        request_id: requestId(),
        ...(action.value === undefined ? {} : { value: action.value }),
      });
      if (started === epoch) {
        action.onSent?.();
        message(strings.sent);
      }
    } catch (error) {
      if (started !== epoch) return;
      handleError(error);
      message(
        error.message || messages.unconfirmed,
        true,
        ["access_paused", "outside_window"].includes(error.code)
          ? "status"
          : "action",
      );
    } finally {
      if (started === epoch) {
        busy = false;
        setTimeout(refresh, 3200);
      }
    }
  });
  $("logout").addEventListener("click", async () => {
    const started = ++epoch;
    busy = true;
    try {
      await api("logout");
      if (started !== epoch) return;
      forget();
      message("");
    } catch (error) {
      if (started !== epoch) return;
      handleError(error);
      message(error.message, true);
    } finally {
      if (started === epoch) busy = false;
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refresh(true);
  });
  setInterval(() => {
    if (expires && expires <= Date.now()) {
      suspendAccess();
      message(messages.outside_window, true, "status");
      refresh();
    }
  }, 1000);
  setInterval(() => {
    if (signedIn) refresh();
  }, 15000);
  function openLink() {
    if (!/^[A-Za-z0-9_-]{43}$/.test(link)) {
      $("login").hidden = true;
      message(strings.invalidLink, true);
    } else refresh(true);
  }
  window.addEventListener("hashchange", () => {
    link = location.hash.slice(1);
    forget();
    message("");
    $("password").value = "";
    for (const request of pendingRequests) request.abort();
    pendingRequests.clear();
    openLink();
  });
  openLink();
})();
