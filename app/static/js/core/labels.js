const STATE_LABELS = Object.freeze({
  New: "Nuevo",
  InProgress: "En curso",
  Closed: "Cerrado",
});

const ROLE_LABELS = Object.freeze({
  Client: "Cliente",
  Representative: "Representante",
  Admin: "Administrador",
});

function lookup(table, code) {
  return Object.hasOwn(table, code) ? table[code] : code;
}

export function stateLabel(code) {
  return lookup(STATE_LABELS, code);
}

export function roleLabel(code) {
  return lookup(ROLE_LABELS, code);
}

export function activeLabel(isActive) {
  return isActive ? "Activo" : "Inactivo";
}
