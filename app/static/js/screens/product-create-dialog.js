import { OWN_MESSAGES, translateError } from "../core/messages.js";
import { openFormDialog } from "../dom/dialog.js";
import { createFields } from "../dom/form.js";
import { productFields, writeBody } from "./product-form.js";

export async function openProductDialog({
  root,
  request,
  showError,
  showStatus,
  opener,
  fallback,
}) {
  showError("");
  showStatus("");
  const types = await request("GET", "/product-types", undefined, "product-types");
  if (!root.isConnected) {
    return null;
  }
  if (!types.ok) {
    showError(translateError(types, "list").message);
    return null;
  }
  return openFormDialog({
    parent: root,
    id: "product-create",
    title: "Nuevo producto",
    submitLabel: "Crear",
    opener,
    fallback,
    form: createFields("product-create", productFields(types.body)),
    onSubmit: async (values, dialog) => {
      showError("");
      showStatus("");
      if (await dialog.send(request("POST", "/products", writeBody(values)))) {
        showStatus(OWN_MESSAGES.productCreated);
      }
    },
  });
}
