import { el } from "../dom/render.js";

export function title() {
  return "Tipos de producto";
}

export function mount({ root }) {
  root.append(el("h1", {}, [title()]));
}
