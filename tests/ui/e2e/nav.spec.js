import { expect, test } from "@playwright/test";
import { installFakeApi, loginAs } from "./support/fake-api.js";

const navLabels = (page) => page.getByRole("navigation").getByRole("link").allInnerTexts();

async function expectNavigation(page, role, links) {
  const api = await installFakeApi(page);
  await loginAs(page, api, role);
  await expect(page.getByRole("navigation")).toBeVisible();
  expect(await navLabels(page)).toEqual(links);
}

test("SPEC-UI-16 shows the representative navigation (TC-UI-16a)", async ({ page }) => {
  await expectNavigation(page, "Representative", ["Tickets", "Nuevo ticket", "Mi cuenta"]);
});

test("SPEC-UI-17 shows the administrator navigation (TC-UI-17a)", async ({ page }) => {
  await expectNavigation(page, "Admin", [
    "Usuarios",
    "Categorías",
    "Tipos de producto",
    "Productos",
    "Tickets",
    "Mi cuenta",
  ]);
});

test("SPEC-UI-18 shows the client navigation (TC-UI-18a)", async ({ page }) => {
  await expectNavigation(page, "Client", ["Mis tickets", "Mi cuenta"]);
});
