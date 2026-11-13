import { translateError } from "../core/messages.js";
import { openFormDialog } from "../dom/dialog.js";
import { markControl } from "../dom/form.js";
import { clear, el } from "../dom/render.js";

const CLIENT_PLACEHOLDER = "Seleccione un cliente";
const CLIENTS_KEY = "dialog-clients";
const PRODUCTS_KEY = "dialog-products";

function searchPath(path, query) {
  const text = query.trim();
  return text === "" ? path : `${path}?q=${encodeURIComponent(text)}`;
}

function itemsOf(body) {
  return Array.isArray(body) ? body : body.items;
}

function field(label, control, mark) {
  return el("div", { class: "field" }, [el("label", { for: control.id }, [label]), control, mark]);
}

function searchRow({ id, label, submitLabel, onSearch }) {
  const input = el("input", { type: "search", id, name: id, autocomplete: "off" });
  const button = el("button", { type: "button" }, [submitLabel]);
  const run = () => onSearch(input.value);
  button.addEventListener("click", run);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      run();
    }
  });
  return el("div", { class: "search-row" }, [
    el("div", { class: "field" }, [el("label", { for: id }, [label]), input]),
    button,
  ]);
}

function createTicketForm({ onSearchClients, onSearchProducts }) {
  const clientSelect = el("select", { id: "ticket-client", name: "client_id" });
  const productSelect = el("select", { id: "ticket-products", name: "product_ids" });
  productSelect.multiple = true;
  const message = el("textarea", { id: "ticket-message", name: "first_message", rows: 5 });
  const marks = {
    client_id: el("p", { id: "ticket-client-mark", class: "field-mark" }),
    first_message: el("p", { id: "ticket-message-mark", class: "field-mark" }),
    product_ids: el("p", { id: "ticket-products-mark", class: "field-mark" }),
  };
  for (const mark of Object.values(marks)) {
    mark.hidden = true;
  }
  const controls = {
    client_id: clientSelect,
    first_message: message,
    product_ids: productSelect,
  };

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

  fillClients([]);
  return {
    elements: [
      searchRow({
        id: "ticket-client-search",
        label: "Buscar cliente",
        submitLabel: "Buscar clientes",
        onSearch: onSearchClients,
      }),
      field("Cliente", clientSelect, marks.client_id),
      field("Primer mensaje", message, marks.first_message),
      searchRow({
        id: "ticket-product-search",
        label: "Buscar producto",
        submitLabel: "Buscar productos",
        onSearch: onSearchProducts,
      }),
      field("Productos", productSelect, marks.product_ids),
    ],
    values: () => ({
      client_id: clientSelect.value === "" ? null : Number(clientSelect.value),
      first_message: message.value,
      product_ids: [...productSelect.selectedOptions].map((option) => Number(option.value)),
    }),
    clearPasswords() {},
    setMarks(next) {
      for (const [name, control] of Object.entries(controls)) {
        markControl(control, marks[name], next[name] ?? null);
      }
    },
    fillClients,
    fillProducts,
  };
}

export function openTicketDialog({ root, request, opener, fallback, navigate, onCancel }) {
  let dialog = null;

  async function search({ path, key, fill, query }) {
    const response = await request("GET", searchPath(path, query), undefined, key);
    if (!dialog.isOpen()) {
      return;
    }
    if (!response.ok) {
      dialog.setFeedback({ message: translateError(response, "list").message });
      return;
    }
    fill(itemsOf(response.body));
  }

  const searchClients = (query) =>
    search({ path: "/clients", key: CLIENTS_KEY, fill: form.fillClients, query });
  const searchProducts = (query) =>
    search({ path: "/products/available", key: PRODUCTS_KEY, fill: form.fillProducts, query });
  const form = createTicketForm({ onSearchClients: searchClients, onSearchProducts: searchProducts });

  dialog = openFormDialog({
    parent: root,
    id: "ticket-create",
    title: "Nuevo ticket",
    submitLabel: "Crear",
    opener,
    fallback,
    form,
    onCancel,
    onSubmit: async (values, controller) => {
      const response = await controller.send(request("POST", "/tickets", values));
      if (response) {
        navigate(`#/tickets/${response.body.id}`);
      }
    },
  });
  searchClients("");
  searchProducts("");
  return dialog;
}
