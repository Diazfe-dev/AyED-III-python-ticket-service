import { homeOf } from "../core/routes.js";
import { el } from "../dom/render.js";

const HOME_LINK = "Ir al inicio";

export function title() {
  return "Página no encontrada";
}

export function mount({ root, user }) {
  const children = [el("h1", {}, [title()])];
  if (user) {
    children.push(el("p", {}, [el("a", { href: homeOf(user.role) }, [HOME_LINK])]));
  }
  root.append(...children);
}
