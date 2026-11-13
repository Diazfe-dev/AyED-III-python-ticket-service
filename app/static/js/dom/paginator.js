import { hasNext, hasPrevious, pageInfo } from "../core/query.js";
import { el } from "./render.js";

const PAGINATOR_LABEL = "Paginación";

function totalText(total) {
  return total === 1 ? "1 resultado" : `${total} resultados`;
}

export function renderPaginator({ state, body, onPrevious, onNext }) {
  const { page, total } = pageInfo(body);
  const previous = el("button", { type: "button", disabled: !hasPrevious(state) }, ["Anterior"]);
  const next = el("button", { type: "button", disabled: !hasNext(body) }, ["Siguiente"]);
  previous.addEventListener("click", onPrevious);
  next.addEventListener("click", onNext);
  return el("div", { class: "paginator", role: "group", "aria-label": PAGINATOR_LABEL }, [
    previous,
    el("span", { class: "page-number" }, [`Página ${page}`]),
    next,
    el("span", { class: "page-total" }, [totalText(total)]),
  ]);
}
