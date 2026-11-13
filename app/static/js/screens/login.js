import { el } from "../dom/render.js";

export function title() {
  return "Iniciar sesión";
}

export function mount({ root }) {
  root.append(el("h1", {}, [title()]));
}
