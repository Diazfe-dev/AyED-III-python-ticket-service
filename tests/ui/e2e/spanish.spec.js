import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { ENGLISH_WORDS, USERS, page as pageOf, ticket } from "./support/fixtures.js";

const CREATED = "2026-01-01T12:00:00+00:00";
const CATEGORY = { id: 2, name: "Hardware" };
const TYPE = { id: 3, name: "Redes", category: CATEGORY };
const PRODUCT = { id: 9, name: "Router X", is_active: true, product_type: TYPE, category: CATEGORY };
const ACCOUNT = {
  id: 5,
  name: "Luis Mora",
  email: "luis@example.com",
  role: "Client",
  preferred_channel: "mail",
  is_active: true,
};
const AUTHOR = { id: 2, name: "Raúl Pérez", role: "Representative" };

const SCREENS = {
  Admin: [
    "#/users",
    "#/categories",
    "#/product-types",
    "#/products",
    "#/tickets",
    "#/tickets/7",
    "#/account",
    "#/inexistente",
  ],
  Representative: ["#/tickets", "#/tickets/7", "#/tickets/new", "#/account", "#/inexistente"],
  Client: ["#/tickets", "#/tickets/7", "#/tickets/new", "#/account", "#/inexistente"],
};

const goToHash = (page, hash) =>
  page.evaluate((value) => {
    window.location.hash = value;
  }, hash);

async function seed(page, role) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS[role] });
  api.on("GET", /^\/tickets\?/, {
    status: 200,
    body: pageOf([ticket(7, "InProgress", CREATED), ticket(8, "Closed", CREATED)]),
  });
  api.on("GET", "/tickets/7", {
    status: 200,
    body: { ...ticket(7, "InProgress", CREATED), products: [PRODUCT] },
  });
  api.on("GET", "/tickets/7/milestones", {
    status: 200,
    body: [{ id: 1, content: "Revisando", author: AUTHOR, created_at: CREATED }],
  });
  api.on("GET", "/tickets/7/state-changes", {
    status: 200,
    body: [{ state: "InProgress", user: AUTHOR, timestamp: CREATED }],
  });
  api.on("GET", "/users", { status: 200, body: pageOf([ACCOUNT]) });
  api.on("GET", /^\/categories(\?.*)?$/, { status: 200, body: [CATEGORY] });
  api.on("GET", "/product-types", { status: 200, body: [TYPE] });
  api.on("GET", "/products", { status: 200, body: pageOf([PRODUCT]) });
  api.on("GET", "/products/available", { status: 200, body: pageOf([PRODUCT]) });
  api.on("GET", "/clients", { status: 200, body: [{ id: 4, name: "Ana Gómez" }] });
  return api;
}

async function expectSpanish(page) {
  await page.waitForTimeout(100);
  const text = await page.evaluate(() => `${document.body.innerText}\n${document.title}`);
  for (const word of ENGLISH_WORDS) {
    expect(text, `"${word}" is visible`).not.toMatch(new RegExp(`\\b${word}\\b`));
  }
}

async function walkScreens(page, role) {
  await seed(page, role);
  await page.goto("/");
  await expect(page.getByRole("navigation")).toBeVisible();
  for (const hash of SCREENS[role]) {
    await goToHash(page, hash);
    await expect(page.locator("#app h1, #app h2").first()).toBeVisible();
    await expectSpanish(page);
  }
}

test("SPEC-UI-55 shows no English word on any screen of the administrator (TC-UI-55a)", async ({
  page,
}) => {
  await walkScreens(page, "Admin");
});

test("SPEC-UI-55 shows no English word on any screen of the representative (TC-UI-55a)", async ({
  page,
}) => {
  await walkScreens(page, "Representative");
});

test("SPEC-UI-55 shows no English word on any screen of the client (TC-UI-55a)", async ({
  page,
}) => {
  await walkScreens(page, "Client");
});

test("SPEC-UI-55 shows no English word on the login, the load error and the inert screen (TC-UI-55a)", async ({
  page,
}) => {
  const api = await seed(page, "Representative");
  api.on("GET", "/me", { status: 401, body: { error: "authentication_required" } });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Iniciar sesión", exact: true })).toBeVisible();
  await expectSpanish(page);

  api.on("GET", "/me", { status: 500, body: { error: "internal_error" } });
  await page.goto("about:blank");
  await page.goto("/");
  await expect(page.getByText("Ocurrió un error inesperado. Intente nuevamente.")).toBeVisible();
  await expectSpanish(page);

  api.on("GET", "/me", { status: 200, body: USERS.Representative });
  const logout = api.defer("POST", "/logout");
  await page.goto("about:blank");
  await page.goto("/#/tickets");
  await expect(page.getByRole("row").filter({ hasText: "#7" })).toBeVisible();
  await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
  await logout.requested;
  await expectSpanish(page);
  logout.release(204);
});
