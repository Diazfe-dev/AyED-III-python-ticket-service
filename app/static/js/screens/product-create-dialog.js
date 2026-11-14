import { translateError } from "../core/messages.js";
import { openFormDialog } from "../dom/dialog.js";
import { createFields } from "../dom/form.js";
import { productFields } from "./product-form.js";

export async function openProductDialog({ root, request, showError, opener, fallback }) {
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
    onSubmit: async () => {},
  });
}
