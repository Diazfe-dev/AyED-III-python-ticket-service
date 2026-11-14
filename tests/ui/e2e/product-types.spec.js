import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { USERS } from "./support/fixtures.js";

const LAPTOP = { id: 4, name: "Notebook" };
const ROUTER = { id: 6, name: "Router" };
const LIST_PATH = /^\/product-types(\?.*)?$/;

const listRequests = (api) =>
  api.requests.filter((r) => r.method === "GET" && /\/product-types(\?|$)/.test(r.url));
const writes = (api, method) =>
  api.requests.filter((r) => r.method === method && /\/product-types(\/|$)/.test(r.url));

async function openProductTypes(page, items = [LAPTOP, ROUTER]) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Admin });
  api.on("GET", LIST_PATH, { status: 200, body: items });
  await page.goto("/#/product-types");
  await expect(page.getByRole("heading", { name: "Tipos de producto", exact: true })).toBeVisible();
  return api;
}

test("SPEC-UI-200 shows one row per product type in API order with Nombre and Acciones (TC-UI-200a)", async ({
  page,
}) => {
  await openProductTypes(page, [
    { id: 8, name: "Impresoras" },
    { id: 4, name: "Portátiles" },
  ]);
  const table = page.getByRole("table", { name: "Tipos de producto", exact: true });
  await expect(table.locator("thead th")).toHaveText(["Nombre", "Acciones"]);
  await expect(table.locator("tbody tr")).toHaveCount(2);
  await expect(table.locator("tbody tr").nth(0).locator("td").first()).toHaveText("Impresoras");
  await expect(table.locator("tbody tr").nth(1).locator("td").first()).toHaveText("Portátiles");
  await expect(page.locator("fieldset")).toHaveCount(0);
  await expect(page.getByText("Categoría")).toHaveCount(0);
});

test("SPEC-UI-200 reads the product types with a single request and never asks for categories (TC-UI-200b)", async ({
  page,
}) => {
  const api = await openProductTypes(page);
  await expect(page.getByRole("row").filter({ hasText: "Notebook" })).toBeVisible();
  expect(listRequests(api)).toHaveLength(1);
  expect(api.requests.filter((r) => /\/categories/.test(r.url))).toHaveLength(0);
});

test("SPEC-UI-115 shows an empty message when there are no product types (TC-UI-115b)", async ({
  page,
}) => {
  await openProductTypes(page, []);
  await expect(page.getByText("No hay resultados")).toBeVisible();
});

test("SPEC-UI-89 searches with q and no page (TC-UI-89a)", async ({ page }) => {
  const api = await openProductTypes(page);
  api.on("GET", "/product-types?q=note", { status: 200, body: [LAPTOP] });
  await page.getByLabel("Buscar", { exact: true }).fill("note");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.getByText("Router", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Notebook", { exact: true })).toBeVisible();
  expect(new URL(listRequests(api).at(-1).url).search).toBe("?q=note");
});

test("SPEC-UI-201 creates a product type with only its name (TC-UI-201a)", async ({
  page,
}) => {
  const api = await openProductTypes(page);
  api.on("POST", "/product-types", {
    status: 201,
    body: { id: 9, name: "Monitor" },
  });
  await page.getByRole("main").getByRole("button", { name: "Nuevo tipo de producto" }).click();
  const form = page.getByRole("dialog", { name: "Nuevo tipo de producto" });
  await form.getByLabel("Nombre", { exact: true }).fill("Monitor");
  await form.getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => writes(api, "POST").length).toBe(1);
  expect(writes(api, "POST")[0].body).toEqual({ name: "Monitor" });
});

test("SPEC-UI-201 shows only the Nombre field in the creation form (TC-UI-201b)", async ({
  page,
}) => {
  await openProductTypes(page);
  await page.getByRole("main").getByRole("button", { name: "Nuevo tipo de producto" }).click();
  const form = page.getByRole("dialog", { name: "Nuevo tipo de producto" });
  await expect(form.getByLabel("Nombre", { exact: true })).toBeVisible();
  await expect(form.locator("select")).toHaveCount(0);
  await expect(form.locator("input, select, textarea")).toHaveCount(1);
});

