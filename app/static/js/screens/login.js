import { OWN_MESSAGES } from "../core/messages.js";
import { el } from "../dom/render.js";

export function title() {
  return "Iniciar sesión";
}

function field(id, label, attrs) {
  return el("div", { class: "field" }, [
    el("label", { for: id }, [label]),
    el("input", { id, name: id, ...attrs }),
  ]);
}

export function mount({ root, params, dispatch, showError, showStatus }) {
  const email = field("login-email", "Email", { type: "text", autocomplete: "username" });
  const password = field("login-password", "Contraseña", {
    type: "password",
    autocomplete: "current-password",
  });
  const form = el("form", { novalidate: true }, [
    email,
    password,
    el("button", { type: "submit" }, ["Ingresar"]),
  ]);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const passwordInput = password.querySelector("input");
    const credentials = {
      email: email.querySelector("input").value,
      password: passwordInput.value,
    };
    passwordInput.value = "";
    showError("");
    showStatus("");
    dispatch({ type: "loginSubmitted", credentials });
  });
  root.append(el("h1", {}, [title()]), form);
  if (params.notice) {
    showStatus(OWN_MESSAGES.sessionExpired);
  }
}
