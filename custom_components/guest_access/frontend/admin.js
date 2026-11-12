import { icon, actionIcon } from "./icons.js?v=0.5.0";
import { createDevicePicker } from "./device-picker.js?v=0.5.0";
const css = `:host { display:block; color:var(--primary-text-color,#202b36); font-family:var(--ha-font-family-body,Roboto,system-ui,sans-serif); background:var(--primary-background-color,#f5f7fa); min-height:100vh; --ga-tint:color-mix(in srgb,var(--primary-color,#03a9f4) 12%,transparent); }
* { box-sizing:border-box; }
[hidden] { display:none !important; }
.wrap { max-width:1040px; padding:32px; margin:auto; }
header { display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:24px; }
.heading { display:flex; align-items:center; gap:16px; }
.heading-icon { display:grid; place-items:center; width:56px; height:56px; flex:0 0 auto; background:var(--ga-tint); color:var(--primary-color); border-radius:18px; }
h1 { margin:0; font-size:28px; font-weight:500; letter-spacing:-.02em; }
header p { margin:5px 0 0; }
p { line-height:1.5; color:var(--secondary-text-color,#65717e); }
.icon { width:20px; height:20px; flex:0 0 auto; vertical-align:middle; }
.heading-icon .icon { width:28px; height:28px; }
button,input,select { font:inherit; }
button { display:inline-flex; justify-content:center; align-items:center; gap:8px; min-height:40px; border:1px solid transparent; border-radius:var(--ha-border-radius-pill,24px); padding:9px 16px; cursor:pointer; background:var(--primary-color,#007eae); color:var(--text-primary-color,white); font-size:14px; font-weight:500; touch-action:manipulation; }
button.secondary { background:var(--ga-tint); color:var(--primary-color,#007eae); }
button.danger { color:var(--error-color,#db4437); background:transparent; }
button:disabled { opacity:.5; cursor:default; }
button:focus-visible,input:focus-visible,summary:focus-visible { outline:2px solid var(--primary-color); outline-offset:3px; }
@media (hover:hover) { button:not(:disabled):hover { filter:brightness(.94); } }
.row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.card { border:var(--ha-card-border-width,1px) solid var(--ha-card-border-color,var(--divider-color,#dce3e9)); background:var(--ha-card-background,var(--card-background-color,white)); border-radius:var(--ha-card-border-radius,16px); padding:24px; margin:20px 0; box-shadow:var(--ha-card-box-shadow,none); }
.card h2 { font-size:20px; font-weight:500; margin:0 0 8px; }
.card .row h2 { margin:0; }
.notice { padding:16px 20px; border-radius:12px; background:var(--ga-tint); white-space:pre-wrap; font-size:14px; line-height:1.6; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
label { display:grid; gap:8px; margin:16px 0; font-size:14px; }
input,select { min-height:48px; padding:12px; border:1px solid var(--divider-color,#ccc); border-radius:8px; background:var(--card-background-color,white); color:inherit; width:100%; }
input[type=checkbox] { width:20px; height:20px; min-height:20px; margin:0; accent-color:var(--primary-color); }
.check { display:flex; align-items:center; gap:12px; }
small { line-height:1.5; }
.toolbar { margin:16px 0 28px; }
.control-summary { display:block; font-size:12px; color:var(--secondary-text-color); margin-top:4px; }
.secret { font-family:monospace; overflow-wrap:anywhere; font-size:18px; }
.actions { margin-top:20px; padding-top:16px; border-top:1px solid var(--divider-color,#ddd); }
.pill { font-size:12px; border-radius:12px; background:var(--ga-tint); color:var(--primary-color); padding:4px 10px; }
details { margin:24px 0; color:var(--secondary-text-color); font-size:14px; }
summary { cursor:pointer; padding:8px 0; }
ul { padding-left:0; list-style:none; }
li { display:flex; align-items:center; gap:10px; padding:6px 0; font-size:14px; }
li .icon { color:var(--primary-color); }
.password-reveal { margin-top:20px; padding:16px; border:1px solid var(--divider-color,#ddd); border-radius:12px; }
.password-reveal p { margin:0 0 12px; font-size:13px; }
.password-reveal input { margin-bottom:12px; }
.empty { display:grid; justify-items:center; padding:40px 24px; border:1px dashed var(--divider-color,#ccc); border-radius:16px; text-align:center; }
.empty>.icon { width:36px; height:36px; color:var(--secondary-text-color); margin-bottom:8px; }
.empty p { max-width:360px; margin-bottom:0; }
.link-editor { padding:32px; }
.link-editor>label { margin:24px 0; }
.link-editor>.grid { gap:24px; }
.link-editor>.actions { margin-top:36px; padding-top:24px; }
.device-sharing { margin-top:36px; padding-top:32px; border-top:1px solid var(--divider-color,#dce3e9); }
.sharing-heading { display:flex; justify-content:space-between; align-items:center; gap:24px; margin-bottom:16px; }
.sharing-heading h3 { margin:0; font-size:20px; font-weight:500; }
.sharing-count { font-size:14px; margin:8px 0 0; }
.shared-device { display:flex; align-items:center; gap:20px; padding:26px 0; border-bottom:1px solid var(--divider-color,#dce3e9); }
.shared-device:last-child { border-bottom:0; padding-bottom:8px; }
.device-badge { width:44px; height:44px; flex:0 0 auto; display:grid; place-items:center; color:var(--primary-color,#007eae); }
.device-badge .icon { width:28px; height:28px; }
.device-copy { flex:1; min-width:0; text-align:left; }
.device-copy h4,.device-copy strong { display:block; margin:0; font-size:16px; font-weight:500; overflow-wrap:anywhere; }
.device-copy p,.device-copy small { display:block; margin:7px 0 0; font-size:14px; line-height:1.5; color:var(--secondary-text-color,#65717e); overflow-wrap:anywhere; }
.device-row-actions { display:flex; align-items:center; gap:12px; }
button.icon-button { padding:10px; min-width:40px; min-height:40px; background:transparent; color:var(--secondary-text-color,#65717e); }
.sharing-empty { padding:24px 0; margin:0; font-size:15px; }
.device-dialog { padding:0; width:min(580px,calc(100vw - 48px)); max-width:none; max-height:calc(100dvh - 64px); border:1px solid var(--divider-color,#dce3e9); border-radius:24px; background:var(--ha-card-background,var(--card-background-color,white)); color:var(--primary-text-color,#202b36); box-shadow:0 16px 48px #0004; overflow:hidden; }
.device-dialog[open] { display:flex; flex-direction:column; }
.device-dialog::backdrop { background:#0008; }
.dialog-header { padding:28px 32px 24px; flex:0 0 auto; }
.dialog-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:20px; }
.dialog-heading h2 { font-size:24px; margin:0; line-height:1.3; overflow-wrap:anywhere; }
.dialog-heading p { font-size:14px; margin:10px 0 0; }
.dialog-heading .icon-button { margin:-6px -10px 0 0; }
.dialog-body { min-height:0; overflow-y:auto; overscroll-behavior:contain; padding:0 32px 28px; }
.dialog-actions { display:flex; justify-content:flex-end; align-items:center; gap:12px; padding:20px 32px; border-top:1px solid var(--divider-color,#dce3e9); flex:0 0 auto; }
.dialog-back { margin:-8px 0 16px -12px; padding:8px 12px; }
.device-search { margin-bottom:20px; font-size:16px; }
button.device-result { display:flex; gap:16px; align-items:center; width:100%; padding:20px 0; background:transparent; color:inherit; border-radius:0; border:0; border-bottom:1px solid var(--divider-color,#dce3e9); }
button.device-result:last-child { border-bottom:0; }
.device-result>.icon { color:var(--secondary-text-color,#65717e); width:16px; }
.dialog-actions .maintenance-toggle { margin-right:auto; font-size:12px; background:transparent; padding:8px 0; text-align:left; }
.selection-tools { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin:4px 0 28px; }
button.plain-button { background:transparent; color:var(--secondary-text-color,#65717e); padding-inline:0; }
.control-group { min-width:0; border:0; padding:0; margin:0 0 28px; }
.control-group:last-child { margin-bottom:0; }
.control-group legend { font-size:14px; font-weight:500; margin:0 0 12px; padding:0; color:var(--secondary-text-color,#65717e); }
.control-check { display:flex; align-items:center; gap:14px; min-height:48px; margin:4px 0; font-size:16px; }
.control-check small { display:block; color:var(--secondary-text-color,#65717e); font-size:12px; }
.guest-name { display:grid; gap:10px; margin:22px 0 0 34px; font-size:13px; color:var(--secondary-text-color,#65717e); }
.guest-name input { font-size:16px; color:var(--primary-text-color,#202b36); }
.action-name { margin-top:8px; margin-bottom:20px; }
.maintenance-actions { margin:28px 0 0; }
.maintenance-actions[open]>summary { margin-bottom:16px; }
.entity-details { margin:24px 0 0; font-size:12px; }
.entity-details p { font-size:12px; overflow-wrap:anywhere; }
.dialog-error { color:var(--error-color,#db4437); font-size:14px; margin-top:20px; }
@media(max-width:650px) { .link-editor{padding:24px 20px}.sharing-heading{gap:16px;align-items:flex-start}.sharing-heading h3{font-size:18px}.sharing-heading>button{white-space:nowrap}.shared-device{gap:12px;padding:24px 0}.device-row-actions{gap:0}.device-badge{width:32px}.device-copy h4{font-size:16px}.device-copy p{font-size:13px}.device-dialog{width:calc(100vw - 24px);max-height:calc(100dvh - 32px);border-radius:18px}.dialog-header{padding:24px}.dialog-body{padding:0 24px 24px}.dialog-actions{padding:18px 24px}.dialog-heading h2{font-size:22px}.guest-name{margin-left:0} }
@media(max-width:650px) { .wrap{padding:24px 16px}.grid{grid-template-columns:1fr}header{align-items:flex-start;flex-wrap:wrap}.heading{gap:12px}.heading-icon{width:44px;height:44px;border-radius:14px}h1{font-size:24px}.card{padding:20px}header p{font-size:13px}.actions{gap:8px}.actions button{padding-inline:12px} }
`;
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "icon") continue;
    if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key in node) node[key] = value;
    else node.setAttribute(key, value);
  }
  if (attrs.icon) node.prepend(icon(attrs.icon));
  for (const child of children) node.append(child);
  return node;
}
const localTime = (value) => {
  const d = new Date(value);
  return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};

class GuestAccessPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.loading = false;
    this.data = null;
    this.editing = null;
  }
  set hass(value) {
    this._hass = value;
    if (!this.data && !this.loading) this.load();
  }
  async call(operation, extra = {}) {
    return this._hass.callApi("POST", "guest_access/admin/manage", {
      operation,
      ...extra,
    });
  }
  async load() {
    this.loading = true;
    try {
      this.data = await this.call("list");
      this.render();
    } catch (error) {
      this.shadowRoot.replaceChildren(
        el("p", { text: error.message || "Unable to load Guest Access." }),
      );
    } finally {
      this.loading = false;
    }
  }
  async perform(operation, extra = {}) {
    try {
      this.data = await this.call(operation, extra);
      this.editing = null;
      this.render();
      return true;
    } catch (error) {
      this.notice.textContent =
        (error.message === "conflict"
          ? "This link changed in another window. Refresh and reopen it before saving."
          : error.message) || "The change could not be saved.";
      return false;
    }
  }
  url(id) {
    return `${this.data.base_url || location.origin}/guest-access#${id}`;
  }
  async copy(text, secret = false) {
    try {
      await navigator.clipboard.writeText(text);
      this.notice.textContent = "Copied.";
    } catch {
      if (secret) {
        this.notice.textContent =
          "Clipboard unavailable. Select and copy the password above.";
        return;
      }
      this.notice.replaceChildren(
        el("p", { text: "Copy this value:" }),
        el("input", { value: text, readOnly: true }),
      );
    }
  }
  render() {
    const root = el("div", { className: "wrap" });
    root.append(
      el("header", {}, [
        el("div", { className: "heading" }, [
          el("span", { className: "heading-icon" }, [icon("key")]),
          el("div", {}, [
            el("h1", { text: "Guest Access" }),
            el("p", { text: "Password-protected access for your guests." }),
          ]),
        ]),
        el("button", {
          text: "New link",
          icon: "plus",
          onclick: () => this.edit(null),
        }),
      ]),
    );
    this.notice = el("div", {
      className: "notice",
      role: "status",
      text: this.data.enabled
        ? "Guest access is enabled. Each link also has its own schedule and pause control."
        : "All guest access is paused.",
    });
    root.append(
      this.notice,
      el("div", { className: "toolbar row" }, [
        el("button", {
          className: this.data.enabled ? "danger" : "",
          text: this.data.enabled ? "Pause all access" : "Enable guest access",
          icon: this.data.enabled ? "pause" : "play",
          onclick: () =>
            this.perform("enabled", { enabled: !this.data.enabled }),
        }),
        el("button", {
          className: "secondary",
          text: "Refresh",
          icon: "refresh",
          onclick: () => this.load(),
        }),
      ]),
    );
    // Secrets are fetched only when an administrator chooses Show password.
    delete this.data.generated_password;
    this.editor = el("section");
    root.append(this.editor);
    if (!this.data.links.length)
      root.append(
        el("section", { className: "empty" }, [
          icon("key"),
          el("h2", { text: "No guest links yet" }),
          el("p", {
            text: "Create a link, choose its actions, and set when it works. You can pause access at any time.",
          }),
        ]),
      );
    for (const link of this.data.links) {
      const summaries = new Map();
      for (const grant of link.grants) {
        const key = `${grant.entity_id}:${grant.label}`;
        if (!summaries.has(key)) summaries.set(key, { ...grant, actions: [] });
        summaries
          .get(key)
          .actions.push(
            this.data.catalog.find(
              (c) =>
                c.entity_id === grant.entity_id && c.action === grant.action,
            )?.action_name || grant.action.replaceAll("_", " "),
          );
      }
      const secretRegion = el("div", {
        className: "password-reveal",
        hidden: true,
      });
      const now = Date.now();
      const status =
        !this.data.enabled || !link.enabled
          ? "Paused"
          : now < Date.parse(link.starts_at)
            ? "Scheduled"
            : now >= Date.parse(link.expires_at)
              ? "Expired"
              : "Active";
      root.append(
        el("article", { className: "card" }, [
          el("div", { className: "row" }, [
            el("h2", { text: link.name }),
            el("span", { className: "pill", text: status }),
          ]),
          el("p", {
            text: `${new Date(link.starts_at).toLocaleString()} → ${new Date(link.expires_at).toLocaleString()}`,
          }),
          el(
            "ul",
            {},
            [...summaries.values()].map((g) =>
              el("li", {}, [
                icon(actionIcon(g.entity_id.split(".")[0] + "." + g.action)),
                el("span", {}, [
                  el("span", { text: g.label }),
                  el("small", {
                    className: "control-summary",
                    text: g.actions.join(" · "),
                  }),
                ]),
              ]),
            ),
          ),
          el("div", { className: "row actions" }, [
            el("button", {
              text: "Copy link",
              icon: "copy",
              onclick: () => this.copy(this.url(link.id)),
            }),
            el("button", {
              className: "secondary",
              text: "Edit",
              icon: "edit",
              onclick: () => this.edit(link),
            }),
            el("button", {
              className: "secondary",
              text: link.enabled ? "Pause" : "Resume",
              icon: link.enabled ? "pause" : "play",
              onclick: () =>
                this.perform("link_enabled", {
                  link_id: link.id,
                  enabled: !link.enabled,
                }),
            }),
            el("button", {
              className: "secondary",
              text: "Show password",
              icon: "eye",
              onclick: () => this.revealPassword(link, secretRegion),
            }),
            el("button", {
              className: "danger",
              text: "Delete",
              icon: "trash",
              onclick: () => {
                if (confirm(`Permanently revoke and delete “${link.name}”?`))
                  this.perform("delete", { link_id: link.id });
              },
            }),
          ]),
          secretRegion,
        ]),
      );
    }
    const history = el("details", {}, [
      el("summary", { text: "Recent activity" }),
    ]);
    history.append(
      el(
        "ul",
        {},
        [...this.data.audit].reverse().map((a) =>
          el("li", {
            text: `${new Date(a.time).toLocaleString()} · ${a.name} · ${a.event}${a.action ? " · " + a.action : ""}`,
          }),
        ),
      ),
    );
    root.append(history);
    this.shadowRoot.replaceChildren(el("style", { text: css }), root);
  }
  async revealPassword(link, region) {
    region.hidden = false;
    region.replaceChildren(el("p", { text: "Loading password…" }));
    try {
      const { password } = await this.call("reveal_password", {
        link_id: link.id,
      });
      if (!region.isConnected) return;
      const field = el("input", {
        value: password,
        readOnly: true,
        className: "secret",
        "aria-label": "Guest password",
        autoComplete: "off",
      });
      const hide = () => {
        field.value = "";
        region.replaceChildren();
        region.hidden = true;
      };
      region.replaceChildren(
        el("p", {
          text: "Share this separately from the link. It will hide automatically after one minute.",
        }),
        field,
        el("div", { className: "row" }, [
          el("button", {
            text: "Copy password",
            icon: "copy",
            onclick: () => this.copy(field.value, true),
          }),
          el("button", {
            text: "Hide",
            icon: "close",
            className: "secondary",
            onclick: hide,
          }),
        ]),
      );
      setTimeout(hide, 60000);
    } catch (error) {
      region.replaceChildren(
        el("p", {
          text: "The password could not be displayed. Try again or set it again under Edit.",
        }),
      );
    }
  }
  edit(link) {
    const now = Date.now();
    const form = el("form", { className: "card link-editor" });
    const field = (text, input) =>
      el("label", {}, [el("span", { text }), input]);
    const name = el("input", {
      value: link?.name || "",
      required: true,
      maxLength: 80,
      placeholder: "For example: Weekend guests",
    });
    const starts = el("input", {
      type: "datetime-local",
      required: true,
      value: localTime(link?.starts_at || now),
    });
    const ends = el("input", {
      type: "datetime-local",
      required: true,
      value: localTime(link?.expires_at || now + 86400000),
    });
    const password = el("input", {
      type: "password",
      autoComplete: "new-password",
      minLength: 12,
      maxLength: 128,
    });
    const enabled = el("input", {
      type: "checkbox",
      checked: link?.enabled || false,
    });
    form.append(
      el("h2", { text: link ? "Edit link" : "New link" }),
      field("Name", name),
      el("div", { className: "grid" }, [
        field("Starts (your local time)", starts),
        field("Expires (your local time)", ends),
      ]),
      field(
        link
          ? "New password (leave blank to keep it)"
          : "Password (leave blank to generate one)",
        password,
      ),
      el("small", {
        text: "At least 12 characters. Changing the password ends existing guest sessions.",
      }),
      el("label", { className: "check" }, [
        enabled,
        el("span", { text: "Enable this link within its access window" }),
      ]),
    );
    const picker = createDevicePicker(this.data.catalog, link?.grants || []);
    form.append(picker);
    const save = el("button", {
      type: "submit",
      text: "Save link",
      icon: "check",
    });
    form.append(
      el("div", { className: "row actions" }, [
        save,
        el("button", {
          type: "button",
          className: "secondary",
          text: "Cancel",
          icon: "close",
          onclick: () => this.editor.replaceChildren(),
        }),
      ]),
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (picker.querySelector("dialog").open) return;
      const grants = picker.getGrants();
      if (!grants.length) {
        this.notice.textContent = "Add at least one shared device.";
        return;
      }
      if (grants.length > 32) {
        this.notice.textContent =
          "A link can share up to 32 controls. Choose fewer controls.";
        return;
      }
      if (new Date(ends.value) <= new Date(starts.value)) {
        this.notice.textContent = "Expiry must be after the start time.";
        return;
      }
      save.disabled = true;
      const extra = {
        link: {
          name: name.value,
          enabled: enabled.checked,
          starts_at: new Date(starts.value).toISOString(),
          expires_at: new Date(ends.value).toISOString(),
          grants,
        },
      };
      if (link) {
        extra.link_id = link.id;
        extra.version = link.version;
      }
      if (password.value) extra.password = password.value;
      await this.perform("save", extra);
      save.disabled = false;
    });
    this.editor.replaceChildren(form);
    this.editor.scrollIntoView({ behavior: "smooth", block: "start" });
    name.focus();
  }
}
customElements.define("guest-access-panel", GuestAccessPanel);
