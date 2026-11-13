import { clear, el } from "./render.js";

const BRAND = "Mesa de ayuda";

export function renderShell(container, user) {
  clear(container);
  const children = [el("span", { class: "brand" }, [BRAND])];
  if (user) {
    children.push(el("span", { class: "user-name" }, [user.name]));
  }
  container.append(...children);
}
