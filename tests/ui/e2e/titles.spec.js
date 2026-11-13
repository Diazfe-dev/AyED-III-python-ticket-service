import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { USERS } from "./support/fixtures.js";

const SUFFIX = "Mesa de ayuda";
const goToHash = (page, hash) =>
  page.evaluate((value) => {
    window.location.hash = value;
  }, hash);

const ADMIN_SCREENS = [
  ["#/users", "Usuarios"],
  ["#/categories", "Categorías"],
  ["#/product-types", "Tipos de producto"],
  ["#/products", "Productos"],
  ["#/tickets", "Tickets"],
  ["#/tickets/7", "Ticket #7"],
  ["#/account", "Mi cuenta"],
  ["#/inexistente", "Página no encontrada"],
];

test("SPEC-UI-112 names the current screen in the page title for the administrator (TC-UI-112a)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Admin });
  await page.goto("/");
  for (const [hash, name] of ADMIN_SCREENS) {
    await goToHash(page, hash);
    await expect(page).toHaveTitle(`${name} · ${SUFFIX}`);
  }
});

test("SPEC-UI-112 names the new ticket screen in the page title for the representative (TC-UI-112a)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Representative });
  await page.goto("/#/tickets/new");
  await expect(page).toHaveTitle(`Nuevo ticket · ${SUFFIX}`);
});

test("SPEC-UI-112 names the loading and login screens in the page title (TC-UI-112a)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  const me = api.defer("GET", "/me");
  await page.goto("/");
  await me.requested;
  await expect(page).toHaveTitle(`Cargando · ${SUFFIX}`);
  me.release(401, { error: "authentication_required" });
  await expect(page).toHaveTitle(`Iniciar sesión · ${SUFFIX}`);
});
