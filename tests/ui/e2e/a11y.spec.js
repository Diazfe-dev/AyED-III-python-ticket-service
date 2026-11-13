import { expect, test } from "@playwright/test";
import { installFakeApi, loginAs } from "./support/fake-api.js";
import { contrastRatio, page as pageOf, ticket } from "./support/fixtures.js";

const NO_SESSION = { status: 401, body: { error: "authentication_required" } };
const CREATED_AT = "2026-01-01T12:00:00+00:00";
const LONG_EMAIL = `${"muy-largo-".repeat(8)}@example.com`;
const USER_ROWS = [
  { id: 5, name: "Lucía Fernández", email: LONG_EMAIL, role: "Client", is_active: true },
  { id: 6, name: "Pablo Núñez", email: "pablo@example.com", role: "Representative", is_active: false },
];
const SCREENS = [
  { name: "tickets", role: "Admin", hash: "#/tickets", heading: "Tickets" },
  { name: "new ticket", role: "Representative", hash: "#/tickets/new", heading: "Tickets" },
  { name: "ticket detail", role: "Representative", hash: "#/tickets/7", heading: "Ticket #7" },
  { name: "account", role: "Client", hash: "#/account", heading: "Mi cuenta" },
  { name: "users", role: "Admin", hash: "#/users", heading: "Usuarios" },
  { name: "categories", role: "Admin", hash: "#/categories", heading: "Categorías" },
  { name: "product types", role: "Admin", hash: "#/product-types", heading: "Tipos de producto" },
  { name: "products", role: "Admin", hash: "#/products", heading: "Productos" },
];
const EMPTY_LISTS = SCREENS.filter((screen) =>
  ["users", "categories", "product types", "products"].includes(screen.name),
);

const headingOf = (page, name) => page.getByRole("heading", { name, exact: true });

async function openScreen(page, { role, hash, heading }, setup = () => {}) {
  const api = await installFakeApi(page);
  api.on("GET", "/tickets/7", { status: 200, body: ticket(7, "InProgress", CREATED_AT) });
  api.on("GET", /^\/tickets\?/, {
    status: 200,
    body: pageOf(
      Array.from({ length: 3 }, (_, i) => ticket(i + 1, "New", CREATED_AT)),
      1,
      3,
    ),
  });
  api.on("GET", "/users", { status: 200, body: pageOf(USER_ROWS) });
  setup(api);
  await loginAs(page, api, role);
  await page.goto(`/${hash}`);
  await expect(headingOf(page, heading)).toBeVisible();
  await expect(page.locator(".loading")).toHaveCount(0);
  return api;
}

test("SPEC-UI-66 declares the Spanish language on the page (TC-UI-66a)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 401, body: { error: "authentication_required" } });
  await page.goto("/");
  const lang = await page.evaluate(() => document.documentElement.lang);
  expect(lang).toBe("es");
});

const visibleFields = (page) =>
  page.evaluate(() => {
    const isVisible = (node) => {
      const box = node.getBoundingClientRect();
      return box.width > 0 && box.height > 0 && getComputedStyle(node).visibility === "visible";
    };
    return [...document.querySelectorAll("input, select, textarea")]
      .filter((node) => isVisible(node))
      .map((node) => ({
        id: node.id,
        labels: [...node.labels].map((label) => isVisible(label) && label.textContent.trim() !== ""),
      }));
  });

test("SPEC-UI-67 every field of every screen has a visible label (TC-UI-67a)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", NO_SESSION);
  await page.goto("/");
  await expect(headingOf(page, "Iniciar sesión")).toBeVisible();
  const loginFields = await visibleFields(page);
  expect(loginFields).toHaveLength(2);
  for (const field of loginFields) {
    expect(field.labels, `login field ${field.id}`).toEqual([true]);
  }
  for (const screen of SCREENS) {
    await openScreen(page, screen);
    const fields = await visibleFields(page);
    expect(fields.length, screen.name).toBeGreaterThan(0);
    for (const field of fields) {
      expect(field.labels, `${screen.name}: field ${field.id}`).toEqual([true]);
    }
  }
});

