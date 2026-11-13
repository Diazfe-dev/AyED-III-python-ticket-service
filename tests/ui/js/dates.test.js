import assert from "node:assert/strict";
import { test } from "node:test";

import { formatDateTime } from "../../../app/static/js/core/dates.js";

test("SPEC-UI-29 formats an ISO UTC date as dd/mm/aaaa HH:mm in a given zone (TC-UI-29a)", () => {
  const iso = "2026-01-01T12:00:00+00:00";
  assert.equal(formatDateTime(iso, "America/Argentina/Buenos_Aires"), "01/01/2026 09:00");
  assert.equal(formatDateTime(iso, "Asia/Kolkata"), "01/01/2026 17:30");
  assert.equal(formatDateTime(iso, "UTC"), "01/01/2026 12:00");
  assert.equal(
    formatDateTime("2026-01-01T01:30:00Z", "America/Argentina/Buenos_Aires"),
    "31/12/2025 22:30",
  );
});

test("SPEC-UI-29 uses a 24-hour clock at midnight (TC-UI-29a)", () => {
  assert.equal(formatDateTime("2026-03-05T00:05:00Z", "UTC"), "05/03/2026 00:05");
});
