// Small local SVGs: no icon font, external requests, or letter placeholders.
const paths = {
  home: ["M3 10.5 12 3l9 7.5", "M5 9v12h5v-7h4v7h5V9"],
  door: ["M4 21h16", "M6 21V3h12v18", "M6 3l8 3v15", "M11 12h.01"],
  lock: ["M7 10V7a5 5 0 0 1 10 0v3", "M5 10h14v11H5z", "M12 14v3"],
  unlock: ["M7 10V7a5 5 0 0 1 9.5-2", "M5 10h14v11H5z", "M12 14v3"],
  clock: ["M12 8v5l3 2", "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0"],
  chevron: ["m9 5 7 7-7 7"],
  arrow: ["M5 12h14", "m13 6 6 6-6 6"],
  logout: ["M10 4H4v16h6", "M9 12h12", "m16 7 5 5-5 5"],
  plus: ["M12 5v14", "M5 12h14"],
  edit: ["m15 5 4 4", "m3 21 5-1L21 7a2.8 2.8 0 0 0-4-4L4 16z"],
  copy: ["M8 8h13v13H8z", "M16 4V2H2v14h2"],
  pause: ["M7 4v16", "M17 4v16"],
  play: ["m7 3 14 9-14 9z"],
  refresh: ["M20 7a9 9 0 1 0 1 8", "M20 2v6h-6"],
  trash: ["M3 6h18", "M9 6V3h6v3", "m5 6 1 15h12l1-15", "M10 10v7", "M14 10v7"],
  eye: [
    "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12",
    "M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
  ],
  close: ["m6 6 12 12", "M6 18 18 6"],
  check: ["m4 12 5 5L20 6"],
  key: ["M13 8a5 5 0 1 1-10 0 5 5 0 0 1 10 0", "m12 12 9 9", "m17 17 3-3"],
  shield: ["m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6z", "m8 12 3 3 5-6"],
  light: ["M9 18h6", "M10 21h4", "M8 15a7 7 0 1 1 8 0l-1 3H9z"],
  power: ["M12 2v10", "M6 5a9 9 0 1 0 12 0"],
  cover: ["M4 3h16v18H4z", "M4 7h16", "M4 11h16", "M4 15h16"],
  stop: ["M5 5h14v14H5z"],
  press: [
    "M12 3v3",
    "M4 7l2 2",
    "m20 7-2 2",
    "M7 16v-3a5 5 0 0 1 10 0v3",
    "M5 16h14v5H5z",
  ],
};
export function icon(name, className = "") {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  for (const [key, value] of Object.entries({
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "1.8",
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
    "aria-hidden": "true",
    focusable: "false",
    class: `icon ${className}`,
  }))
    svg.setAttribute(key, value);
  for (const d of paths[name] || paths.press) {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}
export function actionIcon(kind = "") {
  if (kind === "lock.open") return "door";
  if (kind === "lock.lock") return "lock";
  if (kind === "lock.unlock") return "unlock";
  if (kind.endsWith(".stop_cover")) return "stop";
  if (kind.startsWith("light.")) return "light";
  if (kind.startsWith("cover.")) return "cover";
  if (/\.(turn_on|turn_off)$/.test(kind)) return "power";
  return "press";
}
