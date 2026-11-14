import { expect, test } from "@playwright/test";
import { installFakeApi, loginAs } from "./support/fake-api.js";
import { page as pageOf, ticket } from "./support/fixtures.js";

const CREATED_AT = "2026-01-01T12:00:00+00:00";
const TYPES = [
  { id: 4, name: "Portátiles" },
  { id: 5, name: "Impresoras" },
];

async function openTickets(page) {
  const api = await installFakeApi(page);
  api.on("GET", /^\/tickets\?/, { status: 200, body: pageOf([ticket(1, "New", CREATED_AT)]) });
  api.on("GET", "/product-types", { status: 200, body: TYPES });
  await loginAs(page, api, "Representative");
  await page.goto("/#/tickets");
  await expect(page.locator(".loading")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Tickets", exact: true })).toBeVisible();
  return api;
}

const dialogNamed = (page, name) => page.getByRole("dialog", { name });

test("SPEC-UI-219 opens the empty client dialog without changing the hash (TC-UI-219a)", async ({
  page,
}) => {
  const api = await openTickets(page);
  const before = api.requests.length;
  await page.getByRole("button", { name: "Nuevo cliente", exact: true }).click();
  const dialog = dialogNamed(page, "Nuevo cliente");
  await expect(dialog).toBeVisible();
  for (const label of ["Nombre", "Email", "Contraseña", "Canal"]) {
    await expect(dialog.getByLabel(label)).toBeVisible();
    await expect(dialog.getByLabel(label)).toHaveValue("");
  }
  await expect(dialog.getByLabel("Rol")).toHaveCount(0);
  await expect(dialog.getByRole("button", { name: "Cancelar" })).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Crear" })).toBeVisible();
  await expect(dialog.getByLabel("Nombre")).toBeFocused();
  expect(new URL(page.url()).hash).toBe("#/tickets");
  expect(api.requests.length).toBe(before);
});

test("SPEC-UI-222 opens the empty product dialog with the product types (TC-UI-222a)", async ({
  page,
}) => {
  const api = await openTickets(page);
  await page.getByRole("button", { name: "Nuevo producto", exact: true }).click();
  const dialog = dialogNamed(page, "Nuevo producto");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Nombre")).toHaveValue("");
  await expect(dialog.getByLabel("Tipo").locator("option", { hasText: "Impresoras" })).toHaveCount(1);
  await expect(dialog.getByLabel("Tipo").locator("option", { hasText: "Portátiles" })).toHaveCount(1);
  expect(new URL(page.url()).hash).toBe("#/tickets");
  const reads = api.requests.filter((r) => new URL(r.url).pathname === "/product-types");
  expect(reads.length).toBeGreaterThan(0);
});
