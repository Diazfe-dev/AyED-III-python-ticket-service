import test from "node:test";
import assert from "node:assert/strict";
import {
  canSend,
  currentUser,
  initialState,
  isInert,
  transition,
} from "../../../app/static/js/core/session.js";
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

const open = (role = "Client", route = "#/tickets", epoch = 0) => ({
  name: "open",
  user: user(role),
  route,
  epoch,
});
const closing = (route = "#/tickets", epoch = 1) => ({ name: "closing", route, epoch });
const apiAnswered = (status, epoch = 0, body = null) => ({
  type: "apiAnswered",
  epoch,
  response: reply(status, body),
});
const offlineAnswer = (epoch = 0) => ({ type: "apiAnswered", epoch, response: offline });

test("SPEC-UI-04, SPEC-UI-19, SPEC-UI-20 evaluates the hash with an open session (TC-UI-124c)", () => {
  const allowed = transition(open("Client", "#/tickets"), { type: "hashChanged", hash: "#/account" });
  assert.deepEqual(allowed.state, open("Client", "#/account"));
  assert.deepEqual(allowed.effects, [render("account")]);

  const forbidden = transition(open("Client"), { type: "hashChanged", hash: "#/users" });
  assert.equal(forbidden.state.route, "#/tickets");
  assert.deepEqual(forbidden.effects, [render("tickets-list"), replaceHash("#/tickets")]);

  const unknown = transition(open("Admin", "#/users"), { type: "hashChanged", hash: "#/nope" });
  assert.equal(unknown.state.route, "#/nope");
  assert.deepEqual(unknown.effects, [render("not-found", { home: "#/users" })]);
});

test("SPEC-UI-124, SPEC-UI-132 shows the role home for #/login or an empty hash with a session (TC-UI-124c)", () => {
  for (const role of ROLES) {
    for (const hash of ["#/login", ""]) {
      const result = transition(open(role, "#/account"), { type: "hashChanged", hash });
      assert.equal(result.state.route, HOMES[role], `${role} ${hash}`);
      assert.deepEqual(result.effects, [render(HOME_SCREENS[role]), replaceHash(HOMES[role])]);
      assert.ok(!types(result).includes("request"));
    }
  }
});

test("SPEC-UI-11, SPEC-UI-133, SPEC-UI-134 closes the session at once and sends POST /logout (TC-UI-11a)", () => {
  const result = transition(open("Client", "#/account", 0), { type: "logoutClicked" });
  assert.deepEqual(result.state, closing("#/account", 1));
  assert.equal(currentUser(result.state), null);
  assert.equal(currentUser(open("Admin")).role, "Admin");
  assert.deepEqual(result.effects, [
    { type: "request", kind: "logout", method: "POST", path: "/logout", epoch: 1 },
    { type: "setInert", inert: true },
  ]);
});

test("SPEC-UI-129, SPEC-UI-128 shows the login without notice when POST /logout settles (TC-UI-129e)", () => {
  for (const status of [204, 500, 401]) {
    const result = transition(closing(), { type: "logoutSettled", response: reply(status) });
    assert.deepEqual(result.state, anonymous({ epoch: 1 }), String(status));
    assert.deepEqual(result.effects, [
      render("login", { notice: false }),
      replaceHash("#/login"),
      { type: "setInert", inert: false },
    ]);
  }
  const down = transition(closing(), { type: "logoutSettled", response: offline });
  assert.deepEqual(down.state, anonymous({ epoch: 1 }));
  assert.deepEqual(down.effects.at(-1), { type: "setInert", inert: false });
});

test("SPEC-UI-12, SPEC-UI-128 shows the login with notice on a 401 of the current epoch (TC-UI-12a)", () => {
  const result = transition(open("Client", "#/tickets", 3), apiAnswered(401, 3));
  assert.deepEqual(result.state, anonymous({ notice: true, epoch: 4 }));
  assert.equal(currentUser(result.state), null);
  assert.deepEqual(result.effects, [render("login", { notice: true }), replaceHash("#/login")]);
});

test("SPEC-UI-12 never shows the notice for the 401 of login, logout or the load GET /me (TC-UI-12b)", () => {
  const login = transition(anonymous({ loginPending: true }), {
    type: "loginAnswered",
    response: reply(401, { error: "invalid_credentials" }),
  });
  const logout = transition(closing(), { type: "logoutSettled", response: reply(401) });
  const load = transition(pending("initial"), meWith(reply(401)));
  for (const result of [login, logout, load]) {
    assert.notEqual(result.state.notice, true);
    assert.ok(!result.effects.some((effect) => effect.params?.notice === true));
  }
});

test("SPEC-UI-130 ignores any answer of an old epoch in every state (TC-UI-130a)", () => {
  const states = [closing("#/tickets", 1), anonymous({ epoch: 1 }), open("Client", "#/tickets", 2)];
  for (const state of states) {
    for (const answer of [apiAnswered(401, 0), apiAnswered(200, 0), offlineAnswer(0)]) {
      assert.deepEqual(transition(state, answer), { state, effects: [] }, state.name);
    }
  }
  for (const state of [pending("initial"), errored("login")]) {
    assert.deepEqual(transition(state, apiAnswered(401, 99)), { state, effects: [] });
  }
});

test("SPEC-UI-12 keeps a current non-401 answer for the screen without changing the session (TC-UI-12a)", () => {
  const state = open("Client", "#/tickets", 2);
  for (const answer of [apiAnswered(200, 2), apiAnswered(500, 2), offlineAnswer(2)]) {
    assert.deepEqual(transition(state, answer), { state, effects: [] });
  }
});

test("SPEC-UI-131 keeps the shown screen when the hash changes while POST /logout is pending (TC-UI-131a)", () => {
  const state = closing("#/tickets");
  assert.deepEqual(transition(state, { type: "hashChanged", hash: "#/account" }), {
    state,
    effects: [],
  });
});

test("SPEC-UI-133 ignores every control and a second logout while POST /logout is pending (TC-UI-133a)", () => {
  const state = closing();
  for (const control of ["pagination", "filter", "search", "action", "logout"]) {
    assert.deepEqual(transition(state, { type: "controlActivated", control }), {
      state,
      effects: [],
    });
  }
  assert.deepEqual(transition(state, { type: "logoutClicked" }), { state, effects: [] });
  assert.equal(canSend(state), false);
  assert.equal(canSend(open()), true);
  assert.equal(canSend(anonymous()), true);
});

test("SPEC-UI-134 is inert only while POST /logout is pending (TC-UI-134b)", () => {
  const states = [pending("initial"), errored("login"), anonymous(), open()];
  for (const state of states) {
    assert.equal(isInert(state), false, state.name);
  }
  assert.equal(isInert(closing()), true);
});
