import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { page as pageOf, ticket, USERS } from "./support/fixtures.js";

test.use({ timezoneId: "UTC" });

const GENERIC = "Ocurrió un error inesperado. Intente nuevamente.";
const TICKETS_PATH = /^\/tickets\?/;

const ROWS = [
  ticket(1, "New", "2026-01-01T12:00:00+00:00"),
  ticket(2, "InProgress", "2026-01-02T08:30:00+00:00"),
  ticket(3, "Closed", "2026-01-03T12:00:00+00:00"),
];
const ROWS_A = [ticket(11, "New", "2026-02-01T12:00:00+00:00")];
const ROWS_B = [ticket(21, "InProgress", "2026-02-02T12:00:00+00:00")];

const currentHash = (page) => page.evaluate(() => window.location.hash);
const alertRegion = (page) => page.locator("#alert");
const listCalls = (api) =>
  api.requests.filter((r) => r.method === "GET" && new URL(r.url).pathname === "/tickets");
const lastCall = (api) => new URL(listCalls(api).at(-1).url).searchParams;
const rowFor = (page, id) => page.getByRole("row").filter({ hasText: `#${id}` });
const byPage = (items, total) => (record) => ({
  status: 200,
  body: pageOf(items, Number(new URL(record.url).searchParams.get("page")), total),
});

async function openList(page, role, { tickets = pageOf(ROWS), clients, representatives } = {}) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS[role] });
  api.on("GET", "/clients", { status: 200, body: clients ?? [] });
  api.on("GET", "/representatives", { status: 200, body: representatives ?? [] });
  api.on("GET", TICKETS_PATH, typeof tickets === "function" ? tickets : { status: 200, body: tickets });
  await page.goto("/#/tickets");
  return api;
}

const stateFilter = (page) => page.getByLabel("Estado", { exact: true });
const searchBox = (page) => page.getByLabel("Buscar", { exact: true });
const orderSelect = (page) => page.getByLabel("Orden", { exact: true });
const search = async (page, text) => {
  await searchBox(page).fill(text);
  await page.getByRole("button", { name: "Buscar" }).click();
};

test("SPEC-UI-22 shows each ticket with id, client, state label and creation date (TC-UI-22a)", async ({
  page,
}) => {
  const api = await openList(page, "Representative");
  await expect(rowFor(page, 2)).toBeVisible();
  expect(listCalls(api)[0].url).toMatch(/\/tickets\?page=1&page_size=20$/);
  const row = rowFor(page, 2);
  await expect(row).toContainText("Ana Gómez");
  await expect(row).toContainText("En curso");
  await expect(row).toContainText("02/01/2026 08:30");
  await expect(rowFor(page, 1)).toContainText("Nuevo");
  await expect(rowFor(page, 3)).toContainText("Cerrado");
});

test("SPEC-UI-26 requests the listing with page and page_size 20 (TC-UI-26b)", async ({ page }) => {
  const api = await openList(page, "Representative");
  await expect(rowFor(page, 1)).toBeVisible();
  const params = lastCall(api);
  expect(params.get("page")).toBe("1");
  expect(params.get("page_size")).toBe("20");
});

test("SPEC-UI-23 requests the listing with the state filter (TC-UI-23b)", async ({ page }) => {
  const api = await openList(page, "Representative");
  await expect(rowFor(page, 1)).toBeVisible();
  api.on("GET", TICKETS_PATH, { status: 200, body: pageOf(ROWS_B) });
  await stateFilter(page).selectOption({ label: "En curso" });
  await expect(rowFor(page, 21)).toBeVisible();
  expect(lastCall(api).get("state")).toBe("InProgress");
  await expect(rowFor(page, 1)).toHaveCount(0);
});

test("SPEC-UI-107 requests the listing with the search text (TC-UI-107b)", async ({ page }) => {
  const api = await openList(page, "Representative");
  await expect(rowFor(page, 1)).toBeVisible();
  api.on("GET", TICKETS_PATH, { status: 200, body: pageOf(ROWS_B) });
  await search(page, "impresora");
  await expect(rowFor(page, 21)).toBeVisible();
  expect(lastCall(api).get("q")).toBe("impresora");
});

test("SPEC-UI-108 requests the listing with the creation order (TC-UI-108b)", async ({ page }) => {
  const api = await openList(page, "Representative");
  await expect(rowFor(page, 1)).toBeVisible();
  api.on("GET", TICKETS_PATH, { status: 200, body: pageOf(ROWS_B) });
  await orderSelect(page).selectOption({ label: "Más antiguos primero" });
  await expect(rowFor(page, 21)).toBeVisible();
  expect(lastCall(api).get("order")).toBe("asc");
});