async function tabTo(page, target, limit = 40) {
  for (let step = 0; step < limit; step += 1) {
    await page.keyboard.press("Tab");
    const hit = await page.evaluate(
      ({ id, tag, text }) => {
        const node = document.activeElement;
        return (
          (id === undefined || node.id === id) &&
          (tag === undefined || node.tagName === tag) &&
          (text === undefined || node.textContent.trim() === text)
        );
      },
      target,
    );
    if (hit) {
      return;
    }
  }
  throw new Error(`Tab never reached the control: ${JSON.stringify(target)}`);
}

const isField = (id) => ({ id });
const isButton = (text) => ({ tag: "BUTTON", text });

test("SPEC-UI-68 the whole flow works with the keyboard only (TC-UI-68a)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", NO_SESSION);
  api.on("POST", "/login", { status: 200, body: { id: 2, name: "Raúl Pérez", role: "Representative" } });
  api.on("GET", "/clients", {
    status: 200,
    body: [
      { id: 11, name: "Ana Gómez" },
      { id: 12, name: "Anita Torres" },
    ],
  });
  api.on("POST", "/tickets", { status: 201, body: { id: 15, state: "New" } });
  api.on("GET", "/tickets/15", { status: 200, body: ticket(15, "InProgress", CREATED_AT) });
  api.on("POST", "/tickets/15/close", { status: 200, body: ticket(15, "Closed", CREATED_AT) });
  api.on("POST", "/logout", { status: 204 });
  await page.goto("/");
  await expect(headingOf(page, "Iniciar sesión")).toBeVisible();

  await tabTo(page, isField("login-email"));
  await page.keyboard.type("raul.perez@example.com");
  await page.keyboard.press("Tab");
  await page.keyboard.type("Clave-segura-123");
  api.on("GET", "/me", { status: 200, body: { id: 2, name: "Raúl Pérez", role: "Representative" } });
  await page.keyboard.press("Enter");
  await expect(headingOf(page, "Tickets")).toBeVisible();

  await tabTo(page, { tag: "A", text: "Nuevo ticket" });
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Nuevo ticket" })).toBeVisible();
  await expect(
    page.getByRole("dialog").getByLabel("Cliente", { exact: true }).locator("option"),
  ).toHaveCount(3);

  await tabTo(page, isField("ticket-client"));
  await page.keyboard.press("ArrowDown");
  await page.keyboard.type("Ana");
  await expect(page.getByRole("dialog").getByLabel("Cliente", { exact: true })).toHaveValue("11");
  await tabTo(page, isField("ticket-message"));
  await page.keyboard.type("No enciende");
  await tabTo(page, isButton("Crear"));
  await page.keyboard.press("Space");
  await expect(headingOf(page, "Ticket #15")).toBeVisible();

  await tabTo(page, isButton("Cerrar"));
  await page.keyboard.press("Enter");
  await expect
    .poll(() => api.requests.filter((r) => r.url.endsWith("/tickets/15/close")).length)
    .toBe(1);

  await tabTo(page, isButton("Cerrar sesión"));
  await page.keyboard.press("Enter");
  await expect(headingOf(page, "Iniciar sesión")).toBeVisible();
  const created = api.requests.find((r) => r.method === "POST" && r.url.endsWith("/tickets"));
  expect(created.body.client_id).toBe(11);
});

test("SPEC-UI-113 actions are native controls on every screen (TC-UI-113a)", async ({ page }) => {
  for (const screen of SCREENS) {
    await openScreen(page, screen);
    const offenders = await page.evaluate(() =>
      [
        ...document.querySelectorAll(
          "[role=button], [onclick], div[tabindex], span[tabindex], a:not([href])",
        ),
      ].map((node) => node.outerHTML.slice(0, 80)),
    );
    expect(offenders, screen.name).toEqual([]);
  }
});

