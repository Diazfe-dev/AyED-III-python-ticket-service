import { confirmationMismatch } from "../core/forms.js";
import { activeLabel, roleLabel } from "../core/labels.js";
import { OWN_MESSAGES, translateError } from "../core/messages.js";
import { openFormDialog } from "../dom/dialog.js";
import { createFields } from "../dom/form.js";
import { pageHeader, surface, toolbar } from "../dom/layout.js";
import { createListing, searchField, selectField } from "../dom/listing.js";
import { el } from "../dom/render.js";

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

function accountFields(creating, user) {
  return [
    { name: "name", label: "Nombre", value: user?.name ?? "" },
    { name: "email", label: "Email", type: "email", value: user?.email ?? "" },
    ...(creating
      ? [
          { name: "role", label: "Rol", options: ROLE_OPTIONS, placeholder: "Seleccione un rol" },
          { name: "password", label: "Contraseña", type: "password", autocomplete: "new-password" },
        ]
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

const RESET_FIELDS = [
  { name: "new_password", label: "Nueva contraseña", type: "password", autocomplete: "new-password" },
  {
    name: "confirmation",
    label: "Confirmar nueva contraseña",
    type: "password",
    autocomplete: "new-password",
  },
];

export function mount({ root, request, showError, showStatus }) {
  let listing = null;
  let header = null;

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
      id: "user-create",
      title: "Nuevo usuario",
      submitLabel: "Crear",
      opener,
      fallback,
      form: createFields("user-create", accountFields(true)),
      onSubmit: async (values, dialog) => {
        clearMessages();
        const body = {
          name: values.name,
          email: values.email,
          role: values.role,
          password: values.password,
        };
        if (values.preferred_channel !== "") {
          body.preferred_channel = values.preferred_channel;
        }
        const response = await dialog.send(request("POST", "/users", body));
        if (response) {
          showStatus(OWN_MESSAGES.userCreated);
          await reloadAfter(dialog);
        }
      },
    });
  }

  function openEdit(user, opener) {
    clearMessages();
    openFormDialog({
      parent: root,
      id: `user-edit-${user.id}`,
      title: "Editar usuario",
      submitLabel: "Guardar",
      opener,
      fallback,
      form: createFields(`user-edit-${user.id}`, accountFields(false, user)),
      onSubmit: async (values, dialog) => {
        clearMessages();
        const response = await dialog.send(
          request("PATCH", `/users/${user.id}`, {
            name: values.name,
            email: values.email,
            preferred_channel: values.preferred_channel,
          }),
        );
        if (response) {
          await reloadAfter(dialog);
        }
      },
    });
  }

  function openReset(user, opener) {
    clearMessages();
    const form = createFields(`user-reset-${user.id}`, RESET_FIELDS);
    openFormDialog({
      parent: root,
      id: `user-reset-${user.id}`,
      title: "Restablecer contraseña",
      submitLabel: "Restablecer",
      opener,
      fallback,
      form,
      onSubmit: async (values, dialog) => {
        clearMessages();
        if (confirmationMismatch(values.new_password, values.confirmation)) {
          form.clearPasswords();
          dialog.setFeedback({ marks: { confirmation: MISMATCH_MESSAGE } });
          return;
        }
        const response = await dialog.send(
          request("POST", `/users/${user.id}/password`, { new_password: values.new_password }),
        );
        if (response) {
          showStatus(OWN_MESSAGES.passwordReset);
        }
      },
    });
  }

  function actionButton(text, user, onClick) {
    const button = el("button", { type: "button", "aria-label": `${text} ${user.name}` }, [text]);
    button.addEventListener("click", () => onClick(button));
    return button;
  }

  function userRow(user) {
    const toggle = user.is_active
      ? actionButton("Dar de baja", user, () => runAction(request("POST", `/users/${user.id}/deactivate`)))
      : actionButton("Reactivar", user, () => runAction(request("POST", `/users/${user.id}/activate`)));
    return [
      user.name,
      user.email,
      roleLabel(user.role),
      activeLabel(user.is_active),
      el("div", { class: "row-actions" }, [
        actionButton("Editar", user, (button) => openEdit(user, button)),
        toggle,
        actionButton("Restablecer contraseña", user, (button) => openReset(user, button)),
      ]),
    ];
  }

  listing = createListing({
    request,
    showError,
    path: "/users",
    label: title(),
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
  header = pageHeader({
    title: title(),
    action: { label: "Nuevo usuario", onClick: openCreate },
  });
  root.append(
    header.element,
    surface({ toolbar: toolbar([statusFilter.element, searchForm]), table: listing.element }),
  );
  listing.load();
}
