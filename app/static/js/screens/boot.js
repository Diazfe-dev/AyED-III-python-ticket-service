import { el, loadingIndicator } from "../dom/render.js";

export function title() {
  return "Cargando";
}

export function mount({ root, params, dispatch, showError }) {
  if (!params.error) {
    root.append(loadingIndicator());
    return;
  }
  showError(params.error);
  const retry = el("button", { type: "button" }, ["Reintentar"]);
  retry.addEventListener("click", () => dispatch({ type: "retryClicked" }));
  root.append(retry);
}