test("SPEC-UI-114 every focusable control shows a focus indicator (TC-UI-114a)", async ({
  page,
}) => {
  const screens = [SCREENS[0], SCREENS[2], SCREENS[4]];
  for (const screen of screens) {
    await openScreen(page, screen);
    const count = await page.evaluate(
      () =>
        [...document.querySelectorAll("a[href], button, input, select, textarea")].filter(
          (node) => node.getBoundingClientRect().width > 0,
        ).length,
    );
    expect(count, screen.name).toBeGreaterThan(5);
    await page.evaluate(() => document.activeElement?.blur());
    for (let index = 0; index < count; index += 1) {
      await page.keyboard.press("Tab");
      const result = await page.evaluate(() => {
        const node = document.activeElement;
        const read = () => {
          const style = getComputedStyle(node);
          return { outline: style.outlineStyle, width: style.outlineWidth, shadow: style.boxShadow };
        };
        const focused = read();
        node.blur();
        const plain = read();
        node.focus();
        return { tag: node.tagName, focused, plain };
      });
      if (result.tag === "BODY") {
        continue;
      }
      const outline = result.focused.outline !== "none" && result.focused.width !== "0px";
      const shadow =
        result.focused.shadow !== "none" && result.focused.shadow !== result.plain.shadow;
      expect(outline || shadow, `${screen.name}: ${result.tag} #${index}`).toBe(true);
    }
  }
});

test("SPEC-UI-69 errors go in an alert region and confirmations in a status region (TC-UI-69a)", async ({
  page,
}) => {
  await openScreen(page, SCREENS[3]);
  const fill = async () => {
    await page.getByLabel("Contraseña actual", { exact: true }).fill("Clave-segura-123");
    await page.getByLabel("Nueva contraseña", { exact: true }).fill("Otra-clave-456");
    await page.getByLabel("Confirmar nueva contraseña", { exact: true }).fill("Otra-clave-456");
    await page.getByRole("button", { name: "Cambiar contraseña" }).click();
  };
  await page.route("**/me/password", (route) => route.fulfill({ status: 500, body: "" }));
  await fill();
  const alert = page.getByRole("alert").filter({ hasText: /\S/ });
  await expect(alert).toHaveCount(1);
  await expect(alert).toBeVisible();

  await page.unroute("**/me/password");
  await page.route("**/me/password", (route) => route.fulfill({ status: 204 }));
  await fill();
  const status = page.getByRole("status").filter({ hasText: /\S/ });
  await expect(status).toHaveCount(1);
  await expect(status).toBeVisible();
});

test("SPEC-UI-70 every screen fits in 360 px and tables scroll inside their container (TC-UI-70a)", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const api = await installFakeApi(page);
  api.on("GET", "/me", NO_SESSION);
  await page.goto("/");
  await expect(headingOf(page, "Iniciar sesión")).toBeVisible();
  const fits = () =>
    page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth,
    }));
  const login = await fits();
  expect(login.scroll).toBeLessThanOrEqual(login.client);
  for (const screen of SCREENS) {
    await openScreen(page, screen);
    const size = await fits();
    expect(size.scroll, screen.name).toBeLessThanOrEqual(size.client);
  }
  await openScreen(page, SCREENS.find((screen) => screen.name === "users"));
  const table = await page.evaluate(() => {
    const box = document.querySelector(".table-scroll");
    return { scroll: box.scrollWidth, client: box.clientWidth, overflow: getComputedStyle(box).overflowX };
  });
  expect(table.scroll).toBeGreaterThan(table.client);
  expect(["auto", "scroll"]).toContain(table.overflow);
  const size = await fits();
  expect(size.scroll).toBeLessThanOrEqual(size.client);
});

test("SPEC-UI-115 every empty listing says there are no results (TC-UI-115b)", async ({ page }) => {
  for (const screen of EMPTY_LISTS) {
    await openScreen(page, screen, (api) => api.on("GET", "/users", { status: 200, body: pageOf([]) }));
    await expect(page.locator("#app")).toContainText("No hay resultados");
  }
});

