import { expect, test } from "@playwright/test";
import { installFakeApi, loginAs } from "./support/fake-api.js";
import { CLIENT, REP, page as pageOf, ticket } from "./support/fixtures.js";

const CATEGORY = { id: 2, name: "Hardware" };
const TYPE = { id: 3, name: "Redes", category: CATEGORY };
const product = (id, name) => ({ id, name, is_active: true, product_type: TYPE, category: CATEGORY });
const ROUTER = product(3, "Router X");
const SWITCH = product(4, "Switch Y");
const MODEM = product(5, "Modem Z");

const CREATED = "2026-01-01T12:00:00+00:00";
const withProducts = (state, products = []) => ({ ...ticket(7, state, CREATED), products });
const REP_AUTHOR = { id: REP.id, name: REP.name, role: "Representative" };
const CLIENT_AUTHOR = { id: CLIENT.id, name: CLIENT.name, role: "Client" };
const MILESTONE = {
  id: 1,
  content: "Primer mensaje",
  author: CLIENT_AUTHOR,
  created_at: CREATED,
};

const writes = (api) => api.requests.filter((r) => r.method !== "GET");
const written = (api, method, suffix) =>
  api.requests.filter((r) => r.method === method && new URL(r.url).pathname === `/tickets/7${suffix}`);

async function openDetail(page, role, state = "New", products = []) {
  const api = await installFakeApi(page);
  api.on("GET", "/tickets/7", { status: 200, body: withProducts(state, products) });
  api.on("GET", "/tickets/7/milestones", { status: 200, body: [MILESTONE] });
  api.on("GET", "/tickets/7/state-changes", { status: 200, body: [] });
  await loginAs(page, api, role);
  await page.goto("/#/tickets/7");
  await expect(page.getByRole("heading", { name: "Ticket #7", exact: true })).toBeVisible();
  await expect(page.locator("ol.milestones")).toContainText("Primer mensaje");
  return api;
}

const milestoneForm = (page) => page.getByRole("form", { name: "Agregar hito" });
const button = (page, name) => page.getByRole("button", { name, exact: true });

test("SPEC-UI-34 a representative sends a milestone (TC-UI-34a)", async ({ page }) => {
  const api = await openDetail(page, "Representative", "InProgress");
  api.on("POST", "/tickets/7/milestones", { status: 201, body: MILESTONE });
  await milestoneForm(page).getByLabel("Mensaje").fill("Revisando");
  await button(page, "Agregar hito").click();
  await expect.poll(() => written(api, "POST", "/milestones").length).toBe(1);
  expect(written(api, "POST", "/milestones")[0].body).toEqual({ content: "Revisando" });
});

test("SPEC-UI-34 a client sends a milestone (TC-UI-34b)", async ({ page }) => {
  const api = await openDetail(page, "Client");
  api.on("POST", "/tickets/7/milestones", { status: 201, body: MILESTONE });
  await milestoneForm(page).getByLabel("Mensaje").fill("Gracias");
  await button(page, "Agregar hito").click();
  await expect.poll(() => written(api, "POST", "/milestones").length).toBe(1);
  expect(written(api, "POST", "/milestones")[0].body).toEqual({ content: "Gracias" });
});

test("SPEC-UI-35 the representative sees the start-work option (TC-UI-35a)", async ({ page }) => {
  await openDetail(page, "Representative", "New");
  await expect(milestoneForm(page).getByLabel("Comenzar a trabajar")).toBeVisible();
});

test("SPEC-UI-80 the client does not see the start-work option (TC-UI-80b)", async ({ page }) => {
  await openDetail(page, "Client", "New");
  await expect(milestoneForm(page)).toBeVisible();
  await expect(page.getByLabel("Comenzar a trabajar")).toHaveCount(0);
  await expect(page.locator("#app")).not.toContainText("Comenzar a trabajar");
});

test("SPEC-UI-81 sends start_progress true when the option is checked (TC-UI-81a)", async ({
  page,
}) => {
  const api = await openDetail(page, "Representative", "New");
  api.on("POST", "/tickets/7/milestones", { status: 201, body: MILESTONE });
  await milestoneForm(page).getByLabel("Mensaje").fill("Empiezo");
  await milestoneForm(page).getByLabel("Comenzar a trabajar").check();
  await button(page, "Agregar hito").click();
  await expect.poll(() => written(api, "POST", "/milestones").length).toBe(1);
  expect(written(api, "POST", "/milestones")[0].body).toEqual({
    content: "Empiezo",
    start_progress: true,
  });
});

test("SPEC-UI-81 omits start_progress when the option is not checked (TC-UI-81b)", async ({
  page,
}) => {
  const api = await openDetail(page, "Representative", "New");
  api.on("POST", "/tickets/7/milestones", { status: 201, body: MILESTONE });
  await milestoneForm(page).getByLabel("Mensaje").fill("Sin empezar");
  await button(page, "Agregar hito").click();
  await expect.poll(() => written(api, "POST", "/milestones").length).toBe(1);
  expect(written(api, "POST", "/milestones")[0].body).not.toHaveProperty("start_progress");
});

