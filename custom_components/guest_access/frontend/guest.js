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
  const link = location.hash.slice(1);
  let signedIn = false,
    busy = false,
    selected = null,
    expires = 0;
  const messages = strings.errors;
  function message(text, error = false) {
    $("message").textContent = text;
    $("message").className = error ? "error" : "";
  }
  function forget() {
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
  async function api(operation, data = {}) {
    let response, result;
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
        signal: AbortSignal.timeout(25000),
      });
      result = await response.json();
    } catch {
      throw new Error(
        operation === "action" ? strings.errors.unconfirmed : strings.failure,
      );
    }
    if (!response.ok) {
      if ([401, 403].includes(response.status)) forget();
      const error = new Error(messages[result.error] || strings.failure);
      error.status = response.status;
      throw error;
    }
    return result;
  }
  function render(data) {
    signedIn = true;
    $("login-note").hidden = true;
    expires = new Date(data.expires_at).getTime();
    $("intro").textContent = data.name;
    $("login").hidden = true;
    $("controls").hidden = false;
    $("expiry").textContent = strings.until.replace(
      "{date}",
      new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(data.expires_at)),
    );
    $("actions").replaceChildren();
    for (const action of data.actions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "action-card";
      const badge = document.createElement("span");
      badge.className = "action-icon";
      badge.append(icon(actionIcon(action.kind)));
      const copy = document.createElement("span");
      copy.className = "action-copy";
      const title = document.createElement("span");
      title.className = "action-title";
      title.textContent = labelFor(action.label, strings);
      const caption = document.createElement("span");
      caption.className = "action-caption";
      caption.textContent = action.available
        ? actionName(action.kind, strings)
        : strings.unavailableLabel;
      copy.append(title, caption);
      button.append(badge, copy, icon("chevron", "action-arrow"));
      button.disabled = busy || !action.available || expires <= Date.now();
      button.addEventListener("click", () => {
        selected = action;
        $("confirm-title").textContent = labelFor(action.label, strings);
        $("confirm-body").textContent = `${actionName(action.kind, strings)}?`;
        $("confirm-icon").replaceChildren(icon(actionIcon(action.kind)));
        $("confirm").showModal();
        $("cancel").focus();
      });
      $("actions").append(button);
    }
  }
  async function refresh(silent = false) {
    if (busy) return;
    try {
      render(await api("status"));
    } catch (error) {
      if (!(silent && error.status === 401)) message(error.message, true);
      $("actions")
        .querySelectorAll("button")
        .forEach((b) => (b.disabled = true));
    }
  }
  $("login").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
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
      busy = false;
      render(data);
      message("");
    } catch (error) {
      message(error.message, true);
    } finally {
      busy = false;
      $("login").querySelector("button").disabled = false;
    }
  });
  $("cancel").addEventListener("click", () => {
    selected = null;
    $("confirm").close();
  });
  $("send").addEventListener("click", async () => {
    if (busy || !selected) return;
    const action = selected;
    selected = null;
    $("confirm").close();
    busy = true;
    $("actions")
      .querySelectorAll("button")
      .forEach((b) => (b.disabled = true));
    message(strings.sending);
    try {
      await api("action", {
        action_id: action.id,
        request_id: crypto.randomUUID(),
      });
      message(strings.sent);
    } catch (error) {
      message(error.message || messages.unconfirmed, true);
    } finally {
      busy = false;
      setTimeout(refresh, 3200);
    }
  });
  $("logout").addEventListener("click", async () => {
    try {
      await api("logout");
      forget();
      message("");
    } catch (error) {
      message(error.message, true);
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refresh(true);
  });
  setInterval(() => {
    if (expires && expires <= Date.now()) {
      forget();
      message(messages.outside_window, true);
    }
  }, 1000);
  setInterval(() => {
    if (signedIn) refresh();
  }, 15000);
  if (!/^[A-Za-z0-9_-]{43}$/.test(link)) {
    $("login").hidden = true;
    message(strings.invalidLink, true);
  } else refresh(true);
})();
