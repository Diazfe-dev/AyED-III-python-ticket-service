import { expect, test } from "@playwright/test";
import { installFakeApi, loginAs } from "./support/fake-api.js";
import { REP, historyLength, page as pageOf, ticket } from "./support/fixtures.js";

const TICKETS_PATH = /^\/tickets\?/;
const EXPIRED = "Tu sesión venció. Inicia sesión nuevamente.";
const ROWS_A = [ticket(1, "New", "2026-01-01T12:00:00+00:00")];
const ROWS_B = [ticket(2, "InProgress", "2026-01-02T12:00:00+00:00")];
const ROWS_LATE = [ticket(21, "InProgress", "2026-02-02T12:00:00+00:00")];
const ANA = { id: 11, name: "Ana Gómez" };

const loginHeading = (page) => page.getByRole("heading", { name: "Iniciar sesión", exact: true });
const rowFor = (page, id) => page.getByRole("row").filter({ hasText: `#${id}` });
const nextButton = (page) => page.getByRole("button", { name: "Siguiente", exact: true });
const stateFilter = (page) => page.getByLabel("Estado", { exact: true });
const callsTo = (api, method, path) =>
  api.requests.filter((r) => r.method === method && new URL(r.url).pathname === path);
const settle = (page) =>
  page.evaluate(() => new Promise((done) => setTimeout(() => requestAnimationFrame(done), 50)));

async function openList(page, rows = ROWS_A) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: REP });
  api.on("GET", TICKETS_PATH, (record) => ({
    status: 200,
    body: pageOf(rows, Number(new URL(record.url).searchParams.get("page")), 40),
  }));
  await page.goto("/#/tickets");
  await expect(rowFor(page, rows[0].id)).toBeVisible();
  return api;
}

async function expectExpiredLogin(page) {
  await expect(loginHeading(page)).toBeVisible();
  await expect(page.locator("#status")).toContainText(EXPIRED);
  expect(await page.evaluate(() => window.location.hash)).toBe("#/login");
}

test("SPEC-UI-12 a 401 on the listing shows the login with the notice (TC-UI-12c)", async ({
  page,
}) => {
  const api = await openList(page);
  api.on("GET", TICKETS_PATH, { status: 401, body: { error: "no" } });
  await nextButton(page).click();
  await expectExpiredLogin(page);
  await expect(rowFor(page, 1)).toHaveCount(0);
});

test("SPEC-UI-130 a late 200 after a 401 draws nothing and adds no notice (TC-UI-130d)", async ({
  page,
}) => {
  const api = await openList(page);
  const first = api.defer("GET", TICKETS_PATH);
  await nextButton(page).click();
  await first.requested;
  const second = api.defer("GET", TICKETS_PATH);
  await stateFilter(page).selectOption({ label: "En curso" });
  await second.requested;
  second.release(401, { error: "no" });
  await expectExpiredLogin(page);
  first.release(200, pageOf(ROWS_LATE, 2, 40));
  await expect.poll(() => callsTo(api, "GET", "/tickets")[1].status).toBe(200);
  await settle(page);
  await expect(rowFor(page, 21)).toHaveCount(0);
  await expect(page.locator("#status")).toHaveText(EXPIRED);
  await expectExpiredLogin(page);
});

test("SPEC-UI-128 keeps the history length when the login is shown (TC-UI-128b)", async ({
  page,
}) => {
  const api = await openList(page);
  const logout = api.defer("POST", "/logout");
  const beforeLogout = await historyLength(page);
  await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
  await logout.requested;
  logout.release(204);
  await expect(loginHeading(page)).toBeVisible();
  expect(await historyLength(page)).toBe(beforeLogout);

  await page.evaluate(() => {
    window.location.hash = "#/users";
  });
  const afterHashChange = await historyLength(page);
  await settle(page);
  await expect(loginHeading(page)).toBeVisible();
  expect(await page.evaluate(() => window.location.hash)).toBe("#/login");
  expect(await historyLength(page)).toBe(afterHashChange);
});

test("SPEC-UI-128 a 401 answer keeps the history length (TC-UI-128b)", async ({ page }) => {
  const api = await openList(page);
  const beforeExpiry = await historyLength(page);
  api.on("GET", TICKETS_PATH, { status: 401, body: { error: "no" } });
  await nextButton(page).click();
  await expectExpiredLogin(page);
  expect(await historyLength(page)).toBe(beforeExpiry);
});

test("SPEC-UI-128 a 401 on the first GET /me keeps the history length (TC-UI-128b)", async ({
  page,
}) => {
  await page.addInitScript(() => {
    if (!window.sessionStorage.getItem("startLength")) {
      window.sessionStorage.setItem("startLength", String(window.history.length));
    }
  });
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 401, body: { error: "no" } });
  await page.goto("/#/tickets");
  await expect(loginHeading(page)).toBeVisible();
  expect(await page.evaluate(() => window.location.hash)).toBe("#/login");
  const start = Number(await page.evaluate(() => window.sessionStorage.getItem("startLength")));
  expect(await historyLength(page)).toBe(start);
});

test("SPEC-UI-135 a stale 401 of a replaced listing request shows the notice (TC-UI-135g)", async ({
  page,
}) => {
  const api = await openList(page);
  const stale = api.defer("GET", /^\/tickets\?state=New/);
  await stateFilter(page).selectOption({ label: "Nuevo" });
  await stale.requested;
  api.on("GET", /^\/tickets\?state=InProgress/, { status: 200, body: pageOf(ROWS_B, 1, 1) });
  await stateFilter(page).selectOption({ label: "En curso" });
  await expect(rowFor(page, 2)).toBeVisible();
  stale.release(401, { error: "no" });
  await expectExpiredLogin(page);
});

test("SPEC-UI-136 a 401 of a previous screen instance shows the notice (TC-UI-136g)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/clients", { status: 200, body: [ANA] });
  await loginAs(page, api, "Representative");
  await page.goto("/#/tickets/new");
  await expect(page.getByLabel("Cliente", { exact: true }).locator("option")).toHaveCount(2);
  const gate = api.defer("POST", "/tickets");
  await page.getByLabel("Cliente", { exact: true }).selectOption({ label: "Ana Gómez" });
  await page.getByLabel("Primer mensaje", { exact: true }).fill("No enciende");
  await page.getByRole("button", { name: "Crear ticket" }).click();
  await gate.requested;
  await page.getByRole("link", { name: "Mi cuenta", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Mi cuenta", exact: true })).toBeVisible();
  gate.release(401, { error: "no" });
  await expectExpiredLogin(page);
});
