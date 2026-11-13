import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { USERS } from "./support/fixtures.js";

const PASSWORD_PATH = "/me/password";
const MISMATCH = "La nueva contraseña y su confirmación no coinciden.";
const UPDATED = "Contraseña actualizada.";
const WRONG_CURRENT = "La contraseña actual no es correcta.";

const field = (page, label) => page.getByLabel(label, { exact: true });
const form = (page) => page.getByRole("form", { name: "Cambiar contraseña" });
const passwordPosts = (api) =>
  api.requests.filter((r) => r.method === "POST" && r.url.endsWith(PASSWORD_PATH));

async function openAccount(page, role = "Client") {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS[role] });
  await page.goto("/#/account");
  await expect(page.getByRole("heading", { name: "Mi cuenta", exact: true })).toBeVisible();
  return api;
}

async function fill(page, current, next, confirmation) {
  await field(page, "Contraseña actual").fill(current);
  await field(page, "Nueva contraseña").fill(next);
  await field(page, "Confirmar nueva contraseña").fill(confirmation);
}

const submit = (page) => page.getByRole("button", { name: "Cambiar contraseña" }).click();

test("SPEC-UI-13 sends the current and new password without the confirmation (TC-UI-13a)", async ({
  page,
}) => {
  const api = await openAccount(page);
  api.on("POST", PASSWORD_PATH, { status: 204 });
  await fill(page, "vieja-123", "nueva-456", "nueva-456");
  await submit(page);
  await expect.poll(() => passwordPosts(api).length).toBe(1);
  expect(passwordPosts(api)[0].body).toEqual({
    current_password: "vieja-123",
    new_password: "nueva-456",
  });
});

test("SPEC-UI-122 shows the confirmation only on success (TC-UI-122a)", async ({ page }) => {
  const api = await openAccount(page);
  api.on("POST", PASSWORD_PATH, { status: 204 });
  await fill(page, "vieja-123", "nueva-456", "nueva-456");
  await submit(page);
  await expect(page.locator("#status")).toHaveText(UPDATED);
});

test("SPEC-UI-122 does not show the confirmation on a validation error (TC-UI-122b)", async ({
  page,
}) => {
  const api = await openAccount(page);
  api.on("POST", PASSWORD_PATH, {
    status: 400,
    body: { error: "validation_error", fields: { new_password: "invalid" } },
  });
  await fill(page, "vieja-123", "corta", "corta");
  await submit(page);
  await expect(page.getByText("El valor ingresado no es válido")).toBeVisible();
  await expect(page.getByText(UPDATED)).toHaveCount(0);
});

test("SPEC-UI-14 rejects a mismatched confirmation without calling the API (TC-UI-14b)", async ({
  page,
}) => {
  const api = await openAccount(page);
  api.on("POST", PASSWORD_PATH, { status: 204 });
  await fill(page, "vieja-123", "nueva-456", "otra-789");
  await submit(page);
  await expect(form(page).getByText(MISMATCH)).toBeVisible();
  expect(passwordPosts(api)).toHaveLength(0);
});

test("SPEC-UI-15 shows a wrong current password in the form and keeps the session (TC-UI-15a)", async ({
  page,
}) => {
  const api = await openAccount(page);
  api.on("POST", PASSWORD_PATH, { status: 400, body: { error: "invalid_current_password" } });
  await fill(page, "mala", "nueva-456", "nueva-456");
  await submit(page);
  await expect(form(page).getByText(WRONG_CURRENT)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Mi cuenta", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toHaveCount(0);
  expect(await page.evaluate(() => window.location.hash)).toBe("#/account");
});

async function expectEmptiedAfter(page, reply) {
  const api = await openAccount(page);
  api.on("POST", PASSWORD_PATH, reply);
  await fill(page, "vieja-123", "nueva-456", "nueva-456");
  await submit(page);
  await expect.poll(() => passwordPosts(api).length).toBe(1);
  for (const label of ["Contraseña actual", "Nueva contraseña", "Confirmar nueva contraseña"]) {
    await expect(field(page, label)).toHaveValue("");
  }
}

test("SPEC-UI-64 empties the password fields after a 204 (TC-UI-64a)", async ({ page }) => {
  await expectEmptiedAfter(page, { status: 204 });
});

test("SPEC-UI-64 empties the password fields after a 400 (TC-UI-64a)", async ({ page }) => {
  await expectEmptiedAfter(page, { status: 400, body: { error: "invalid_current_password" } });
});
