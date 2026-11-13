export const GENERIC_ERROR_MESSAGE = "Ocurrió un error inesperado. Intente nuevamente.";
export const CONNECTION_ERROR_MESSAGE = "No se pudo conectar con el servidor. Intente nuevamente.";

export const API_ERROR_MESSAGES = Object.freeze({
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
});

export const OWN_MESSAGES = Object.freeze({
  passwordUpdated: "Contraseña actualizada.",
  userCreated: "Usuario creado.",
  sessionExpired: "Tu sesión venció. Inicia sesión nuevamente.",
});

export const FIELD_MARKS = Object.freeze({
  required: "Este campo es obligatorio",
  invalid: "El valor ingresado no es válido",
});

const SERVER_ERROR_STATUS = 500;

function errorCode(body) {
  if (body !== null && typeof body === "object" && typeof body.error === "string") {
    return body.error;
  }
  return null;
}

function fieldMarks(fields) {
  if (fields === null || typeof fields !== "object") {
    return null;
  }
  const marks = {};
  for (const [field, reason] of Object.entries(fields)) {
    marks[field] = FIELD_MARKS[reason] ?? FIELD_MARKS.invalid;
  }
  return Object.keys(marks).length > 0 ? marks : null;
}

function general(message) {
  return { message, fields: null };
}

export function translateError(response, context = "general") {
  if (response.ok) {
    return null;
  }
  const code = response.networkError ? null : errorCode(response.body);
  if (code === null) {
    return general(CONNECTION_ERROR_MESSAGE);
  }
  if (response.status >= SERVER_ERROR_STATUS) {
    return general(GENERIC_ERROR_MESSAGE);
  }
  if (code === "validation_error" && context === "form") {
    const marks = fieldMarks(response.body.fields);
    if (marks !== null) {
      return { message: null, fields: marks };
    }
  }
  return general(Object.hasOwn(API_ERROR_MESSAGES, code) ? API_ERROR_MESSAGES[code] : GENERIC_ERROR_MESSAGE);
}
