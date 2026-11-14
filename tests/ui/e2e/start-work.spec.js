import { expect, test } from "@playwright/test";
import { ABORT, installFakeApi, loginAs } from "./support/fake-api.js";
import { REP, ticket } from "./support/fixtures.js";

const CREATED = "2026-01-01T12:00:00+00:00";
const START_WORK_MESSAGE = "El representante comenzó a trabajar en tu consulta.";
const REP_AUTHOR = { id: REP.id, name: REP.name, role: "Representative" };
const STARTED = { id: 2, content: START_WORK_MESSAGE, author: REP_AUTHOR, created_at: CREATED };
const CHANGE = { state: "InProgress", user: REP_AUTHOR, timestamp: CREATED };

const startButton = (page) => page.getByRole("button", { name: "Comenzar a trabajar", exact: true });
const posts = (api) =>
  api.requests.filter(
    (r) => r.method === "POST" && new URL(r.url).pathname === "/tickets/7/milestones",
  );

async function openDetail(page, role, state) {
  const api = await installFakeApi(page);
  api.on("GET", "/tickets/7", { status: 200, body: ticket(7, state, CREATED) });
  api.on("GET", "/tickets/7/milestones", { status: 200, body: [] });
  api.on("GET", "/tickets/7/state-changes", { status: 200, body: [] });
  await loginAs(page, api, role);
  await page.goto("/#/tickets/7");
  await expect(page.getByRole("heading", { name: "Ticket #7", exact: true })).toBeVisible();
  await expect(page.locator(".ticket-state")).toBeVisible();
  return api;
}

test("SPEC-UI-211 the representative sees the start-work button in the header (TC-UI-211b)", async ({
  page,
}) => {
  await openDetail(page, "Representative", "New");
  await expect(startButton(page)).toBeVisible();
  await expect(page.locator(".page-header").getByRole("button", { name: "Comenzar a trabajar" })).toBeVisible();
  await expect(page.getByRole("form", { name: "Agregar hito" }).getByRole("button", { name: "Comenzar a trabajar" })).toHaveCount(0);
  await page.setViewportSize({ width: 360, height: 740 });
  await expect(startButton(page)).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

async function expectsNoStartWork(page, role, state) {
  await openDetail(page, role, state);
  await expect(startButton(page)).toHaveCount(0);
  await expect(page.locator("#app")).not.toContainText("Comenzar a trabajar");
}

test("SPEC-UI-212 the representative sees no start-work on an InProgress ticket (TC-UI-212b)", async ({
  page,
}) => {
  await expectsNoStartWork(page, "Representative", "InProgress");
});

test("SPEC-UI-212 the representative sees no start-work on a Closed ticket (TC-UI-212b)", async ({
  page,
}) => {
  await expectsNoStartWork(page, "Representative", "Closed");
});

test("SPEC-UI-213 the client sees no start-work (TC-UI-213b)", async ({ page }) => {
  await expectsNoStartWork(page, "Client", "New");
  await expect(page.locator("#app")).not.toContainText("Comenzar a trabajar");
});

test("SPEC-UI-213 the administrator sees no start-work (TC-UI-213b)", async ({ page }) => {
  await expectsNoStartWork(page, "Admin", "New");
  await expect(page.locator("#app")).not.toContainText("Comenzar a trabajar");
});

test("SPEC-UI-214 starts work with a fixed milestone and reloads the detail (TC-UI-214a)", async ({
  page,
}) => {
  const api = await openDetail(page, "Representative", "New");
  api.on("POST", "/tickets/7/milestones", { status: 201, body: STARTED });
  api.on("GET", "/tickets/7", { status: 200, body: ticket(7, "InProgress", CREATED) });
  api.on("GET", "/tickets/7/milestones", { status: 200, body: [STARTED] });
  api.on("GET", "/tickets/7/state-changes", { status: 200, body: [CHANGE] });
  const before = api.requests.length;
  await startButton(page).click();
  await expect(page.locator(".ticket-state")).toHaveText("En curso");
  await expect(page.locator("ol.milestones")).toContainText(START_WORK_MESSAGE);
  await expect(startButton(page)).toHaveCount(0);
  expect(posts(api)).toHaveLength(1);
  expect(posts(api)[0].body).toEqual({ content: START_WORK_MESSAGE, start_progress: true });
  const after = api.requests.slice(before).map((r) => `${r.method} ${new URL(r.url).pathname}`);
  expect(after[0]).toBe("POST /tickets/7/milestones");
  expect(after).toEqual(
    expect.arrayContaining([
      "GET /tickets/7",
      "GET /tickets/7/milestones",
      "GET /tickets/7/state-changes",
    ]),
  );
});

test("SPEC-UI-214 disables the button while the request is pending (TC-UI-214b)", async ({
  page,
}) => {
  const api = await openDetail(page, "Representative", "New");
  const pending = api.defer("POST", "/tickets/7/milestones");
  await startButton(page).click();
  await pending.requested;
  await expect(startButton(page)).toBeDisabled();
  await startButton(page).click({ force: true });
  await startButton(page).dispatchEvent("click");
  api.on("GET", "/tickets/7", { status: 200, body: ticket(7, "InProgress", CREATED) });
  pending.release(201, STARTED);
  await expect(page.locator(".ticket-state")).toHaveText("En curso");
  expect(posts(api)).toHaveLength(1);
});

async function expectsUnchanged(page, api, reads, message) {
  await expect(page.locator("#alert")).toContainText(message);
  await expect(page.locator(".ticket-state")).toHaveText("Nuevo");
  await expect(page.locator("ol.milestones > li")).toHaveCount(0);
  await expect(startButton(page)).toBeEnabled();
  expect(api.requests.length).toBe(reads);
  expect(posts(api)).toHaveLength(1);
}

const FAILURES = [
  [409, { error: "invalid_transition", message: "Invalid transition" }, "Esa acción no está permitida en el estado actual del ticket."],
  [403, { error: "forbidden", message: "Forbidden" }, "No tiene permiso para realizar esta acción."],
  [500, { error: "internal_error", message: "Internal error" }, "Ocurrió un error inesperado. Intente nuevamente."],
];

async function failsWith(page, [status, body, message]) {
  const api = await openDetail(page, "Representative", "New");
  api.on("POST", "/tickets/7/milestones", { status, body });
  const reads = api.requests.length + 1;
  await startButton(page).click();
  await expectsUnchanged(page, api, reads, message);
}

test("SPEC-UI-215 shows the conflict error and keeps the ticket (TC-UI-215a)", async ({ page }) => {
  await failsWith(page, FAILURES[0]);
});

test("SPEC-UI-215 shows the forbidden error and keeps the ticket (TC-UI-215a)", async ({ page }) => {
  await failsWith(page, FAILURES[1]);
});

test("SPEC-UI-215 shows the server error and keeps the ticket (TC-UI-215a)", async ({ page }) => {
  await failsWith(page, FAILURES[2]);
});

test("SPEC-UI-215 shows the connection error and keeps the ticket (TC-UI-215b)", async ({
  page,
}) => {
  const api = await openDetail(page, "Representative", "New");
  api.on("POST", "/tickets/7/milestones", ABORT);
  const reads = api.requests.length + 1;
  await startButton(page).click();
  await expectsUnchanged(page, api, reads, "No se pudo conectar con el servidor. Intente nuevamente.");
});
