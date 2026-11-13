import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { REP, page as pageOf, ticket } from "./support/fixtures.js";

const TICKETS_PATH = /^\/tickets\?/;
const ROWS = [ticket(1, "New", "2026-01-01T12:00:00+00:00")];
const ROWS_LATE = [ticket(21, "InProgress", "2026-02-02T12:00:00+00:00")];
const EXPIRED = "Tu sesión venció. Inicia sesión nuevamente.";

const logoutButton = (page) => page.getByRole("button", { name: "Cerrar sesión", exact: true });
const nextButton = (page) => page.getByRole("button", { name: "Siguiente", exact: true });
const listHeading = (page) => page.getByRole("heading", { name: "Tickets", exact: true });
const loginHeading = (page) => page.getByRole("heading", { name: "Iniciar sesión", exact: true });
const rowFor = (page, id) => page.getByRole("row").filter({ hasText: `#${id}` });
const currentHash = (page) => page.evaluate(() => window.location.hash);
const settle = (page) =>
  page.evaluate(() => new Promise((done) => setTimeout(() => requestAnimationFrame(done), 50)));

async function openList(page, { total = 40 } = {}) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: REP });
  api.on("GET", TICKETS_PATH, (record) => ({
    status: 200,
    body: pageOf(ROWS, Number(new URL(record.url).searchParams.get("page")), total),
  }));
  const logout = api.defer("POST", "/logout");
  await page.goto("/#/tickets");
  await expect(rowFor(page, 1)).toBeVisible();
  return { api, logout };
}

async function startLogout(page, logout) {
  await logoutButton(page).click();
  await logout.requested;
}

const callsTo = (api, method, path) =>
  api.requests.filter((r) => r.method === method && new URL(r.url).pathname === path);

async function expectPlainLogin(page) {
  await expect(loginHeading(page)).toBeVisible();
  await expect(page.locator("#status")).not.toContainText(EXPIRED);
  expect(await currentHash(page)).toBe("#/login");
}

test("SPEC-UI-11 sends one POST /logout and no other request after the click (TC-UI-11b)", async ({
  page,
}) => {
  const { api, logout } = await openList(page);
  await startLogout(page, logout);
  const before = api.requests.length;
  await logoutButton(page).click({ force: true });
  await settle(page);
  expect(callsTo(api, "POST", "/logout")).toHaveLength(1);
  expect(api.requests).toHaveLength(before);
  logout.release(204);
  await expectPlainLogin(page);
});

test("SPEC-UI-11 a listing answer sent before the click draws no rows (TC-UI-11c)", async ({
  page,
}) => {
  const { api, logout } = await openList(page);
  const late = api.defer("GET", TICKETS_PATH);
  await nextButton(page).click();
  await late.requested;
  await startLogout(page, logout);
  late.release(200, pageOf(ROWS_LATE, 2, 40));
  await expect.poll(() => callsTo(api, "GET", "/tickets").at(-1).status).toBe(200);
  await settle(page);
  await expect(rowFor(page, 21)).toHaveCount(0);
  logout.release(204);
  await expectPlainLogin(page);
});

async function settleLogoutWith(page, answer) {
  const { logout } = await openList(page);
  await startLogout(page, logout);
  answer(logout);
  await expectPlainLogin(page);
}

test("SPEC-UI-129 shows the login without notice on a 204 (TC-UI-129a)", async ({ page }) => {
  await settleLogoutWith(page, (logout) => logout.release(204));
});

test("SPEC-UI-129 shows the login without notice on a 500 (TC-UI-129b)", async ({ page }) => {
  await settleLogoutWith(page, (logout) => logout.release(500, { error: "boom" }));
});

test("SPEC-UI-129 shows the login without notice on a 401 (TC-UI-129c)", async ({ page }) => {
  await settleLogoutWith(page, (logout) => logout.release(401, { error: "no" }));
});

test("SPEC-UI-129 shows the login without notice when the connection fails (TC-UI-129d)", async ({
  page,
}) => {
  await settleLogoutWith(page, (logout) => logout.abort());
});

test("SPEC-UI-130 a 401 released before POST /logout answers shows no notice (TC-UI-130b)", async ({
  page,
}) => {
  const { api, logout } = await openList(page);
  const late = api.defer("GET", TICKETS_PATH);
  await nextButton(page).click();
  await late.requested;
  await startLogout(page, logout);
  late.release(401, { error: "no" });
  await expect.poll(() => callsTo(api, "GET", "/tickets").at(-1).status).toBe(401);
  await settle(page);
  await expect(page.locator("#status")).not.toContainText(EXPIRED);
  await expect(listHeading(page)).toBeVisible();
  logout.release(204);
  await expectPlainLogin(page);
});