test("SPEC-UI-24 lets a representative filter by client from GET /clients (TC-UI-24b)", async ({
  page,
}) => {
  const api = await openList(page, "Representative", {
    clients: [{ id: 7, name: "Ana Gómez" }],
  });
  await expect(rowFor(page, 1)).toBeVisible();
  const clientCalls = api.requests.filter((r) => new URL(r.url).pathname === "/clients");
  expect(clientCalls).toHaveLength(1);
  expect(new URL(clientCalls[0].url).searchParams.has("page")).toBe(false);
  api.on("GET", TICKETS_PATH, { status: 200, body: pageOf(ROWS_B) });
  await page.getByLabel("Cliente", { exact: true }).selectOption({ label: "Ana Gómez" });
  await expect(rowFor(page, 21)).toBeVisible();
  const params = lastCall(api);
  expect(params.get("client_id")).toBe("7");
  expect(params.get("page")).toBe("1");
  expect(params.get("page_size")).toBe("20");
  await expect(page.getByLabel("Representante", { exact: true })).toHaveCount(0);
});

test("SPEC-UI-24 lets an administrator filter by client from GET /clients (TC-UI-24c)", async ({
  page,
}) => {
  const api = await openList(page, "Admin", { clients: [{ id: 7, name: "Ana Gómez" }] });
  await expect(rowFor(page, 1)).toBeVisible();
  api.on("GET", TICKETS_PATH, { status: 200, body: pageOf(ROWS_B) });
  await page.getByLabel("Cliente", { exact: true }).selectOption({ label: "Ana Gómez" });
  await expect(rowFor(page, 21)).toBeVisible();
  expect(lastCall(api).get("client_id")).toBe("7");
});

test("SPEC-UI-25 lets an administrator filter by representative from GET /representatives (TC-UI-25b)", async ({
  page,
}) => {
  const api = await openList(page, "Admin", {
    representatives: [{ id: 3, name: "Raúl Pérez" }],
  });
  await expect(rowFor(page, 1)).toBeVisible();
  const repCalls = api.requests.filter((r) => new URL(r.url).pathname === "/representatives");
  expect(repCalls).toHaveLength(1);
  expect(new URL(repCalls[0].url).searchParams.has("page")).toBe(false);
  api.on("GET", TICKETS_PATH, { status: 200, body: pageOf(ROWS_B) });
  await page.getByLabel("Representante", { exact: true }).selectOption({ label: "Raúl Pérez" });
  await expect(rowFor(page, 21)).toBeVisible();
  expect(lastCall(api).get("representative_id")).toBe("3");
});