const readTextColors = () => {
  const channels = (value) => (value.match(/[\d.]+/g) ?? []).map(Number);
  const blend = (top, under) => {
    const alpha = top[3] ?? 1;
    return [0, 1, 2].map((i) => top[i] * alpha + under[i] * (1 - alpha));
  };
  const backgroundOf = (node) => {
    const layers = [];
    for (let current = node; current; current = current.parentElement) {
      const color = channels(getComputedStyle(current).backgroundColor);
      if (color.length > 0 && (color[3] ?? 1) > 0) {
        layers.push(color);
        if ((color[3] ?? 1) === 1) {
          break;
        }
      }
    }
    return layers.reduceRight((under, layer) => blend(layer, under), [255, 255, 255]);
  };
  const visible = (node) => {
    const box = node.getBoundingClientRect();
    return box.width > 0 && box.height > 0 && getComputedStyle(node).visibility === "visible";
  };
  const found = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let text = walker.nextNode(); text; text = walker.nextNode()) {
    const owner = text.parentElement;
    if (text.textContent.trim() === "" || owner.closest("option, script, style") || !visible(owner)) {
      continue;
    }
    const background = backgroundOf(owner);
    found.push({
      text: text.textContent.trim().slice(0, 40),
      color: blend(channels(getComputedStyle(owner).color), background),
      background,
    });
  }
  for (const select of document.querySelectorAll("select")) {
    if (visible(select)) {
      const background = backgroundOf(select);
      found.push({
        text: `select ${select.id}`,
        color: blend(channels(getComputedStyle(select).color), background),
        background,
      });
    }
  }
  return found;
};

async function expectReadable(page, label) {
  const found = await page.evaluate(readTextColors);
  expect(found.length, label).toBeGreaterThan(0);
  for (const item of found) {
    const ratio = contrastRatio(item.color, item.background);
    expect(ratio, `${label}: "${item.text}" has contrast ${ratio.toFixed(2)}`).toBeGreaterThanOrEqual(4.5);
  }
}

test("SPEC-UI-72 text keeps a 4.5:1 contrast on every screen, at rest and with a message (TC-UI-72a)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", NO_SESSION);
  await page.goto("/");
  await expect(headingOf(page, "Iniciar sesión")).toBeVisible();
  await expectReadable(page, "login");
  for (const screen of SCREENS) {
    await openScreen(page, screen);
    await expectReadable(page, screen.name);
    await page.evaluate(() => {
      document.querySelector("#alert").textContent = "No se pudo completar la operación.";
      document.querySelector("#status").textContent = "La operación se realizó.";
    });
    await expectReadable(page, `${screen.name} with messages`);
  }
});

test("SPEC-UI-72 text keeps a 4.5:1 contrast while the screen is inert (TC-UI-72a)", async ({
  page,
}) => {
  for (const screen of [SCREENS[0], SCREENS[4]]) {
    let logout;
    await openScreen(page, screen, (api) => {
      logout = api.defer("POST", "/logout");
    });
    await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
    await logout.requested;
    await expect(page.getByRole("button", { name: "Cerrar sesión", exact: true })).toBeDisabled();
    await expectReadable(page, `${screen.name} inert`);
    logout.release(204);
  }
});

const focusedHeading = (page) =>
  page.evaluate(() => {
    const node = document.activeElement;
    return node?.tagName === "H1" ? node.textContent : `${node?.tagName}:${node?.textContent}`;
  });

const navLink = (page, name) =>
  page.getByRole("navigation").getByRole("link", { name, exact: true });

test("SPEC-UI-137 moves focus to the heading of the login screen (TC-UI-137a)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  api.on("GET", "/me", NO_SESSION);
  await page.goto("/");
  await expect(headingOf(page, "Iniciar sesión")).toBeVisible();
  await expect(headingOf(page, "Iniciar sesión")).toBeFocused();
});

test("SPEC-UI-137 moves focus to the heading of the role home after the session check (TC-UI-137b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Admin");
  await expect(headingOf(page, "Usuarios")).toBeVisible();
  expect(await focusedHeading(page)).toBe("Usuarios");
});