test("SPEC-UI-130 a 200 released after POST /logout answers draws no rows (TC-UI-130c)", async ({
  page,
}) => {
  const { api, logout } = await openList(page);
  const late = api.defer("GET", TICKETS_PATH);
  await nextButton(page).click();
  await late.requested;
  await startLogout(page, logout);
  logout.release(204);
  await expectPlainLogin(page);
  late.release(200, pageOf(ROWS_LATE, 2, 40));
  await expect.poll(() => callsTo(api, "GET", "/tickets").at(-1).status).toBe(200);
  await settle(page);
  await expect(rowFor(page, 21)).toHaveCount(0);
  await expectPlainLogin(page);
});

test("SPEC-UI-131 keeps the shown screen and sends nothing when the hash changes (TC-UI-131b)", async ({
  page,
}) => {
  const { api, logout } = await openList(page);
  await startLogout(page, logout);
  const before = api.requests.length;
  await page.evaluate(() => {
    window.location.hash = "#/account";
  });
  await settle(page);
  await expect(listHeading(page)).toBeVisible();
  expect(api.requests).toHaveLength(before);
  logout.release(204);
  await expectPlainLogin(page);
});

test("SPEC-UI-133 inert listing controls send nothing and change nothing (TC-UI-133b)", async ({
  page,
}) => {
  const { api, logout } = await openList(page);
  await startLogout(page, logout);
  const before = api.requests.length;
  await nextButton(page).click({ force: true });
  await page
    .getByLabel("Estado", { exact: true })
    .selectOption({ label: "En curso" }, { force: true });
  await page.getByRole("search").dispatchEvent("submit");
  await logoutButton(page).click({ force: true });
  await settle(page);
  expect(api.requests).toHaveLength(before);
  await expect(page.getByText("Página 1", { exact: true })).toBeVisible();
  await expect(rowFor(page, 1)).toBeVisible();
  await expect(page.getByLabel("Estado", { exact: true })).toHaveValue("");
  logout.release(204);
  await expectPlainLogin(page);
});

test("SPEC-UI-133 an inert ticket action sends nothing (TC-UI-133b)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: REP });
  api.on("GET", "/tickets/7", {
    status: 200,
    body: ticket(7, "InProgress", "2026-01-01T12:00:00+00:00"),
  });
  const logout = api.defer("POST", "/logout");
  await page.goto("/#/tickets/7");
  const close = page.getByRole("button", { name: "Cerrar", exact: true });
  await expect(close).toBeVisible();
  await startLogout(page, logout);
  const before = api.requests.length;
  await close.click({ force: true });
  await close.dispatchEvent("click");
  await settle(page);
  expect(api.requests).toHaveLength(before);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  logout.release(204);
  await expectPlainLogin(page);
});

test("SPEC-UI-133 inert navigation links and disabled buttons do nothing (TC-UI-133c)", async ({
  page,
}) => {
  const { api, logout } = await openList(page);
  await startLogout(page, logout);
  const before = api.requests.length;
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Mi cuenta" })
    .dispatchEvent("click");
  await page.getByRole("button", { name: "Anterior", exact: true }).dispatchEvent("click");
  await settle(page);
  expect(api.requests).toHaveLength(before);
  await expect(listHeading(page)).toBeVisible();
  logout.release(204);
  await expectPlainLogin(page);
});

test("SPEC-UI-134 disables every control and link while POST /logout is pending (TC-UI-134a)", async ({
  page,
}) => {
  const { logout } = await openList(page);
  await startLogout(page, logout);
  const flags = await page.evaluate(() => {
    const scope = [document.getElementById("shell"), document.getElementById("app")];
    const inside = (selector) => scope.flatMap((node) => [...node.querySelectorAll(selector)]);
    return {
      controls: inside("button, input, select, textarea").every((node) => node.disabled),
      links: inside("a").every((node) => node.getAttribute("aria-disabled") === "true"),
      count: inside("button, input, select, textarea, a").length,
    };
  });
  expect(flags.count).toBeGreaterThan(5);
  expect(flags.controls).toBe(true);
  expect(flags.links).toBe(true);
  logout.release(204);
  await expectPlainLogin(page);
});
