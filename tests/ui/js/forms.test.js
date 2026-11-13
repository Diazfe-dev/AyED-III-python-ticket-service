import assert from "node:assert/strict";
import { test } from "node:test";

import { confirmationMismatch } from "../../../app/static/js/core/forms.js";

test("SPEC-UI-14 reports a mismatch only when the values differ (TC-UI-14a)", () => {
  assert.equal(confirmationMismatch("clave-uno-1", "clave-dos-2"), true);
  assert.equal(confirmationMismatch("clave-uno-1", "clave-uno-1"), false);
});

test("SPEC-UI-100 compares the values as typed, trailing spaces included (TC-UI-100b)", () => {
  assert.equal(confirmationMismatch("clave-uno-1 ", "clave-uno-1"), true);
  assert.equal(confirmationMismatch("clave-uno-1", "clave-uno-1 "), true);
});
