import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { page as pageOf, ticket, USERS } from "./support/fixtures.js";

test.use({ timezoneId: "UTC" });

const CREATED_AT = "2026-01-01T12:00:00+00:00";

const account = (id) => ({
  id,
  name: `Cuenta ${String(id).padStart(3, "0")}`,
  email: `cuenta${id}@example.com`,
  role: "Client",
  preferred_channel: "mail",
  is_active: true,
});
const accounts = (from, to) => Array.from({ length: to - from + 1 }, (_, i) => account(from + i));
const typesOf = (count) =>
  Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `Tipo ${String(i + 1).padStart(3, "0")}`,
  }));

const SERVER_PAGED = [
  { name: "users", role: "Admin", hash: "#/users", path: "/users", table: "Usuarios" },
  { name: "products", role: "Admin", hash: "#/products", path: "/products", table: "Productos" },
  { name: "tickets", role: "Representative", hash: "#/tickets", path: "/tickets", table: "Tickets" },
];
const IN_MEMORY = [
  { name: "product types", hash: "#/product-types", path: "/product-types", table: "Tipos de producto" },
];
const TYPES = IN_MEMORY[0];

const pathOf = (record) => new URL(record.url).pathname;
const calls = (api, path) =>
  api.requests.filter((r) => r.method === "GET" && pathOf(r) === path);
const lastParams = (api, path) => new URL(calls(api, path).at(-1).url).searchParams;
const pagedBody = (make, total) => (record) => {
  const params = new URL(record.url).searchParams;
  const size = Number(params.get("page_size"));
  const n = Number(params.get("page"));
  const items = make(Math.min(size, Math.max(0, total - (n - 1) * size)), (n - 1) * size);
  return { status: 200, body: { items, page: n, page_size: size, total } };
};

async function open(page, screen, { total = 57, role = screen.role ?? "Admin" } = {}) {
  await page.goto("about:blank");
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS[role] });
  api.on("GET", "/users", pagedBody((count, from) => accounts(from + 1, from + count), total));
  api.on(
    "GET",
    "/products",
    pagedBody(
      (count, from) =>
        Array.from({ length: count }, (_, i) => ({
          id: from + i + 1,
          name: `Producto ${String(from + i + 1).padStart(3, "0")}`,
          is_active: true,
          product_type: { id: 4, name: "Notebook" },
        })),
      total,
    ),
  );
  api.on(
    "GET",
    /^\/tickets\?/,
    pagedBody(
      (count, from) =>
        Array.from({ length: count }, (_, i) => ticket(from + i + 1, "New", CREATED_AT)),
      total,
    ),
  );
  await page.goto(`/${screen.hash}`);
  await expect(page.locator(".loading")).toHaveCount(0);
  return api;
}

async function openMemory(page, screen, count = 45) {
  await page.goto("about:blank");
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Admin });
  api.on("GET", /^\/product-types(\?|$)/, { status: 200, body: typesOf(count) });
  await page.goto(`/${screen.hash}`);
  await expect(page.locator(".loading")).toHaveCount(0);
  return api;
}

const footer = (page) => page.locator(".table-footer");
const sizeSelect = (page) => footer(page).getByLabel("Filas por página");
const bodyRows = (page) => page.locator("tbody tr");

test("SPEC-UI-139 shows each listing as a native table with column headers and an Acciones column (TC-UI-139a)", async ({
  page,
}) => {
  const expectations = [
    { screen: SERVER_PAGED[0], last: "Acciones" },
    { screen: SERVER_PAGED[1], last: "Acciones" },
    { screen: IN_MEMORY[0], last: "Acciones" },
  ];
  for (const { screen, last } of expectations) {
    if (screen.role) {
      await open(page, screen);
    } else {
      await openMemory(page, screen);
    }
    const table = page.getByRole("table", { name: screen.table, exact: true });
    await expect(table).toBeVisible();
    const headers = table.locator("thead th");
    expect(await headers.count(), screen.name).toBeGreaterThan(1);
    for (const scope of await headers.evaluateAll((nodes) => nodes.map((n) => n.getAttribute("scope")))) {
      expect(scope, screen.name).toBe("col");
    }
    await expect(headers.last(), screen.name).toHaveText(last);
    await expect(table.locator("tbody tr").first().locator("td").last().getByRole("button").first()).toBeVisible();
  }
});

test("SPEC-UI-139 shows the ticket table without an Acciones column (TC-UI-139b)", async ({ page }) => {
  for (const role of ["Representative", "Admin", "Client"]) {
    await open(page, SERVER_PAGED[2], { role });
    const table = page.getByRole("table", { name: "Tickets", exact: true });
    await expect(table.locator("thead th")).toHaveText(["Número", "Cliente", "Estado", "Creado"]);
    await expect(table.getByRole("columnheader", { name: "Acciones" })).toHaveCount(0);
  }
});

