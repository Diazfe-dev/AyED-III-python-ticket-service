import { el } from "../dom/render.js";

export function title() {
  return "Página no encontrada";
}

export function mount({ root }) {
  root.append(el("h1", {}, [title()]));
}
