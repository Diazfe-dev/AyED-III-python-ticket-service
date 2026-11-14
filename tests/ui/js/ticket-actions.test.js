import test from "node:test";
import assert from "node:assert/strict";
import { ticketActions } from "../../../app/static/js/core/ticket-actions.js";

const STATES = ["New", "InProgress", "Closed"];
const WORKERS = ["Representative", "Client"];

test("SPEC-UI-217 actions change only by role and by the state rules (TC-UI-217a)", () => {
  assert.equal(ticketActions.length, 2);
  assert.deepEqual(ticketActions("Representative", "New"), [
    "milestone",
    "close",
    "associate",
    "remove",
    "startWork",
  ]);
  assert.deepEqual(ticketActions("Representative", "InProgress"), [
    "milestone",
    "close",
    "associate",
    "remove",
  ]);
  assert.deepEqual(ticketActions("Representative", "Closed"), ["reopen", "associate", "remove"]);
  assert.deepEqual(ticketActions("Client", "New"), ["milestone", "close"]);
  assert.deepEqual(ticketActions("Client", "InProgress"), ["milestone", "close"]);
  assert.deepEqual(ticketActions("Client", "Closed"), ["reopen"]);
  for (const state of STATES) {
    assert.deepEqual(ticketActions("Admin", state), []);
  }
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

test("SPEC-UI-211 the representative is offered startWork on a New ticket (TC-UI-211a)", () => {
  assert.ok(ticketActions("Representative", "New").includes("startWork"));
});

test("SPEC-UI-212 the representative is offered no startWork once started or closed (TC-UI-212a)", () => {
  for (const state of ["InProgress", "Closed"]) {
    assert.ok(!ticketActions("Representative", state).includes("startWork"), state);
  }
});

test("SPEC-UI-213 clients and administrators are offered no startWork (TC-UI-213a)", () => {
  for (const role of ["Client", "Admin"]) {
    for (const state of STATES) {
      assert.ok(!ticketActions(role, state).includes("startWork"), `${role} ${state}`);
    }
  }
});