async function closesTicket(page, role) {
  const api = await openDetail(page, role, "InProgress");
  api.on("POST", "/tickets/7/close", { status: 200, body: withProducts("Closed") });
  await button(page, "Cerrar").click();
  await expect.poll(() => written(api, "POST", "/close").length).toBe(1);
}

test("SPEC-UI-36 the representative closes the ticket (TC-UI-36a)", async ({ page }) => {
  await closesTicket(page, "Representative");
});

test("SPEC-UI-36 the client closes the ticket (TC-UI-36a)", async ({ page }) => {
  await closesTicket(page, "Client");
});

test("SPEC-UI-37 reopens a closed ticket (TC-UI-37a)", async ({ page }) => {
  const api = await openDetail(page, "Representative", "Closed");
  api.on("POST", "/tickets/7/reopen", { status: 200, body: withProducts("InProgress") });
  await button(page, "Reabrir").click();
  await expect.poll(() => written(api, "POST", "/reopen").length).toBe(1);
});

test("SPEC-UI-32 searches available products to associate (TC-UI-32b)", async ({ page }) => {
  const api = await openDetail(page, "Representative", "New");
  api.on("GET", "/products/available", { status: 200, body: pageOf([SWITCH, MODEM]) });
  await page.getByLabel("Buscar productos").fill("note");
  await button(page, "Buscar").click();
  await expect(page.getByLabel("Switch Y")).toBeVisible();
  await expect(page.getByLabel("Modem Z")).toBeVisible();
  await expect(page.getByLabel("Router X")).toHaveCount(0);
  const searches = api.requests.filter((r) => new URL(r.url).pathname === "/products/available");
  expect(searches.length).toBeGreaterThan(0);
  expect(new URL(searches.at(-1).url).searchParams.get("q")).toBe("note");
});

test("SPEC-UI-38 associates the chosen products (TC-UI-38a)", async ({ page }) => {
  const api = await openDetail(page, "Representative", "New");
  api.on("GET", "/products/available", { status: 200, body: pageOf([ROUTER, SWITCH, MODEM]) });
  api.on("POST", "/tickets/7/products", { status: 200, body: withProducts("New", [ROUTER]) });
  await page.getByLabel("Buscar productos").fill("a");
  await button(page, "Buscar").click();
  await page.getByLabel("Router X").check();
  await page.getByLabel("Switch Y").check();
  await button(page, "Asociar").click();
  await expect.poll(() => written(api, "POST", "/products").length).toBe(1);
  expect(written(api, "POST", "/products")[0].body).toEqual({ product_ids: [3, 4] });
});

test("SPEC-UI-39 removes a product from the ticket (TC-UI-39a)", async ({ page }) => {
  const api = await openDetail(page, "Representative", "New", [ROUTER, SWITCH]);
  api.on("DELETE", "/tickets/7/products/3", { status: 200, body: withProducts("New", [SWITCH]) });
  await button(page, "Quitar Router X").click();
  await expect.poll(() => written(api, "DELETE", "/products/3").length).toBe(1);
});

test("SPEC-UI-77 a closed ticket offers no close (TC-UI-77b)", async ({ page }) => {
  for (const role of ["Representative", "Client"]) {
    await openDetail(page, role, "Closed");
    await expect(button(page, "Cerrar")).toHaveCount(0);
  }
});

test("SPEC-UI-78 a closed ticket offers no milestone form (TC-UI-78b)", async ({ page }) => {
  for (const role of ["Representative", "Client"]) {
    await openDetail(page, role, "Closed");
    await expect(milestoneForm(page)).toHaveCount(0);
    await expect(button(page, "Agregar hito")).toHaveCount(0);
  }
});

test("SPEC-UI-79 new and in-progress tickets offer no reopen (TC-UI-79b)", async ({ page }) => {
  for (const state of ["New", "InProgress"]) {
    await openDetail(page, "Representative", state);
    await expect(button(page, "Reabrir")).toHaveCount(0);
  }
});

test("SPEC-UI-40 the client only gets milestone, close and reopen (TC-UI-40a)", async ({
  page,
}) => {
  await openDetail(page, "Client", "New", [ROUTER]);
  await expect(button(page, "Agregar hito")).toBeVisible();
  await expect(button(page, "Cerrar")).toBeVisible();
  await expect(button(page, "Reabrir")).toHaveCount(0);
  await expect(page.locator("#app button")).toHaveCount(2);
  await expect(page.getByLabel("Buscar productos")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Quitar/ })).toHaveCount(0);

  await openDetail(page, "Client", "Closed", [ROUTER]);
  await expect(button(page, "Reabrir")).toBeVisible();
  await expect(page.locator("#app button")).toHaveCount(1);
});

test("SPEC-UI-21 shows the API conflict when closing is refused (TC-UI-21b)", async ({ page }) => {
  const api = await openDetail(page, "Representative", "InProgress");
  api.on("POST", "/tickets/7/close", { status: 409, body: { error: "invalid_transition" } });
  await button(page, "Cerrar").click();
  await expect(page.locator("#alert")).toHaveText(
    "Esa acción no está permitida en el estado actual del ticket.",
  );
  await expect(button(page, "Cerrar")).toBeVisible();
  await expect(button(page, "Cerrar")).toBeEnabled();
});

