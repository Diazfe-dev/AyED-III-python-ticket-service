import { confirmationMismatch } from "../core/forms.js";
import { activeLabel, roleLabel } from "../core/labels.js";
import { OWN_MESSAGES, translateError } from "../core/messages.js";
import { createListing, searchField, selectField } from "../dom/listing.js";
import { clear, el } from "../dom/render.js";

const COLUMNS = ["Nombre", "Email", "Rol", "Estado", "Acciones"];
const MISMATCH_MESSAGE = "La nueva contraseña y su confirmación no coinciden.";
const ROLE_OPTIONS = [
  { value: "Admin", label: roleLabel("Admin") },
  { value: "Representative", label: roleLabel("Representative") },
  { value: "Client", label: roleLabel("Client") },
];
const CHANNEL_OPTIONS = [
  { value: "mail", label: "Correo" },
  { value: "whatsapp", label: "WhatsApp" },
];
const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "true", label: activeLabel(true) },
  { value: "false", label: activeLabel(false) },
];

export function title() {
  return "Usuarios";
}

function optionList(options, placeholder) {
  const placeholders = placeholder === undefined ? [] : [{ value: "", label: placeholder }];
  return [...placeholders, ...options].map((option) =>
    el("option", { value: option.value }, [option.label]),
  );
}

function buildField(formId, field) {
  const id = `${formId}-${field.name}`;
  const control =
    field.options === undefined
      ? el("input", {
          type: field.type ?? "text",
          id,
          name: field.name,
          autocomplete: field.autocomplete ?? "off",
          value: field.value ?? "",
        })
      : el("select", { id, name: field.name }, optionList(field.options, field.placeholder));
  if (field.options !== undefined && field.value !== undefined) {
    control.value = field.value;
  }
  const mark = el("p", { id: `${id}-mark`, class: "field-mark" });
  mark.hidden = true;
  return {
    field,
    control,
    mark,
    element: el("div", { class: "field" }, [el("label", { for: id }, [field.label]), control, mark]),
  };
}

function buildForm({ id, label, fields, submitLabel, extraButtons = [], onSubmit }) {
  const built = fields.map((field) => buildField(id, field));
  const message = el("p", { class: "message-error", role: "alert" });
  message.hidden = true;
  const submit = el("button", { type: "submit" }, [submitLabel]);
  const element = el("form", { "aria-label": label, novalidate: true }, [
    ...built.map((entry) => entry.element),
    message,
    submit,
    ...extraButtons,
  ]);

  function values() {
    return Object.fromEntries(built.map((entry) => [entry.field.name, entry.control.value]));
  }

  function clearPasswords() {
    for (const entry of built) {
      if (entry.field.type === "password") {
        entry.control.value = "";
      }
    }
  }

  function setFeedback({ message: text = null, marks = {} } = {}) {
    message.textContent = text ?? "";
    message.hidden = text === null;
    for (const entry of built) {
      const mark = marks[entry.field.name] ?? null;
      entry.mark.textContent = mark ?? "";
      entry.mark.hidden = mark === null;
      if (mark === null) {
        entry.control.removeAttribute("aria-invalid");
        entry.control.removeAttribute("aria-describedby");
      } else {
        entry.control.setAttribute("aria-invalid", "true");
        entry.control.setAttribute("aria-describedby", entry.mark.id);
      }
    }
  }

  function reset() {
    for (const entry of built) {
      entry.control.value = entry.field.value ?? "";
    }
    setFeedback();
  }

  element.addEventListener("submit", (event) => {
    event.preventDefault();
    onSubmit(values());
  });
  return { element, values, clearPasswords, setFeedback, reset };
}

function accountFields(prefix, user) {
  return [
    { name: "name", label: "Nombre", value: user?.name ?? "" },
    { name: "email", label: "Email", type: "email", value: user?.email ?? "" },
    ...(prefix === "create"
      ? [{ name: "role", label: "Rol", options: ROLE_OPTIONS, placeholder: "Seleccione un rol" }]
      : []),
    ...(prefix === "create"
      ? [{ name: "password", label: "Contraseña", type: "password", autocomplete: "new-password" }]
      : []),
    {
      name: "preferred_channel",
      label: "Canal",
      options: CHANNEL_OPTIONS,
      placeholder: "Sin especificar",
      value: user?.preferred_channel ?? "",
    },
  ];
}

