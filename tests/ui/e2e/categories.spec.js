import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { USERS } from "./support/fixtures.js";

const COMPUTING = { id: 3, name: "Computación" };
const NETWORKS = { id: 5, name: "Redes" };
const LIST_PATH = /^\/categories(\?.*)?$/;

const listRequests = (api) =>
  api.requests.filter((r) => r.method === "GET" && /\/categories(\?|$)/.test(r.url));
const writes = (api, method) =>
  api.requests.filter((r) => r.method === method && /\/categories(\/|$)/.test(r.url));

const newDialog = (page) => page.getByRole("dialog", { name: "Nueva categoría" });
const openNewDialog = (page) =>
  page.getByRole("main").getByRole("button", { name: "Nueva categoría" }).click();

async function openCategories(page, items = [COMPUTING, NETWORKS]) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Admin });
  api.on("GET", LIST_PATH, { status: 200, body: items });
  await page.goto("/#/categories");
  await expect(page.getByRole("heading", { name: "Categorías", exact: true })).toBeVisible();
  return api;
}

test("SPEC-UI-49 lists the categories returned by the API (TC-UI-49a)", async ({ page }) => {
  const api = await openCategories(page);
  await expect(page.getByText("Computación", { exact: true })).toBeVisible();
  await expect(page.getByText("Redes", { exact: true })).toBeVisible();
  expect(listRequests(api)[0].url).toMatch(/\/categories$/);
});

test("SPEC-UI-115 shows an empty message when there are no categories (TC-UI-115b)", async ({
  page,
}) => {
  await openCategories(page, []);
  await expect(page.getByText("No hay resultados")).toBeVisible();
});

test("SPEC-UI-86 creates a category with its name (TC-UI-86a)", async ({ page }) => {
  const api = await openCategories(page);
  api.on("POST", "/categories", { status: 201, body: { id: 9, name: "Impresión" } });
  await openNewDialog(page);
  await newDialog(page).getByLabel("Nombre", { exact: true }).fill("Impresión");
  await newDialog(page).getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => writes(api, "POST").length).toBe(1);
  expect(writes(api, "POST")[0].body).toEqual({ name: "Impresión" });
});

test("SPEC-UI-86 marks the name field on a validation error (TC-UI-86a)", async ({ page }) => {
  const api = await openCategories(page);
  api.on("POST", "/categories", {
    status: 400,
    body: { error: "validation_error", fields: { name: "required" } },
  });
  await openNewDialog(page);
  await newDialog(page).getByRole("button", { name: "Crear" }).click();
  await expect(newDialog(page).getByText("Este campo es obligatorio")).toBeVisible();
});

test("SPEC-UI-87 edits the name of a category (TC-UI-87a)", async ({ page }) => {
  const api = await openCategories(page);
  api.on("PATCH", "/categories/3", { status: 200, body: { id: 3, name: "Cómputo" } });
  await page.getByRole("button", { name: "Editar Computación" }).click();
  const edit = page.getByRole("dialog", { name: "Editar categoría" });
  await edit.getByLabel("Nombre", { exact: true }).fill("Cómputo");
  await edit.getByRole("button", { name: "Guardar" }).click();
  await expect.poll(() => writes(api, "PATCH").length).toBe(1);
  expect(writes(api, "PATCH")[0].url).toMatch(/\/categories\/3$/);
  expect(writes(api, "PATCH")[0].body).toEqual({ name: "Cómputo" });
});

test("SPEC-UI-88 searches with q and no page (TC-UI-88a)", async ({ page }) => {
  const api = await openCategories(page);
  api.on("GET", "/categories?q=comp", { status: 200, body: [COMPUTING] });
  await page.getByLabel("Buscar", { exact: true }).fill("comp");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.getByText("Redes", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Computación", { exact: true })).toBeVisible();
  const last = listRequests(api).at(-1);
  expect(new URL(last.url).search).toBe("?q=comp");
});

test("SPEC-UI-54 deletes only after confirming the dialog (TC-UI-54a)", async ({ page }) => {
  const api = await openCategories(page);
  api.on("DELETE", "/categories/3", { status: 204 });
  await page.getByRole("button", { name: "Eliminar Computación" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Cancelar" }).click();
  await expect(dialog).toHaveCount(0);
  expect(writes(api, "DELETE")).toHaveLength(0);
  await page.getByRole("button", { name: "Eliminar Computación" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirmar" }).click();
  await expect.poll(() => writes(api, "DELETE").length).toBe(1);
  expect(writes(api, "DELETE")[0].url).toMatch(/\/categories\/3$/);
});

test("SPEC-UI-54 shows the API error when the category is in use (TC-UI-54a)", async ({ page }) => {
  const api = await openCategories(page);
  api.on("DELETE", "/categories/3", { status: 409, body: { error: "category_in_use" } });
  await page.getByRole("button", { name: "Eliminar Computación" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirmar" }).click();
  await expect(page.locator("#alert")).toHaveText(
    "La categoría tiene tipos de producto asociados y no se puede eliminar.",
  );
});

test("SPEC-UI-120 reloads the full list with the same q after a creation (TC-UI-120c)", async ({
  page,
}) => {
  const api = await openCategories(page);
  api.on("GET", "/categories?q=comp", { status: 200, body: [COMPUTING] });
  await page.getByLabel("Buscar", { exact: true }).fill("comp");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.getByText("Redes", { exact: true })).toHaveCount(0);
  api.on("POST", "/categories", { status: 201, body: { id: 9, name: "Computadoras" } });
  api.on("GET", "/categories?q=comp", {
    status: 200,
    body: [COMPUTING, { id: 9, name: "Computadoras" }],
  });
  const before = listRequests(api).length;
  await openNewDialog(page);
  await newDialog(page).getByLabel("Nombre", { exact: true }).fill("Computadoras");
  await newDialog(page).getByRole("button", { name: "Crear" }).click();
  await expect(page.getByText("Computadoras", { exact: true })).toBeVisible();
  const reloads = listRequests(api).slice(before);
  expect(reloads).toHaveLength(1);
  expect(new URL(reloads[0].url).search).toBe("?q=comp");
});
