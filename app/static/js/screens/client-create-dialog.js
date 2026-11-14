import { OWN_MESSAGES } from "../core/messages.js";
import { openFormDialog } from "../dom/dialog.js";
import { createFields } from "../dom/form.js";
import { accountFields } from "./account-form.js";

export function openClientDialog({ root, request, showError, showStatus, opener, fallback }) {
  showError("");
  showStatus("");
  return openFormDialog({
    parent: root,
    id: "client-create",
    title: "Nuevo cliente",
    submitLabel: "Crear",
    opener,
    fallback,
    form: createFields("client-create", accountFields(true, undefined, { withRole: false })),
    onSubmit: async (values, dialog) => {
      showError("");
      showStatus("");
      const body = {
        name: values.name,
        email: values.email,
        password: values.password,
        role: "Client",
      };
      if (values.preferred_channel !== "") {
        body.preferred_channel = values.preferred_channel;
      }
      if (await dialog.send(request("POST", "/users", body))) {
        showStatus(OWN_MESSAGES.clientCreated);
      }
    },
  });
}
