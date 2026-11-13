import assert from "node:assert/strict";
import { test } from "node:test";

import { activeLabel, roleLabel, stateLabel } from "../../../app/static/js/core/labels.js";

test("SPEC-UI-96 ticket states, roles and account status use the label table (TC-UI-96a)", () => {
  assert.equal(stateLabel("New"), "Nuevo");
  assert.equal(stateLabel("InProgress"), "En curso");
  assert.equal(stateLabel("Closed"), "Cerrado");
  assert.equal(roleLabel("Client"), "Cliente");
  assert.equal(roleLabel("Representative"), "Representante");
  assert.equal(roleLabel("Admin"), "Administrador");
  assert.equal(activeLabel(true), "Activo");
  assert.equal(activeLabel(false), "Inactivo");
});

test("SPEC-UI-123 unknown state or role codes are returned as they arrive (TC-UI-123a)", () => {
  assert.equal(stateLabel("Escalado"), "Escalado");
  assert.equal(roleLabel("Auditor"), "Auditor");
});
