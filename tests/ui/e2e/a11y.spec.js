import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";

test("SPEC-UI-66 declares the Spanish language on the page (TC-UI-66a)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 401, body: { error: "authentication_required" } });
  await page.goto("/");
  const lang = await page.evaluate(() => document.documentElement.lang);
  expect(lang).toBe("es");
});