test("SPEC-UI-137 moves focus to the heading of each screen reached from the navigation (TC-UI-137c)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Representative");
  await expect(headingOf(page, "Tickets")).toBeVisible();
  for (const name of ["Mi cuenta", "Tickets"]) {
    await navLink(page, name).click();
    await expect(headingOf(page, name)).toBeVisible();
    expect(await focusedHeading(page), name).toBe(name);
  }
});

test("SPEC-UI-137 moves focus to the first field of the dialog on #/tickets/new (TC-UI-137f)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Representative");
  await expect(headingOf(page, "Tickets")).toBeVisible();
  await navLink(page, "Nuevo ticket").click();
  const dialog = page.getByRole("dialog", { name: "Nuevo ticket" });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator("input, select, textarea").first()).toBeFocused();
});

test("SPEC-UI-137 moves focus to the heading of the not-found screen (TC-UI-137d)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Client");
  await expect(headingOf(page, "Tickets")).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/does-not-exist";
  });
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText("Tickets");
  expect(await page.evaluate(() => document.activeElement.tagName)).toBe("H1");
});

test("SPEC-UI-137 keeps the focus indicator on controls while the heading has no ring (TC-UI-137e)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Admin");
  await expect(headingOf(page, "Usuarios")).toBeFocused();
  const outline = await headingOf(page, "Usuarios").evaluate(
    (node) => getComputedStyle(node).outlineStyle,
  );
  expect(outline).toBe("none");
  await page.keyboard.press("Tab");
  const control = await page.evaluate(() => {
    const node = document.activeElement;
    const read = () => {
      const style = getComputedStyle(node);
      return { outline: style.outlineStyle, width: style.outlineWidth, shadow: style.boxShadow };
    };
    const focused = read();
    node.blur();
    const plain = read();
    node.focus();
    return { focused, plain };
  });
  const ring = control.focused.outline !== "none" && control.focused.width !== "0px";
  const shadow = control.focused.shadow !== "none" && control.focused.shadow !== control.plain.shadow;
  expect(ring || shadow).toBe(true);
});

const currentLinks = (page) =>
  page.getByRole("navigation").evaluate((nav) =>
    [...nav.querySelectorAll("a[aria-current]")].map((link) => ({
      text: link.textContent,
      value: link.getAttribute("aria-current"),
    })),
  );

test("SPEC-UI-138 marks only the navigation link of the shown route for an administrator (TC-UI-138a)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Admin");
  await expect(headingOf(page, "Usuarios")).toBeVisible();
  expect(await currentLinks(page)).toEqual([{ text: "Usuarios", value: "page" }]);
  for (const name of ["Mi cuenta", "Tickets", "Productos"]) {
    await navLink(page, name).click();
    await expect(headingOf(page, name)).toBeVisible();
    expect(await currentLinks(page), name).toEqual([{ text: name, value: "page" }]);
  }
});

test("SPEC-UI-138 marks only the navigation link of the shown route for a client (TC-UI-138b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await loginAs(page, api, "Client");
  await expect(headingOf(page, "Tickets")).toBeVisible();
  expect(await currentLinks(page)).toEqual([{ text: "Mis tickets", value: "page" }]);
  await navLink(page, "Mi cuenta").click();
  await expect(headingOf(page, "Mi cuenta")).toBeVisible();
  expect(await currentLinks(page)).toEqual([{ text: "Mi cuenta", value: "page" }]);
});

test("SPEC-UI-138 marks no navigation link on the ticket detail (TC-UI-138c)", async ({ page }) => {
  const api = await installFakeApi(page);
  api.on("GET", "/tickets/7", { status: 200, body: ticket(7, "New", CREATED_AT) });
  await loginAs(page, api, "Representative");
  await expect(headingOf(page, "Tickets")).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/tickets/7";
  });
  await expect(headingOf(page, "Ticket #7")).toBeVisible();
  expect(await currentLinks(page)).toEqual([]);
});
