import test from "node:test";
import assert from "node:assert/strict";
import { initialState, transition } from "../../../app/static/js/core/session.js";
import {
  CONNECTION_ERROR_MESSAGE,
  GENERIC_ERROR_MESSAGE,
  API_ERROR_MESSAGES,
} from "../../../app/static/js/core/messages.js";

const HOMES = { Admin: "#/users", Representative: "#/tickets", Client: "#/tickets" };
const HOME_SCREENS = { Admin: "users", Representative: "tickets-list", Client: "tickets-list" };
const ROLES = Object.keys(HOMES);

const reply = (status, body = null) => ({
  ok: status >= 200 && status < 300,
  status,
  body,
  networkError: false,
});
const offline = { ok: false, status: 0, body: null, networkError: true };
const user = (role) => ({ id: 1, email: "a@b.c", role });
const meOk = (role, hash = "") => ({ type: "meAnswered", response: reply(200, user(role)), hash });
const meWith = (response, hash = "") => ({ type: "meAnswered", response, hash });
const pending = (origin) => ({ name: "mePending", origin, epoch: 0 });
const errored = (origin) => ({ name: "meError", origin, error: "x", epoch: 0 });
const anonymous = (extra = {}) => ({
  name: "anonymous",
  notice: false,
  loginPending: false,
  epoch: 0,
  ...extra,
});
const render = (screen, params = {}) => ({ type: "render", screen, params });
const replaceHash = (hash) => ({ type: "replaceHash", hash });
const requestMe = { type: "request", kind: "me", method: "GET", path: "/me", epoch: 0 };
const types = (result) => result.effects.map((effect) => effect.type);

test("SPEC-UI-07 starts waiting for the initial GET /me (TC-UI-07a)", () => {
  assert.deepEqual(initialState(), pending("initial"));
});

test("SPEC-UI-07, SPEC-UI-132 shows the role home when GET /me answers 200 with an empty hash (TC-UI-07a, TC-UI-132a)", () => {
  for (const role of ROLES) {
    const result = transition(pending("initial"), meOk(role, ""));
    assert.equal(result.state.name, "open", role);
    assert.deepEqual(result.state.user, user(role));
    assert.equal(result.state.route, HOMES[role]);
    assert.deepEqual(result.effects, [render(HOME_SCREENS[role]), replaceHash(HOMES[role])]);
  }
});

test("SPEC-UI-07 treats #/login like the empty hash on load (TC-UI-07b)", () => {
  for (const role of ROLES) {
    assert.deepEqual(
      transition(pending("initial"), meOk(role, "#/login")),
      transition(pending("initial"), meOk(role, "")),
      role,
    );
  }
});

test("SPEC-UI-08, SPEC-UI-128 shows the login without notice on 401 of the initial GET /me (TC-UI-08a, TC-UI-128a)", () => {
  const result = transition(pending("initial"), meWith(reply(401, { error: "unauthenticated" }), "#/tickets"));
  assert.deepEqual(result.state, anonymous());
  assert.deepEqual(result.effects, [render("login", { notice: false }), replaceHash("#/login")]);
});

test("SPEC-UI-08 shows the login without notice on 401 after login and after a retry (TC-UI-08b)", () => {
  const afterLogin = transition(pending("login"), meWith(reply(401)));
  assert.deepEqual(afterLogin.state, anonymous());
  assert.deepEqual(afterLogin.effects, [render("login", { notice: false }), replaceHash("#/login")]);

  const retry = transition(errored("initial"), { type: "retryClicked" });
  const again = transition(retry.state, meWith(reply(401)));
  assert.deepEqual(again.state, anonymous());
  assert.deepEqual(again.effects, [render("login", { notice: false }), replaceHash("#/login")]);
});

test("SPEC-UI-116 renders the requested screen without replacing the hash (TC-UI-116a)", () => {
  const cases = [
    ["#/account", "Admin", "account", {}],
    ["#/account", "Representative", "account", {}],
    ["#/account", "Client", "account", {}],
    ["#/products", "Admin", "products", {}],
    ["#/tickets/new", "Representative", "ticket-new", {}],
    ["#/tickets/5", "Client", "ticket-detail", { id: "5" }],
  ];
  for (const [hash, role, screen, params] of cases) {
    const result = transition(pending("initial"), meOk(role, hash));
    assert.equal(result.state.name, "open", hash);
    assert.equal(result.state.route, hash);
    assert.deepEqual(result.effects, [render(screen, params)], `${role} ${hash}`);
  }
});

test("SPEC-UI-19, SPEC-UI-132 sends a forbidden hash to the role home on load (TC-UI-132a)", () => {
  const result = transition(pending("initial"), meOk("Client", "#/users"));
  assert.equal(result.state.route, "#/tickets");
  assert.deepEqual(result.effects, [render("tickets-list"), replaceHash("#/tickets")]);
});

test("SPEC-UI-20, SPEC-UI-97 shows not found for an unknown hash or an invalid id on load (TC-UI-116a)", () => {
  for (const hash of ["#/nope", "#/tickets/abc", "#/tickets/007"]) {
    const result = transition(pending("initial"), meOk("Admin", hash));
    assert.equal(result.state.name, "open", hash);
    assert.deepEqual(result.effects, [render("not-found", { home: "#/users" })], hash);
  }
});

test("SPEC-UI-117 keeps the error screen for a GET /me that is neither 200 nor 401 (TC-UI-117a)", () => {
  const cases = [
    [reply(500, { error: "internal_error" }), GENERIC_ERROR_MESSAGE],
    [reply(403, { error: "forbidden" }), API_ERROR_MESSAGES.forbidden],
    [reply(404, null), CONNECTION_ERROR_MESSAGE],
    [offline, CONNECTION_ERROR_MESSAGE],
  ];
  for (const origin of ["initial", "login"]) {
    for (const [response, message] of cases) {
      const result = transition(pending(origin), meWith(response, "#/tickets"));
      assert.deepEqual(result.state, { name: "meError", origin, error: message, epoch: 0 });
      assert.deepEqual(result.effects, [render("boot", { error: message })]);
    }
  }
});

