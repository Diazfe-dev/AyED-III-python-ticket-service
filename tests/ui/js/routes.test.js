import test from "node:test";
import assert from "node:assert/strict";
import {
  classify,
  homeOf,
  isValidTicketId,
  navItems,
  routeOf,
  sharesScreenInstance,
} from "../../../app/static/js/core/routes.js";

const ROLES = ["Representative", "Admin", "Client"];
const MAX_ID = "9223372036854775807";

const screen = (name, params) => ({ kind: "screen", screen: name, ...(params ? { params } : {}) });

test("SPEC-UI-04 classifies every route of the table for every role (TC-UI-04a)", () => {
  const allowed = {
    "#/tickets": { Representative: "tickets-list", Admin: "tickets-list", Client: "tickets-list" },
    "#/tickets/new": { Representative: "ticket-new" },
    "#/users": { Admin: "users" },
    "#/categories": { Admin: "categories" },
    "#/product-types": { Admin: "product-types" },
    "#/products": { Admin: "products" },
    "#/account": { Representative: "account", Admin: "account", Client: "account" },
  };
  for (const [hash, byRole] of Object.entries(allowed)) {
    for (const role of ROLES) {
      const expected = byRole[role]
        ? screen(byRole[role])
        : { kind: "forbidden", home: homeOf(role) };
      assert.deepEqual(classify(hash, role), expected, `${role} ${hash}`);
    }
  }
  assert.deepEqual(classify("#/tickets/7", "Client"), screen("ticket-detail", { id: "7" }));
  assert.deepEqual(classify("#/tickets/7", "Admin"), screen("ticket-detail", { id: "7" }));
  assert.deepEqual(classify("#/tickets/new", "Representative"), screen("ticket-new"));
});

test("SPEC-UI-16 lists the representative navigation entries (TC-UI-16b)", () => {
  assert.deepEqual(navItems("Representative"), [
    { label: "Tickets", route: "#/tickets" },
    { label: "Nuevo ticket", route: "#/tickets/new" },
    { label: "Mi cuenta", route: "#/account" },
    { label: "Cerrar sesión", action: "logout" },
  ]);
});

test("SPEC-UI-17 lists the administrator navigation entries (TC-UI-17b)", () => {
  assert.deepEqual(navItems("Admin"), [
    { label: "Usuarios", route: "#/users" },
    { label: "Categorías", route: "#/categories" },
    { label: "Tipos de producto", route: "#/product-types" },
    { label: "Productos", route: "#/products" },
    { label: "Tickets", route: "#/tickets" },
    { label: "Mi cuenta", route: "#/account" },
    { label: "Cerrar sesión", action: "logout" },
  ]);
});

test("SPEC-UI-18 lists the client navigation entries (TC-UI-18b)", () => {
  assert.deepEqual(navItems("Client"), [
    { label: "Mis tickets", route: "#/tickets" },
    { label: "Mi cuenta", route: "#/account" },
    { label: "Cerrar sesión", action: "logout" },
  ]);
});

test("SPEC-UI-19 sends a route the role does not allow to the role home (TC-UI-19a)", () => {
  for (const [role, hash] of [
    ["Representative", "#/users"],
    ["Representative", "#/products"],
    ["Client", "#/tickets/new"],
    ["Client", "#/categories"],
    ["Admin", "#/tickets/new"],
  ]) {
    assert.deepEqual(classify(hash, role), { kind: "forbidden", home: homeOf(role) });
  }
  assert.equal(homeOf("Admin"), "#/users");
  assert.equal(homeOf("Representative"), "#/tickets");
  assert.equal(homeOf("Client"), "#/tickets");
});

test("SPEC-UI-20 classifies unknown hashes as not found but the empty hash as home (TC-UI-20a)", () => {
  for (const hash of ["#/desconocido", "#/users/1", "#/tickets/", "#/"]) {
    for (const role of ROLES) {
      assert.deepEqual(classify(hash, role), { kind: "not_found", home: homeOf(role) }, hash);
    }
  }
  assert.equal(classify("", "Client").kind, "home");
});

test("SPEC-UI-97 validates ticket ids and routes invalid ones to not found (TC-UI-97a)", () => {
  for (const bad of ["0", "007", "-1", "1.5", "abc", "9223372036854775808", ""]) {
    assert.equal(isValidTicketId(bad), false, bad);
  }
  for (const bad of ["0", "007", "-1", "1.5", "abc", "9223372036854775808"]) {
    assert.equal(classify(`#/tickets/${bad}`, "Representative").kind, "not_found", bad);
  }
  for (const good of ["1", MAX_ID]) {
    assert.equal(isValidTicketId(good), true, good);
    assert.deepEqual(classify(`#/tickets/${good}`, "Client"), screen("ticket-detail", { id: good }));
  }
  assert.deepEqual(classify("#/tickets/new", "Representative"), screen("ticket-new"));
});

test("SPEC-UI-124 shows the role home for the empty hash and #/login with a session (TC-UI-124a)", () => {
  for (const role of ROLES) {
    assert.deepEqual(classify("", role), { kind: "home", home: homeOf(role) });
    assert.deepEqual(classify("#/login", role), { kind: "home", home: homeOf(role) });
  }
});

test("SPEC-UI-126 sends every hash to login without a session (TC-UI-126a)", () => {
  for (const hash of ["", "#/users", "#/tickets/007", "#/tickets/new", "#/desconocido", "#/login"]) {
    assert.deepEqual(classify(hash, null), { kind: "login" }, hash);
  }
});

test("SPEC-UI-138 maps a screen to the exact route of its navigation link (TC-UI-138d)", () => {
  assert.equal(routeOf("tickets-list"), "#/tickets");
  assert.equal(routeOf("ticket-new"), "#/tickets/new");
  assert.equal(routeOf("account"), "#/account");
  assert.equal(routeOf("users"), "#/users");
  assert.equal(routeOf("ticket-detail"), null);
  assert.equal(routeOf("login"), null);
  assert.equal(routeOf("not-found"), null);
});

test("SPEC-UI-170 treats the ticket list and the ticket creation route as one screen instance (TC-UI-170c)", () => {
  assert.equal(sharesScreenInstance("tickets-list", "ticket-new"), true);
  assert.equal(sharesScreenInstance("ticket-new", "tickets-list"), true);
  assert.equal(sharesScreenInstance("tickets-list", "tickets-list"), true);
  assert.equal(sharesScreenInstance("tickets-list", "ticket-detail"), false);
  assert.equal(sharesScreenInstance("ticket-new", "account"), false);
  assert.equal(sharesScreenInstance("users", "users"), false);
  assert.equal(sharesScreenInstance(null, "tickets-list"), false);
});
