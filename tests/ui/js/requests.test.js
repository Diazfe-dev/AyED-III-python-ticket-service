import assert from "node:assert/strict";
import { test } from "node:test";

import { initialRequests, issue, openScreen, verdict } from "../../../app/static/js/core/requests.js";

const STATUSES = [200, 204, 400, 404, 500, null];

function open() {
  return openScreen(initialRequests());
}

test("SPEC-UI-135 a replaced read is ignored and the newer one is delivered (TC-UI-135a)", () => {
  let s = open();
  const first = issue(s, "GET", "list");
  s = first.state;
  const second = issue(s, "GET", "list");
  s = second.state;
  const other = issue(s, "GET", "clients");
  s = other.state;
  const keyless1 = issue(s, "GET");
  s = keyless1.state;
  const keyless2 = issue(s, "GET");
  s = keyless2.state;
  for (const status of STATUSES) {
    assert.equal(verdict(s, first.tag, status), "ignore");
  }
  assert.equal(verdict(s, second.tag, 200), "deliver");
  assert.equal(verdict(s, other.tag, 200), "deliver");
  assert.equal(verdict(s, keyless1.tag, 200), "deliver");
  assert.equal(verdict(s, keyless2.tag, 200), "deliver");
});

test("SPEC-UI-135 a 401 of a replaced read is delivered (TC-UI-135b)", () => {
  let s = open();
  const first = issue(s, "GET", "list");
  s = first.state;
  s = issue(s, "GET", "list").state;
  assert.equal(verdict(s, first.tag, 401), "deliver");
});

test("SPEC-UI-135 writes are never replaced, even with a key (TC-UI-135d)", () => {
  let s = open();
  const w1 = issue(s, "POST");
  s = w1.state;
  const w2 = issue(s, "PATCH", "list");
  s = w2.state;
  const r = issue(s, "GET", "list");
  s = r.state;
  assert.equal(verdict(s, r.tag, 200), "deliver");
  const w3 = issue(s, "DELETE");
  s = w3.state;
  const r2 = issue(s, "GET", "list");
  s = r2.state;
  assert.equal(w1.tag.write, true);
  assert.equal(w2.tag.write, true);
  assert.equal(w3.tag.write, true);
  for (const tag of [w1.tag, w2.tag, w3.tag]) {
    for (const status of [201, 204, 400, 409, 500, null]) {
      assert.equal(verdict(s, tag, status), "deliver");
    }
  }
  assert.equal(verdict(s, r.tag, 200), "ignore");
  assert.equal(verdict(s, r2.tag, 200), "deliver");
});

test("SPEC-UI-135 distinct resources do not replace each other (TC-UI-135e)", () => {
  let s = open();
  const keys = ["ticket", "milestones", "state-changes"];
  const roundA = [];
  for (const key of keys) {
    const issued = issue(s, "GET", key);
    s = issued.state;
    roundA.push(issued.tag);
  }
  for (const tag of [...roundA].reverse()) {
    assert.equal(verdict(s, tag, 200), "deliver");
  }
  const roundB = [];
  for (const key of keys) {
    const issued = issue(s, "GET", key);
    s = issued.state;
    roundB.push(issued.tag);
  }
  for (const tag of roundA) {
    assert.equal(verdict(s, tag, 200), "ignore");
    assert.equal(verdict(s, tag, null), "ignore");
  }
  for (const tag of roundB) {
    assert.equal(verdict(s, tag, 200), "deliver");
  }
});

test("SPEC-UI-136 a request of a previous screen instance is ignored (TC-UI-136a)", () => {
  const s = open();
  const read = issue(s, "GET", "list");
  const write = issue(read.state, "POST");
  const s2 = openScreen(write.state);
  for (const status of [200, 201, 400, 403, 409, 500, null]) {
    assert.equal(verdict(s2, read.tag, status), "ignore");
    assert.equal(verdict(s2, write.tag, status), "ignore");
  }
  const fresh = issue(s2, "GET", "list");
  assert.equal(verdict(fresh.state, fresh.tag, 200), "deliver");
});

test("SPEC-UI-136 a 401 of a previous screen instance is delivered (TC-UI-136b)", () => {
  const s = open();
  const read = issue(s, "GET", "list");
  const s2 = openScreen(read.state);
  assert.equal(verdict(s2, read.tag, 401), "deliver");
});

test("SPEC-UI-136 every openScreen is a new instance, even for the same route (TC-UI-136d)", () => {
  const s1 = open();
  const w = issue(s1, "POST");
  const s2 = openScreen(w.state);
  const s3 = openScreen(s2);
  for (const status of [201, 400, null]) {
    assert.equal(verdict(s3, w.tag, status), "ignore");
  }
  assert.equal(verdict(s3, w.tag, 401), "deliver");
  const s4 = openScreen(w.state);
  assert.equal(verdict(s4, w.tag, 201), "ignore");
});
