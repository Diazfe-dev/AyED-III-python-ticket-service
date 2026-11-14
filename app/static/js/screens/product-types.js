import { translateError } from "../core/messages.js";
import { confirmAction } from "../dom/confirm.js";
import { openFormDialog } from "../dom/dialog.js";
import { createFields } from "../dom/form.js";
import { pageHeader, surface, toolbar } from "../dom/layout.js";
import { createMemoryListing, searchField } from "../dom/listing.js";
import { el } from "../dom/render.js";

const CONFIRM_MESSAGE = "Esta acción no se puede deshacer. ¿Eliminar el tipo de producto";
const COLUMNS = ["Nombre", "Acciones"];
const LIST_KEY = "list";

export function title() {
  return "Tipos de producto";
}

function listPath(query) {
  return query === "" ? "/product-types" : `/product-types?q=${encodeURIComponent(query)}`;
}

function typeFields(type) {
  return [{ name: "name", label: "Nombre", value: type?.name ?? "" }];
}

export function mount({ root, request, showError, showStatus }) {
  let header = null;
  const fallback = () => header.button;
  const clearMessages = () => {
    showError("");
    showStatus("");
  };

  async function fetchItems(query) {
    const response = await request("GET", listPath(query), undefined, LIST_KEY);
    if (!response.ok) {
      return { ok: false, message: translateError(response).message };
    }
    return { ok: true, items: response.body };
  }

  const listing = createMemoryListing({
    fetchItems,
    showError,
    label: title(),
    columns: COLUMNS,
    row: typeRow,
  });

  async function reloadAfter(dialog) {
    await listing.reload();
    dialog.refocus();
  }

  function openCreate(opener) {
    clearMessages();
    openFormDialog({
      parent: root,
      id: "product-type-create",
      title: "Nuevo tipo de producto",
      submitLabel: "Crear",
      opener,
      fallback,
      form: createFields("product-type-create", typeFields()),
      onSubmit: async (values, dialog) => {
        clearMessages();
        const response = await dialog.send(request("POST", "/product-types", { name: values.name }));
        if (response) {
          await reloadAfter(dialog);
        }
      },
    });
  }

  function openEdit(type, opener) {
    clearMessages();
    openFormDialog({
      parent: root,
      id: `product-type-edit-${type.id}`,
      title: "Editar tipo de producto",
      submitLabel: "Guardar",
      opener,
      fallback,
      form: createFields(`product-type-edit-${type.id}`, typeFields(type)),
      onSubmit: async (values, dialog) => {
        clearMessages();
        const response = await dialog.send(
          request("PATCH", `/product-types/${type.id}`, { name: values.name }),
        );
        if (response) {
          await reloadAfter(dialog);
        }
      },
    });
  }

  async function removeType(type) {
    clearMessages();
    const confirmed = await confirmAction(root, `${CONFIRM_MESSAGE} «${type.name}»?`);
    if (!confirmed) {
      return;
    }
    const response = await request("DELETE", `/product-types/${type.id}`);
    if (response.ok) {
      await listing.reload();
      return;
    }
    showError(translateError(response, "form").message ?? translateError(response).message);
  }

  function typeRow(type) {
    const edit = el("button", { type: "button", "aria-label": `Editar ${type.name}` }, ["Editar"]);
    const remove = el("button", { type: "button", "aria-label": `Eliminar ${type.name}` }, [
      "Eliminar",
    ]);
    edit.addEventListener("click", () => openEdit(type, edit));
    remove.addEventListener("click", () => removeType(type));
    return [type.name, el("div", { class: "row-actions" }, [edit, remove])];
  }

  const searchForm = searchField({
    id: "product-types-search",
    label: "Buscar",
    submitLabel: "Buscar",
    onSubmit: (value) => {
      clearMessages();
      listing.apply({ q: value.trim() });
    },
  });
  header = pageHeader({
    title: title(),
    action: { label: "Nuevo tipo de producto", onClick: openCreate },
  });
  root.append(header.element, surface({ toolbar: toolbar([searchForm]), table: listing.element }));
  listing.load();
}
