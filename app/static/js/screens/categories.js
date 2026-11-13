import { translateError } from "../core/messages.js";
import { confirmAction } from "../dom/confirm.js";
import { openFormDialog } from "../dom/dialog.js";
import { createFields } from "../dom/form.js";
import { pageHeader, surface, toolbar } from "../dom/layout.js";
import { createMemoryListing, searchField } from "../dom/listing.js";
import { el } from "../dom/render.js";

const CONFIRM_MESSAGE = "Esta acción no se puede deshacer. ¿Eliminar la categoría";
const COLUMNS = ["Nombre", "Acciones"];
const LIST_KEY = "list";

export function title() {
  return "Categorías";
}

function listPath(query) {
  return query === "" ? "/categories" : `/categories?q=${encodeURIComponent(query)}`;
}

const nameFields = (name = "") => [{ name: "name", label: "Nombre", value: name }];

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
    row: categoryRow,
  });

  async function reloadAfter(dialog) {
    await listing.reload();
    dialog.refocus();
  }

  function openCreate(opener) {
    clearMessages();
    openFormDialog({
      parent: root,
      id: "category-create",
      title: "Nueva categoría",
      submitLabel: "Crear",
      opener,
      fallback,
      form: createFields("category-create", nameFields()),
      onSubmit: async (values, dialog) => {
        clearMessages();
        const response = await dialog.send(request("POST", "/categories", { name: values.name }));
        if (response) {
          await reloadAfter(dialog);
        }
      },
    });
  }

  function openEdit(category, opener) {
    clearMessages();
    openFormDialog({
      parent: root,
      id: `category-edit-${category.id}`,
      title: "Editar categoría",
      submitLabel: "Guardar",
      opener,
      fallback,
      form: createFields(`category-edit-${category.id}`, nameFields(category.name)),
      onSubmit: async (values, dialog) => {
        clearMessages();
        const response = await dialog.send(
          request("PATCH", `/categories/${category.id}`, { name: values.name }),
        );
        if (response) {
          await reloadAfter(dialog);
        }
      },
    });
  }

  async function removeCategory(category) {
    clearMessages();
    const confirmed = await confirmAction(root, `${CONFIRM_MESSAGE} «${category.name}»?`);
    if (!confirmed) {
      return;
    }
    const response = await request("DELETE", `/categories/${category.id}`);
    if (response.ok) {
      await listing.reload();
      return;
    }
    showError(translateError(response, "form").message ?? translateError(response).message);
  }

  function categoryRow(category) {
    const edit = el("button", { type: "button", "aria-label": `Editar ${category.name}` }, ["Editar"]);
    const remove = el("button", { type: "button", "aria-label": `Eliminar ${category.name}` }, [
      "Eliminar",
    ]);
    edit.addEventListener("click", () => openEdit(category, edit));
    remove.addEventListener("click", () => removeCategory(category));
    return [category.name, el("div", { class: "row-actions" }, [edit, remove])];
  }

  const searchForm = searchField({
    id: "categories-search",
    label: "Buscar",
    submitLabel: "Buscar",
    onSubmit: (value) => {
      clearMessages();
      listing.apply({ q: value.trim() });
    },
  });
  header = pageHeader({ title: title(), action: { label: "Nueva categoría", onClick: openCreate } });
  root.append(header.element, surface({ toolbar: toolbar([searchForm]), table: listing.element }));
  listing.load();
}
