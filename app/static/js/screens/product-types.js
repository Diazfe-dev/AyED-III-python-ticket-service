import { translateError } from "../core/messages.js";
import { confirmAction } from "../dom/confirm.js";
import { clear, el, emptyResults, loadingIndicator } from "../dom/render.js";

const CONFIRM_MESSAGE = "Esta acción no se puede deshacer. ¿Eliminar el tipo de producto";

export function title() {
  return "Tipos de producto";
}

function listPath(query) {
  return query === "" ? "/product-types" : `/product-types?q=${encodeURIComponent(query)}`;
}

function categorySelect(categories, selectedId, attrs) {
  const select = el("select", { name: "category_id", required: true, ...attrs });
  for (const category of categories) {
    select.append(el("option", { value: String(category.id) }, [category.name]));
  }
  if (selectedId !== null) {
    select.value = String(selectedId);
  }
  return select;
}

export function mount({ root, request, showError, showStatus }) {
  let query = "";
  let editingId = null;
  let categories = [];
  let items = [];

  const searchInput = el("input", {
    type: "search",
    id: "product-types-search",
    name: "q",
    autocomplete: "off",
  });
  const searchForm = el(
    "form",
    { role: "search", "aria-label": "Buscar tipos de producto", novalidate: true },
    [
      el("label", { for: "product-types-search" }, ["Buscar"]),
      searchInput,
      el("button", { type: "submit" }, ["Buscar"]),
    ],
  );

  const createForm = el("form", { "aria-label": "Nuevo tipo de producto", novalidate: true });
  const list = el("div", { class: "product-types-list" });
  root.append(el("h1", {}, [title()]), searchForm, createForm, list);

  function drawCreate(feedback = {}) {
    clear(createForm);
    const mark = feedback.marks?.name ?? null;
    const nameInput = el("input", {
      type: "text",
      id: "product-type-new-name",
      name: "name",
      required: true,
      autocomplete: "off",
    });
    if (mark) {
      nameInput.setAttribute("aria-invalid", "true");
      nameInput.setAttribute("aria-describedby", "product-type-new-name-mark");
    }
    createForm.append(
      el("div", { class: "field" }, [
        el("label", { for: "product-type-new-name" }, ["Nombre"]),
        nameInput,
      ]),
      el("div", { class: "field" }, [
        el("label", { for: "product-type-new-category" }, ["Categoría"]),
        categorySelect(categories, null, { id: "product-type-new-category" }),
      ]),
    );
    if (mark) {
      createForm.append(el("p", { id: "product-type-new-name-mark", class: "field-mark" }, [mark]));
    }
    if (feedback.message) {
      createForm.append(el("p", { class: "message-error", role: "alert" }, [feedback.message]));
    }
    createForm.append(el("button", { type: "submit" }, ["Crear"]));
  }

  function viewRow(type) {
    const edit = el("button", { type: "button", "aria-label": `Editar ${type.name}` }, ["Editar"]);
    const remove = el("button", { type: "button", "aria-label": `Eliminar ${type.name}` }, [
      "Eliminar",
    ]);
    edit.addEventListener("click", () => {
      editingId = type.id;
      drawList();
    });
    remove.addEventListener("click", () => removeType(type));
    return el("li", {}, [
      el("span", {}, [type.name]),
      el("div", { class: "row-actions" }, [edit, remove]),
    ]);
  }

  function editRow(type) {
    const form = el("form", { "aria-label": `Editar ${type.name}`, novalidate: true });
    const input = el("input", {
      type: "text",
      name: "name",
      value: type.name,
      required: true,
      autocomplete: "off",
      "aria-label": `Nuevo nombre de ${type.name}`,
    });
    const select = categorySelect(categories, type.category_id, {
      "aria-label": `Nueva categoría de ${type.name}`,
    });
    const cancel = el("button", { type: "button" }, ["Cancelar"]);
    form.append(input, select, el("button", { type: "submit" }, ["Guardar"]), cancel);
    cancel.addEventListener("click", () => {
      editingId = null;
      drawList();
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      saveEdit(type, { name: input.value, category_id: Number(select.value) });
    });
    return el("li", {}, [form]);
  }

  function drawList() {
    clear(list);
    if (items.length === 0) {
      list.append(emptyResults());
      return;
    }
    for (const category of categories) {
      const types = items.filter((type) => type.category_id === category.id);
      if (types.length === 0) {
        continue;
      }
      const rows = types.map((type) => (type.id === editingId ? editRow(type) : viewRow(type)));
      list.append(
        el("fieldset", { class: "category-group" }, [
          el("legend", {}, [category.name]),
          el("ul", {}, rows),
        ]),
      );
    }
  }

  async function load() {
    clear(list);
    list.append(loadingIndicator());
    const [typesResponse, categoriesResponse] = await Promise.all([
      request("GET", listPath(query)),
      request("GET", "/categories"),
    ]);
    const failed = [typesResponse, categoriesResponse].find((response) => !response.ok);
    if (failed) {
      clear(list);
      showError(translateError(failed).message);
      return;
    }
    items = typesResponse.body;
    categories = categoriesResponse.body;
    if (createForm.elements.category_id?.options.length !== categories.length) {
      drawCreate();
    }
    drawList();
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

  async function saveEdit(type, body) {
    showError("");
    showStatus("");
    const response = await request("PATCH", `/product-types/${type.id}`, body);
    await afterWrite(response, (error) => showError(error.message));
  }

  async function removeType(type) {
    showError("");
    showStatus("");
    const confirmed = await confirmAction(root, `${CONFIRM_MESSAGE} «${type.name}»?`);
    if (!confirmed) {
      return;
    }
    const response = await request("DELETE", `/product-types/${type.id}`);
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
    const body = {
      name: createForm.elements.name.value,
      category_id: Number(createForm.elements.category_id.value),
    };
    const response = await request("POST", "/product-types", body);
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
