import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { ADMIN, CLIENT, USERS, page as pageOf } from "./support/fixtures.js";

const NO_SESSION = { status: 401, body: { error: "authentication_required" } };
const STRICT_CSP =
  "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'";
const SECRET_PARAMS = ["token", "api_key", "secret"];
const ROLE_SCREENS = {
  Admin: [
    "#/users",
    "#/categories",
    "#/product-types",
    "#/products",
    "#/tickets",
    "#/tickets/1",
    "#/account",
  ],
  Representative: ["#/tickets", "#/tickets/1", "#/account"],
  Client: ["#/tickets", "#/tickets/new", "#/tickets/1", "#/account"],
};

const heading = (page, name) => page.getByRole("heading", { name, exact: true });
const settle = (page) =>
  page.evaluate(() => new Promise((done) => setTimeout(() => requestAnimationFrame(done), 50)));

function recordRequests(page) {
  const seen = [];
  page.on("request", (request) => seen.push(request));
  return seen;
}

async function login(page, api, role) {
  api.on("GET", "/me", NO_SESSION);
  api.on("POST", "/login", { status: 200, body: USERS[role] });
  await page.goto("/");
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  api.on("GET", "/me", { status: 200, body: USERS[role] });
  await page.getByLabel("Email").fill(USERS[role].email);
  await page.getByLabel("Contraseña").fill("Clave-segura-123");
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(heading(page, "Tickets").or(heading(page, "Usuarios"))).toBeVisible();
}

async function tour(page, role) {
  for (const hash of ROLE_SCREENS[role]) {
    await page.evaluate((value) => {
      window.location.hash = value;
    }, hash);
    await expect(page.locator("#app")).not.toBeEmpty();
    await settle(page);
  }
}

async function fullTour(page, role) {
  const api = await installFakeApi(page);
  const seen = recordRequests(page);
  await login(page, api, role);
  await tour(page, role);
  return { api, seen };
}

// Must run after installFakeApi: Playwright tries the latest registered route first.
async function serveWithStrictPolicy(page) {
  await page.route(
    (url) => url.pathname === "/",
    async (route) => {
      const response = await route.fetch();
      await route.fulfill({
        response,
        headers: { ...response.headers(), "content-security-policy": STRICT_CSP },
      });
    },
  );
}

test("SPEC-UI-05 every API request has the same origin and a relative path (TC-UI-05b)", async ({
  page,
  baseURL,
}) => {
  for (const role of Object.keys(ROLE_SCREENS)) {
    const { api, seen } = await fullTour(page, role);
    expect(api.requests.length).toBeGreaterThan(2);
    for (const record of api.requests) {
      expect(new URL(record.url).origin, record.url).toBe(baseURL);
    }
    for (const request of seen) {
      expect(new URL(request.url()).origin, request.url()).toBe(baseURL);
    }
  }
});

test("SPEC-UI-06 loads no script, stylesheet or font from another origin (TC-UI-06b)", async ({
  page,
  baseURL,
}) => {
  const api = await installFakeApi(page);
  const seen = recordRequests(page);
  await login(page, api, "Admin");
  await tour(page, "Admin");
  const resources = seen.filter((request) =>
    ["script", "stylesheet", "font"].includes(request.resourceType()),
  );
  expect(resources.length).toBeGreaterThan(1);
  for (const request of resources) {
    expect(new URL(request.url()).origin, request.url()).toBe(baseURL);
  }
});

test("SPEC-UI-60 no request carries Authorization or a token in the URL (TC-UI-60b)", async ({
  page,
}) => {
  for (const role of Object.keys(ROLE_SCREENS)) {
    const { seen } = await fullTour(page, role);
    expect(seen.length).toBeGreaterThan(3);
    for (const request of seen) {
      const headers = await request.allHeaders();
      expect(Object.keys(headers), request.url()).not.toContain("authorization");
      const params = [...new URL(request.url()).searchParams.keys()].map((k) => k.toLowerCase());
      for (const name of SECRET_PARAMS) {
        expect(params, request.url()).not.toContain(name);
      }
    }
  }
});

test("SPEC-UI-62 keeps no role or identity in storage, cookies or the hash (TC-UI-62a)", async ({
  page,
}) => {
  for (const role of Object.keys(ROLE_SCREENS)) {
    await fullTour(page, role);
    const user = USERS[role];
    const state = await page.evaluate(() => ({
      local: localStorage.length,
      session: sessionStorage.length,
      cookie: document.cookie,
      hash: window.location.hash,
    }));
    expect(state.local).toBe(0);
    expect(state.session).toBe(0);
    for (const value of [user.role, user.email, user.name, String(user.id)]) {
      expect(state.cookie).not.toContain(value);
    }
    for (const value of [user.role, user.email, user.name]) {
      expect(state.hash).not.toContain(value);
    }
  }
});

test("SPEC-UI-65 raises no CSP violation under a strict policy (TC-UI-65b)", async ({ page }) => {
  const messages = [];
  page.on("console", (message) => messages.push(message.text()));
  await page.addInitScript(() => {
    window.__violations = [];
    document.addEventListener("securitypolicyviolation", (event) =>
      window.__violations.push(`${event.violatedDirective} ${event.blockedURI}`),
    );
  });
  for (const role of Object.keys(ROLE_SCREENS)) {
    const api = await installFakeApi(page);
    await serveWithStrictPolicy(page);
    await login(page, api, role);
    await tour(page, role);
    expect(await page.evaluate(() => window.__violations)).toEqual([]);
  }
  expect(messages.filter((text) => /content security policy/i.test(text))).toEqual([]);
});

test("SPEC-UI-65 the strict policy is really enforced on the page (TC-UI-65b)", async ({
  page,
}) => {
  const api = await installFakeApi(page);
  await serveWithStrictPolicy(page);
  await login(page, api, "Admin");
  const blocked = await page.evaluate(
    () =>
      new Promise((resolve) => {
        document.addEventListener("securitypolicyviolation", () => resolve(true), { once: true });
        fetch("http://127.0.0.1:1/probe").catch(() => {});
        setTimeout(() => resolve(false), 500);
      }),
  );
  expect(blocked).toBe(true);
});

test("SPEC-UI-65 renders API text as text and never as markup (TC-UI-65b)", async ({ page }) => {
  const hostile = '<img src=x onerror="window.__pwned=1"><b>boom</b>';
  const api = await installFakeApi(page);
  api.on("GET", "/users", {
    status: 200,
    body: pageOf([{ ...CLIENT, id: 9, name: hostile, email: "x@example.com" }]),
  });
  api.on("GET", "/me", { status: 200, body: ADMIN });
  await page.goto("/#/users");
  await expect(page.getByText(hostile, { exact: false }).first()).toBeVisible();
  await settle(page);
  expect(await page.evaluate(() => window.__pwned)).toBeUndefined();
  await expect(page.locator("#app img, #app b")).toHaveCount(0);
});
