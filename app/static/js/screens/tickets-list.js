import { el } from "../dom/render.js";

export function title() {
  return "Tickets";
}

export function mount({ root }) {
  root.append(el("h1", {}, [title()]));
}
