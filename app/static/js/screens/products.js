import { activeLabel } from "../core/labels.js";
import { translateError } from "../core/messages.js";
import { createListing, searchField, selectField } from "../dom/listing.js";
import { clear, el } from "../dom/render.js";

const COLUMNS = ["Nombre", "Tipo", "Categoría", "Estado", "Acciones"];
const ALL_OPTION = { value: "", label: "Todos" };
const STATUS_OPTIONS = [
  ALL_OPTION,
  { value: "true", label: activeLabel(true) },
  { value: "false", label: activeLabel(false) },
];

export function title() {
  return "Productos";
}

function optionNodes(options) {
  return options.map((option) => el("option", { value: String(option.value) }, [option.label]));
}

function typeOptions(productTypes) {
  return productTypes.map((type) => ({ value: type.id, label: type.name }));
}

function buildForm({ label, productTypes, product, submitLabel, extraButtons = [], onSubmit }) {
  const prefix = product === undefined ? "product-new" : `product-edit-${product.id}`;
  const nameInput = el("input", {
    type: "text",
    id: `${prefix}-name`,
    name: "name",
    autocomplete: "off",
    value: product?.name ?? "",
  });
  const typeSelect = el(
    "select",
    { id: `${prefix}-type`, name: "product_type_id" },
    optionNodes([{ value: "", label: "Seleccione un tipo" }, ...typeOptions(productTypes)]),
  );
  typeSelect.value = product === undefined ? "" : String(product.product_type.id);
  const message = el("p", { class: "message-error", role: "alert" });
  message.hidden = true;
  const form = el("form", { "aria-label": label, novalidate: true }, [
    el("div", { class: "field" }, [el("label", { for: nameInput.id }, ["Nombre"]), nameInput]),
    el("div", { class: "field" }, [el("label", { for: typeSelect.id }, ["Tipo"]), typeSelect]),
    message,
    el("button", { type: "submit" }, [submitLabel]),
    ...extraButtons,
  ]);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    onSubmit({ name: nameInput.value, typeId: typeSelect.value });
  });
  return {
    element: form,
    reset() {
      nameInput.value = "";
      typeSelect.value = "";
      message.hidden = true;
    },
    showMessage(text) {
      message.textContent = text;
      message.hidden = false;
    },
  };
}

export function mount({ root, request, showError, showStatus }) {
  const panel = el("div", { class: "product-panel" });
  const createSlot = el("div", { class: "product-create" });
  let listing = null;
  let productTypes = [];

  function closePanel() {
    clear(panel);
  }

  async function runAction(promise) {
    showError("");
    showStatus("");
    const response = await promise;
    if (response.ok) {
      await listing.reload();
      return;
    }
    showError(translateError(response).message);
  }

  function writeBody({ name, typeId }) {
    return { name, product_type_id: Number(typeId) };
  }

  function drawCreate() {
    clear(createSlot);
    const form = buildForm({
      label: "Nuevo producto",
      productTypes,
      submitLabel: "Crear",
      onSubmit: async (values) => {
        showError("");
        showStatus("");
        const response = await request("POST", "/products", writeBody(values));
        if (response.ok) {
          form.reset();
          await listing.reload();
          return;
        }
        form.showMessage(translateError(response, "form").message);
      },
    });
    createSlot.append(form.element);
  }

  function openEdit(product) {
    const cancel = el("button", { type: "button" }, ["Cancelar"]);
    cancel.addEventListener("click", closePanel);
    const form = buildForm({
      label: "Editar producto",
      productTypes,
      product,
      submitLabel: "Guardar",
      extraButtons: [cancel],
      onSubmit: async (values) => {
        showError("");
        showStatus("");
        const response = await request("PATCH", `/products/${product.id}`, writeBody(values));
        if (response.ok) {
          closePanel();
          await listing.reload();
          return;
        }
        form.showMessage(translateError(response, "form").message);
      },
    });
    clear(panel);
    panel.append(form.element);
  }

  function actionButton(text, product, onClick) {
    const button = el("button", { type: "button", "aria-label": `${text} ${product.name}` }, [text]);
    button.addEventListener("click", onClick);
    return button;
  }

  function productRow(product) {
    const toggle = product.is_active
      ? actionButton("Dar de baja", product, () =>
          runAction(request("POST", `/products/${product.id}/deactivate`)),
        )
      : actionButton("Reactivar", product, () =>
          runAction(request("POST", `/products/${product.id}/activate`)),
        );
    return [
      product.name,
      product.product_type.name,
      product.category.name,
      activeLabel(product.is_active),
      el("div", { class: "row-actions" }, [actionButton("Editar", product, () => openEdit(product)), toggle]),
    ];
  }

  listing = createListing({
    request,
    showError,
    path: "/products",
    columns: COLUMNS,
    row: productRow,
  });
  const statusFilter = selectField({
    id: "filter-state",
    label: "Estado",
    options: STATUS_OPTIONS,
    onChange: (value) => listing.apply({ is_active: value }),
  });
  const categoryFilter = selectField({
    id: "filter-category",
    label: "Categoría",
    options: [ALL_OPTION],
    onChange: (value) => listing.apply({ category_id: value }),
  });
  const typeFilter = selectField({
    id: "filter-type",
    label: "Tipo",
    options: [ALL_OPTION],
    onChange: (value) => listing.apply({ product_type_id: value }),
  });
  const searchForm = searchField({
    id: "filter-q",
    label: "Buscar",
    submitLabel: "Buscar",
    onSubmit: (value) => listing.apply({ q: value }),
  });

  async function loadSelectors() {
    const [categories, types] = await Promise.all([
      request("GET", "/categories", undefined, "categories"),
      request("GET", "/product-types", undefined, "product-types"),
    ]);
    if (!root.isConnected) {
      return;
    }
    if (categories.ok) {
      categoryFilter.select.append(...optionNodes(typeOptions(categories.body)));
    } else {
      showError(translateError(categories, "list").message);
    }
    if (types.ok) {
      productTypes = types.body;
      typeFilter.select.append(...optionNodes(typeOptions(types.body)));
      drawCreate();
    } else {
      showError(translateError(types, "list").message);
    }
  }

  root.append(
    el("h1", {}, [title()]),
    createSlot,
    panel,
    el("div", { class: "filters" }, [
      statusFilter.element,
      categoryFilter.element,
      typeFilter.element,
      searchForm,
    ]),
    listing.element,
  );
  drawCreate();
  loadSelectors();
  listing.load();
}
