import { navItems } from "../core/routes.js";
import { clear, el } from "./render.js";

const BRAND = "Mesa de ayuda";
const NAV_LABEL = "Principal";

function navEntry(item, current, onLogout) {
  if (item.route) {
    const attrs = { href: item.route, "aria-current": item.route === current ? "page" : null };
    return el("a", attrs, [item.label]);
  }
  const button = el("button", { type: "button" }, [item.label]);
  button.addEventListener("click", onLogout);
  return button;
}

function navigation(role, current, onLogout) {
  const entries = navItems(role).map((item) => navEntry(item, current, onLogout));
  return el("nav", { "aria-label": NAV_LABEL }, entries);
}

export function renderShell(container, user, onLogout = () => {}, current = null) {
  clear(container);
  const children = [el("span", { class: "brand" }, [BRAND])];
  if (user) {
    children.push(navigation(user.role, current, onLogout), el("span", { class: "user-name" }, [user.name]));
  }
  container.append(...children);
}
