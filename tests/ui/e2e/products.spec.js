import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { page as pageOf, USERS } from "./support/fixtures.js";

const PRODUCTS_PATH = "/products";
const COMPUTING = { id: 3, name: "Computación" };
const NETWORKS = { id: 5, name: "Redes" };
const LAPTOP_TYPE = { id: 4, name: "Notebook", category_id: 3 };
const ROUTER_TYPE = { id: 6, name: "Router", category_id: 5 };

const product = (id, name, type, category, isActive = true) => ({
  id,
  name,
  is_active: isActive,
  product_type: type,
  category,
});

const LENOVO = product(9, "Lenovo T14", LAPTOP_TYPE, COMPUTING);
const ARCHER = product(10, "Archer AX", ROUTER_TYPE, NETWORKS, false);

const productCalls = (api) =>
  api.requests.filter((r) => r.method === "GET" && new URL(r.url).pathname === PRODUCTS_PATH);
const lastCall = (api) => new URL(productCalls(api).at(-1).url).searchParams;
const writes = (api, method, path) =>
  api.requests.filter((r) => r.method === method && new URL(r.url).pathname === path);
const rowFor = (page, name) => page.getByRole("row").filter({ hasText: name });
const byPage = (items, total) => (record) => ({
  status: 200,
  body: pageOf(items, Number(new URL(record.url).searchParams.get("page")), total),
});

const createForm = (page) => page.getByRole("dialog", { name: "Nuevo producto" });
const editForm = (page) => page.getByRole("dialog", { name: "Editar producto" });
const openCreateDialog = (page) =>
  page.getByRole("main").getByRole("button", { name: "Nuevo producto" }).click();

async function openProducts(page, listing = { status: 200, body: pageOf([LENOVO, ARCHER]) }) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Admin });
  api.on("GET", /^\/categories(\?|$)/, { status: 200, body: [COMPUTING, NETWORKS] });
  api.on("GET", "/product-types", { status: 200, body: [LAPTOP_TYPE, ROUTER_TYPE] });
  api.on("GET", PRODUCTS_PATH, listing);
  await page.goto("/#/products");
  await expect(page.getByRole("heading", { name: "Productos", exact: true })).toBeVisible();
  return api;
}

test("SPEC-UI-51 shows name, type, category and state of each product (TC-UI-51a)", async ({
  page,
}) => {
  await openProducts(page);
  const active = rowFor(page, "Lenovo T14");
  await expect(active).toContainText("Notebook");
  await expect(active).toContainText("Computación");
  await expect(active).toContainText("Activo");
  const inactive = rowFor(page, "Archer AX");
  await expect(inactive).toContainText("Router");
  await expect(inactive).toContainText("Redes");
  await expect(inactive).toContainText("Inactivo");
});

test("SPEC-UI-26 requests GET /products with page and page_size 20 (TC-UI-26d)", async ({
  page,
}) => {
  const api = await openProducts(page);
  await expect(rowFor(page, "Lenovo T14")).toBeVisible();
  const params = lastCall(api);
  expect(params.get("page")).toBe("1");
  expect(params.get("page_size")).toBe("20");
});

test("SPEC-UI-92 requests the listing with the search text (TC-UI-92a)", async ({ page }) => {
  const api = await openProducts(page);
  await expect(rowFor(page, "Lenovo T14")).toBeVisible();
  api.on("GET", PRODUCTS_PATH, { status: 200, body: pageOf([LENOVO]) });
  await page.getByLabel("Buscar", { exact: true }).fill("lenovo");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(rowFor(page, "Archer AX")).toHaveCount(0);
  expect(lastCall(api).get("q")).toBe("lenovo");
});

test("SPEC-UI-93 requests the listing with is_active (TC-UI-93a)", async ({ page }) => {
  const api = await openProducts(page);
  await expect(rowFor(page, "Lenovo T14")).toBeVisible();
  api.on("GET", PRODUCTS_PATH, { status: 200, body: pageOf([ARCHER]) });
  await page.getByLabel("Estado", { exact: true }).selectOption({ label: "Inactivo" });
  await expect(rowFor(page, "Archer AX")).toBeVisible();
  expect(lastCall(api).get("is_active")).toBe("false");
});

test("SPEC-UI-94 requests the listing with category_id from the category selector (TC-UI-94a)", async ({
  page,
}) => {
  const api = await openProducts(page);
  await expect(rowFor(page, "Lenovo T14")).toBeVisible();
  api.on("GET", PRODUCTS_PATH, { status: 200, body: pageOf([ARCHER]) });
  await page.getByLabel("Categoría", { exact: true }).selectOption({ label: "Redes" });
  await expect(rowFor(page, "Lenovo T14")).toHaveCount(0);
  expect(lastCall(api).get("category_id")).toBe("5");
});

test("SPEC-UI-95 requests the listing with product_type_id from the type selector (TC-UI-95a)", async ({
  page,
}) => {
  const api = await openProducts(page);
  await expect(rowFor(page, "Lenovo T14")).toBeVisible();
  api.on("GET", PRODUCTS_PATH, { status: 200, body: pageOf([LENOVO]) });
  await page.locator("#filter-type").selectOption({ label: "Notebook" });
  await expect(rowFor(page, "Archer AX")).toHaveCount(0);
  expect(lastCall(api).get("product_type_id")).toBe("4");
});

