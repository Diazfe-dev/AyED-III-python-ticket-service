import { confirmationMismatch } from "../core/forms.js";
import { OWN_MESSAGES, translateError } from "../core/messages.js";
import { clear, el } from "../dom/render.js";

const MISMATCH_MESSAGE = "La nueva contraseña y su confirmación no coinciden.";
const FIELDS = [
  { name: "current_password", id: "account-current", label: "Contraseña actual", autocomplete: "current-password" },
  { name: "new_password", id: "account-new", label: "Nueva contraseña", autocomplete: "new-password" },
  { name: "confirmation", id: "account-confirmation", label: "Confirmar nueva contraseña", autocomplete: "new-password" },
];

export function title() {
  return "Mi cuenta";
}

function fieldRow(field, mark) {
  const input = el("input", {
    type: "password",
    id: field.id,
    name: field.name,
    autocomplete: field.autocomplete,
    required: true,
    "aria-describedby": mark ? `${field.id}-mark` : false,
    "aria-invalid": mark ? "true" : false,
  });
  const children = [el("label", { for: field.id }, [field.label]), input];
  if (mark) {
    children.push(el("p", { id: `${field.id}-mark`, class: "field-mark" }, [mark]));
  }
  return el("div", { class: "field" }, children);
}

export function mount({ root, request, showStatus }) {
  const form = el("form", { "aria-label": "Cambiar contraseña", novalidate: true });
  root.append(el("h1", {}, [title()]), form);

  function draw(feedback = {}) {
    const marks = feedback.marks ?? {};
    clear(form);
    for (const field of FIELDS) {
      form.append(fieldRow(field, marks[field.name] ?? null));
    }
    if (feedback.message) {
      form.append(el("p", { class: "message-error", role: "alert" }, [feedback.message]));
    }
    form.append(el("button", { type: "submit" }, ["Cambiar contraseña"]));
  }

  function read() {
    const values = {};
    for (const field of FIELDS) {
      values[field.name] = form.elements[field.name].value;
    }
    return values;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showStatus("");
    const values = read();
    if (confirmationMismatch(values.new_password, values.confirmation)) {
      draw({ marks: { confirmation: MISMATCH_MESSAGE } });
      return;
    }
    const pending = request("POST", "/me/password", {
      current_password: values.current_password,
      new_password: values.new_password,
    });
    draw();
    const response = await pending;
    if (response.ok) {
      showStatus(OWN_MESSAGES.passwordUpdated);
      return;
    }
    const error = translateError(response, "form");
    draw({ message: error.message, marks: error.fields ?? {} });
  });

  draw();
}
