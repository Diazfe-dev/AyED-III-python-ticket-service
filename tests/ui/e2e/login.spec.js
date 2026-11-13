import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { ADMIN, CLIENT } from "./support/fixtures.js";

const CONNECTION = "No se pudo conectar con el servidor. Intente nuevamente.";
const INVALID = "Email o contraseña incorrectos.";
const EXPIRED = "Tu sesión venció. Inicia sesión nuevamente.";
const NO_SESSION = { status: 401, body: { error: "authentication_required" } };

const heading = (page, name) => page.getByRole("heading", { name, exact: true });
const emailField = (page) => page.getByLabel("Email");
const passwordField = (page) => page.getByLabel("Contraseña");
const submit = (page) => page.getByRole("button", { name: "Ingresar", exact: true });
const currentHash = (page) => page.evaluate(() => window.location.hash);
const goToHash = (page, hash) =>
  page.evaluate((value) => {
    window.location.hash = value;
  }, hash);
const loginRequests = (api) => api.requests.filter((r) => r.url.endsWith("/login"));

async function openLogin(page, api) {
  api.on("GET", "/me", NO_SESSION);
  await page.goto("/");
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
}

async function fillAndSubmit(page, email = CLIENT.email, password = "Clave-segura-123") {
  await emailField(page).fill(email);
  await passwordField(page).fill(password);
  await submit(page).click();
}

test("SPEC-UI-09 sends the credentials and shows the role home (TC-UI-09b)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("POST", "/login", { status: 200, body: CLIENT });
  await openLogin(page, api);
  api.on("GET", "/me", { status: 200, body: CLIENT });
  await fillAndSubmit(page);
  await expect(heading(page, "Tickets")).toBeVisible();
  await expect.poll(() => currentHash(page)).toBe("#/tickets");
  expect(loginRequests(api)[0].body).toEqual({
    email: CLIENT.email,
    password: "Clave-segura-123",
  });
});

test("SPEC-UI-10 shows the generic invalid credentials message (TC-UI-10b)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("POST", "/login", { status: 401, body: { error: "invalid_credentials" } });
  await openLogin(page, api);
  await fillAndSubmit(page);
  await expect(page.getByRole("alert")).toHaveText(INVALID);
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await expect.poll(() => currentHash(page)).toBe("#/login");
  await expect(page.getByText(EXPIRED)).toHaveCount(0);
});

test("SPEC-UI-64 clears the password and keeps the email after a rejected login (TC-UI-64b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("POST", "/login", { status: 401, body: { error: "invalid_credentials" } });
  await openLogin(page, api);
  await fillAndSubmit(page);
  await expect(page.getByRole("alert")).toHaveText(INVALID);
  await expect(passwordField(page)).toHaveValue("");
  await expect(emailField(page)).toHaveValue(CLIENT.email);
});

test("SPEC-UI-117 keeps the error and does not return to the login when GET /me fails after login (TC-UI-117d)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("POST", "/login", { status: 200, body: CLIENT });
  await openLogin(page, api);
  api.on("GET", "/me", { status: 503 });
  await fillAndSubmit(page);
  await expect(page.getByText(CONNECTION)).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar" })).toBeVisible();
  await expect(heading(page, "Iniciar sesión")).toHaveCount(0);
});

test("SPEC-UI-118 retries GET /me after login and shows the role home (TC-UI-118c)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("POST", "/login", { status: 200, body: ADMIN });
  await openLogin(page, api);
  api.on("GET", "/me", [
    { status: 500, body: { error: "internal_error" } },
    { status: 200, body: ADMIN },
  ]);
  await fillAndSubmit(page, ADMIN.email);
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(heading(page, "Usuarios")).toBeVisible();
  await expect.poll(() => currentHash(page)).toBe("#/users");
});

test("SPEC-UI-126 keeps showing the login without a notice for any other hash (TC-UI-126d)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await openLogin(page, api);
  const before = api.requests.length;
  for (const hash of ["", "#/users", "#/tickets/abc", "#/desconocido"]) {
    await goToHash(page, hash);
    await expect(heading(page, "Iniciar sesión")).toBeVisible();
    await expect(page.getByText(EXPIRED)).toHaveCount(0);
    await expect.poll(() => currentHash(page)).toBe("#/login");
  }
  expect(api.requests).toHaveLength(before);
});

test("SPEC-UI-126 keeps the form and the pending login when the hash changes (TC-UI-126e)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  const login = api.defer("POST", "/login");
  await openLogin(page, api);
  api.on("GET", "/me", { status: 200, body: ADMIN });
  await emailField(page).fill(ADMIN.email);
  await passwordField(page).fill("Clave-segura-123");
  await submit(page).click();
  await login.requested;
  await goToHash(page, "#/users");
  await expect.poll(() => currentHash(page)).toBe("#/login");
  await expect(emailField(page)).toHaveValue(ADMIN.email);
  login.release(200, ADMIN);
  await expect(heading(page, "Usuarios")).toBeVisible();
  await expect.poll(() => currentHash(page)).toBe("#/users");
  expect(loginRequests(api)).toHaveLength(1);
});

test("SPEC-UI-127 shows the loading state while the GET /me after login is pending (TC-UI-127d)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("POST", "/login", { status: 200, body: CLIENT });
  await openLogin(page, api);
  const me = api.defer("GET", "/me");
  await fillAndSubmit(page);
  await me.requested;
  await expect(page.getByText("Cargando…")).toBeVisible();
  await goToHash(page, "#/account");
  await expect(page.getByText("Cargando…")).toBeVisible();
  me.release(200, CLIENT);
  await expect(heading(page, "Tickets")).toBeVisible();
  await expect.poll(() => currentHash(page)).toBe("#/tickets");
});
