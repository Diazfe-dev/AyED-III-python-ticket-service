import { openFormDialog } from "../dom/dialog.js";
import { createFields } from "../dom/form.js";
import { accountFields } from "./account-form.js";

export function openClientDialog({ root, opener, fallback }) {
  return openFormDialog({
    parent: root,
    id: "client-create",
    title: "Nuevo cliente",
    submitLabel: "Crear",
    opener,
    fallback,
    form: createFields("client-create", accountFields(true, undefined, { withRole: false })),
    onSubmit: async () => {},
  });
}
