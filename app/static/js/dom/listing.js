import { translateError } from "../core/messages.js";
import { applyFilter, listState, nextPage, previousPage, reloadQuery } from "../core/query.js";
import { renderPaginator } from "./paginator.js";
import { clear, el, emptyResults, loadingIndicator } from "./render.js";

const LIST_KEY = "list";
const LIST_CONTEXT = "list";

export function selectField({ id, label, options, onChange }) {
  const select = el(
    "select",
    { id, name: id },
    options.map((option) => el("option", { value: option.value }, [option.label])),
  );
  select.addEventListener("change", () => onChange(select.value));
  return { element: el("div", { class: "field" }, [el("label", { for: id }, [label]), select]), select };
}

export function searchField({ id, label, submitLabel, onSubmit }) {
  const input = el("input", { type: "search", id, name: id, autocomplete: "off" });
  const form = el("form", { role: "search", novalidate: true }, [
    el("div", { class: "field" }, [el("label", { for: id }, [label]), input]),
    el("button", { type: "submit" }, [submitLabel]),
  ]);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    onSubmit(input.value);
  });
  return form;
}

export async function fillOptions({ select, request, path, key, showError }) {
  const response = await request("GET", path, undefined, key);
  if (!select.isConnected) {
    return;
  }
  if (!response.ok) {
    showError(translateError(response, LIST_CONTEXT).message);
    return;
  }
  for (const item of response.body) {
    select.append(el("option", { value: item.id }, [item.name]));
  }
}

function buildTable(columns, items, row) {
  const head = el("tr", {}, columns.map((name) => el("th", { scope: "col" }, [name])));
  const body = items.map((item) => el("tr", {}, row(item).map((cell) => el("td", {}, [cell]))));
  return el("div", { class: "table-scroll" }, [
    el("table", {}, [el("thead", {}, [head]), el("tbody", {}, body)]),
  ]);
}

export function createListing({ request, showError, path, columns, row, filters = {} }) {
  let state = listState(filters, 1);
  const element = el("div", { class: "listing" });

  function draw(body) {
    clear(element);
    if (body.items.length === 0) {
      element.append(emptyResults());
    } else {
      element.append(buildTable(columns, body.items, row));
    }
    if (body.total > 0) {
      element.append(
        renderPaginator({
          state,
          body,
          onPrevious: () => go(previousPage(state)),
          onNext: () => go(nextPage(state)),
        }),
      );
    }
  }

  async function load() {
    showError("");
    clear(element);
    element.append(loadingIndicator());
    const response = await request("GET", reloadQuery(path, state), undefined, LIST_KEY);
    if (!element.isConnected) {
      return;
    }
    clear(element);
    if (response.ok) {
      draw(response.body);
    } else {
      showError(translateError(response, LIST_CONTEXT).message);
    }
  }

  function go(next) {
    state = next;
    return load();
  }

  return {
    element,
    load,
    apply: (changes) => go(applyFilter(state, changes)),
    state: () => state,
  };
}
