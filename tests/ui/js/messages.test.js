import assert from "node:assert/strict";
import { test } from "node:test";

import {
  API_ERROR_MESSAGES,
  CONNECTION_ERROR_MESSAGE,
  FIELD_MARKS,
  GENERIC_ERROR_MESSAGE,
  OWN_MESSAGES,
  translateError,
} from "../../../app/static/js/core/messages.js";

const EXPECTED = {
  invalid_credentials: "Email o contraseña incorrectos.",
  invalid_current_password: "La contraseña actual no es correcta.",
  forbidden: "No tiene permiso para realizar esta acción.",
  duplicate_email: "Ya existe un usuario con ese email.",
  self_deactivation: "No puede darse de baja a sí mismo.",
  user_not_found: "El usuario no existe.",
  duplicate_category: "Ya existe una categoría con ese nombre.",
  category_in_use: "La categoría tiene tipos de producto asociados y no se puede eliminar.",
  category_not_found: "La categoría no existe.",
  duplicate_product_type: "Ya existe un tipo de producto con ese nombre en la categoría.",
  product_type_in_use: "El tipo de producto tiene productos asociados y no se puede eliminar.",
  product_type_not_found: "El tipo de producto no existe.",
  duplicate_product: "Ya existe un producto con ese nombre en el tipo de producto.",
  product_not_found: "El producto no existe.",
  ticket_not_found: "El ticket no existe.",
  ticket_closed: "El ticket está cerrado. Reábralo para agregar mensajes.",
  invalid_transition: "Esa acción no está permitida en el estado actual del ticket.",
  invalid_client: "El cliente indicado no existe o está inactivo.",
  invalid_product: "Alguno de los productos no existe o está inactivo.",
  product_not_in_ticket: "El producto no está asociado al ticket.",
};

const FORBIDDEN_WORDS = [
  "Save", "Cancel", "Delete", "Loading", "Search", "Login", "Logout",
  "Close", "Reopen", "Submit", "Name", "Password", "Next", "Previous",
];

const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, body, networkError: false });

test("SPEC-UI-10 shows the generic invalid credentials message for a 401 (TC-UI-10a)", () => {
  const result = translateError(reply(401, { error: "invalid_credentials" }));
  assert.equal(result.message, "Email o contraseña incorrectos.");
  assert.equal(result.fields, null);
});

test("SPEC-UI-56 maps each of the 20 API error codes to its exact text (TC-UI-56a)", () => {
  assert.equal(Object.keys(API_ERROR_MESSAGES).length, 20);
  for (const [code, text] of Object.entries(EXPECTED)) {
    assert.equal(API_ERROR_MESSAGES[code], text, code);
    assert.equal(translateError(reply(409, { error: code })).message, text, code);
  }
});

test("SPEC-UI-56 keeps the own interface messages in their table (TC-UI-56a)", () => {
  assert.equal(OWN_MESSAGES.passwordUpdated, "Contraseña actualizada.");
  assert.equal(OWN_MESSAGES.passwordReset, "Contraseña restablecida.");
  assert.equal(OWN_MESSAGES.userCreated, "Usuario creado.");
  assert.equal(OWN_MESSAGES.sessionExpired, "Tu sesión venció. Inicia sesión nuevamente.");
});

test("SPEC-UI-55 uses no forbidden English word in the message tables (TC-UI-55b)", () => {
  const texts = [
    ...Object.values(API_ERROR_MESSAGES),
    ...Object.values(OWN_MESSAGES),
    ...Object.values(FIELD_MARKS),
    GENERIC_ERROR_MESSAGE,
    CONNECTION_ERROR_MESSAGE,
  ];
  for (const text of texts) {
    for (const word of FORBIDDEN_WORDS) {
      assert.ok(!new RegExp(`\\b${word}\\b`).test(text), `${word} in ${text}`);
    }
  }
});

test("SPEC-UI-57 marks each field of a form validation_error as required or invalid (TC-UI-57a)", () => {
  const result = translateError(
    reply(400, { error: "validation_error", fields: { email: "invalid", name: "required" } }),
    "form",
  );
  assert.deepEqual(result.fields, {
    email: "El valor ingresado no es válido",
    name: "Este campo es obligatorio",
  });
});

test("SPEC-UI-58 shows the generic message for unknown codes and 5xx with JSON (TC-UI-58a)", () => {
  const generic = "Ocurrió un error inesperado. Intente nuevamente.";
  assert.equal(translateError(reply(400, { error: "algo_raro" })).message, generic);
  assert.equal(translateError(reply(500, { error: "internal_error" })).message, generic);
  assert.equal(translateError(reply(500, { error: "forbidden" })).message, generic);
});

test("SPEC-UI-59 shows the connection message without a usable error body and treats 2xx as success (TC-UI-59a)", () => {
  const offline = "No se pudo conectar con el servidor. Intente nuevamente.";
  assert.equal(translateError({ ok: false, status: 0, body: null, networkError: true }).message, offline);
  assert.equal(translateError(reply(502, null)).message, offline);
  assert.equal(translateError(reply(400, { detail: "x" })).message, offline);
  assert.equal(translateError(reply(400, { error: 7 })).message, offline);
  assert.equal(translateError(reply(204, null)), null);
});

test("SPEC-UI-119 shows the generic message without marks for a list validation_error (TC-UI-119a)", () => {
  const result = translateError(
    reply(400, { error: "validation_error", fields: { page: "invalid" } }),
    "list",
  );
  assert.equal(result.message, "Ocurrió un error inesperado. Intente nuevamente.");
  assert.equal(result.fields, null);
});