test("SPEC-UI-90 shows the API error on a duplicate type (TC-UI-90a)", async ({ page }) => {
  const api = await openProductTypes(page);
  api.on("POST", "/product-types", { status: 409, body: { error: "duplicate_product_type" } });
  await page.getByRole("main").getByRole("button", { name: "Nuevo tipo de producto" }).click();
  const form = page.getByRole("dialog", { name: "Nuevo tipo de producto" });
  await form.getByLabel("Nombre", { exact: true }).fill("Notebook");
  await form.getByRole("button", { name: "Crear" }).click();
  await expect(form.getByRole("alert")).toHaveText(
    "Ya existe un tipo de producto con ese nombre.",
  );
});

test("SPEC-UI-202 edits only the name of a product type (TC-UI-202a)", async ({ page }) => {
  const api = await openProductTypes(page);
  api.on("PATCH", "/product-types/4", {
    status: 200,
    body: { id: 4, name: "Laptop" },
  });
  await page.getByRole("button", { name: "Editar Notebook" }).click();
  const edit = page.getByRole("dialog", { name: "Editar tipo de producto" });
  await edit.getByLabel("Nombre", { exact: true }).fill("Laptop");
  await expect(edit.locator("select")).toHaveCount(0);
  await edit.getByRole("button", { name: "Guardar" }).click();
  await expect.poll(() => writes(api, "PATCH").length).toBe(1);
  expect(writes(api, "PATCH")[0].url).toMatch(/\/product-types\/4$/);
  expect(writes(api, "PATCH")[0].body).toEqual({ name: "Laptop" });
});

test("SPEC-UI-204 deletes a product type only after confirming (TC-UI-204a)", async ({ page }) => {
  const api = await openProductTypes(page);
  api.on("DELETE", "/product-types/4", { status: 204 });
  await page.getByRole("button", { name: "Eliminar Notebook" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Cancelar" }).click();
  await expect(dialog).toHaveCount(0);
  expect(writes(api, "DELETE")).toHaveLength(0);
  await page.getByRole("button", { name: "Eliminar Notebook" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirmar" }).click();
  await expect.poll(() => writes(api, "DELETE").length).toBe(1);
  expect(writes(api, "DELETE")[0].url).toMatch(/\/product-types\/4$/);
});

test("SPEC-UI-54 shows the API error when the type is in use (TC-UI-54b)", async ({ page }) => {
  const api = await openProductTypes(page);
  api.on("DELETE", "/product-types/4", { status: 409, body: { error: "product_type_in_use" } });
  await page.getByRole("button", { name: "Eliminar Notebook" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirmar" }).click();
  await expect(page.locator("#alert")).toHaveText(
    "El tipo de producto tiene productos asociados y no se puede eliminar.",
  );
});

test("SPEC-UI-205 reloads the full list with the same q after a deletion (TC-UI-205d)", async ({
  page,
}) => {
  const api = await openProductTypes(page);
  api.on("GET", "/product-types?q=note", { status: 200, body: [LAPTOP] });
  await page.getByLabel("Buscar", { exact: true }).fill("note");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.getByText("Router", { exact: true })).toHaveCount(0);
  api.on("DELETE", "/product-types/4", { status: 204 });
  api.on("GET", "/product-types?q=note", { status: 200, body: [] });
  const before = listRequests(api).length;
  await page.getByRole("button", { name: "Eliminar Notebook" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirmar" }).click();
  await expect(page.getByText("No hay resultados")).toBeVisible();
  const reloads = listRequests(api).slice(before);
  expect(reloads).toHaveLength(1);
  expect(new URL(reloads[0].url).search).toBe("?q=note");
});
