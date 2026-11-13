import { expect, test } from "@playwright/test";
import { ABORT, installFakeApi } from "./support/fake-api.js";
import { CLIENT, USERS } from "./support/fixtures.js";

const GENERIC = "Ocurrió un error inesperado. Intente nuevamente.";
const CONNECTION = "No se pudo conectar con el servidor. Intente nuevamente.";
const EXPIRED = "Tu sesión venció. Inicia sesión nuevamente.";

const heading = (page, name) => page.getByRole("heading", { name, exact: true });
const loading = (page) => page.getByText("Cargando…");
const currentHash = (page) => page.evaluate(() => window.location.hash);
const goToHash = (page, hash) =>
  page.evaluate((value) => {
    window.location.hash = value;
  }, hash);
const meRequests = (api) => api.requests.filter((r) => r.method === "GET" && r.url.endsWith("/me"));

test("SPEC-UI-07 shows the role home when the hash is empty (TC-UI-07c)", async ({ page }) => {
  const api = await installFakeApi(page);
  const expected = { Admin: "Usuarios", Representative: "Tickets", Client: "Tickets" };
  for (const [role, name] of Object.entries(expected)) {
    api.on("GET", "/me", { status: 200, body: USERS[role] });
    await page.goto("/");
    await expect(heading(page, name)).toBeVisible();
  }
});

test("SPEC-UI-07 shows the role home instead of the login for #/login (TC-UI-07d)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: CLIENT });
  await page.goto("/#/login");
  await expect(heading(page, "Tickets")).toBeVisible();
  await expect(heading(page, "Iniciar sesión")).toHaveCount(0);
  await expect.poll(() => currentHash(page)).toBe("#/tickets");
});

test("SPEC-UI-08 shows the login without an expiry notice on a 401 (TC-UI-08c)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 401, body: { error: "authentication_required" } });
  await page.goto("/#/tickets");
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await expect(page.getByText(EXPIRED)).toHaveCount(0);
  await expect.poll(() => currentHash(page)).toBe("#/login");
});

test("SPEC-UI-116 shows the screen named by the hash for a permitted role (TC-UI-116b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: CLIENT });
  await page.goto("/#/account");
  await expect(heading(page, "Mi cuenta")).toBeVisible();
});

test("SPEC-UI-117 shows the generic error with a retry on a 500 (TC-UI-117b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 500, body: { error: "internal_error" } });
  await page.goto("/");
  await expect(page.getByText(GENERIC)).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar" })).toBeVisible();
  await expect(heading(page, "Iniciar sesión")).toHaveCount(0);
});

test("SPEC-UI-117 shows the connection error with a retry when offline (TC-UI-117c)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", ABORT);
  await page.goto("/");
  await expect(page.getByText(CONNECTION)).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar" })).toBeVisible();
});

test("SPEC-UI-118 repeats GET /me and continues as the initial load (TC-UI-118b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", [
    { status: 500, body: { error: "internal_error" } },
    { status: 200, body: CLIENT },
  ]);
  await page.goto("/#/account");
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(heading(page, "Mi cuenta")).toBeVisible();
  expect(meRequests(api)).toHaveLength(2);
});

test("SPEC-UI-118 shows the login without a notice when the retry gets a 401 (TC-UI-118d)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", [
    { status: 500, body: { error: "internal_error" } },
    { status: 401, body: { error: "authentication_required" } },
  ]);
  await page.goto("/");
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await expect(page.getByText(EXPIRED)).toHaveCount(0);
});

test("SPEC-UI-127 keeps the loading state when the hash changes meanwhile (TC-UI-127b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  const me = api.defer("GET", "/me");
  await page.goto("/#/tickets");
  await me.requested;
  await expect(loading(page)).toBeVisible();
  await goToHash(page, "#/account");
  await expect(loading(page)).toBeVisible();
  await expect(heading(page, "Mi cuenta")).toHaveCount(0);
  me.release(200, CLIENT);
  await expect(heading(page, "Mi cuenta")).toBeVisible();
});

test("SPEC-UI-127 keeps the error when the hash changes and then retries (TC-UI-127c)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", [
    { status: 500, body: { error: "internal_error" } },
    { status: 200, body: CLIENT },
  ]);
  await page.goto("/");
  await expect(page.getByText(GENERIC)).toBeVisible();
  await goToHash(page, "#/account");
  await expect(page.getByText(GENERIC)).toBeVisible();
  await expect(heading(page, "Mi cuenta")).toHaveCount(0);
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(heading(page, "Mi cuenta")).toBeVisible();
});

test("SPEC-UI-127 shows the login without a notice when a 401 follows a hash change (TC-UI-127e)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  const me = api.defer("GET", "/me");
  await page.goto("/");
  await me.requested;
  await goToHash(page, "#/users");
  me.release(401, { error: "authentication_required" });
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await expect(page.getByText(EXPIRED)).toHaveCount(0);
  await expect.poll(() => currentHash(page)).toBe("#/login");
});

test("SPEC-UI-71 shows a loading indicator while GET /me is pending (TC-UI-71b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  const me = api.defer("GET", "/me");
  await page.goto("/");
  await me.requested;
  await expect(loading(page)).toBeVisible();
  me.release(401, { error: "authentication_required" });
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await expect(loading(page)).toHaveCount(0);
});
