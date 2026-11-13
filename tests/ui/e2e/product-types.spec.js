import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { USERS } from "./support/fixtures.js";

const COMPUTING = { id: 3, name: "Computación" };
const NETWORKS = { id: 5, name: "Redes" };
const LAPTOP = { id: 4, name: "Notebook", category_id: 3 };
const ROUTER = { id: 6, name: "Router", category_id: 5 };
const LIST_PATH = /^\/product-types(\?.*)?$/;

const listRequests = (api) =>
  api.requests.filter((r) => r.method === "GET" && /\/product-types(\?|$)/.test(r.url));
const writes = (api, method) =>
  api.requests.filter((r) => r.method === method && /\/product-types(\/|$)/.test(r.url));

async function openProductTypes(page, items = [LAPTOP, ROUTER]) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Admin });
  api.on("GET", /^\/categories(\?|$)/, { status: 200, body: [COMPUTING, NETWORKS] });
  api.on("GET", LIST_PATH, { status: 200, body: items });
  await page.goto("/#/product-types");
  await expect(page.getByRole("heading", { name: "Tipos de producto", exact: true })).toBeVisible();
  return api;
}

test("SPEC-UI-50 shows each product type in a table row with its category (TC-UI-50a)", async ({
  page,
}) => {
  const api = await openProductTypes(page);
  const notebook = page.getByRole("row").filter({ hasText: "Notebook" });
  const router = page.getByRole("row").filter({ hasText: "Router" });
  await expect(notebook).toContainText("Computación");
  await expect(router).toContainText("Redes");
  await expect(notebook).not.toContainText("Redes");
  expect(listRequests(api).find((r) => /\/product-types$/.test(r.url))).toBeTruthy();
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

test("SPEC-UI-90 creates a product type with the category from the selector (TC-UI-90a)", async ({
  page,
}) => {
  const api = await openProductTypes(page);
  api.on("POST", "/product-types", {
    status: 201,
    body: { id: 9, name: "Monitor", category_id: 3 },
  });
  await page.getByRole("main").getByRole("button", { name: "Nuevo tipo de producto" }).click();
  const form = page.getByRole("dialog", { name: "Nuevo tipo de producto" });
  await expect(form.getByRole("option", { name: "Redes" })).toHaveCount(1);
  await form.getByLabel("Nombre", { exact: true }).fill("Monitor");
  await form.getByLabel("Categoría", { exact: true }).selectOption({ label: "Computación" });
  await form.getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => writes(api, "POST").length).toBe(1);
  expect(writes(api, "POST")[0].body).toEqual({ name: "Monitor", category_id: 3 });
});

test("SPEC-UI-90 shows the API error on a duplicate type (TC-UI-90a)", async ({ page }) => {
  const api = await openProductTypes(page);
  api.on("POST", "/product-types", { status: 409, body: { error: "duplicate_product_type" } });
  await page.getByRole("main").getByRole("button", { name: "Nuevo tipo de producto" }).click();
  const form = page.getByRole("dialog", { name: "Nuevo tipo de producto" });
  await form.getByLabel("Nombre", { exact: true }).fill("Notebook");
  await form.getByRole("button", { name: "Crear" }).click();
  await expect(form.getByRole("alert")).toHaveText(
    "Ya existe un tipo de producto con ese nombre en la categoría.",
  );
});

test("SPEC-UI-91 edits the name and category of a product type (TC-UI-91a)", async ({ page }) => {
  const api = await openProductTypes(page);
  api.on("PATCH", "/product-types/4", {
    status: 200,
    body: { id: 4, name: "Laptop", category_id: 5 },
  });
  await page.getByRole("button", { name: "Editar Notebook" }).click();
  const edit = page.getByRole("dialog", { name: "Editar tipo de producto" });
  await edit.getByLabel("Nombre", { exact: true }).fill("Laptop");
  await edit.getByLabel("Categoría", { exact: true }).selectOption({ label: "Redes" });
  await edit.getByRole("button", { name: "Guardar" }).click();
  await expect.poll(() => writes(api, "PATCH").length).toBe(1);
  expect(writes(api, "PATCH")[0].url).toMatch(/\/product-types\/4$/);
  expect(writes(api, "PATCH")[0].body).toEqual({ name: "Laptop", category_id: 5 });
});

test("SPEC-UI-54 deletes a product type only after confirming (TC-UI-54b)", async ({ page }) => {
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

test("SPEC-UI-120 reloads the full list with the same q after a deletion (TC-UI-120d)", async ({
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
