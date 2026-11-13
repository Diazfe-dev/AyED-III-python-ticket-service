import { el } from "./render.js";

const CONFIRM_LABEL = "Confirmar";
const CANCEL_LABEL = "Cancelar";

export function confirmAction(parent, message) {
  return new Promise((resolve) => {
    const messageId = "confirm-message";
    const confirmButton = el("button", { type: "button" }, [CONFIRM_LABEL]);
    const cancelButton = el("button", { type: "button" }, [CANCEL_LABEL]);
    const dialog = el("dialog", { "aria-labelledby": messageId }, [
      el("p", { id: messageId }, [message]),
      el("div", { class: "dialog-actions" }, [confirmButton, cancelButton]),
    ]);

    function settle(confirmed) {
      dialog.close();
      dialog.remove();
      resolve(confirmed);
    }

    confirmButton.addEventListener("click", () => settle(true));
    cancelButton.addEventListener("click", () => settle(false));
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      settle(false);
    });

    parent.append(dialog);
    dialog.showModal();
    cancelButton.focus();
  });
}
