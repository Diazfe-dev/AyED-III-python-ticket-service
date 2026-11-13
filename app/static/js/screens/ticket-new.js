import { translateError } from "../core/messages.js";
import { clear, el } from "../dom/render.js";

const CLIENT_PLACEHOLDER = "Seleccione un cliente";

export function title() {
  return "Nuevo ticket";
}

function searchPath(path, query) {
  const text = query.trim();
  return text === "" ? path : `${path}?q=${encodeURIComponent(text)}`;
}

function itemsOf(body) {
  return Array.isArray(body) ? body : body.items;
}

function searchForm({ id, label, submitLabel, onSubmit }) {
  const input = el("input", { type: "search", id, name: id, autocomplete: "off" });
  const form = el("form", { role: "search", "aria-label": submitLabel, novalidate: true }, [
    el("div", { class: "field" }, [el("label", { for: id }, [label]), input]),
    el("button", { type: "submit" }, [submitLabel]),
  ]);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    onSubmit(input.value);
  });
  return form;
}

function fieldMark(id, mark) {
  return mark ? el("p", { id: `${id}-mark`, class: "field-mark" }, [mark]) : null;
}

function describe(control, id, mark) {
  if (mark) {
    control.setAttribute("aria-invalid", "true");
    control.setAttribute("aria-describedby", `${id}-mark`);
  }
}

export function mount({ root, request, showError, navigate }) {
  const clientSelect = el("select", { id: "ticket-client", name: "client_id" });
  const productSelect = el("select", { id: "ticket-products", name: "product_ids" });
  productSelect.multiple = true;
  const message = el("textarea", {
    id: "ticket-message",
    name: "first_message",
    rows: 5,
    required: true,
  });
  const form = el("form", { "aria-label": "Nuevo ticket", novalidate: true });
  const marks = {};

  function fillClients(clients) {
    clear(clientSelect);
    clientSelect.append(el("option", { value: "" }, [CLIENT_PLACEHOLDER]));
    for (const client of clients) {
      clientSelect.append(el("option", { value: client.id }, [client.name]));
    }
  }

  function fillProducts(products) {
    clear(productSelect);
    for (const product of products) {
      productSelect.append(el("option", { value: product.id }, [product.name]));
    }
  }

  async function search({ path, key, fill, query }) {
    const response = await request("GET", searchPath(path, query), undefined, key);
    if (!form.isConnected) {
      return;
    }
    if (!response.ok) {
      showError(translateError(response, "list").message);
      return;
    }
    showError("");
    fill(itemsOf(response.body));
  }

  const clientSearch = searchForm({
    id: "ticket-client-search",
    label: "Buscar cliente",
    submitLabel: "Buscar clientes",
    onSubmit: (query) => search({ path: "/clients", key: "clients", fill: fillClients, query }),
  });
  const productSearch = searchForm({
    id: "ticket-product-search",
    label: "Buscar producto",
    submitLabel: "Buscar productos",
    onSubmit: (query) =>
      search({ path: "/products/available", key: "products", fill: fillProducts, query }),
  });

  function draw(feedback = {}) {
    const fields = feedback.marks ?? {};
    for (const control of [clientSelect, message, productSelect]) {
      control.removeAttribute("aria-invalid");
      control.removeAttribute("aria-describedby");
    }
    describe(clientSelect, "ticket-client", fields.client_id);
    describe(message, "ticket-message", fields.first_message);
    describe(productSelect, "ticket-products", fields.product_ids);
    marks.client = fieldMark("ticket-client", fields.client_id);
    marks.message = fieldMark("ticket-message", fields.first_message);
    marks.products = fieldMark("ticket-products", fields.product_ids);
    for (const node of form.querySelectorAll(".field-mark")) {
      node.remove();
    }
    const children = [
      el("div", { class: "field" }, [el("label", { for: "ticket-client" }, ["Cliente"]), clientSelect]),
      marks.client,
      el("div", { class: "field" }, [
        el("label", { for: "ticket-message" }, ["Primer mensaje"]),
        message,
      ]),
      marks.message,
      el("div", { class: "field" }, [
        el("label", { for: "ticket-products" }, ["Productos"]),
        productSelect,
      ]),
      marks.products,
    ].filter((node) => node !== null);
    form.replaceChildren(...children, el("button", { type: "submit" }, ["Crear ticket"]));
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    const clientId = clientSelect.value === "" ? null : Number(clientSelect.value);
    const productIds = [...productSelect.selectedOptions].map((option) => Number(option.value));
    const response = await request("POST", "/tickets", {
      client_id: clientId,
      first_message: message.value,
      product_ids: productIds,
    });
    if (response.ok) {
      navigate(`#/tickets/${response.body.id}`);
      return;
    }
    const error = translateError(response, "form");
    draw({ marks: error.fields ?? {} });
    if (error.message) {
      showError(error.message);
    }
  });

  fillClients([]);
  draw();
  root.append(el("h1", {}, [title()]), clientSearch, productSearch, form);
  search({ path: "/clients", key: "clients", fill: fillClients, query: "" });
  search({ path: "/products/available", key: "products", fill: fillProducts, query: "" });
}
