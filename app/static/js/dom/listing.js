import { translateError } from "../core/messages.js";
import {
  applyFilter,
  changePageSize,
  hasNext,
  lastValidPage,
  listState,
  memoryPage,
  nextPage,
  previousPage,
  reloadQuery,
} from "../core/query.js";
import { createFooter } from "./paginator.js";
import { clear, el, emptyResults, loadingIndicator } from "./render.js";
import { buildTable } from "./table.js";

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

function listingFrame(footerHandlers) {
  const body = el("div", { class: "listing-body" });
  const footer = createFooter(footerHandlers);
  const element = el("div", { class: "listing" }, [body, footer.element]);
  return { element, body, footer };
}

function drawBody(body, { label, columns, row, items }) {
  clear(body);
  body.append(items.length === 0 ? emptyResults() : buildTable({ label, columns, items, row }));
}

export function createListing({ request, showError, path, label, columns, row, filters = {} }) {
  let state = listState(filters, 1);
  const frame = listingFrame({
    onPrevious: () => go(previousPage(state)),
    onNext: () => go(nextPage(state)),
    onPageSize: (size) => go(changePageSize(state, size)),
  });

  function draw(body) {
    drawBody(frame.body, { label, columns, row, items: body.items });
    frame.footer.update({
      page: body.page,
      pageSize: state.pageSize,
      total: body.total,
      hasNext: hasNext({ page: body.page, page_size: state.pageSize, total: body.total }),
    });
  }

  async function load({ clampToLastPage = false } = {}) {
    showError("");
    clear(frame.body);
    frame.body.append(loadingIndicator());
    const response = await request("GET", reloadQuery(path, state), undefined, LIST_KEY);
    if (!frame.element.isConnected) {
      return;
    }
    if (response.ok && clampToLastPage && response.body.items.length === 0 && response.body.total > 0) {
      state = listState(state.filters, lastValidPage(response.body.total, state.pageSize), state.pageSize);
      return load();
    }
    clear(frame.body);
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
    element: frame.element,
    load,
    reload: () => load({ clampToLastPage: true }),
    apply: (changes) => go(applyFilter(state, changes)),
    state: () => state,
  };
}

export function createMemoryListing({ fetchItems, showError, label, columns, row }) {
  let state = listState({}, 1);
  let items = [];
  const frame = listingFrame({
    onPrevious: () => show(previousPage(state)),
    onNext: () => show(nextPage(state)),
    onPageSize: (size) => show(changePageSize(state, size)),
  });

  function show(next) {
    state = next;
    const view = memoryPage(items, state.page, state.pageSize);
    state = listState(state.filters, view.page, state.pageSize);
    drawBody(frame.body, { label, columns, row, items: view.items });
    frame.footer.update({
      page: view.page,
      pageSize: view.pageSize,
      total: view.total,
      hasNext: hasNext({ page: view.page, page_size: view.pageSize, total: view.total }),
    });
  }

  async function load(next) {
    state = next;
    showError("");
    clear(frame.body);
    frame.body.append(loadingIndicator());
    const result = await fetchItems(state.filters.q ?? "");
    if (!frame.element.isConnected) {
      return;
    }
    clear(frame.body);
    if (result.ok) {
      items = result.items;
      show(next);
    } else {
      showError(result.message);
    }
  }

  return {
    element: frame.element,
    load: () => load(state),
    reload: () => load(state),
    apply: (changes) => load(applyFilter(state, changes)),
    state: () => state,
  };
}
