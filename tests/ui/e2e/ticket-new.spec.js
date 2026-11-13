import { expect, test } from "@playwright/test";
import { installFakeApi, loginAs } from "./support/fake-api.js";

const ANA = { id: 11, name: "Ana Gómez" };
const ANITA = { id: 12, name: "Anita Torres" };
const CATEGORY = { id: 2, name: "Hardware" };
const PRODUCT_TYPE = { id: 3, name: "Portátiles", category: CATEGORY };
const NOTEBOOK = {
  id: 21,
  name: "Notebook X",
  is_active: true,
  product_type: PRODUCT_TYPE,
  category: CATEGORY,
};
const NOTEBOOK_PRO = { ...NOTEBOOK, id: 22, name: "Notebook Pro" };
const MONITOR = { ...NOTEBOOK, id: 23, name: "Monitor 24" };
const CREATED = { id: 15, state: "New" };

const writes = (api) => api.requests.filter((r) => r.method === "POST" && /\/tickets$/.test(r.url));
const ticketReads = (api) =>
  api.requests.filter((r) => r.method === "GET" && /\/tickets\/15$/.test(r.url));
const optionTexts = (select) => select.locator("option").allInnerTexts();
const settle = (page) =>
  page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
const heading = (page, name) => page.getByRole("heading", { name, exact: true });

async function openNew(page) {
  const api = await installFakeApi(page);
  api.on("GET", "/clients", { status: 200, body: [ANA, ANITA] });
  api.on("GET", "/products/available", { status: 200, body: [NOTEBOOK, NOTEBOOK_PRO, MONITOR] });
  await loginAs(page, api, "Representative");
  await page.goto("/#/tickets/new");
  await expect(heading(page, "Nuevo ticket")).toBeVisible();
  await expect(page.getByLabel("Cliente", { exact: true }).locator("option")).toHaveCount(3);
  await expect(page.getByLabel("Productos", { exact: true }).locator("option")).toHaveCount(3);
  return api;
}

async function fillForm(page) {
  await page.getByLabel("Cliente", { exact: true }).selectOption({ label: "Ana Gómez" });
  await page.getByLabel("Primer mensaje", { exact: true }).fill("No enciende");
  await page.getByLabel("Productos", { exact: true }).selectOption({ label: "Notebook X" });
}

async function submitAndLeave(page, api, link) {
  const gate = api.defer("POST", "/tickets");
  await fillForm(page);
  await page.getByRole("button", { name: "Crear ticket" }).click();
  await gate.requested;
  await page.getByRole("link", { name: link, exact: true }).click();
  return gate;
}