test("SPEC-UI-21 shows the API refusal for a milestone (TC-UI-21c)", async ({ page }) => {
  const api = await openDetail(page, "Client", "New");
  api.on("POST", "/tickets/7/milestones", { status: 403, body: { error: "forbidden" } });
  await milestoneForm(page).getByLabel("Mensaje").fill("Hola");
  await button(page, "Agregar hito").click();
  await expect(page.locator("#alert")).toHaveText("No tiene permiso para realizar esta acción.");
});

test("SPEC-UI-42 reloads the three reads after an action (TC-UI-42a)", async ({ page }) => {
  const api = await openDetail(page, "Representative", "InProgress");
  api.on("GET", "/tickets/7", [
    { status: 200, body: withProducts("InProgress") },
    { status: 200, body: withProducts("Closed") },
  ]);
  api.on("GET", "/tickets/7/state-changes", [
    { status: 200, body: [] },
    {
      status: 200,
      body: [{ state: "Closed", user: REP_AUTHOR, timestamp: "2026-01-05T12:00:00+00:00" }],
    },
  ]);
  api.on("POST", "/tickets/7/close", { status: 200, body: withProducts("Closed") });
  await page.reload();
  await expect(page.locator(".ticket-state")).toHaveText("En curso");
  const before = api.requests.length;
  await button(page, "Cerrar").click();
  await expect(page.locator(".ticket-state")).toHaveText("Cerrado");
  await expect(page.locator("ol.state-changes > li")).toHaveCount(1);
  const after = api.requests.slice(before).map((r) => `${r.method} ${new URL(r.url).pathname}`);
  expect(after[0]).toBe("POST /tickets/7/close");
  expect(after).toEqual(
    expect.arrayContaining([
      "GET /tickets/7",
      "GET /tickets/7/milestones",
      "GET /tickets/7/state-changes",
    ]),
  );
  await expect(button(page, "Cerrar")).toHaveCount(0);
});

test("SPEC-UI-43 disables the button while its action runs (TC-UI-43a)", async ({ page }) => {
  const api = await openDetail(page, "Representative", "InProgress");
  const close = api.defer("POST", "/tickets/7/close");
  api.on("GET", "/tickets/7", [
    { status: 200, body: withProducts("InProgress") },
    { status: 200, body: withProducts("Closed") },
  ]);
  await page.reload();
  await expect(page.locator(".ticket-state")).toHaveText("En curso");
  await button(page, "Cerrar").click();
  await close.requested;
  await expect(button(page, "Cerrar")).toBeDisabled();
  await button(page, "Cerrar").click({ force: true });
  await button(page, "Cerrar").dispatchEvent("click");
  close.release(200, withProducts("Closed"));
  await expect(page.locator(".ticket-state")).toHaveText("Cerrado");
  expect(written(api, "POST", "/close")).toHaveLength(1);
  expect(writes(api)).toHaveLength(1);
});

test("SPEC-UI-135 draws the three parallel reads released in reverse order (TC-UI-135h)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Representative");
  const reads = () => ({
    ticket: api.defer("GET", "/tickets/7"),
    milestones: api.defer("GET", "/tickets/7/milestones"),
    changes: api.defer("GET", "/tickets/7/state-changes"),
  });
  const release = async (held, data) => {
    await Promise.all([held.ticket.requested, held.milestones.requested, held.changes.requested]);
    held.changes.release(200, data.changes);
    held.milestones.release(200, data.milestones);
    held.ticket.release(200, data.ticket);
  };
  let held = reads();
  await page.goto("/#/tickets/7");
  await release(held, {
    ticket: withProducts("New"),
    milestones: [MILESTONE],
    changes: [{ state: "New", user: CLIENT_AUTHOR, timestamp: CREATED }],
  });
  await expect(page.locator(".ticket-state")).toHaveText("Nuevo");
  await expect(page.locator("ol.milestones")).toContainText("Primer mensaje");
  await expect(page.locator("ol.state-changes > li")).toHaveCount(1);

  api.on("POST", "/tickets/7/milestones", { status: 201, body: MILESTONE });
  held = reads();
  await milestoneForm(page).getByLabel("Mensaje").fill("Nuevo mensaje");
  await milestoneForm(page).getByLabel("Comenzar a trabajar").check();
  await button(page, "Agregar hito").click();
  await release(held, {
    ticket: withProducts("InProgress"),
    milestones: [{ ...MILESTONE, id: 2, content: "Nuevo mensaje", author: REP_AUTHOR }],
    changes: [
      { state: "InProgress", user: REP_AUTHOR, timestamp: "2026-01-02T12:00:00+00:00" },
      { state: "New", user: CLIENT_AUTHOR, timestamp: CREATED },
    ],
  });
  await expect(page.locator(".ticket-state")).toHaveText("En curso");
  await expect(page.locator("ol.milestones")).toContainText("Nuevo mensaje");
  await expect(page.locator("ol.state-changes > li")).toHaveCount(2);
});
