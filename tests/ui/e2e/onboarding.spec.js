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

const clientDialog = (page) => dialogNamed(page, "Nuevo cliente");
const usersPosts = (api) =>
  api.requests.filter((r) => r.method === "POST" && new URL(r.url).pathname === "/users");
const ticketReads = (api) =>
  api.requests.filter((r) => r.method === "GET" && new URL(r.url).pathname === "/tickets");

async function openClient(page, api) {
  await page.getByRole("button", { name: "Nuevo cliente", exact: true }).click();
  await expect(clientDialog(page)).toBeVisible();
  return clientDialog(page);
}

async function fillClient(dialog, { name = "Nora Díaz", channel = null } = {}) {
  await dialog.getByLabel("Nombre").fill(name);
  await dialog.getByLabel("Email").fill("nora@example.com");
  await dialog.getByLabel("Contraseña", { exact: true }).fill("clave-larga-1");
  if (channel !== null) {
    await dialog.getByLabel("Canal").selectOption(channel);
  }
}

test("SPEC-UI-220 posts the client with the fixed Client role and the optional channel (TC-UI-220a)", async ({
  page,
}) => {
  const api = await openTickets(page);
  api.on("POST", "/users", { status: 201, body: { id: 9 } });
  let dialog = await openClient(page, api);
  await fillClient(dialog);
  await dialog.getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => usersPosts(api).length).toBe(1);
  expect(usersPosts(api)[0].body).toEqual({
    name: "Nora Díaz",
    email: "nora@example.com",
    password: "clave-larga-1",
    role: "Client",
  });
  await expect(clientDialog(page)).toHaveCount(0);
  dialog = await openClient(page, api);
  await fillClient(dialog, { channel: "whatsapp" });
  await dialog.getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => usersPosts(api).length).toBe(2);
  expect(usersPosts(api)[1].body).toEqual({
    name: "Nora Díaz",
    email: "nora@example.com",
    password: "clave-larga-1",
    role: "Client",
    preferred_channel: "whatsapp",
  });
});

async function failsClient(page, reply, expectations) {
  const api = await openTickets(page);
  api.on("POST", "/users", reply);
  const dialog = await openClient(page, api);
  await fillClient(dialog);
  await dialog.getByRole("button", { name: "Crear" }).click();
  await expectations(dialog);
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Nombre")).toHaveValue("Nora Díaz");
  await expect(dialog.getByLabel("Email")).toHaveValue("nora@example.com");
  await expect(dialog.getByLabel("Contraseña", { exact: true })).toHaveValue("");
}

test("SPEC-UI-220 marks the invalid client fields inside the dialog (TC-UI-220b)", async ({
  page,
}) => {
  const reply = {
    status: 400,
    body: { error: "validation_error", fields: { name: "required", email: "invalid" } },
  };
  await failsClient(page, reply, async (dialog) => {
    await expect(dialog.locator(".field", { has: page.getByLabel("Nombre") })).toContainText(
      "Este campo es obligatorio",
    );
    await expect(dialog.locator(".field", { has: page.getByLabel("Email") })).toContainText(
      "El valor ingresado no es válido",
    );
  });
});

test("SPEC-UI-220 shows the duplicate email error inside the dialog (TC-UI-220b)", async ({
  page,
}) => {
  await failsClient(page, { status: 409, body: { error: "duplicate_email" } }, async (dialog) => {
    await expect(dialog.getByRole("alert")).toHaveText("Ya existe un usuario con ese email.");
  });
});

test("SPEC-UI-220 shows the forbidden error inside the dialog (TC-UI-220b)", async ({ page }) => {
  await failsClient(page, { status: 403, body: { error: "forbidden" } }, async (dialog) => {
    await expect(dialog.getByRole("alert")).toHaveText("No tiene permiso para realizar esta acción.");
  });
});

test("SPEC-UI-221 closes the dialog and confirms without reloading the tickets (TC-UI-221b)", async ({
  page,
}) => {
  const api = await openTickets(page);
  api.on("POST", "/users", { status: 201, body: { id: 9 } });
  const dialog = await openClient(page, api);
  await fillClient(dialog);
  const reads = ticketReads(api).length;
  await dialog.getByRole("button", { name: "Crear" }).click();
  await expect(clientDialog(page)).toHaveCount(0);
  await expect(page.getByRole("status")).toHaveText("Cliente creado.");
  expect(ticketReads(api).length).toBe(reads);
});
