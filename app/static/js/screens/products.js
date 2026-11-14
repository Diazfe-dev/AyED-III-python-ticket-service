import { activeLabel } from "../core/labels.js";
import { translateError } from "../core/messages.js";
import { openFormDialog } from "../dom/dialog.js";
import { createFields } from "../dom/form.js";
import { pageHeader, surface, toolbar } from "../dom/layout.js";
import { createListing, searchField, selectField } from "../dom/listing.js";
import { el } from "../dom/render.js";
import { productFields, typeOptions, writeBody } from "./product-form.js";

const COLUMNS = ["Nombre", "Tipo", "Estado", "Acciones"];
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

export function mount({ root, request, showError, showStatus }) {
  let listing = null;
  let header = null;
  let productTypes = [];
  const fallback = () => header.button;
  const clearMessages = () => {
    showError("");
    showStatus("");
  };

  async function reloadAfter(dialog) {
    await listing.reload();
    dialog.refocus();
  }

  async function runAction(promise) {
    clearMessages();
    const response = await promise;
    if (response.ok) {
      await listing.reload();
      return;
    }
    showError(translateError(response).message);
  }

  function openCreate(opener) {
    clearMessages();
    openFormDialog({
      parent: root,
      id: "product-create",
      title: "Nuevo producto",
      submitLabel: "Crear",
      opener,
      fallback,
      form: createFields("product-create", productFields(productTypes)),
      onSubmit: async (values, dialog) => {
        clearMessages();
        const response = await dialog.send(request("POST", "/products", writeBody(values)));
        if (response) {
          await reloadAfter(dialog);
        }
      },
    });
  }

  function openEdit(product, opener) {
    clearMessages();
    openFormDialog({
      parent: root,
      id: `product-edit-${product.id}`,
      title: "Editar producto",
      submitLabel: "Guardar",
      opener,
      fallback,
      form: createFields(`product-edit-${product.id}`, productFields(productTypes, product)),
      onSubmit: async (values, dialog) => {
        clearMessages();
        const response = await dialog.send(
          request("PATCH", `/products/${product.id}`, writeBody(values)),
        );
        if (response) {
          await reloadAfter(dialog);
        }
      },
    });
  }

  function actionButton(text, product, onClick) {
    const button = el("button", { type: "button", "aria-label": `${text} ${product.name}` }, [text]);
    button.addEventListener("click", () => onClick(button));
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
      activeLabel(product.is_active),
      el("div", { class: "row-actions" }, [
        actionButton("Editar", product, (button) => openEdit(product, button)),
        toggle,
      ]),
    ];
  }

  listing = createListing({
    request,
    showError,
    path: "/products",
    label: title(),
    columns: COLUMNS,
    row: productRow,
  });
  const statusFilter = selectField({
    id: "filter-state",
    label: "Estado",
    options: STATUS_OPTIONS,
    onChange: (value) => listing.apply({ is_active: value }),
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
    const types = await request("GET", "/product-types", undefined, "product-types");
    if (!root.isConnected) {
      return;
    }
    if (types.ok) {
      productTypes = types.body;
      typeFilter.select.append(...optionNodes(typeOptions(types.body)));
    } else {
      showError(translateError(types, "list").message);
    }
  }

  header = pageHeader({ title: title(), action: { label: "Nuevo producto", onClick: openCreate } });
  root.append(
    header.element,
    surface({
      toolbar: toolbar([statusFilter.element, typeFilter.element, searchForm]),
      table: listing.element,
    }),
  );
  loadSelectors();
  listing.load();
}
