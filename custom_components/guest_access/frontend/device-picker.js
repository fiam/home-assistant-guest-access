import { icon, actionIcon } from "./icons.js?v=0.5.0";

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key in node) node[key] = value;
    else node.setAttribute(key, value);
  }
  node.append(...children);
  return node;
}
const keyFor = (grant) => `${grant.entity_id}:${grant.action}`;
const grantFor = (choice, label) => ({
  entity_id: choice.entity_id,
  action: choice.action,
  label,
});

export function createDevicePicker(catalog, grants = []) {
  const selections = new Map(
    grants.map((g) => [keyFor(g), grantFor(g, g.label)]),
  );
  const choices = new Map(
    catalog
      .filter((c) => c.selectable !== false || selections.has(keyFor(c)))
      .map((c) => [keyFor(c), { ...c, key: keyFor(c) }]),
  );
  for (const grant of grants) {
    const key = keyFor(grant);
    if (!choices.has(key))
      choices.set(key, {
        ...grant,
        key,
        name: grant.label,
        device_name: grant.label,
        action_name: grant.action.replaceAll("_", " "),
        available: false,
        selectable: false,
      });
  }
  const groups = new Map();
  for (const choice of choices.values()) {
    const key = choice.device_id
      ? `device:${choice.device_id}`
      : `entity:${choice.entity_id}`;
    if (!groups.has(key))
      groups.set(key, {
        key,
        name: choice.device_name || choice.name,
        area: choice.area,
        controls: [],
      });
    groups.get(key).controls.push(choice);
  }
  const ordered = [...groups.values()].sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  const selectedFor = (group) =>
    group.controls.filter((c) => selections.has(c.key));
  const primary = (group) =>
    group.controls.find((c) => !c.maintenance) || group.controls[0];
  const badge = (group) =>
    el("span", { className: "device-badge" }, [
      icon(
        actionIcon(
          `${primary(group).entity_id.split(".")[0]}.${primary(group).action}`,
        ),
      ),
    ]);
  const summary = (controls) => {
    const names = [...new Set(controls.map((c) => c.action_name))];
    return names.length > 3
      ? `${names.slice(0, 2).join(", ")} and ${names.length - 2} more`
      : names.join(", ");
  };
  const section = el("section", {
    className: "device-sharing",
    "aria-labelledby": "shared-devices-heading",
  });
  const count = el("p", { className: "sharing-count", role: "status" });
  const list = el("div", { className: "shared-devices" });
  const add = el("button", {
    type: "button",
    className: "secondary",
    text: "Add device",
    onclick: () => open(null, add),
  });
  add.prepend(icon("plus"));
  section.append(
    el("div", { className: "sharing-heading" }, [
      el("div", {}, [
        el("h3", { id: "shared-devices-heading", text: "Shared devices" }),
        count,
      ]),
      add,
    ]),
    list,
  );
  const dialog = el("dialog", {
    className: "device-dialog",
    "aria-labelledby": "device-dialog-title",
  });
  section.append(dialog);
  let opener = null,
    query = "",
    showMaintenance = false;
  const finish = () => {
    dialog.close();
    if (opener?.isConnected) opener.focus();
  };
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    finish();
  });
  dialog.addEventListener("keydown", (event) => {
    // Inputs belong to the outer link form; Enter must never save it from here.
    if (event.key === "Enter" && event.target.tagName === "INPUT")
      event.preventDefault();
  });
  function shell(title, subtitle, content, actions, back) {
    const close = el(
      "button",
      {
        type: "button",
        className: "icon-button secondary",
        "aria-label": "Close device settings",
        onclick: finish,
      },
      [icon("close")],
    );
    const heading = el("div", { className: "dialog-heading" }, [
      el("div", {}, [
        el("h2", { id: "device-dialog-title", text: title }),
        ...(subtitle ? [el("p", { text: subtitle })] : []),
      ]),
      close,
    ]);
    const header = el("div", { className: "dialog-header" });
    if (back)
      header.append(
        el("button", {
          type: "button",
          className: "dialog-back secondary",
          text: "Back to devices",
          onclick: () => browse(true),
        }),
      );
    header.append(heading);
    dialog.replaceChildren(
      header,
      el("div", { className: "dialog-body" }, [content]),
      el("div", { className: "dialog-actions" }, actions),
    );
  }
  function open(group, button) {
    opener = button;
    if (group) edit(group, false);
    else browse(false);
    dialog.showModal();
    const first = dialog.querySelector(
      "input:not([type=checkbox]), input[type=checkbox]",
    );
    first?.focus();
  }
  function drawSelected() {
    const shared = ordered.filter((g) => selectedFor(g).length);
    count.textContent = shared.length
      ? `${shared.length} ${shared.length === 1 ? "device" : "devices"} selected`
      : "Choose what your guest can use.";
    list.replaceChildren();
    if (!shared.length)
      list.append(
        el("p", { className: "sharing-empty", text: "No devices shared yet." }),
      );
    for (const group of shared) {
      const selected = selectedFor(group);
      const labels = [
        ...new Set(selected.map((c) => selections.get(c.key).label)),
      ];
      const title = labels.length === 1 ? labels[0] : group.name;
      const editButton = el("button", {
        type: "button",
        className: "secondary device-edit",
        text: "Edit",
        "aria-label": `Edit ${title}`,
      });
      editButton.addEventListener("click", () => open(group, editButton));
      const remove = el(
        "button",
        {
          type: "button",
          className: "icon-button device-remove",
          "aria-label": `Remove ${title}`,
          onclick: () => {
            for (const control of group.controls)
              selections.delete(control.key);
            drawSelected();
            add.focus();
          },
        },
        [icon("close")],
      );
      list.append(
        el("div", { className: "shared-device", "data-device": group.key }, [
          badge(group),
          el("div", { className: "device-copy" }, [
            el("h4", { text: title }),
            el("p", { text: summary(selected) }),
            ...(selected.some((c) => c.available === false)
              ? [el("small", { text: "Some controls are unavailable" })]
              : []),
          ]),
          el("div", { className: "device-row-actions" }, [editButton, remove]),
        ]),
      );
    }
  }
  function browse(focus) {
    const content = el("div");
    const search = el("input", {
      type: "search",
      value: query,
      className: "device-search",
      placeholder: "Search devices, rooms or actions",
      "aria-label": "Search devices, rooms or actions",
    });
    const results = el("div", { className: "device-results" });
    const extra = el("button", {
      type: "button",
      className: "secondary maintenance-toggle",
      hidden: !ordered.some(
        (g) => !selectedFor(g).length && g.controls.every((c) => c.maintenance),
      ),
      text: showMaintenance
        ? "Hide maintenance devices"
        : "Show maintenance devices",
    });
    const draw = () => {
      results.replaceChildren();
      const q = query.trim().toLowerCase();
      const sorted = [...ordered].sort(
        (a, b) =>
          Number(!!selectedFor(b).length) - Number(!!selectedFor(a).length),
      );
      for (const group of sorted) {
        if (
          !showMaintenance &&
          !selectedFor(group).length &&
          group.controls.every((c) => c.maintenance)
        )
          continue;
        if (
          q &&
          !`${group.name} ${group.area || ""} ${group.controls.map((c) => `${c.name} ${c.entity_id} ${c.action_name}`).join(" ")}`
            .toLowerCase()
            .includes(q)
        )
          continue;
        const shared = selectedFor(group).length;
        const button = el(
          "button",
          {
            type: "button",
            className: "device-result",
            "data-device": group.key,
            onclick: () => edit(group, true),
          },
          [
            badge(group),
            el("span", { className: "device-copy" }, [
              el("strong", { text: group.name }),
              el("small", {
                text:
                  [group.area, shared ? "Already shared" : ""]
                    .filter(Boolean)
                    .join(" · ") || "Choose controls",
              }),
            ]),
            icon("chevron"),
          ],
        );
        results.append(button);
      }
      if (!results.children.length)
        results.append(
          el("p", { className: "sharing-empty", text: "No matching devices." }),
        );
    };
    search.addEventListener("input", () => {
      query = search.value;
      draw();
    });
    extra.addEventListener("click", () => {
      showMaintenance = !showMaintenance;
      extra.textContent = showMaintenance
        ? "Hide maintenance devices"
        : "Show maintenance devices";
      draw();
    });
    content.append(search, results);
    shell(
      "Add a device",
      "Choose a device to set its shared controls.",
      content,
      [
        extra,
        el("button", {
          type: "button",
          className: "secondary",
          text: "Cancel",
          onclick: finish,
        }),
      ],
    );
    draw();
    if (focus) search.focus();
  }
  function edit(group, back) {
    const draft = new Map(
      selectedFor(group).map((c) => [c.key, { ...selections.get(c.key) }]),
    );
    const content = el("div", { className: "device-settings" });
    const fields = new Map();
    const error = el("p", {
      className: "dialog-error",
      role: "alert",
      hidden: true,
    });
    const normal = group.controls.filter(
      (c) => !c.maintenance && c.selectable !== false,
    );
    const all = el("button", {
      type: "button",
      className: "secondary",
      text: `Share all ${normal.length} controls`,
      hidden: !normal.length,
    });
    const clear = el("button", {
      type: "button",
      className: "plain-button",
      text: "Clear selection",
    });
    content.append(el("div", { className: "selection-tools" }, [all, clear]));
    const sections = new Map();
    for (const choice of group.controls) {
      if (!sections.has(choice.entity_id)) sections.set(choice.entity_id, []);
      sections.get(choice.entity_id).push(choice);
    }
    const maintenance = el("details", { className: "maintenance-actions" }, [
      el("summary", { text: "Maintenance actions" }),
    ]);
    const detailIds = [];
    for (const [entity, controls] of sections) {
      const first = controls[0];
      const selected = controls.filter((c) => draft.has(c.key));
      const labels = [...new Set(selected.map((c) => draft.get(c.key).label))];
      const separateNames = labels.length > 1;
      const fieldset = el("fieldset", { className: "control-group" });
      fieldset.append(
        el("legend", {
          text: sections.size > 1 ? first.name : "Shared controls",
        }),
      );
      const sharedName = el("input", {
        type: "text",
        maxLength: 80,
        value: labels[0] || first.name.slice(0, 80),
      });
      const nameLabel = el("label", { className: "guest-name" }, [
        el("span", { text: "Name shown to guests" }),
        sharedName,
      ]);
      for (const choice of controls) {
        const check = el("input", {
          type: "checkbox",
          checked: draft.has(choice.key),
          "data-action": choice.key,
        });
        const name = separateNames
          ? el("input", {
              type: "text",
              maxLength: 80,
              value: draft.get(choice.key)?.label || choice.name.slice(0, 80),
            })
          : sharedName;
        const ownLabel = separateNames
          ? el("label", { className: "guest-name action-name" }, [
              el("span", { text: `Guest name for ${choice.action_name}` }),
              name,
            ])
          : null;
        const copy = el("span", {}, [
          el("span", { text: choice.action_name }),
          ...(choice.available === false
            ? [el("small", { text: "Currently unavailable" })]
            : []),
        ]);
        fieldset.append(
          el("label", { className: "control-check" }, [check, copy]),
        );
        if (ownLabel) fieldset.append(ownLabel);
        fields.set(choice.key, { check, name, ownLabel });
        check.addEventListener("change", () => {
          if (check.checked)
            draft.set(choice.key, grantFor(choice, name.value));
          else draft.delete(choice.key);
          sync();
        });
        if (separateNames)
          name.addEventListener("input", () => {
            if (draft.has(choice.key)) draft.get(choice.key).label = name.value;
          });
      }
      if (!separateNames) {
        fieldset.append(nameLabel);
        sharedName.addEventListener("input", () => {
          for (const c of controls)
            if (draft.has(c.key)) draft.get(c.key).label = sharedName.value;
        });
      }
      fieldset.updateName = () => {
        nameLabel.hidden = !controls.some((c) => draft.has(c.key));
      };
      if (first.maintenance) {
        maintenance.append(fieldset);
        if (selected.length) maintenance.open = true;
      } else content.append(fieldset);
      detailIds.push(entity);
    }
    if (maintenance.children.length > 1) content.append(maintenance);
    content.append(
      el("details", { className: "entity-details" }, [
        el("summary", { text: "Technical details" }),
        ...detailIds.map((id) => el("p", { text: id })),
      ]),
      error,
    );
    function sync() {
      for (const [key, field] of fields) {
        field.check.checked = draft.has(key);
        if (field.ownLabel) field.ownLabel.hidden = !draft.has(key);
      }
      content.querySelectorAll("fieldset").forEach((f) => f.updateName?.());
      all.disabled = normal.every((c) => draft.has(c.key));
      clear.disabled = !draft.size;
      error.hidden = true;
    }
    all.addEventListener("click", () => {
      for (const choice of normal)
        if (!draft.has(choice.key))
          draft.set(
            choice.key,
            grantFor(choice, fields.get(choice.key).name.value),
          );
      sync();
    });
    clear.addEventListener("click", () => {
      draft.clear();
      sync();
    });
    const done = el("button", {
      type: "button",
      text: "Done",
      onclick: () => {
        if ([...draft.values()].some((g) => !g.label.trim())) {
          error.textContent = "Enter a name for each shared control.";
          error.hidden = false;
          return;
        }
        const others = [...selections.keys()].filter(
          (key) => !group.controls.some((c) => c.key === key),
        ).length;
        if (others + draft.size > 32) {
          error.textContent =
            "A link can share up to 32 controls. Choose fewer controls.";
          error.hidden = false;
          return;
        }
        for (const c of group.controls) selections.delete(c.key);
        for (const [key, value] of draft) selections.set(key, value);
        drawSelected();
        finish();
        if (!opener?.isConnected)
          (
            [...list.children]
              .find((row) => row.dataset.device === group.key)
              ?.querySelector(".device-edit") || add
          ).focus();
      },
    });
    shell(
      group.name,
      group.area || "Choose what your guest can use.",
      content,
      [
        el("button", {
          type: "button",
          className: "secondary",
          text: "Cancel",
          onclick: finish,
        }),
        done,
      ],
      back,
    );
    sync();
    if (dialog.open)
      (dialog.querySelector('input[type="checkbox"]') || done).focus();
  }
  section.getGrants = () => [...selections.values()].map((g) => ({ ...g }));
  drawSelected();
  return section;
}
