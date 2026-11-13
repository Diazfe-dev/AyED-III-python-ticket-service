import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { page as pageOf, ticket, USERS } from "./support/fixtures.js";

const CREATED_AT = "2026-01-01T12:00:00+00:00";
const ROLE_SCREENS = [
  { id: 149, name: "users", role: "Admin", hash: "#/users", title: "Usuarios", action: "Nuevo usuario" },
  { id: 150, name: "categories", role: "Admin", hash: "#/categories", title: "Categorías", action: "Nueva categoría" },
  {
    id: 151,
    name: "product types",
    role: "Admin",
    hash: "#/product-types",
    title: "Tipos de producto",
    action: "Nuevo tipo de producto",
  },
  { id: 152, name: "products", role: "Admin", hash: "#/products", title: "Productos", action: "Nuevo producto" },
];
const LISTINGS = [
  ...ROLE_SCREENS,
  { id: 153, name: "tickets", role: "Representative", hash: "#/tickets", title: "Tickets", action: "Nuevo ticket" },
];

async function open(page, { role, hash }) {
  await page.goto("about:blank");
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS[role] });
  api.on("GET", "/users", {
    status: 200,
    body: pageOf([{ id: 5, name: "Luis", email: "l@example.com", role: "Client", is_active: true }]),
  });
  api.on("GET", /^\/tickets\?/, { status: 200, body: pageOf([ticket(1, "New", CREATED_AT)]) });
  api.on("GET", /^\/categories(\?|$)/, { status: 200, body: [{ id: 3, name: "Computación" }] });
  api.on("GET", /^\/product-types(\?|$)/, {
    status: 200,
    body: [{ id: 4, name: "Notebook", category_id: 3 }],
  });
  api.on("GET", "/products", {
    status: 200,
    body: pageOf([
      {
        id: 9,
        name: "Lenovo",
        is_active: true,
        product_type: { id: 4, name: "Notebook", category_id: 3 },
        category: { id: 3, name: "Computación" },
      },
    ]),
  });
  await page.goto(`/${hash}`);
  await expect(page.locator(".loading")).toHaveCount(0);
  return api;
}

const heading = (page, name) => page.getByRole("heading", { name, exact: true });

async function expectHeader(page, screen) {
  await open(page, screen);
  const header = page.locator("main > .page-header");
  await expect(header.getByRole("heading", { level: 1 })).toHaveText(screen.title);
  await expect(header.getByRole("button")).toHaveText([screen.action]);
  const [h1, button] = await Promise.all([
    header.getByRole("heading", { level: 1 }).boundingBox(),
    header.getByRole("button").boundingBox(),
  ]);
  expect(button.x).toBeGreaterThan(h1.x);
  expect(Math.abs(button.y + button.height / 2 - (h1.y + h1.height / 2))).toBeLessThan(24);
  const color = await header
    .getByRole("button")
    .evaluate((node) => getComputedStyle(node).backgroundColor);
  expect(color).toBe("rgb(25, 118, 210)");
}

test("SPEC-UI-149 shows the users header with its h1 and primary button (TC-UI-149a)", async ({
  page,
}) => {
  await expectHeader(page, ROLE_SCREENS[0]);
});

test("SPEC-UI-150 shows the categories header with its h1 and primary button (TC-UI-150a)", async ({
  page,
}) => {
  await expectHeader(page, ROLE_SCREENS[1]);
});

test("SPEC-UI-151 shows the product types header with its h1 and primary button (TC-UI-151a)", async ({
  page,
}) => {
  await expectHeader(page, ROLE_SCREENS[2]);
});

test("SPEC-UI-152 shows the products header with its h1 and primary button (TC-UI-152a)", async ({
  page,
}) => {
  await expectHeader(page, ROLE_SCREENS[3]);
});

test("SPEC-UI-153 shows Tickets and Nuevo ticket for a representative on both routes (TC-UI-153a)", async ({
  page,
}) => {
  for (const hash of ["#/tickets", "#/tickets/new"]) {
    await open(page, { role: "Representative", hash });
    const header = page.locator("main > .page-header");
    await expect(header.getByRole("heading", { level: 1 })).toHaveText("Tickets");
    await expect(header.getByRole("button")).toHaveText(["Nuevo ticket"]);
  }
});

test("SPEC-UI-153 gives an administrator and a client a header without an action (TC-UI-153b)", async ({
  page,
}) => {
  for (const role of ["Admin", "Client"]) {
    await open(page, { role, hash: "#/tickets" });
    const header = page.locator("main > .page-header");
    await expect(header.getByRole("heading", { level: 1 })).toHaveText("Tickets");
    await expect(header.getByRole("button")).toHaveCount(0);
    await expect(page.getByRole("main").getByRole("button", { name: "Nuevo ticket" })).toHaveCount(0);
  }
});

test("SPEC-UI-148 composes each listing as header plus one surface with toolbar, table and footer (TC-UI-148a)", async ({
  page,
}) => {
  for (const screen of LISTINGS) {
    await open(page, screen);
    const main = page.locator("main");
    await expect(main.locator("> .page-header")).toHaveCount(1);
    await expect(main.locator("> .surface")).toHaveCount(1);
    const surface = main.locator("> .surface");
    await expect(surface.locator("> .toolbar")).toHaveCount(1);
    await expect(surface.locator("table")).toHaveCount(1);
    await expect(surface.locator(".table-footer")).toHaveCount(1);
    const boxes = await Promise.all([
      main.locator("> .page-header").boundingBox(),
      surface.locator("> .toolbar").boundingBox(),
      surface.locator("table").boundingBox(),
      surface.locator(".table-footer").boundingBox(),
    ]);
    const tops = boxes.map((box) => box.y);
    expect([...tops].sort((a, b) => a - b), screen.name).toEqual(tops);
    expect(boxes[2].y + boxes[2].height, screen.name).toBeLessThanOrEqual(boxes[3].y + 1);
  }
});

test("SPEC-UI-148 uses the whole width of the content area at any window size (TC-UI-148b)", async ({
  page,
}) => {
  for (const width of [1000, 1900]) {
    await page.setViewportSize({ width, height: 800 });
    await open(page, LISTINGS[0]);
    const widths = await page.evaluate(() => {
      const main = document.querySelector("main");
      const surface = document.querySelector("main > .surface");
      const style = getComputedStyle(main);
      const inner = main.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
      return { surface: surface.getBoundingClientRect().width, inner };
    });
    expect(Math.abs(widths.surface - widths.inner), `width ${width}`).toBeLessThanOrEqual(1);
  }
});

test("SPEC-UI-154 puts filters and search in the toolbar, not in the header or the body (TC-UI-154a)", async ({
  page,
}) => {
  for (const screen of LISTINGS) {
    await open(page, screen);
    const toolbar = page.locator("main > .surface > .toolbar");
    await expect(toolbar.getByRole("search")).toHaveCount(1);
    await expect(page.locator("main > .page-header").getByRole("search")).toHaveCount(0);
    await expect(page.locator("main > .page-header select, main > .page-header input")).toHaveCount(0);
    const outside = await page.evaluate(
      () =>
        [...document.querySelectorAll("main select, main input[type=search]")].filter(
          (node) => !node.closest(".toolbar") && !node.closest(".table-footer") && !node.closest("dialog"),
        ).length,
    );
    expect(outside, screen.name).toBe(0);
  }
  await open(page, LISTINGS[0]);
  await expect(page.locator("main > .surface > .toolbar").getByLabel("Estado", { exact: true })).toBeVisible();
  await expect(heading(page, "Usuarios")).toBeVisible();
});
