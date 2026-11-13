import { navItems } from "../core/routes.js";
import { clear, el } from "./render.js";

const BRAND = "Mesa de ayuda";
const NAV_LABEL = "Principal";

function navEntry(item, onLogout) {
  if (item.route) {
    return el("a", { href: item.route }, [item.label]);
  }
  const button = el("button", { type: "button" }, [item.label]);
  button.addEventListener("click", onLogout);
  return button;
}

function navigation(role, onLogout) {
  const entries = navItems(role).map((item) => navEntry(item, onLogout));
  return el("nav", { "aria-label": NAV_LABEL }, entries);
}

export function renderShell(container, user, onLogout = () => {}) {
  clear(container);
  const children = [el("span", { class: "brand" }, [BRAND])];
  if (user) {
    children.push(navigation(user.role, onLogout), el("span", { class: "user-name" }, [user.name]));
  }
  container.append(...children);
}
