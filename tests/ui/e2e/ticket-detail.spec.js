import { expect, test } from "@playwright/test";
import { installFakeApi, loginAs } from "./support/fake-api.js";
import { CLIENT, REP, ticket } from "./support/fixtures.js";

const CATEGORY = { id: 2, name: "Hardware" };
const PRODUCT = {
  id: 9,
  name: "Router X",
  is_active: true,
  product_type: { id: 3, name: "Redes", category: CATEGORY },
  category: CATEGORY,
};
const DETAIL = {
  ...ticket(7, "InProgress", "2026-01-01T12:00:00+00:00"),
  products: [PRODUCT],
};
const MILESTONES = [
  {
    id: 2,
    content: "Segundo mensaje",
    author: { id: REP.id, name: REP.name, role: "Representative" },
    created_at: "2026-01-02T12:00:00+00:00",
  },
  {
    id: 1,
    content: "Primer mensaje",
    author: { id: CLIENT.id, name: CLIENT.name, role: "Client" },
    created_at: "2026-01-01T12:00:00+00:00",
  },
];
const CHANGES = [
  {
    state: "InProgress",
    user: { id: REP.id, name: REP.name, role: "Representative" },
    timestamp: "2026-01-03T12:00:00+00:00",
  },
  {
    state: "New",
    user: { id: CLIENT.id, name: CLIENT.name, role: "Client" },
    timestamp: "2026-01-01T12:00:00+00:00",
  },
];

async function openDetail(page, role) {
  const api = await installFakeApi(page);
  api.on("GET", "/tickets/7", { status: 200, body: DETAIL });
  api.on("GET", "/tickets/7/milestones", { status: 200, body: MILESTONES });
  api.on("GET", "/tickets/7/state-changes", { status: 200, body: CHANGES });
  await loginAs(page, api, role);
  await page.goto("/#/tickets/7");
  await expect(page.getByRole("heading", { name: "Ticket #7", exact: true })).toBeVisible();
  return api;
}

test("SPEC-UI-27 requests the ticket, milestones and history and shows them (TC-UI-27a)", async ({
  page,
}) => {
  const api = await openDetail(page, "Representative");
  const paths = () => api.requests.map((r) => `${r.method} ${new URL(r.url).pathname}`);
  const main = page.locator("#app");
  await expect(main).toContainText("Primer mensaje");
  await expect.poll(paths).toEqual(
    expect.arrayContaining([
      "GET /tickets/7",
      "GET /tickets/7/milestones",
      "GET /tickets/7/state-changes",
    ]),
  );
  await expect(page.locator(".ticket-state")).toHaveText("En curso");
  await expect(main).toContainText("Ana Gómez");
  await expect(main).toContainText("Raúl Pérez");
  await expect(main).toContainText("Router X");
  await expect(page.locator("ol.state-changes")).toContainText("Nuevo");
});

test("SPEC-UI-28 shows milestones and history in the order received (TC-UI-28a)", async ({
  page,
}) => {
  await openDetail(page, "Client");
  const milestones = page.locator("ol.milestones > li");
  await expect(milestones).toHaveCount(2);
  await expect(milestones.nth(0)).toContainText("Segundo mensaje");
  await expect(milestones.nth(0)).toContainText("Raúl Pérez");
  await expect(milestones.nth(0)).toContainText("Representante");
  await expect(milestones.nth(0)).toContainText("02/01/2026");
  await expect(milestones.nth(1)).toContainText("Primer mensaje");
  await expect(milestones.nth(1)).toContainText("Cliente");
  const changes = page.locator("ol.state-changes > li");
  await expect(changes).toHaveCount(2);
  await expect(changes.nth(0)).toContainText("En curso");
  await expect(changes.nth(0)).toContainText("Raúl Pérez");
  await expect(changes.nth(0)).toContainText("Representante");
  await expect(changes.nth(1)).toContainText("Nuevo");
  await expect(changes.nth(1)).toContainText("Cliente");
});

test.describe("browser in Buenos Aires", () => {
  test.use({ timezoneId: "America/Argentina/Buenos_Aires" });

  test("SPEC-UI-29 shows dates in the browser time zone (TC-UI-29b)", async ({ page }) => {
    await openDetail(page, "Client");
    await expect(page.locator("ol.milestones > li").nth(1)).toContainText("01/01/2026 09:00");
    await expect(page.locator("ol.state-changes > li").nth(1)).toContainText("01/01/2026 09:00");
  });
});

test("SPEC-UI-41 shows no forms or buttons to the admin in the detail (TC-UI-41b)", async ({
  page,
}) => {
  await openDetail(page, "Admin");
  await expect(page.locator("ol.milestones > li")).toHaveCount(2);
  await expect(page.locator("#app form")).toHaveCount(0);
  await expect(page.locator("#app button")).toHaveCount(0);
});