test("SPEC-UI-118 retries GET /me keeping the origin and continues as the load or as a login (TC-UI-118a)", () => {
  for (const origin of ["initial", "login"]) {
    const retry = transition(errored(origin), { type: "retryClicked" });
    assert.deepEqual(retry.state, pending(origin));
    assert.deepEqual(retry.effects, [render("boot", { error: null }), requestMe]);
  }
  const initial = transition(pending("initial"), meOk("Client", "#/account"));
  assert.deepEqual(initial.effects, [render("account")]);
  const login = transition(pending("login"), meOk("Client", "#/account"));
  assert.deepEqual(login.effects, [render("tickets-list"), replaceHash("#/tickets")]);
});

test("SPEC-UI-09, SPEC-UI-132 asks for GET /me after the login and shows the role home (TC-UI-09a, TC-UI-132a)", () => {
  const sent = transition(anonymous(), { type: "loginSubmitted" });
  assert.deepEqual(sent.state, anonymous({ loginPending: true }));
  assert.deepEqual(sent.effects, [
    { type: "request", kind: "login", method: "POST", path: "/login", epoch: 0 },
  ]);

  const answered = transition(sent.state, { type: "loginAnswered", response: reply(200, null) });
  assert.deepEqual(answered.state, pending("login"));
  assert.deepEqual(answered.effects, [render("boot", { error: null }), requestMe]);

  const done = transition(answered.state, meOk("Client", "#/account"));
  assert.equal(done.state.name, "open");
  assert.equal(done.state.route, "#/tickets");
  assert.deepEqual(done.effects, [render("tickets-list"), replaceHash("#/tickets")]);
});

test("SPEC-UI-10 reports a failed login without leaving the login screen (TC-UI-09a)", () => {
  const sent = transition(anonymous(), { type: "loginSubmitted" }).state;
  const failed = transition(sent, {
    type: "loginAnswered",
    response: reply(401, { error: "invalid_credentials" }),
  });
  assert.deepEqual(failed.state, anonymous());
  assert.deepEqual(failed.effects, [
    { type: "showError", message: API_ERROR_MESSAGES.invalid_credentials },
  ]);
  const down = transition(sent, { type: "loginAnswered", response: offline });
  assert.deepEqual(down.effects, [{ type: "showError", message: CONNECTION_ERROR_MESSAGE }]);
});

test("SPEC-UI-09 ignores a second submit while POST /login is pending (TC-UI-09a)", () => {
  const state = anonymous({ loginPending: true });
  assert.deepEqual(transition(state, { type: "loginSubmitted" }), { state, effects: [] });
});

test("SPEC-UI-126 shows the login for any other hash without session and without requests (TC-UI-126b)", () => {
  const hashes = ["", "#/users", "#/tickets/007", "#/tickets/new", "#/desconocido"];
  for (const hash of hashes) {
    const result = transition(anonymous(), { type: "hashChanged", hash });
    assert.deepEqual(result.state, anonymous(), hash);
    assert.deepEqual(result.effects, [replaceHash("#/login")], hash);
    assert.ok(!types(result).includes("request"));
  }
  const same = transition(anonymous(), { type: "hashChanged", hash: "#/login" });
  assert.deepEqual(same, { state: anonymous(), effects: [] });
});

test("SPEC-UI-126 keeps the pending login and clears any notice when the hash changes (TC-UI-126b)", () => {
  const state = anonymous({ loginPending: true, notice: true });
  const result = transition(state, { type: "hashChanged", hash: "#/users" });
  assert.deepEqual(result.state, anonymous({ loginPending: true, notice: false }));
  assert.deepEqual(result.effects, [replaceHash("#/login")]);
});

test("SPEC-UI-126 does not apply while GET /me is pending or failed (TC-UI-126c)", () => {
  for (const state of [pending("initial"), pending("login"), errored("initial"), errored("login")]) {
    assert.deepEqual(transition(state, { type: "hashChanged", hash: "#/users" }), {
      state,
      effects: [],
    });
  }
});

test("SPEC-UI-127 holds the hash while GET /me is pending and evaluates it on answer (TC-UI-127a)", () => {
  for (const state of [pending("initial"), errored("initial"), pending("login")]) {
    assert.deepEqual(transition(state, { type: "hashChanged", hash: "#/account" }), {
      state,
      effects: [],
    });
  }
  const initial = transition(pending("initial"), meOk("Client", "#/account"));
  assert.deepEqual(initial.effects, [render("account")]);
  const login = transition(pending("login"), meOk("Client", "#/account"));
  assert.deepEqual(login.effects, [render("tickets-list"), replaceHash("#/tickets")]);
});

test("SPEC-UI-128 every transition that shows the login replaces the hash (TC-UI-128a)", () => {
  const shown = [
    transition(pending("initial"), meWith(reply(401))),
    transition(pending("login"), meWith(reply(401))),
    transition(anonymous(), { type: "hashChanged", hash: "#/x" }),
  ];
  for (const result of shown) {
    assert.deepEqual(result.effects.at(-1), replaceHash("#/login"));
    assert.ok(!types(result).includes("pushHash"));
  }
});

test("SPEC-UI-132 does not replace the hash when the screen is allowed (TC-UI-132a)", () => {
  const result = transition(pending("initial"), meOk("Admin", "#/categories"));
  assert.deepEqual(result.effects, [render("categories")]);
});
