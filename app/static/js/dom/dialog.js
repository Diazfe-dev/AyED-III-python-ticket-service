import { translateError } from "../core/messages.js";
import { el } from "./render.js";

const CANCEL_LABEL = "Cancelar";
const ALL_CONTROLS = "button, input, select, textarea";
const FIRST_FIELD = "input, select, textarea";

const controllers = new WeakMap();

function usable(node) {
  return node !== null && node !== undefined && node.isConnected && !node.disabled;
}

function focusNode(node) {
  if (node.tagName === "H1") {
    node.setAttribute("tabindex", "-1");
  }
  node.focus();
}

export function closeDialogs(container) {
  for (const dialog of container.querySelectorAll("dialog")) {
    controllers.get(dialog)?.close({ reason: "session", restoreFocus: false });
  }
}

export function openFormDialog({
  parent,
  id,
  title,
  form,
  submitLabel,
  opener = null,
  fallback = () => null,
  onSubmit,
  onCancel = () => {},
}) {
  const titleId = `${id}-title`;
  const message = el("p", { class: "message-error", role: "alert" });
  message.hidden = true;
  const cancel = el("button", { type: "button", class: "text-button" }, [CANCEL_LABEL]);
  const submit = el("button", { type: "submit" }, [submitLabel]);
  const element = el("form", { novalidate: true, class: "dialog-form" }, [
    el("h2", { id: titleId }, [title]),
    ...form.elements,
    message,
    el("div", { class: "form-actions" }, [cancel, submit]),
  ]);
  const dialog = el("dialog", { "aria-labelledby": titleId, class: "form-dialog" }, [element]);
  let closed = false;
  let pending = false;

  function refocus({ force = false } = {}) {
    const active = document.activeElement;
    if (!force && active !== null && active !== document.body && active.isConnected) {
      return;
    }
    const target = [opener, fallback(), parent.querySelector("h1")].find(usable);
    if (target !== undefined) {
      focusNode(target);
    }
  }

  function finish({ reason, restoreFocus = true }) {
    if (closed) {
      return;
    }
    closed = true;
    if (dialog.open) {
      dialog.close();
    }
    dialog.remove();
    if (restoreFocus) {
      refocus({ force: true });
    }
    if (reason === "cancel") {
      onCancel();
    }
  }

  function setPending(value) {
    pending = value;
    for (const control of dialog.querySelectorAll(ALL_CONTROLS)) {
      control.disabled = value;
    }
  }

  function setFeedback({ message: text = null, marks = {} } = {}) {
    message.textContent = text ?? "";
    message.hidden = text === null;
    form.setMarks(marks);
  }

  const controller = {
    element: dialog,
    isOpen: () => !closed && dialog.isConnected,
    close: (options = { reason: "external" }) => finish(options),
    refocus,
    setFeedback,
    async send(promise) {
      setFeedback();
      setPending(true);
      const response = await promise;
      form.clearPasswords();
      if (!controller.isOpen()) {
        return null;
      }
      setPending(false);
      if (response.ok) {
        finish({ reason: "success" });
        return response;
      }
      const error = translateError(response, "form");
      setFeedback({ message: error.message, marks: error.fields ?? {} });
      const invalid = dialog.querySelector("[aria-invalid=true]");
      (invalid ?? submit).focus();
      return null;
    },
  };

  cancel.addEventListener("click", () => finish({ reason: "cancel" }));
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    if (!pending) {
      finish({ reason: "cancel" });
    }
  });
  dialog.addEventListener("close", () => finish({ reason: "cancel" }));
  element.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!pending) {
      onSubmit(form.values(), controller);
    }
  });

  controllers.set(dialog, controller);
  parent.append(dialog);
  dialog.showModal();
  dialog.querySelector(FIRST_FIELD)?.focus();
  return controller;
}
