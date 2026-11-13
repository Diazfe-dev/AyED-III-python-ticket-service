import { formatDateTime } from "../core/dates.js";
import { roleLabel, stateLabel } from "../core/labels.js";
import { translateError } from "../core/messages.js";
import { ticketActions } from "../core/ticket-actions.js";
import { clear, el, emptyResults, loadingIndicator } from "../dom/render.js";

export function title({ id }) {
  return `Ticket #${id}`;
}

function productItem(product, canRemove, onRemove) {
  const children = [el("span", {}, [product.name])];
  if (canRemove) {
    const remove = el("button", { type: "button", "aria-label": `Quitar ${product.name}` }, ["Quitar"]);
    remove.addEventListener("click", () => onRemove(remove, product));
    children.push(remove);
  }
  return el("li", {}, children);
}

function summary(ticket, canRemove, onRemove) {
  const products = ticket.products.map((product) => productItem(product, canRemove, onRemove));
  return el("section", { "aria-label": "Datos del ticket" }, [
    el("p", {}, ["Estado: ", el("span", { class: "ticket-state" }, [stateLabel(ticket.state)])]),
    el("p", {}, [`Cliente: ${ticket.client.name}`]),
    el("p", {}, [`Representante: ${ticket.representative.name}`]),
    el("p", {}, [`Creado: ${formatDateTime(ticket.created_at)}`]),
    el("h2", {}, ["Productos"]),
    products.length > 0 ? el("ul", { class: "products" }, products) : el("p", {}, ["Sin productos"]),
  ]);
}

function milestoneItem(milestone) {
  const { author } = milestone;
  return el("li", {}, [
    el("p", {}, [milestone.content]),
    el("p", {}, [
      `${author.name} (${roleLabel(author.role)}) · ${formatDateTime(milestone.created_at)}`,
    ]),
  ]);
}

function changeItem(change) {
  const { user } = change;
  return el("li", {}, [
    el("p", {}, [stateLabel(change.state)]),
    el("p", {}, [`${user.name} (${roleLabel(user.role)}) · ${formatDateTime(change.timestamp)}`]),
  ]);
}

function timeline(heading, className, items, render) {
  return el("section", { "aria-label": heading }, [
    el("h2", {}, [heading]),
    el("ol", { class: className }, items.map(render)),
  ]);
}

function errorText(response) {
  const error = translateError(response, "form");
  return error.message ?? Object.values(error.fields)[0];
}

function searchPath(query) {
  return query === "" ? "/products/available" : `/products/available?q=${encodeURIComponent(query)}`;
}

export function mount({ root, params, user, request, showError, showStatus }) {
  const content = el("div", {}, [loadingIndicator()]);
  root.append(el("h1", {}, [title(params)]), content);
  const base = `/tickets/${params.id}`;

  async function load() {
    const responses = await Promise.all([
      request("GET", base, undefined, "ticket"),
      request("GET", `${base}/milestones`, undefined, "milestones"),
      request("GET", `${base}/state-changes`, undefined, "state-changes"),
    ]);
    clear(content);
    const failed = responses.find((response) => !response.ok);
    if (failed) {
      showError(translateError(failed).message);
      return;
    }
    const [ticket, milestones, changes] = responses.map((response) => response.body);
    const actions = ticketActions(user.role, ticket.state);
    content.append(
      summary(ticket, actions.includes("remove"), (control, product) =>
        perform(control, () => request("DELETE", `${base}/products/${product.id}`)),
      ),
      ...actionSections(actions),
      timeline("Hitos", "milestones", milestones, milestoneItem),
      timeline("Cambios de estado", "state-changes", changes, changeItem),
    );
  }

  async function perform(control, send) {
    if (control.disabled) {
      return;
    }
    control.disabled = true;
    showError("");
    showStatus("");
    const response = await send();
    if (!response.ok) {
      control.disabled = false;
      showError(errorText(response));
      return;
    }
    await load();
  }

  function milestoneForm(actions) {
    const content_ = el("textarea", { id: "milestone-content", name: "content", rows: "3", required: true });
    const fields = [el("div", { class: "field" }, [el("label", { for: "milestone-content" }, ["Mensaje"]), content_])];
    let startProgress = null;
    if (actions.includes("startProgress")) {
      startProgress = el("input", { type: "checkbox", id: "milestone-start", name: "start_progress" });
      fields.push(
        el("div", { class: "field" }, [
          startProgress,
          el("label", { for: "milestone-start" }, ["Comenzar a trabajar"]),
        ]),
      );
    }
    const submit = el("button", { type: "submit" }, ["Agregar hito"]);
    const form = el("form", { "aria-label": "Agregar hito", novalidate: true }, [...fields, submit]);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const body = { content: content_.value };
      if (startProgress?.checked) {
        body.start_progress = true;
      }
      perform(submit, () => request("POST", `${base}/milestones`, body));
    });
    return form;
  }

  function associateSection() {
    const input = el("input", { type: "search", id: "products-search", name: "q", autocomplete: "off" });
    const search = el("button", { type: "submit" }, ["Buscar"]);
    const form = el("form", { role: "search", "aria-label": "Productos disponibles", novalidate: true }, [
      el("div", { class: "field" }, [el("label", { for: "products-search" }, ["Buscar productos"]), input]),
      search,
    ]);
    const results = el("div", { class: "available-products" });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      showError("");
      const response = await request("GET", searchPath(input.value.trim()), undefined, "products");
      if (!response.ok) {
        showError(translateError(response).message);
        return;
      }
      drawResults(results, response.body.items);
    });
    return el("section", { "aria-label": "Asociar productos" }, [el("h2", {}, ["Asociar productos"]), form, results]);
  }

  function drawResults(results, items) {
    clear(results);
    if (items.length === 0) {
      results.append(emptyResults());
      return;
    }
    const boxes = items.map((item) =>
      el("input", { type: "checkbox", id: `available-${item.id}`, value: item.id, name: "product" }),
    );
    const rows = items.map((item, index) =>
      el("li", {}, [boxes[index], el("label", { for: `available-${item.id}` }, [item.name])]),
    );
    const confirm = el("button", { type: "button" }, ["Asociar"]);
    confirm.addEventListener("click", () => {
      const ids = boxes.filter((box) => box.checked).map((box) => Number(box.value));
      if (ids.length > 0) {
        perform(confirm, () => request("POST", `${base}/products`, { product_ids: ids }));
      }
    });
    results.append(el("ul", {}, rows), confirm);
  }

  function actionSections(actions) {
    const sections = [];
    if (actions.includes("milestone")) {
      sections.push(milestoneForm(actions));
    }
    const buttons = [];
    for (const [action, label, path] of [
      ["close", "Cerrar", "close"],
      ["reopen", "Reabrir", "reopen"],
    ]) {
      if (actions.includes(action)) {
        const control = el("button", { type: "button" }, [label]);
        control.addEventListener("click", () => perform(control, () => request("POST", `${base}/${path}`)));
        buttons.push(control);
      }
    }
    if (buttons.length > 0) {
      sections.push(el("div", { class: "ticket-actions" }, buttons));
    }
    if (actions.includes("associate")) {
      sections.push(associateSection());
    }
    return sections;
  }

  load();
}