test("SPEC-UI-101 shows the paginator with the page number and the total (TC-UI-101b)", async ({
  page,
}) => {
  await openList(page, "Representative", { tickets: pageOf(ROWS, 1, 45) });
  await expect(page.getByRole("button", { name: "Anterior" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Siguiente" })).toBeVisible();
  await expect(page.getByText("Página 1")).toBeVisible();
  await expect(page.getByText("45 resultados")).toBeVisible();
});

test("SPEC-UI-102 requests the next page with the same filters (TC-UI-102b)", async ({ page }) => {
  const api = await openList(page, "Representative", { tickets: byPage(ROWS, 45) });
  await stateFilter(page).selectOption({ label: "Nuevo" });
  await expect(page.getByText("Página 1")).toBeVisible();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 2")).toBeVisible();
  const params = lastCall(api);
  expect(params.get("page")).toBe("2");
  expect(params.get("page_size")).toBe("20");
  expect(params.get("state")).toBe("New");
});

test("SPEC-UI-103 requests the previous page with the same filters (TC-UI-103b)", async ({
  page,
}) => {
  const api = await openList(page, "Representative", { tickets: byPage(ROWS, 45) });
  await stateFilter(page).selectOption({ label: "Nuevo" });
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 2")).toBeVisible();
  await page.getByRole("button", { name: "Anterior" }).click();
  await expect(page.getByText("Página 1")).toBeVisible();
  const params = lastCall(api);
  expect(params.get("page")).toBe("1");
  expect(params.get("state")).toBe("New");
});

test("SPEC-UI-104 goes back to page 1 when the filter changes (TC-UI-104b)", async ({ page }) => {
  const api = await openList(page, "Representative", { tickets: byPage(ROWS, 45) });
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 2")).toBeVisible();
  await stateFilter(page).selectOption({ label: "Cerrado" });
  await expect(page.getByText("Página 1")).toBeVisible();
  const params = lastCall(api);
  expect(params.get("page")).toBe("1");
  expect(params.get("state")).toBe("Closed");
});

test("SPEC-UI-105 disables Anterior on the first page (TC-UI-105b)", async ({ page }) => {
  await openList(page, "Representative", { tickets: pageOf(ROWS, 1, 45) });
  await expect(page.getByRole("button", { name: "Anterior" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Siguiente" })).toBeEnabled();
});

test("SPEC-UI-106 disables Siguiente on the last page (TC-UI-106b)", async ({ page }) => {
  await openList(page, "Representative", { tickets: byPage(ROWS, 45) });
  await page.getByRole("button", { name: "Siguiente" }).click();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 3")).toBeVisible();
  await expect(page.getByRole("button", { name: "Siguiente" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Anterior" })).toBeEnabled();
});

test("SPEC-UI-41 gives the administrator a read-only listing (TC-UI-41a)", async ({ page }) => {
  await openList(page, "Admin");
  await expect(rowFor(page, 1)).toBeVisible();
  await expect(page.getByRole("button", { name: "Nuevo ticket" })).toHaveCount(0);
  await expect(page.getByRole("main").getByRole("link", { name: "Nuevo ticket" })).toHaveCount(0);
  await expect(page.getByRole("main").getByRole("button")).toHaveText([
    "Buscar",
    "Anterior",
    "Siguiente",
  ]);
});

test("SPEC-UI-71 shows the loading indicator while the listing is pending (TC-UI-71a)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Representative });
  api.on("GET", "/clients", { status: 200, body: [] });
  const pending = api.defer("GET", TICKETS_PATH);
  await page.goto("/#/tickets");
  await pending.requested;
  await expect(page.getByText("Cargando…")).toBeVisible();
  pending.release(200, pageOf(ROWS));
  await expect(rowFor(page, 1)).toBeVisible();
  await expect(page.getByText("Cargando…")).toHaveCount(0);
});

test("SPEC-UI-115 shows No hay resultados for an empty listing (TC-UI-115a)", async ({ page }) => {
  await openList(page, "Representative", { tickets: pageOf([], 1, 0) });
  await expect(page.getByText("No hay resultados")).toBeVisible();
});

test("SPEC-UI-119 shows the general message for a validation error without field marks (TC-UI-119b)", async ({
  page,
}) => {
  await openList(page, "Representative", {
    tickets: () => ({
      status: 400,
      body: { error: "validation_error", fields: { state: "invalid" } },
    }),
  });
  await expect(alertRegion(page)).toHaveText(GENERIC);
  await expect(page.locator("[aria-invalid]")).toHaveCount(0);
  await expect(page.locator(".field-mark")).toHaveCount(0);
});

async function replacedFilter(page, release) {
  const api = await openList(page, "Representative");
  await expect(rowFor(page, 1)).toBeVisible();
  const first = api.defer("GET", /^\/tickets\?.*state=New/);
  await stateFilter(page).selectOption({ label: "Nuevo" });
  await first.requested;
  api.on("GET", /^\/tickets\?.*state=InProgress/, { status: 200, body: pageOf(ROWS_B) });
  await stateFilter(page).selectOption({ label: "En curso" });
  await expect(rowFor(page, 21)).toBeVisible();
  release(first);
  await page.waitForTimeout(150);
  await expect(rowFor(page, 21)).toBeVisible();
  await expect(rowFor(page, 11)).toHaveCount(0);
  await expect(stateFilter(page)).toHaveValue("InProgress");
  await expect(alertRegion(page)).toHaveText("");
  expect(await currentHash(page)).toBe("#/tickets");
}

test("SPEC-UI-135 ignores the answer of a replaced filter (TC-UI-135c)", async ({ page }) => {
  await replacedFilter(page, (first) => first.release(200, pageOf(ROWS_A)));
});

test("SPEC-UI-135 ignores a replaced filter answered with a 500 (TC-UI-135c, variant)", async ({
  page,
}) => {
  await replacedFilter(page, (first) => first.release(500, { error: "internal_error" }));
});

async function replacedSearch(page, release) {
  const api = await openList(page, "Representative");
  await expect(rowFor(page, 1)).toBeVisible();
  const first = api.defer("GET", /^\/tickets\?.*q=Notebook/);
  await search(page, "Notebook");
  await first.requested;
  api.on("GET", /^\/tickets\?.*q=Monitor/, { status: 200, body: pageOf(ROWS_B) });
  await search(page, "Monitor");
  await expect(rowFor(page, 21)).toBeVisible();
  release(first);
  await page.waitForTimeout(150);
  await expect(rowFor(page, 21)).toBeVisible();
  await expect(alertRegion(page)).toHaveText("");
  await expect(page.getByText("Cargando…")).toHaveCount(0);
  expect(await currentHash(page)).toBe("#/tickets");
}

test("SPEC-UI-135 ignores a replaced search answered with a 400 (TC-UI-135f)", async ({ page }) => {
  await replacedSearch(page, (first) =>
    first.release(400, { error: "validation_error", fields: { q: "invalid" } }),
  );
});

test("SPEC-UI-135 ignores a replaced search whose connection fails (TC-UI-135f, variant)", async ({
  page,
}) => {
  await replacedSearch(page, (first) => first.abort());
});
