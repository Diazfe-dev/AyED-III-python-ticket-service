import { PAGE_SIZE_OPTIONS, rangeText } from "../core/query.js";
import { el } from "./render.js";

const PAGINATOR_LABEL = "Paginación";
const SIZE_LABEL = "Filas por página";
const SIZE_ID = "page-size";

export function createFooter({ onPrevious, onNext, onPageSize }) {
  const select = el(
    "select",
    { id: SIZE_ID, name: SIZE_ID },
    PAGE_SIZE_OPTIONS.map((size) => el("option", { value: size }, [String(size)])),
  );
  const range = el("span", { class: "page-range" });
  const number = el("span", { class: "page-number" });
  const previous = el("button", { type: "button", disabled: true }, ["Anterior"]);
  const next = el("button", { type: "button", disabled: true }, ["Siguiente"]);
  select.addEventListener("change", () => onPageSize(select.value));
  previous.addEventListener("click", onPrevious);
  next.addEventListener("click", onNext);
  const element = el("div", { class: "table-footer", role: "group", "aria-label": PAGINATOR_LABEL }, [
    el("div", { class: "page-size" }, [el("label", { for: SIZE_ID }, [SIZE_LABEL]), select]),
    range,
    number,
    previous,
    next,
  ]);
  select.value = "20";
  return {
    element,
    update({ page, pageSize, total, hasNext }) {
      select.value = String(pageSize);
      range.textContent = rangeText({ page, pageSize, total });
      number.textContent = `Página ${page}`;
      previous.disabled = page <= 1;
      next.disabled = !hasNext;
    },
  };
}