test("SPEC-UI-140 offers 10, 20 and 50 rows per page with 20 selected in every footer (TC-UI-140b)", async ({
  page,
}) => {
  for (const screen of SERVER_PAGED) {
    await open(page, screen);
    const select = sizeSelect(page);
    await expect(select, screen.name).toHaveValue("20");
    await expect(select.locator("option")).toHaveText(["10", "20", "50"]);
    await expect(footer(page).getByText("Filas por página")).toBeVisible();
  }
  for (const screen of IN_MEMORY) {
    await openMemory(page, screen);
    await expect(sizeSelect(page), screen.name).toHaveValue("20");
    await expect(sizeSelect(page).locator("option")).toHaveText(["10", "20", "50"]);
  }
});

test("SPEC-UI-141 asks for page 1 with the new size and the same filters, q and order (TC-UI-141c)", async ({
  page,
}) => {
  const api = await open(page, SERVER_PAGED[2]);
  await page.getByLabel("Estado", { exact: true }).selectOption({ label: "Nuevo" });
  await page.getByLabel("Orden", { exact: true }).selectOption({ label: "Más antiguos primero" });
  await page.getByLabel("Buscar", { exact: true }).fill("caja");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(footer(page)).toContainText("1–20 de 57");
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(footer(page)).toContainText("21–40 de 57");
  await sizeSelect(page).selectOption("50");
  await expect(footer(page)).toContainText("1–50 de 57");
  const params = lastParams(api, "/tickets");
  expect(params.get("page")).toBe("1");
  expect(params.get("page_size")).toBe("50");
  expect(params.get("state")).toBe("New");
  expect(params.get("order")).toBe("asc");
  expect(params.get("q")).toBe("caja");
});

test("SPEC-UI-141 applies to users and products and keeps the size on the next page (TC-UI-141d)", async ({
  page,
}) => {
  for (const screen of SERVER_PAGED.slice(0, 2)) {
    const api = await open(page, screen);
    await sizeSelect(page).selectOption("10");
    await expect(footer(page)).toContainText("1–10 de 57");
    expect(lastParams(api, screen.path).get("page_size")).toBe("10");
    expect(lastParams(api, screen.path).get("page")).toBe("1");
    await footer(page).getByRole("button", { name: "Siguiente" }).click();
    await expect(footer(page)).toContainText("11–20 de 57");
    expect(lastParams(api, screen.path).get("page_size")).toBe("10");
    expect(lastParams(api, screen.path).get("page")).toBe("2");
    await expect(bodyRows(page)).toHaveCount(10);
  }
});

test("SPEC-UI-142 shows the visible range and the total in the footer (TC-UI-142c)", async ({
  page,
}) => {
  await open(page, SERVER_PAGED[0], { total: 57 });
  await expect(footer(page)).toContainText("1–20 de 57");
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(footer(page)).toContainText("21–40 de 57");
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(footer(page)).toContainText("41–57 de 57");
  await expect(footer(page).getByRole("button", { name: "Siguiente" })).toBeDisabled();
});

test("SPEC-UI-142 shows 0 de 0 for an empty listing (TC-UI-142d)", async ({ page }) => {
  for (const screen of SERVER_PAGED) {
    await open(page, screen, { total: 0 });
    await expect(footer(page), screen.name).toContainText("0 de 0");
    await expect(page.getByText("No hay resultados")).toBeVisible();
    await expect(footer(page).getByRole("button", { name: "Anterior" })).toBeDisabled();
    await expect(footer(page).getByRole("button", { name: "Siguiente" })).toBeDisabled();
  }
  await openMemory(page, IN_MEMORY[0], 0);
  await expect(footer(page)).toContainText("0 de 0");
});

test("SPEC-UI-207 asks for the full product types without paging and slices them in the browser (TC-UI-207b)", async ({
  page,
}) => {
  const api = await openMemory(page, TYPES, 45);
  expect(new URL(calls(api, "/product-types")[0].url).search).toBe("");
  await expect(bodyRows(page)).toHaveCount(20);
  await expect(footer(page)).toContainText("1–20 de 45");
  await expect(footer(page).getByRole("button", { name: "Anterior" })).toBeDisabled();
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(bodyRows(page)).toHaveCount(5);
  await expect(footer(page)).toContainText("41–45 de 45");
  await expect(footer(page).getByRole("button", { name: "Siguiente" })).toBeDisabled();
});

