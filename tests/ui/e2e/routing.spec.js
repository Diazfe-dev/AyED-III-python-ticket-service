import { expect, test } from "@playwright/test";
import { installFakeApi, loginAs } from "./support/fake-api.js";
import { ADMIN, CLIENT } from "./support/fixtures.js";

const heading = (page, name) => page.getByRole("heading", { name, exact: true });
const nav = (page, name) => page.getByRole("navigation").getByRole("link", { name, exact: true });
const currentHash = (page) => page.evaluate(() => window.location.hash);
const goToHash = (page, hash) =>
  page.evaluate((value) => {
    window.location.hash = value;
  }, hash);
const apiRequests = (api) => api.requests.filter((r) => !r.url.endsWith("/me"));

test("SPEC-UI-04 changes screen without reloading the document (TC-UI-04b)", async ({ page }) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Representative");
  await expect(heading(page, "Tickets")).toBeVisible();
  await page.evaluate(() => {
    window.__marca = 1;
  });
  const documents = [];
  page.on("request", (request) => {
    if (request.resourceType() === "document") documents.push(request.url());
  });
  await nav(page, "Nuevo ticket").click();
  await expect(heading(page, "Tickets")).toBeVisible();
  await expect(page.getByRole("dialog", { name: "Nuevo ticket" })).toBeVisible();
  await page.keyboard.press("Escape");
  await nav(page, "Mi cuenta").click();
  await expect(heading(page, "Mi cuenta")).toBeVisible();
  await nav(page, "Tickets").click();
  await expect(heading(page, "Tickets")).toBeVisible();
  expect(await page.evaluate(() => window.__marca)).toBe(1);
  expect(documents).toEqual([]);
});

test("SPEC-UI-19 sends a client to the home when opening #/users (TC-UI-19b)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: CLIENT });
  await page.goto("/#/users");
  await expect(heading(page, "Tickets")).toBeVisible();
  await expect.poll(() => currentHash(page)).toBe("#/tickets");
});

test("SPEC-UI-20 shows not found with a link to the role home (TC-UI-20b)", async ({ page }) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Admin");
  await goToHash(page, "#/desconocido");
  await expect(heading(page, "Página no encontrada")).toBeVisible();
  await page.getByRole("main").getByRole("link").click();
  await expect(heading(page, "Usuarios")).toBeVisible();
  await expect.poll(() => currentHash(page)).toBe("#/users");
});

test("SPEC-UI-97 shows not found for an invalid ticket id without API calls (TC-UI-97b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Client");
  await expect(heading(page, "Tickets")).toBeVisible();
  await expect(page.getByText("No hay resultados")).toBeVisible();
  const before = apiRequests(api).length;
  await goToHash(page, "#/tickets/007");
  await expect(heading(page, "Página no encontrada")).toBeVisible();
  expect(apiRequests(api)).toHaveLength(before);
});

test("SPEC-UI-124 shows the role home for #/login and the empty hash (TC-UI-124b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: ADMIN });
  await page.goto("/#/tickets/1");
  await expect(heading(page, "Ticket #1")).toBeVisible();
  await goToHash(page, "#/login");
  await expect(heading(page, "Usuarios")).toBeVisible();
  await goToHash(page, "#/tickets");
  await expect(heading(page, "Tickets")).toBeVisible();
  await goToHash(page, "");
  await expect(heading(page, "Usuarios")).toBeVisible();
});

test("SPEC-UI-132 keeps the history length when redirecting to the home (TC-UI-132b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: CLIENT });
  await page.goto("/#/users");
  await expect(heading(page, "Tickets")).toBeVisible();
  const length = await page.evaluate(() => window.history.length);
  await goToHash(page, "#/login");
  await expect.poll(() => currentHash(page)).toBe("#/tickets");
  expect(await page.evaluate(() => window.history.length)).toBeLessThanOrEqual(length + 1);
});
