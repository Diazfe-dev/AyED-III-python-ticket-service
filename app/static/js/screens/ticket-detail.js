import { el } from "../dom/render.js";

export function title({ id }) {
  return `Ticket #${id}`;
}

export function mount({ root, params }) {
  root.append(el("h1", {}, [title(params)]));
}
