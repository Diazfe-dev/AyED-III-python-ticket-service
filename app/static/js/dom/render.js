const ALLOWED_ATTRIBUTES = new Set([
  "class",
  "id",
  "href",
  "type",
  "for",
  "name",
  "value",
  "role",
  "disabled",
  "required",
  "autocomplete",
  "placeholder",
  "rows",
  "colspan",
  "scope",
  "tabindex",
  "novalidate",
  "checked",
  "selected",
  "min",
  "max",
  "maxlength",
]);

const TITLE_SUFFIX = "Mesa de ayuda";
const LOADING_TEXT = "Cargando…";
const EMPTY_TEXT = "No hay resultados";

function isAllowed(name) {
  return ALLOWED_ATTRIBUTES.has(name) || name.startsWith("aria-");
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (!isAllowed(name)) {
      throw new Error(`Attribute not allowed: ${name}`);
    }
    if (value !== false && value !== null && value !== undefined) {
      node.setAttribute(name, value === true ? "" : String(value));
    }
  }
  for (const child of children) {
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

export function clear(node) {
  node.replaceChildren();
}

export function setTitle(screenTitle) {
  document.title = `${screenTitle} · ${TITLE_SUFFIX}`;
}

export function loadingIndicator() {
  return el("p", { class: "loading" }, [LOADING_TEXT]);
}

export function emptyResults() {
  return el("p", { class: "empty" }, [EMPTY_TEXT]);
}

function region(id) {
  return document.getElementById(id);
}

export function showError(message) {
  region("alert").textContent = message;
}

export function showStatus(message) {
  region("status").textContent = message;
}

export function clearMessages() {
  showError("");
  showStatus("");
}