test("SPEC-UI-52 creates a product with the type chosen in the selector (TC-UI-52a)", async ({
  page,
}) => {
  const api = await openProducts(page);
  api.on("POST", PRODUCTS_PATH, { status: 201, body: product(11, "Dell", LAPTOP_TYPE, COMPUTING) });
  await openCreateDialog(page);
  await createForm(page).getByLabel("Nombre").fill("Dell");
  await createForm(page).getByLabel("Tipo").selectOption({ label: "Notebook" });
  await createForm(page).getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => writes(api, "POST", PRODUCTS_PATH).length).toBe(1);
  expect(writes(api, "POST", PRODUCTS_PATH)[0].body).toEqual({ name: "Dell", product_type_id: 4 });
});

test("SPEC-UI-109 edits the name and the type of a product (TC-UI-109a)", async ({ page }) => {
  const api = await openProducts(page);
  api.on("PATCH", "/products/9", { status: 200, body: LENOVO });
  await rowFor(page, "Lenovo T14").getByRole("button", { name: "Editar" }).click();
  await editForm(page).getByLabel("Nombre").fill("Lenovo T15");
  await editForm(page).getByLabel("Tipo").selectOption({ label: "Router" });
  await editForm(page).getByRole("button", { name: "Guardar" }).click();
  await expect.poll(() => writes(api, "PATCH", "/products/9").length).toBe(1);
  expect(writes(api, "PATCH", "/products/9")[0].body).toEqual({
    name: "Lenovo T15",
    product_type_id: 6,
  });
});

test("SPEC-UI-53 deactivates an active product (TC-UI-53a)", async ({ page }) => {
  const api = await openProducts(page);
  api.on("POST", "/products/9/deactivate", { status: 200, body: { ...LENOVO, is_active: false } });
  await expect(rowFor(page, "Lenovo T14").getByRole("button", { name: "Reactivar" })).toHaveCount(0);
  await rowFor(page, "Lenovo T14").getByRole("button", { name: "Dar de baja" }).click();
  await expect.poll(() => writes(api, "POST", "/products/9/deactivate").length).toBe(1);
});

test("SPEC-UI-111 reactivates an inactive product (TC-UI-111a)", async ({ page }) => {
  const api = await openProducts(page, {
    status: 200,
    body: pageOf([product(9, "Lenovo T14", LAPTOP_TYPE, COMPUTING, false)]),
  });
  api.on("POST", "/products/9/activate", { status: 200, body: LENOVO });
  await expect(rowFor(page, "Lenovo T14").getByRole("button", { name: "Dar de baja" })).toHaveCount(
    0,
  );
  await rowFor(page, "Lenovo T14").getByRole("button", { name: "Reactivar" }).click();
  await expect.poll(() => writes(api, "POST", "/products/9/activate").length).toBe(1);
});

test("SPEC-UI-120 reloads the current page with the same filters after a create (TC-UI-120b)", async ({
  page,
}) => {
  const api = await openProducts(page, byPage([LENOVO], 45));
  api.on("POST", PRODUCTS_PATH, { status: 201, body: product(11, "Dell", LAPTOP_TYPE, COMPUTING) });
  await page.getByLabel("Estado", { exact: true }).selectOption({ label: "Activo" });
  await page.getByLabel("Buscar", { exact: true }).fill("len");
  await page.getByRole("button", { name: "Buscar" }).click();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 2")).toBeVisible();
  const before = productCalls(api).length;
  api.on("GET", PRODUCTS_PATH, { status: 200, body: pageOf([ARCHER], 2, 46) });
  await openCreateDialog(page);
  await createForm(page).getByLabel("Nombre").fill("Dell");
  await createForm(page).getByLabel("Tipo").selectOption({ label: "Notebook" });
  await createForm(page).getByRole("button", { name: "Crear" }).click();
  await expect(rowFor(page, "Archer AX")).toBeVisible();
  expect(productCalls(api)).toHaveLength(before + 1);
  const params = lastCall(api);
  expect(params.get("q")).toBe("len");
  expect(params.get("is_active")).toBe("true");
  expect(params.get("page")).toBe("2");
});

test("SPEC-UI-125 asks for the last valid page when the reloaded page is empty (TC-UI-125c)", async ({
  page,
}) => {
  let deactivated = false;
  const api = await openProducts(page, (record) => {
    const n = Number(new URL(record.url).searchParams.get("page"));
    if (deactivated && n === 3) {
      return { status: 200, body: pageOf([], 3, 40) };
    }
    return { status: 200, body: pageOf(n === 2 ? [ARCHER] : [LENOVO], n, deactivated ? 40 : 60) };
  });
  await page.getByRole("button", { name: "Siguiente" }).click();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 3")).toBeVisible();
  api.on("POST", "/products/9/deactivate", () => {
    deactivated = true;
    return { status: 200, body: { ...LENOVO, is_active: false } };
  });
  await rowFor(page, "Lenovo T14").getByRole("button", { name: "Dar de baja" }).click();
  await expect(page.getByText("Página 2")).toBeVisible();
  const pages = productCalls(api).map((r) => new URL(r.url).searchParams.get("page"));
  expect(pages.slice(-2)).toEqual(["3", "2"]);
});
