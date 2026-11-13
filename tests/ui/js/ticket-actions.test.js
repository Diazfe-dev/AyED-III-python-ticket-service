import test from "node:test";
import assert from "node:assert/strict";
import { ticketActions } from "../../../app/static/js/core/ticket-actions.js";

const STATES = ["New", "InProgress", "Closed"];
const WORKERS = ["Representative", "Client"];

test("SPEC-UI-21 actions change only by role and by the three state rules (TC-UI-21a)", () => {
  assert.equal(ticketActions.length, 2);
  assert.deepEqual(ticketActions("Representative", "New"), [
    "milestone",
    "close",
    "associate",
    "remove",
    "startProgress",
  ]);
  assert.deepEqual(ticketActions("Representative", "InProgress"), [
    "milestone",
    "close",
    "associate",
    "remove",
    "startProgress",
  ]);
  assert.deepEqual(ticketActions("Representative", "Closed"), ["reopen", "associate", "remove"]);
  assert.deepEqual(ticketActions("Client", "New"), ["milestone", "close"]);
  assert.deepEqual(ticketActions("Client", "InProgress"), ["milestone", "close"]);
  assert.deepEqual(ticketActions("Client", "Closed"), ["reopen"]);
  for (const state of STATES) {
    assert.deepEqual(ticketActions("Admin", state), []);
  }
});

test("SPEC-UI-35 the representative is offered startProgress (TC-UI-35b)", () => {
  assert.ok(ticketActions("Representative", "New").includes("startProgress"));
});

test("SPEC-UI-77 Closed tickets offer no close (TC-UI-77a)", () => {
  for (const role of WORKERS) {
    assert.ok(!ticketActions(role, "Closed").includes("close"), role);
  }
});

test("SPEC-UI-78 Closed tickets offer no milestone (TC-UI-78a)", () => {
  for (const role of WORKERS) {
    assert.ok(!ticketActions(role, "Closed").includes("milestone"), role);
  }
});

test("SPEC-UI-79 New and InProgress tickets offer no reopen (TC-UI-79a)", () => {
  for (const role of WORKERS) {
    for (const state of ["New", "InProgress"]) {
      assert.ok(!ticketActions(role, state).includes("reopen"), `${role} ${state}`);
    }
  }
});

test("SPEC-UI-80 the client is offered no startProgress (TC-UI-80a)", () => {
  assert.ok(!ticketActions("Client", "New").includes("startProgress"));
});

test("SPEC-UI-40 the client gets a subset of milestone, close and reopen (TC-UI-40b)", () => {
  const allowed = new Set(["milestone", "close", "reopen"]);
  for (const state of STATES) {
    for (const action of ticketActions("Client", state)) {
      assert.ok(allowed.has(action), `${state} ${action}`);
    }
  }
});

test("SPEC-UI-41 the administrator gets no actions in any state (TC-UI-41c)", () => {
  for (const state of STATES) {
    assert.deepEqual(ticketActions("Admin", state), []);
  }
});
