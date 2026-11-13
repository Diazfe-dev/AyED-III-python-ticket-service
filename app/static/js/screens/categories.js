import { translateError } from "../core/messages.js";
import { confirmAction } from "../dom/confirm.js";
import { clear, el, emptyResults, loadingIndicator } from "../dom/render.js";

const CONFIRM_MESSAGE = "Esta acción no se puede deshacer. ¿Eliminar la categoría";

export function title() {
  return "Categorías";
}

function listPath(query) {
  return query === "" ? "/categories" : `/categories?q=${encodeURIComponent(query)}`;
}

function nameField(id, label, value = "") {
  return [
    el("label", { for: id }, [label]),
    el("input", { type: "text", id, name: "name", value, required: true, autocomplete: "off" }),
  ];
}

export function mount({ root, request, showError, showStatus }) {
  let query = "";
  let editingId = null;

  const searchInput = el("input", { type: "search", id: "categories-search", name: "q", autocomplete: "off" });
  const searchForm = el("form", { role: "search", "aria-label": "Buscar categorías", novalidate: true }, [
    el("label", { for: "categories-search" }, ["Buscar"]),
    searchInput,
    el("button", { type: "submit" }, ["Buscar"]),
  ]);

  const createForm = el("form", { "aria-label": "Nueva categoría", novalidate: true });
  const list = el("div", { class: "categories-list" });
  root.append(el("h1", {}, [title()]), searchForm, createForm, list);

  function drawCreate(feedback = {}) {
    clear(createForm);
    const mark = feedback.marks?.name ?? null;
    const [label, input] = nameField("category-new-name", "Nombre");
    if (mark) {
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("aria-describedby", "category-new-name-mark");
    }
    createForm.append(el("div", { class: "field" }, [label, input]));
    if (mark) {
      createForm.append(el("p", { id: "category-new-name-mark", class: "field-mark" }, [mark]));
    }
    if (feedback.message) {
      createForm.append(el("p", { class: "message-error", role: "alert" }, [feedback.message]));
    }
    createForm.append(el("button", { type: "submit" }, ["Crear"]));
  }

  function viewRow(category) {
    const actions = el("div", { class: "row-actions" }, [
      el("button", { type: "button", "aria-label": `Editar ${category.name}` }, ["Editar"]),
      el("button", { type: "button", "aria-label": `Eliminar ${category.name}` }, ["Eliminar"]),
    ]);
    const [edit, remove] = actions.children;
    edit.addEventListener("click", () => {
      editingId = category.id;
      drawList(items);
    });
    remove.addEventListener("click", () => removeCategory(category));
    return el("li", {}, [el("span", {}, [category.name]), actions]);
  }

  function editRow(category) {
    const id = `category-edit-${category.id}`;
    const form = el("form", { "aria-label": `Editar ${category.name}`, novalidate: true });
    const input = el("input", {
      type: "text",
      id,
      name: "name",
      value: category.name,
      required: true,
      autocomplete: "off",
      "aria-label": `Nuevo nombre de ${category.name}`,
    });
    const cancel = el("button", { type: "button" }, ["Cancelar"]);
    form.append(input, el("button", { type: "submit" }, ["Guardar"]), cancel);
    cancel.addEventListener("click", () => {
      editingId = null;
      drawList(items);
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      saveEdit(category, input.value);
    });
    return el("li", {}, [form]);
  }

  let items = [];

  function drawList(categories) {
    items = categories;
    clear(list);
    if (categories.length === 0) {
      list.append(emptyResults());
      return;
    }
    const rows = categories.map((category) =>
      category.id === editingId ? editRow(category) : viewRow(category),
    );
    list.append(el("ul", {}, rows));
  }

  async function load() {
    clear(list);
    list.append(loadingIndicator());
    const response = await request("GET", listPath(query));
    if (!response.ok) {
      clear(list);
      showError(translateError(response).message);
      return;
    }
    drawList(response.body);
  }

  async function afterWrite(response, onFailure) {
    if (response.ok) {
      editingId = null;
      await load();
      return true;
    }
    onFailure(translateError(response, "form"));
    return false;
  }

  async function saveEdit(category, name) {
    showError("");
    showStatus("");
    const response = await request("PATCH", `/categories/${category.id}`, { name });
    await afterWrite(response, (error) => showError(error.message ?? translateError(response).message));
  }

  async function removeCategory(category) {
    showError("");
    showStatus("");
    const confirmed = await confirmAction(root, `${CONFIRM_MESSAGE} «${category.name}»?`);
    if (!confirmed) {
      return;
    }
    const response = await request("DELETE", `/categories/${category.id}`);
    await afterWrite(response, (error) => showError(error.message));
  }

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    showError("");
    showStatus("");
    query = searchInput.value.trim();
    load();
  });

  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    showStatus("");
    const name = createForm.elements.name.value;
    const response = await request("POST", "/categories", { name });
    const created = await afterWrite(response, (error) =>
      drawCreate({ message: error.message, marks: error.fields ?? {} }),
    );
    if (created) {
      drawCreate();
    }
  });

  drawCreate();
  load();
}