test("SPEC-UI-30 shows client, first message and optional products (TC-UI-30a)", async ({
  page,
}) => {
  await openNew(page);
  await expect(page.getByLabel("Cliente", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Primer mensaje", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Productos", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Crear ticket" })).toBeVisible();
});

test("SPEC-UI-31 searches clients with q and offers only the returned names (TC-UI-31a)", async ({
  page,
}) => {
  const api = await openNew(page);
  api.on("GET", "/clients?q=anita", { status: 200, body: [ANITA] });
  await page.getByLabel("Buscar cliente", { exact: true }).fill("anita");
  await page.getByRole("button", { name: "Buscar clientes" }).click();
  const select = page.getByLabel("Cliente", { exact: true });
  await expect(select.locator("option")).toHaveCount(2);
  expect(await optionTexts(select)).toContain("Anita Torres");
  expect(await optionTexts(select)).not.toContain("Ana Gómez");
  const last = api.requests.filter((r) => /\/clients/.test(r.url)).at(-1);
  expect(new URL(last.url).search).toBe("?q=anita");
});

test("SPEC-UI-32 searches available products with q (TC-UI-32a)", async ({ page }) => {
  const api = await openNew(page);
  api.on("GET", "/products/available?q=note", { status: 200, body: [NOTEBOOK, NOTEBOOK_PRO] });
  await page.getByLabel("Buscar producto", { exact: true }).fill("note");
  await page.getByRole("button", { name: "Buscar productos" }).click();
  const select = page.getByLabel("Productos", { exact: true });
  await expect(select.locator("option")).toHaveCount(2);
  expect(await optionTexts(select)).not.toContain("Monitor 24");
  const last = api.requests.filter((r) => /\/products\/available/.test(r.url)).at(-1);
  expect(new URL(last.url).search).toBe("?q=note");
});

test("SPEC-UI-33 creates the ticket and shows its detail (TC-UI-33a)", async ({ page }) => {
  const api = await openNew(page);
  api.on("POST", "/tickets", { status: 201, body: CREATED });
  await fillForm(page);
  await page.getByRole("button", { name: "Crear ticket" }).click();
  await expect.poll(() => new URL(page.url()).hash).toBe("#/tickets/15");
  await expect.poll(() => ticketReads(api).length).toBeGreaterThan(0);
  expect(writes(api)[0].body).toEqual({
    client_id: 11,
    first_message: "No enciende",
    product_ids: [21],
  });
});

test("SPEC-UI-33 marks the fields on a validation error (TC-UI-33a)", async ({ page }) => {
  const api = await openNew(page);
  api.on("POST", "/tickets", {
    status: 400,
    body: { error: "validation_error", fields: { first_message: "required" } },
  });
  await page.getByRole("button", { name: "Crear ticket" }).click();
  await expect(page.getByText("Este campo es obligatorio")).toBeVisible();
  expect(new URL(page.url()).hash).toBe("#/tickets/new");
});

test("SPEC-UI-136 ignores a 201 that arrives on another screen (TC-UI-136c)", async ({ page }) => {
  const api = await openNew(page);
  const gate = await submitAndLeave(page, api, "Mi cuenta");
  await expect(heading(page, "Mi cuenta")).toBeVisible();
  gate.release(201, CREATED);
  await expect.poll(() => writes(api)[0].status).toBe(201);
  await settle(page);
  expect(new URL(page.url()).hash).toBe("#/account");
  expect(ticketReads(api)).toHaveLength(0);
});

test("SPEC-UI-136 shows no error for a stale 400 (TC-UI-136c)", async ({ page }) => {
  const api = await openNew(page);
  const gate = await submitAndLeave(page, api, "Mi cuenta");
  await expect(heading(page, "Mi cuenta")).toBeVisible();
  gate.release(400, { error: "validation_error", fields: { first_message: "required" } });
  await expect.poll(() => writes(api)[0].status).toBe(400);
  await settle(page);
  await expect(page.locator("#alert")).toHaveText("");
  await expect(page.getByText("Este campo es obligatorio")).toHaveCount(0);
  expect(new URL(page.url()).hash).toBe("#/account");
});

test("SPEC-UI-136 ignores the earlier 201 after leaving and coming back (TC-UI-136e)", async ({
  page,
}) => {
  const api = await openNew(page);
  const gate = await submitAndLeave(page, api, "Mi cuenta");
  await expect(heading(page, "Mi cuenta")).toBeVisible();
  await page.getByRole("link", { name: "Nuevo ticket", exact: true }).click();
  await expect(heading(page, "Nuevo ticket")).toBeVisible();
  gate.release(201, CREATED);
  await expect.poll(() => writes(api)[0].status).toBe(201);
  await settle(page);
  await expect(heading(page, "Nuevo ticket")).toBeVisible();
  await expect(page.getByLabel("Primer mensaje", { exact: true })).toHaveValue("");
  expect(new URL(page.url()).hash).toBe("#/tickets/new");
  expect(ticketReads(api)).toHaveLength(0);
});

async function expectStaleFailureIgnored(page, finish) {
  const api = await openNew(page);
  const gate = await submitAndLeave(page, api, "Tickets");
  await expect(heading(page, "Tickets")).toBeVisible();
  finish(gate);
  await expect.poll(() => writes(api)[0].status !== undefined || writes(api)[0].aborted).toBe(true);
  await settle(page);
  await expect(page.locator("#alert")).toHaveText("");
  await expect(heading(page, "Tickets")).toBeVisible();
  expect(new URL(page.url()).hash).toBe("#/tickets");
}

test("SPEC-UI-136 shows no error for a stale 500 (TC-UI-136f)", async ({ page }) => {
  await expectStaleFailureIgnored(page, (gate) => gate.release(500, { error: "internal_error" }));
});

test("SPEC-UI-136 shows no error for a stale route.abort (TC-UI-136f)", async ({ page }) => {
  await expectStaleFailureIgnored(page, (gate) => gate.abort());
});