export function mount({ root, request, showError, showStatus }) {
  const panel = el("div", { class: "user-panel" });
  let listing = null;

  function closePanel() {
    clear(panel);
  }

  async function runAction(promise) {
    showError("");
    showStatus("");
    const response = await promise;
    if (response.ok) {
      await listing.reload();
      return true;
    }
    showError(translateError(response).message);
    return false;
  }

  const createForm = buildForm({
    id: "user-create",
    label: "Nueva cuenta",
    fields: accountFields("create"),
    submitLabel: "Crear",
    onSubmit: async (values) => {
      showError("");
      showStatus("");
      const body = {
        name: values.name,
        email: values.email,
        role: values.role,
        password: values.password,
      };
      if (values.preferred_channel !== "") {
        body.preferred_channel = values.preferred_channel;
      }
      const response = await request("POST", "/users", body);
      createForm.clearPasswords();
      if (response.ok) {
        createForm.reset();
        showStatus(OWN_MESSAGES.userCreated);
        await listing.reload();
        return;
      }
      const error = translateError(response, "form");
      createForm.setFeedback({ message: error.message, marks: error.fields ?? {} });
    },
  });

  function openEdit(user) {
    const cancel = el("button", { type: "button" }, ["Cancelar"]);
    cancel.addEventListener("click", closePanel);
    const form = buildForm({
      id: `user-edit-${user.id}`,
      label: "Editar cuenta",
      fields: accountFields("edit", user),
      submitLabel: "Guardar",
      extraButtons: [cancel],
      onSubmit: async (values) => {
        showError("");
        showStatus("");
        const response = await request("PATCH", `/users/${user.id}`, {
          name: values.name,
          email: values.email,
          preferred_channel: values.preferred_channel,
        });
        if (response.ok) {
          closePanel();
          await listing.reload();
          return;
        }
        const error = translateError(response, "form");
        form.setFeedback({ message: error.message, marks: error.fields ?? {} });
      },
    });
    clear(panel);
    panel.append(form.element);
  }

  function openReset(user) {
    const cancel = el("button", { type: "button" }, ["Cancelar"]);
    cancel.addEventListener("click", closePanel);
    const form = buildForm({
      id: `user-reset-${user.id}`,
      label: "Restablecer contraseña",
      fields: [
        { name: "new_password", label: "Nueva contraseña", type: "password", autocomplete: "new-password" },
        {
          name: "confirmation",
          label: "Confirmar nueva contraseña",
          type: "password",
          autocomplete: "new-password",
        },
      ],
      submitLabel: "Restablecer",
      extraButtons: [cancel],
      onSubmit: async (values) => {
        showError("");
        showStatus("");
        if (confirmationMismatch(values.new_password, values.confirmation)) {
          form.clearPasswords();
          form.setFeedback({ marks: { confirmation: MISMATCH_MESSAGE } });
          return;
        }
        const response = await request("POST", `/users/${user.id}/password`, {
          new_password: values.new_password,
        });
        form.clearPasswords();
        if (response.ok) {
          closePanel();
          showStatus(OWN_MESSAGES.passwordUpdated);
          return;
        }
        const error = translateError(response, "form");
        form.setFeedback({ message: error.message, marks: error.fields ?? {} });
      },
    });
    clear(panel);
    panel.append(form.element);
  }

  function actionButton(text, user, onClick) {
    const button = el("button", { type: "button", "aria-label": `${text} ${user.name}` }, [text]);
    button.addEventListener("click", onClick);
    return button;
  }

  function userRow(user) {
    const toggle = user.is_active
      ? actionButton("Dar de baja", user, () =>
          runAction(request("POST", `/users/${user.id}/deactivate`)),
        )
      : actionButton("Reactivar", user, () =>
          runAction(request("POST", `/users/${user.id}/activate`)),
        );
    return [
      user.name,
      user.email,
      roleLabel(user.role),
      activeLabel(user.is_active),
      el("div", { class: "row-actions" }, [
        actionButton("Editar", user, () => openEdit(user)),
        toggle,
        actionButton("Restablecer contraseña", user, () => openReset(user)),
      ]),
    ];
  }

  listing = createListing({
    request,
    showError,
    path: "/users",
    columns: COLUMNS,
    row: userRow,
  });
  const statusFilter = selectField({
    id: "filter-state",
    label: "Estado",
    options: STATUS_OPTIONS,
    onChange: (value) => listing.apply({ is_active: value }),
  });
  const searchForm = searchField({
    id: "filter-q",
    label: "Buscar",
    submitLabel: "Buscar",
    onSubmit: (value) => listing.apply({ q: value }),
  });
  root.append(
    el("h1", {}, [title()]),
    createForm.element,
    panel,
    el("div", { class: "filters" }, [statusFilter.element, searchForm]),
    listing.element,
  );
  listing.load();
}
