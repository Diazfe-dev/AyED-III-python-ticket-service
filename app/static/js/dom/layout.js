import { el } from "./render.js";

function headerButton(className, { label, onClick }) {
  const button = el("button", { type: "button", class: className }, [label]);
  button.addEventListener("click", () => onClick(button));
  return button;
}

export function pageHeader({ title, action = null, secondary = [] }) {
  const heading = el("h1", {}, [title]);
  const button = action === null ? null : headerButton("primary-action", action);
  const extras = secondary.map((entry) => headerButton("secondary-action", entry));
  const children = [heading, ...(button === null ? [] : [button]), ...extras];
  return { element: el("div", { class: "page-header" }, children), heading, button, secondary: extras };
}

export function surface({ toolbar, table }) {
  return el("div", { class: "surface" }, [toolbar, table]);
}

export function toolbar(children) {
  return el("div", { class: "toolbar filters" }, children);
}
