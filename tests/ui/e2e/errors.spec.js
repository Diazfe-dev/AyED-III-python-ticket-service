import { expect, test } from "@playwright/test";
import { ABORT, installFakeApi, loginAs } from "./support/fake-api.js";
import { ADMIN, CLIENT, REP, USERS, page as pageOf, ticket } from "./support/fixtures.js";

const GENERIC = "Ocurrió un error inesperado. Intente nuevamente.";
const CONNECTION = "No se pudo conectar con el servidor. Intente nuevamente.";
const CREATED = "2026-01-01T12:00:00+00:00";
const REP_AUTHOR = { id: REP.id, name: REP.name, role: "Representative" };
const CLIENT_AUTHOR = { id: CLIENT.id, name: CLIENT.name, role: "Client" };

const alertRegion = (page) => page.locator("#alert");
const heading = (page, name) => page.getByRole("heading", { name, exact: true });

async function openDetail(page, role, detail, milestones = [], changes = []) {
  const api = await installFakeApi(page);
  api.on("GET", "/tickets/7", { status: 200, body: detail });
  api.on("GET", "/tickets/7/milestones", { status: 200, body: milestones });
  api.on("GET", "/tickets/7/state-changes", { status: 200, body: changes });
  await loginAs(page, api, role);
  await page.goto("/#/tickets/7");
  await expect(heading(page, "Ticket #7")).toBeVisible();
  return api;
}

test("SPEC-UI-56 shows the duplicate category message on a 409 (TC-UI-56b)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: ADMIN });
  api.on("GET", /^\/categories(\?.*)?$/, { status: 200, body: [] });
  await page.goto("/#/categories");
  await expect(heading(page, "Categorías")).toBeVisible();
  api.on("POST", "/categories", { status: 409, body: { error: "duplicate_category" } });
  await page.getByLabel("Nombre", { exact: true }).fill("Redes");
  await page.getByRole("button", { name: "Crear" }).click();
  await expect(page.getByText("Ya existe una categoría con ese nombre.")).toBeVisible();
});

test("SPEC-UI-58 shows the generic message and hides an internal detail on a 500 (TC-UI-58b)", async ({
  page,
}) => {
  const api = await openDetail(page, "Representative", {
    ...ticket(7, "InProgress", CREATED),
  });
  api.on("POST", "/tickets/7/close", {
    status: 500,
    body: { error: "internal_error", detail: "Traceback secreto en la base" },
  });
  await page.getByRole("button", { name: "Cerrar", exact: true }).click();
  await expect(page.getByText(GENERIC)).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Traceback secreto");
});

test("SPEC-UI-59 shows the connection message when the listing request aborts (TC-UI-59b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: REP });
  api.on("GET", /^\/tickets\?/, ABORT);
  await page.goto("/#/tickets");
  await expect(alertRegion(page)).toHaveText(CONNECTION);
});

test("SPEC-UI-96 shows labels and never raw codes in the listing, the detail and the users (TC-UI-96b)", async ({
  page,
}) => {
  const api = await openDetail(
    page,
    "Admin",
    ticket(7, "InProgress", CREATED),
    [{ id: 1, content: "Hola", author: REP_AUTHOR, created_at: CREATED }],
    [{ state: "InProgress", user: REP_AUTHOR, timestamp: CREATED }],
  );
  const body = page.locator("body");
  await expect(page.locator(".ticket-state")).toHaveText("En curso");
  await expect(body).toContainText("Representante");
  for (const raw of ["InProgress", "Representative"]) {
    await expect(body).not.toContainText(raw);
  }

  api.on("GET", /^\/tickets\?/, {
    status: 200,
    body: pageOf([ticket(7, "InProgress", CREATED)]),
  });
  await page.goto("/#/tickets");
  await expect(page.getByRole("row").filter({ hasText: "#7" })).toContainText("En curso");
  await expect(body).not.toContainText("InProgress");

  api.on("GET", "/users", {
    status: 200,
    body: pageOf([
      {
        id: 2,
        name: REP.name,
        email: REP.email,
        role: "Representative",
        preferred_channel: "mail",
        is_active: true,
      },
    ]),
  });
  await page.goto("/#/users");
  const row = page.getByRole("row").filter({ hasText: REP.email });
  await expect(row).toContainText("Representante");
  await expect(row).toContainText("Activo");
  for (const raw of ["Representative", "true"]) {
    await expect(body).not.toContainText(raw);
  }
});

test("SPEC-UI-123 shows an unknown state code as it comes in the row and the detail (TC-UI-123b)", async ({
  page,
}) => {
  const api = await openDetail(page, "Representative", ticket(7, "Escalado", CREATED));
  await expect(page.locator(".ticket-state")).toHaveText("Escalado");
  api.on("GET", /^\/tickets\?/, {
    status: 200,
    body: pageOf([ticket(7, "Escalado", CREATED)]),
  });
  await page.goto("/#/tickets");
  await expect(page.getByRole("row").filter({ hasText: "#7" })).toContainText("Escalado");
});

test("SPEC-UI-63 draws API text as literal text without creating elements (TC-UI-63a)", async ({
  page,
}) => {
  const hostile = '<img src=x onerror="window.__xss=1">';
  await openDetail(
    page,
    "Representative",
    { ...ticket(7, "InProgress", CREATED), client: { id: CLIENT.id, name: hostile } },
    [{ id: 1, content: "<b>hola</b>", author: CLIENT_AUTHOR, created_at: CREATED }],
  );
  await expect(page.locator("#app")).toContainText(hostile);
  await expect(page.locator("ol.milestones")).toContainText("<b>hola</b>");
  await expect(page.locator("#app img, #app b")).toHaveCount(0);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
});

test("SPEC-UI-63 draws the users page values as literal text (TC-UI-63a)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Admin });
  api.on("GET", "/users", {
    status: 200,
    body: pageOf([
      {
        id: 9,
        name: '<img src=x onerror="window.__xss=1">',
        email: "x@example.com",
        role: "Client",
        preferred_channel: "mail",
        is_active: true,
      },
    ]),
  });
  await page.goto("/#/users");
  await expect(page.getByRole("row").filter({ hasText: "x@example.com" })).toContainText("<img");
  await expect(page.locator("#app img")).toHaveCount(0);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
});
