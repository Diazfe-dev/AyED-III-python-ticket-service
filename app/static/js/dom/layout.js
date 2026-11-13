import { el } from "./render.js";

export function pageHeader({ title, action = null }) {
  const heading = el("h1", {}, [title]);
  const button = action === null ? null : el("button", { type: "button", class: "primary-action" }, [action.label]);
  if (button !== null) {
    button.addEventListener("click", () => action.onClick(button));
  }
  const children = button === null ? [heading] : [heading, button];
  return { element: el("div", { class: "page-header" }, children), heading, button };
}

export function surface({ toolbar, table }) {
  return el("div", { class: "surface" }, [toolbar, table]);
}

export function toolbar(children) {
  return el("div", { class: "toolbar filters" }, children);
}
