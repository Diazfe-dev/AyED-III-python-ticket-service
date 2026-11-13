import { navItems } from "../core/routes.js";
import { clear, el } from "./render.js";

const BRAND = "Mesa de ayuda";
const NAV_LABEL = "Principal";

function navigation(role) {
  const links = navItems(role)
    .filter((item) => item.route)
    .map((item) => el("a", { href: item.route }, [item.label]));
  return el("nav", { "aria-label": NAV_LABEL }, links);
}

export function renderShell(container, user) {
  clear(container);
  const children = [el("span", { class: "brand" }, [BRAND])];
  if (user) {
    children.push(navigation(user.role), el("span", { class: "user-name" }, [user.name]));
  }
  container.append(...children);
}
