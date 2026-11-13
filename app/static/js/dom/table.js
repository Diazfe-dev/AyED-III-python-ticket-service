import { el } from "./render.js";

export function buildTable({ label, columns, items, row }) {
  const head = el("tr", {}, columns.map((name) => el("th", { scope: "col" }, [name])));
  const body = items.map((item) => el("tr", {}, row(item).map((cell) => el("td", {}, [cell]))));
  return el("div", { class: "table-scroll" }, [
    el("table", { "aria-label": label }, [el("thead", {}, [head]), el("tbody", {}, body)]),
  ]);
}