test("SPEC-UI-207 shows the product types as a flat list without a category column (TC-UI-207c)", async ({
  page,
}) => {
  await openMemory(page, TYPES, 5);
  const table = page.getByRole("table", { name: "Tipos de producto", exact: true });
  await expect(table.locator("thead th")).toHaveText(["Nombre", "Acciones"]);
  await expect(bodyRows(page)).toHaveCount(5);
  const names = await bodyRows(page).evaluateAll((nodes) =>
    nodes.map((n) => n.querySelector("td").textContent),
  );
  expect(names).toEqual(["Tipo 001", "Tipo 002", "Tipo 003", "Tipo 004", "Tipo 005"]);
  await expect(page.locator("fieldset")).toHaveCount(0);
});

test("SPEC-UI-208 moves between pages and sizes without any request to the API (TC-UI-208b)", async ({
  page,
}) => {
  const api = await openMemory(page, TYPES, 45);
  await expect(bodyRows(page)).toHaveCount(20);
  const sent = api.requests.length;
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(footer(page)).toContainText("21–40 de 45");
  await footer(page).getByRole("button", { name: "Anterior" }).click();
  await expect(footer(page)).toContainText("1–20 de 45");
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await sizeSelect(page).selectOption("10");
  await expect(footer(page)).toContainText("1–10 de 45");
  await expect(bodyRows(page)).toHaveCount(10);
  await sizeSelect(page).selectOption("50");
  await expect(footer(page)).toContainText("1–45 de 45");
  await expect(bodyRows(page)).toHaveCount(45);
  expect(api.requests.length).toBe(sent);
});

test("SPEC-UI-209 shows page 1 of the API result when a new search text is entered (TC-UI-209b)", async ({
  page,
}) => {
  const api = await openMemory(page, TYPES, 45);
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await sizeSelect(page).selectOption("10");
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(footer(page)).toContainText("11–20 de 45");
  api.on("GET", "/product-types?q=00", { status: 200, body: typesOf(15) });
  await page.getByLabel("Buscar", { exact: true }).fill("00");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(footer(page)).toContainText("1–10 de 15");
  expect(new URL(calls(api, "/product-types").at(-1).url).search).toBe("?q=00");
  await expect(sizeSelect(page)).toHaveValue("10");
});

test("SPEC-UI-210 shows the last valid page after a reload leaves the page out of range (TC-UI-210b)", async ({
  page,
}) => {
  const api = await openMemory(page, TYPES, 21);
  api.on("DELETE", "/product-types/21", { status: 204 });
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(footer(page)).toContainText("21–21 de 21");
  api.on("GET", /^\/product-types(\?|$)/, { status: 200, body: typesOf(20) });
  const before = calls(api, "/product-types").length;
  await page.getByRole("button", { name: "Eliminar Tipo 021" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirmar" }).click();
  await expect(footer(page)).toContainText("1–20 de 20");
  await expect(bodyRows(page)).toHaveCount(20);
  expect(calls(api, "/product-types")).toHaveLength(before + 1);
});

test("SPEC-UI-210 keeps the page and the size when the reloaded list still reaches them (TC-UI-210c)", async ({
  page,
}) => {
  const api = await openMemory(page, TYPES, 45);
  api.on("DELETE", "/product-types/25", { status: 204 });
  await sizeSelect(page).selectOption("10");
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(footer(page)).toContainText("21–30 de 45");
  api.on("GET", /^\/product-types(\?|$)/, { status: 200, body: typesOf(45).slice(1) });
  const before = calls(api, "/product-types").length;
  await page.getByRole("button", { name: "Eliminar Tipo 025" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirmar" }).click();
  await expect(footer(page)).toContainText("21–30 de 44");
  await expect(sizeSelect(page)).toHaveValue("10");
  expect(calls(api, "/product-types")).toHaveLength(before + 1);
});

test("SPEC-UI-26 requests the chosen page_size and keeps it in later pages (TC-UI-26f)", async ({
  page,
}) => {
  const api = await open(page, SERVER_PAGED[0]);
  expect(lastParams(api, "/users").get("page_size")).toBe("20");
  await sizeSelect(page).selectOption("50");
  await expect.poll(() => lastParams(api, "/users").get("page_size")).toBe("50");
  await expect(bodyRows(page)).toHaveCount(50);
});

test("SPEC-UI-120 reloads the current page with the chosen page_size after an action (TC-UI-120f)", async ({
  page,
}) => {
  const api = await open(page, SERVER_PAGED[0]);
  api.on("POST", "/users/11/deactivate", { status: 200, body: account(11) });
  await sizeSelect(page).selectOption("10");
  await footer(page).getByRole("button", { name: "Siguiente" }).click();
  await expect(footer(page)).toContainText("11–20 de 57");
  const before = calls(api, "/users").length;
  await page.getByRole("button", { name: "Dar de baja Cuenta 011" }).click();
  await expect.poll(() => calls(api, "/users").length).toBe(before + 1);
  const params = lastParams(api, "/users");
  expect(params.get("page")).toBe("2");
  expect(params.get("page_size")).toBe("10");
});
