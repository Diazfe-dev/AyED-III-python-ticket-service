import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { historyLength, page as pageOf, ticket, USERS } from "./support/fixtures.js";

const account = (id, name, role, channel = "mail") => ({
  id,
  name,
  email: `cuenta${id}@example.com`,
  role,
  preferred_channel: channel,
  is_active: true,
});
const LUIS = account(5, "Luis Mora", "Client");
const COMPUTING = { id: 3, name: "Computación" };
const NETWORKS = { id: 5, name: "Redes" };
const LAPTOP = { id: 4, name: "Notebook", category_id: 3 };
const ROUTER = { id: 6, name: "Router", category_id: 5 };
const LENOVO = {
  id: 9,
  name: "Lenovo T14",
  is_active: true,
  product_type: LAPTOP,
  category: COMPUTING,
};
const ANA = { id: 11, name: "Ana Gómez" };
const NOTEBOOK = { id: 21, name: "Notebook X" };
const CREATED = { id: 15, state: "New" };

const SCREENS = [
  {
    name: "users",
    role: "Admin",
    hash: "#/users",
    heading: "Usuarios",
    create: { button: "Nuevo usuario", submit: "Crear" },
    edit: { row: "Luis Mora", title: "Editar usuario", submit: "Guardar" },
  },
  {
    name: "categories",
    role: "Admin",
    hash: "#/categories",
    heading: "Categorías",
    create: { button: "Nueva categoría", submit: "Crear" },
    edit: { row: "Computación", title: "Editar categoría", submit: "Guardar" },
  },
  {
    name: "product types",
    role: "Admin",
    hash: "#/product-types",
    heading: "Tipos de producto",
    create: { button: "Nuevo tipo de producto", submit: "Crear" },
    edit: { row: "Notebook", title: "Editar tipo de producto", submit: "Guardar" },
  },
  {
    name: "products",
    role: "Admin",
    hash: "#/products",
    heading: "Productos",
    create: { button: "Nuevo producto", submit: "Crear" },
    edit: { row: "Lenovo T14", title: "Editar producto", submit: "Guardar" },
  },
  {
    name: "tickets",
    role: "Representative",
    hash: "#/tickets",
    heading: "Tickets",
    create: { button: "Nuevo ticket", submit: "Crear" },
  },
];

async function installScreen(page, role) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS[role] });
  api.on("GET", "/users", { status: 200, body: pageOf([LUIS]) });
  api.on("GET", /^\/categories(\?|$)/, { status: 200, body: [COMPUTING, NETWORKS] });
  api.on("GET", /^\/product-types(\?|$)/, { status: 200, body: [LAPTOP, ROUTER] });
  api.on("GET", "/products", { status: 200, body: pageOf([LENOVO]) });
  api.on("GET", "/clients", { status: 200, body: [ANA] });
  api.on("GET", "/products/available", { status: 200, body: [NOTEBOOK] });
  return api;
}

async function openScreen(page, screen) {
  await page.goto("about:blank");
  const api = await installScreen(page, screen.role);
  await page.goto(`/${screen.hash}`);
  await expect(page.getByRole("heading", { name: screen.heading, exact: true })).toBeVisible();
  if (screen.edit) {
    await expect(page.getByRole("row").filter({ hasText: screen.edit.row })).toBeVisible();
  }
  return api;
}

const dialogOf = (page) => page.getByRole("dialog");
const mainButton = (page, name) => page.getByRole("main").getByRole("button", { name, exact: true });
const rowOf = (page, text) => page.getByRole("row").filter({ hasText: text });
const heading = (page, name) => page.getByRole("heading", { name, exact: true });
const hashOf = (page) => page.evaluate(() => window.location.hash);
const settle = (page) =>
  page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
const writesOf = (api) => api.requests.filter((r) => r.method !== "GET");
const callsTo = (api, path) =>
  api.requests.filter((r) => r.method === "GET" && new URL(r.url).pathname === path);
const outsideForms = (page) =>
  page.evaluate(
    () =>
      [...document.querySelectorAll("main form")].filter(
        (form) => !form.closest("dialog") && form.getAttribute("role") !== "search",
      ).length,
  );

async function fillUser(page, name = "Rosa Paz") {
  const dialog = dialogOf(page);
  await dialog.getByLabel("Nombre").fill(name);
  await dialog.getByLabel("Email").fill("rosa@example.com");
  await dialog.getByLabel("Rol").selectOption({ label: "Cliente" });
  await dialog.getByLabel("Contraseña", { exact: true }).fill("clave-larga-1");
}

test("SPEC-UI-155 shows no create, edit or reset form in the page body (TC-UI-155a)", async ({
  page,
}) => {
  for (const screen of SCREENS) {
    await openScreen(page, screen);
    expect(await outsideForms(page), screen.name).toBe(0);
    await expect(dialogOf(page)).toHaveCount(0);
    await mainButton(page, screen.create.button).click();
    await expect(dialogOf(page)).toBeVisible();
    expect(await outsideForms(page), `${screen.name} with the dialog open`).toBe(0);
    await page.keyboard.press("Escape");
    await expect(dialogOf(page)).toHaveCount(0);
  }
});

test("SPEC-UI-156 opens an empty create dialog from the header button without changing the hash (TC-UI-156a)", async ({
  page,
}) => {
  for (const screen of SCREENS) {
    await openScreen(page, screen);
    const before = await hashOf(page);
    await mainButton(page, screen.create.button).click();
    const dialog = dialogOf(page);
    await expect(dialog).toBeVisible();
    expect(await hashOf(page), screen.name).toBe(before);
    for (const field of await dialog.locator("input:not([type=search]), textarea").all()) {
      await expect(field).toHaveValue("");
    }
    await dialog.getByRole("button", { name: "Cancelar" }).click();
  }
});

test("SPEC-UI-157 opens the edit dialog with the values of the row as field text (TC-UI-157a)", async ({
  page,
}) => {
  const tricky = { ...LUIS, name: "<b>Luis</b> Mora" };
  const api = await installScreen(page, "Admin");
  api.on("GET", "/users", { status: 200, body: pageOf([tricky]) });
  await page.goto("/#/users");
  await rowOf(page, "Mora").getByRole("button", { name: "Editar" }).click();
  const user = dialogOf(page);
  await expect(user.getByLabel("Nombre")).toHaveValue("<b>Luis</b> Mora");
  await expect(user.getByLabel("Email")).toHaveValue("cuenta5@example.com");
  await expect(user.getByLabel("Canal")).toHaveValue("mail");
  await expect(user.locator("b")).toHaveCount(0);

  await page.goto("/#/categories");
  await rowOf(page, "Computación").getByRole("button", { name: "Editar" }).click();
  await expect(dialogOf(page).getByLabel("Nombre")).toHaveValue("Computación");
  await page.keyboard.press("Escape");

  await page.goto("/#/product-types");
  await rowOf(page, "Router").getByRole("button", { name: "Editar" }).click();
  await expect(dialogOf(page).getByLabel("Nombre")).toHaveValue("Router");
  await expect(dialogOf(page).getByLabel("Categoría")).toHaveValue("5");
  await page.keyboard.press("Escape");

  await page.goto("/#/products");
  await rowOf(page, "Lenovo T14").getByRole("button", { name: "Editar" }).click();
  await expect(dialogOf(page).getByLabel("Nombre")).toHaveValue("Lenovo T14");
  await expect(dialogOf(page).getByLabel("Tipo")).toHaveValue("4");
});

test("SPEC-UI-158 opens the reset dialog with two empty password fields (TC-UI-158a)", async ({
  page,
}) => {
  const api = await installScreen(page, "Admin");
  await page.goto("/#/users");
  await rowOf(page, "Luis Mora").getByRole("button", { name: "Restablecer contraseña" }).click();
  const dialog = dialogOf(page);
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Nueva contraseña", { exact: true })).toHaveValue("");
  await expect(dialog.getByLabel("Confirmar nueva contraseña")).toHaveValue("");
  await expect(dialog.getByLabel("Nueva contraseña", { exact: true })).toHaveAttribute(
    "type",
    "password",
  );
  expect(writesOf(api)).toHaveLength(0);
});

test("SPEC-UI-159 shows each form in a native modal dialog with a labelled title and the table texts (TC-UI-159a)", async ({
  page,
}) => {
  const titles = new Map([
    ["Nuevo usuario", "Crear"],
    ["Nueva categoría", "Crear"],
    ["Nuevo tipo de producto", "Crear"],
    ["Nuevo producto", "Crear"],
    ["Nuevo ticket", "Crear"],
  ]);
  for (const screen of SCREENS) {
    await openScreen(page, screen);
    await mainButton(page, screen.create.button).click();
    const dialog = dialogOf(page);
    const state = await dialog.evaluate((node) => ({
      modal: node.matches(":modal"),
      labelledby: node.getAttribute("aria-labelledby"),
      title: document.getElementById(node.getAttribute("aria-labelledby"))?.textContent,
      inRoot: document.getElementById("app").contains(node),
    }));
    expect(state.modal, screen.name).toBe(true);
    expect(state.inRoot, screen.name).toBe(true);
    expect(state.title, screen.name).toBe(screen.create.button);
    await expect(dialog.getByRole("button", { name: "Cancelar", exact: true })).toBeVisible();
    await expect(
      dialog.getByRole("button", { name: titles.get(state.title), exact: true }),
    ).toBeVisible();
    await page.keyboard.press("Escape");
  }
  for (const screen of SCREENS.filter((candidate) => candidate.edit)) {
    await openScreen(page, screen);
    await rowOf(page, screen.edit.row).getByRole("button", { name: "Editar" }).click();
    const dialog = dialogOf(page);
    await expect(dialog).toBeVisible();
    const title = await dialog.evaluate((node) =>
      document.getElementById(node.getAttribute("aria-labelledby")).textContent,
    );
    expect(title, screen.name).toBe(screen.edit.title);
    await expect(dialog.getByRole("button", { name: "Guardar", exact: true })).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Cancelar", exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
  }
  await installScreen(page, "Admin");
  await page.goto("/#/users");
  await rowOf(page, "Luis Mora").getByRole("button", { name: "Restablecer contraseña" }).click();
  const reset = dialogOf(page);
  await expect(reset.getByRole("heading", { name: "Restablecer contraseña" })).toBeVisible();
  await expect(reset.getByRole("button", { name: "Restablecer", exact: true })).toBeVisible();
  await expect(reset.getByRole("button", { name: "Cancelar", exact: true })).toBeVisible();
});

test("SPEC-UI-159 keeps the fields and the validation of the form inside the dialog (TC-UI-159b)", async ({
  page,
}) => {
  const api = await installScreen(page, "Admin");
  await page.goto("/#/users");
  await rowOf(page, "Luis Mora").getByRole("button", { name: "Restablecer contraseña" }).click();
  const dialog = dialogOf(page);
  await dialog.getByLabel("Nueva contraseña", { exact: true }).fill("clave-nueva-1");
  await dialog.getByLabel("Confirmar nueva contraseña").fill("clave-nueva-2");
  await dialog.getByRole("button", { name: "Restablecer", exact: true }).click();
  await expect(dialog).toContainText("La nueva contraseña y su confirmación no coinciden.");
  await expect(dialog).toBeVisible();
  expect(writesOf(api)).toHaveLength(0);
});

test("SPEC-UI-160 moves the focus to the first field when a dialog opens (TC-UI-160a)", async ({
  page,
}) => {
  for (const screen of SCREENS) {
    await openScreen(page, screen);
    await mainButton(page, screen.create.button).click();
    const first = dialogOf(page).locator("input, select, textarea").first();
    await expect(first, screen.name).toBeFocused();
    await page.keyboard.press("Escape");
    if (screen.edit) {
      await rowOf(page, screen.edit.row).getByRole("button", { name: "Editar" }).click();
      await expect(dialogOf(page).locator("input, select, textarea").first(), screen.name).toBeFocused();
      await page.keyboard.press("Escape");
    }
  }
});

test("SPEC-UI-161 returns the focus to the control that opened the dialog (TC-UI-161a)", async ({
  page,
}) => {
  await openScreen(page, SCREENS[0]);
  const create = mainButton(page, "Nuevo usuario");
  await create.click();
  await page.keyboard.press("Escape");
  await expect(create).toBeFocused();
  await create.click();
  await dialogOf(page).getByRole("button", { name: "Cancelar" }).click();
  await expect(create).toBeFocused();
  const edit = rowOf(page, "Luis Mora").getByRole("button", { name: "Editar" });
  await edit.click();
  await page.keyboard.press("Escape");
  await expect(edit).toBeFocused();
  const reset = rowOf(page, "Luis Mora").getByRole("button", { name: "Restablecer contraseña" });
  await reset.click();
  await dialogOf(page).getByRole("button", { name: "Cancelar" }).click();
  await expect(reset).toBeFocused();
});

test("SPEC-UI-161 moves the focus to the header button when the opener no longer exists (TC-UI-161b)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[0]);
  api.on("PATCH", "/users/5", { status: 200, body: LUIS });
  await rowOf(page, "Luis Mora").getByRole("button", { name: "Editar" }).click();
  await dialogOf(page).getByRole("button", { name: "Guardar" }).click();
  await expect(dialogOf(page)).toHaveCount(0);
  await expect(mainButton(page, "Nuevo usuario")).toBeFocused();
});

test("SPEC-UI-162 closes with Escape or Cancelar without a request and discards what was typed (TC-UI-162a)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[0]);
  const before = api.requests.length;
  for (const close of [
    () => page.keyboard.press("Escape"),
    () => dialogOf(page).getByRole("button", { name: "Cancelar" }).click(),
  ]) {
    await mainButton(page, "Nuevo usuario").click();
    await fillUser(page);
    await close();
    await expect(dialogOf(page)).toHaveCount(0);
    await mainButton(page, "Nuevo usuario").click();
    await expect(dialogOf(page).getByLabel("Nombre")).toHaveValue("");
    await expect(dialogOf(page).getByLabel("Contraseña", { exact: true })).toHaveValue("");
    await page.keyboard.press("Escape");
  }
  expect(api.requests.length).toBe(before);
});

test("SPEC-UI-163 shows field marks and the API message inside the open dialog and keeps what was typed (TC-UI-163a)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[0]);
  api.on("POST", "/users", [
    {
      status: 400,
      body: { error: "validation_error", fields: { name: "required", email: "invalid" } },
    },
    { status: 409, body: { error: "duplicate_email" } },
  ]);
  await mainButton(page, "Nuevo usuario").click();
  await fillUser(page, "");
  const dialog = dialogOf(page);
  await dialog.getByRole("button", { name: "Crear" }).click();
  await expect(dialog.getByLabel("Nombre")).toHaveAttribute("aria-invalid", "true");
  await expect(dialog.locator(".field", { has: page.getByLabel("Nombre") })).toContainText(
    "Este campo es obligatorio",
  );
  await expect(dialog.locator(".field", { has: page.getByLabel("Email") })).toContainText(
    "El valor ingresado no es válido",
  );
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Email")).toHaveValue("rosa@example.com");
  await expect(dialog.getByLabel("Contraseña", { exact: true })).toHaveValue("");
  await dialog.getByLabel("Nombre").fill("Rosa Paz");
  await dialog.getByLabel("Contraseña", { exact: true }).fill("clave-larga-1");
  await dialog.getByRole("button", { name: "Crear" }).click();
  await expect(dialog.getByRole("alert")).toHaveText("Ya existe un usuario con ese email.");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Nombre")).toHaveValue("Rosa Paz");
  await expect(page.locator("#alert")).toHaveText("");
});

test("SPEC-UI-163 shows the API error inside the dialog of every other form (TC-UI-163b)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[1]);
  api.on("POST", "/categories", { status: 409, body: { error: "duplicate_category" } });
  await mainButton(page, "Nueva categoría").click();
  await dialogOf(page).getByLabel("Nombre").fill("Computación");
  await dialogOf(page).getByRole("button", { name: "Crear" }).click();
  await expect(dialogOf(page).getByRole("alert")).toHaveText(
    "Ya existe una categoría con ese nombre.",
  );
  await expect(dialogOf(page).getByLabel("Nombre")).toHaveValue("Computación");

  const productsApi = await openScreen(page, SCREENS[3]);
  productsApi.on("POST", "/products", { status: 409, body: { error: "duplicate_product" } });
  await mainButton(page, "Nuevo producto").click();
  await dialogOf(page).getByLabel("Nombre").fill("Lenovo T14");
  await dialogOf(page).getByLabel("Tipo").selectOption({ label: "Notebook" });
  await dialogOf(page).getByRole("button", { name: "Crear" }).click();
  await expect(dialogOf(page).getByRole("alert")).toHaveText(
    "Ya existe un producto con ese nombre en el tipo de producto.",
  );
  await expect(dialogOf(page)).toBeVisible();
});

test("SPEC-UI-164 closes the dialog on success and shows the confirmation of the spec (TC-UI-164a)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[0]);
  api.on("POST", "/users", { status: 201, body: account(9, "Rosa Paz", "Client") });
  const reloaded = callsTo(api, "/users").length;
  await mainButton(page, "Nuevo usuario").click();
  await fillUser(page);
  await dialogOf(page).getByRole("button", { name: "Crear" }).click();
  await expect(dialogOf(page)).toHaveCount(0);
  await expect(page.locator("#status")).toHaveText("Usuario creado.");
  await expect.poll(() => callsTo(api, "/users").length).toBe(reloaded + 1);
});

test("SPEC-UI-164 closes the dialog on success without a message when the spec defines none (TC-UI-164b)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[1]);
  api.on("POST", "/categories", { status: 201, body: { id: 9, name: "Impresión" } });
  await mainButton(page, "Nueva categoría").click();
  await dialogOf(page).getByLabel("Nombre").fill("Impresión");
  await dialogOf(page).getByRole("button", { name: "Crear" }).click();
  await expect(dialogOf(page)).toHaveCount(0);
  await expect(page.locator("#status")).toHaveText("");
  await expect.poll(() => callsTo(api, "/categories").length).toBe(2);
});

test("SPEC-UI-165 disables every control of the dialog and ignores Escape while the submit is pending (TC-UI-165a)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[0]);
  const gate = api.defer("POST", "/users");
  await mainButton(page, "Nuevo usuario").click();
  await fillUser(page);
  await dialogOf(page).getByRole("button", { name: "Crear" }).click();
  await gate.requested;
  const dialog = dialogOf(page);
  const controls = dialog.locator("button, input, select, textarea");
  const count = await controls.count();
  expect(count).toBeGreaterThanOrEqual(6);
  for (let index = 0; index < count; index += 1) {
    await expect(controls.nth(index)).toBeDisabled();
  }
  await page.keyboard.press("Escape");
  await settle(page);
  await expect(dialog).toBeVisible();
  gate.release(201, account(9, "Rosa Paz", "Client"));
  await expect(dialog).toHaveCount(0);
});

test("SPEC-UI-166 closes the dialog at once when the session closes by the logout button (TC-UI-166a)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[0]);
  const logout = api.defer("POST", "/logout");
  await mainButton(page, "Nuevo usuario").click();
  await fillUser(page);
  const before = api.requests.length;
  await page.getByRole("button", { name: "Cerrar sesión", exact: true }).dispatchEvent("click");
  await logout.requested;
  await expect(dialogOf(page)).toHaveCount(0);
  expect(api.requests.slice(before).map((r) => `${r.method} ${new URL(r.url).pathname}`)).toEqual([
    "POST /logout",
  ]);
  logout.release(204);
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await expect(dialogOf(page)).toHaveCount(0);
});

test("SPEC-UI-166 closes the dialog when a 401 closes the session and shows the notice (TC-UI-166b)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[0]);
  const gate = api.defer("POST", "/users");
  api.on("POST", "/users/5/deactivate", { status: 401, body: { error: "authentication_required" } });
  await mainButton(page, "Nuevo usuario").click();
  await fillUser(page);
  await dialogOf(page).getByRole("button", { name: "Crear" }).click();
  await gate.requested;
  await rowOf(page, "Luis Mora")
    .getByRole("button", { name: "Dar de baja" })
    .dispatchEvent("click");
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await expect(page.getByText("Tu sesión venció. Inicia sesión nuevamente.")).toBeVisible();
  await expect(dialogOf(page)).toHaveCount(0);
  gate.release(201, account(9, "Rosa Paz", "Client"));
  await settle(page);
  await expect(page.locator("#status")).not.toHaveText("Usuario creado.");
  await expect(page.getByText("Tu sesión venció. Inicia sesión nuevamente.")).toBeVisible();
});

test("SPEC-UI-167 ignores the response of a dialog that a hash change closed (TC-UI-167a)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[0]);
  const gate = api.defer("POST", "/users");
  await mainButton(page, "Nuevo usuario").click();
  await fillUser(page);
  await dialogOf(page).getByRole("button", { name: "Crear" }).click();
  await gate.requested;
  const usersCalls = callsTo(api, "/users").length;
  await page.evaluate(() => {
    window.location.hash = "#/categories";
  });
  await expect(heading(page, "Categorías")).toBeVisible();
  await expect(dialogOf(page)).toHaveCount(0);
  gate.release(201, account(9, "Rosa Paz", "Client"));
  await expect.poll(() => api.requests.find((r) => r.method === "POST").status).toBe(201);
  await settle(page);
  await expect(page.locator("#status")).toHaveText("");
  expect(callsTo(api, "/users")).toHaveLength(usersCalls);
  expect(await hashOf(page)).toBe("#/categories");
});

test("SPEC-UI-167 ignores a late error and a lost connection of a closed dialog (TC-UI-167b)", async ({
  page,
}) => {
  for (const finish of [
    (gate) => gate.release(400, { error: "validation_error", fields: { name: "required" } }),
    (gate) => gate.release(500, { error: "internal_error" }),
    (gate) => gate.abort(),
  ]) {
    const api = await openScreen(page, SCREENS[1]);
    const gate = api.defer("POST", "/categories");
    await mainButton(page, "Nueva categoría").click();
    await dialogOf(page).getByLabel("Nombre").fill("Impresión");
    await dialogOf(page).getByRole("button", { name: "Crear" }).click();
    await gate.requested;
    await page.evaluate(() => {
      window.location.hash = "#/users";
    });
    await expect(heading(page, "Usuarios")).toBeVisible();
    finish(gate);
    await expect.poll(() => api.requests.find((r) => r.method === "POST").status !== undefined || api.requests.find((r) => r.method === "POST").aborted).toBe(true);
    await settle(page);
    await expect(page.locator("#alert")).toHaveText("");
    await expect(page.getByText("Este campo es obligatorio")).toHaveCount(0);
    await expect(dialogOf(page)).toHaveCount(0);
  }
});

test("SPEC-UI-167 treats each opening of the dialog as a new instance (TC-UI-167c)", async ({
  page,
}) => {
  const api = await openScreen(page, SCREENS[4]);
  const gate = api.defer("POST", "/tickets");
  await mainButton(page, "Nuevo ticket").click();
  await dialogOf(page).getByLabel("Primer mensaje").fill("No enciende");
  await dialogOf(page).getByRole("button", { name: "Crear" }).click();
  await gate.requested;
  await page.evaluate(() => {
    window.location.hash = "#/tickets/new";
  });
  await settle(page);
  await expect(dialogOf(page)).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/tickets";
  });
  await expect(dialogOf(page)).toHaveCount(0);
  await mainButton(page, "Nuevo ticket").click();
  await expect(dialogOf(page).getByLabel("Primer mensaje")).toHaveValue("");
  gate.release(400, { error: "validation_error", fields: { first_message: "required" } });
  await expect.poll(() => api.requests.find((r) => r.method === "POST").status).toBe(400);
  await settle(page);
  await expect(dialogOf(page).getByText("Este campo es obligatorio")).toHaveCount(0);
  await expect(dialogOf(page)).toBeVisible();
});

test("SPEC-UI-168 closes the dialog when the hash changes with the Back button (TC-UI-168a)", async ({
  page,
}) => {
  const api = await installScreen(page, "Admin");
  await page.goto("/#/users");
  await expect(heading(page, "Usuarios")).toBeVisible();
  await page.getByRole("navigation").getByRole("link", { name: "Productos", exact: true }).click();
  await expect(heading(page, "Productos")).toBeVisible();
  await mainButton(page, "Nuevo producto").click();
  await expect(dialogOf(page)).toBeVisible();
  const before = writesOf(api).length;
  await page.goBack();
  await expect(heading(page, "Usuarios")).toBeVisible();
  await expect(dialogOf(page)).toHaveCount(0);
  expect(writesOf(api)).toHaveLength(before);
});

test("SPEC-UI-169 sets the hash to #/tickets without a new history entry when the route dialog is cancelled (TC-UI-169a)", async ({
  page,
}) => {
  await installScreen(page, "Representative");
  await page.goto("/#/tickets/new");
  await expect(dialogOf(page)).toBeVisible();
  const length = await historyLength(page);
  await page.keyboard.press("Escape");
  await expect(dialogOf(page)).toHaveCount(0);
  expect(await hashOf(page)).toBe("#/tickets");
  expect(await historyLength(page)).toBe(length);
  await page.getByRole("navigation").getByRole("link", { name: "Nuevo ticket", exact: true }).click();
  await expect(dialogOf(page)).toBeVisible();
  const again = await historyLength(page);
  await dialogOf(page).getByRole("button", { name: "Cancelar" }).click();
  await expect(dialogOf(page)).toHaveCount(0);
  expect(await hashOf(page)).toBe("#/tickets");
  expect(await historyLength(page)).toBe(again);
});

test("SPEC-UI-169 leaves the hash alone when a dialog opened by the button is closed (TC-UI-169b)", async ({
  page,
}) => {
  await installScreen(page, "Representative");
  await page.goto("/#/tickets");
  await mainButton(page, "Nuevo ticket").click();
  await expect(dialogOf(page)).toBeVisible();
  expect(await hashOf(page)).toBe("#/tickets");
  await page.keyboard.press("Escape");
  expect(await hashOf(page)).toBe("#/tickets");
});

test("SPEC-UI-170 moves between #/tickets and #/tickets/new as one screen instance (TC-UI-170a)", async ({
  page,
}) => {
  const api = await installScreen(page, "Representative");
  await page.goto("/#/tickets");
  await expect(heading(page, "Tickets")).toBeVisible();
  await page.getByLabel("Estado", { exact: true }).selectOption({ label: "Nuevo" });
  await page.getByLabel("Buscar", { exact: true }).fill("caja");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect.poll(() => callsTo(api, "/tickets").length).toBeGreaterThan(2);
  const loaded = callsTo(api, "/tickets").length;
  await page.evaluate(() => {
    window.location.hash = "#/tickets/new";
  });
  await expect(dialogOf(page)).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/tickets";
  });
  await expect(dialogOf(page)).toHaveCount(0);
  await settle(page);
  expect(callsTo(api, "/tickets")).toHaveLength(loaded);
  await expect(page.getByLabel("Estado", { exact: true })).toHaveValue("New");
  await expect(page.getByLabel("Buscar", { exact: true })).toHaveValue("caja");
});

test("SPEC-UI-170 does not move the focus to the heading between the two routes (TC-UI-170b)", async ({
  page,
}) => {
  await installScreen(page, "Representative");
  await page.goto("/#/tickets");
  await expect(heading(page, "Tickets")).toBeVisible();
  await page.getByRole("navigation").getByRole("link", { name: "Nuevo ticket", exact: true }).click();
  await expect(dialogOf(page)).toBeVisible();
  await expect(dialogOf(page).locator("input, select, textarea").first()).toBeFocused();
  await page.goBack();
  await expect(dialogOf(page)).toHaveCount(0);
  expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe("H1");
  await expect(mainButton(page, "Nuevo ticket")).toBeFocused();
});

test("SPEC-UI-171 fits the dialog in 360 px and scrolls inside it when it is taller than the window (TC-UI-171a)", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 320 });
  for (const screen of [SCREENS[0], SCREENS[4]]) {
    await openScreen(page, screen);
    await mainButton(page, screen.create.button).click();
    const metrics = await dialogOf(page).evaluate((node) => {
      const box = node.getBoundingClientRect();
      return {
        left: box.left,
        right: box.right,
        top: box.top,
        bottom: box.bottom,
        scrollHeight: node.scrollHeight,
        clientHeight: node.clientHeight,
        overflowY: getComputedStyle(node).overflowY,
        pageScroll: document.documentElement.scrollWidth,
        pageClient: document.documentElement.clientWidth,
      };
    });
    expect(metrics.left, screen.name).toBeGreaterThanOrEqual(0);
    expect(metrics.right, screen.name).toBeLessThanOrEqual(360);
    expect(metrics.top, screen.name).toBeGreaterThanOrEqual(0);
    expect(metrics.bottom, screen.name).toBeLessThanOrEqual(320);
    expect(metrics.scrollHeight, screen.name).toBeGreaterThan(metrics.clientHeight);
    expect(["auto", "scroll"]).toContain(metrics.overflowY);
    expect(metrics.pageScroll, screen.name).toBeLessThanOrEqual(metrics.pageClient);
    await page.keyboard.press("Escape");
  }
});

test("SPEC-UI-30 shows the ticket list with the creation dialog open on #/tickets/new (TC-UI-30b)", async ({
  page,
}) => {
  const api = await installScreen(page, "Representative");
  await page.goto("/#/tickets/new");
  await expect(heading(page, "Tickets")).toBeVisible();
  const dialog = dialogOf(page);
  await expect(dialog.getByLabel("Cliente", { exact: true })).toBeVisible();
  await expect(dialog.getByLabel("Primer mensaje", { exact: true })).toBeVisible();
  await expect(dialog.getByLabel("Productos", { exact: true })).toBeVisible();
  await expect(dialog.getByLabel("Cliente", { exact: true }).locator("option")).toHaveCount(2);
  expect(callsTo(api, "/tickets").length).toBeGreaterThan(0);
  await expect(dialog.locator("input, select, textarea").first()).toBeFocused();
});

test("SPEC-UI-33 closes the dialog and shows the detail of the created ticket (TC-UI-33b)", async ({
  page,
}) => {
  const api = await installScreen(page, "Representative");
  api.on("POST", "/tickets", { status: 201, body: CREATED });
  await page.goto("/#/tickets/new");
  const dialog = dialogOf(page);
  await dialog.getByLabel("Cliente", { exact: true }).selectOption({ label: "Ana Gómez" });
  await dialog.getByLabel("Primer mensaje", { exact: true }).fill("No enciende");
  await dialog.getByLabel("Productos", { exact: true }).selectOption({ label: "Notebook X" });
  await dialog.getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => hashOf(page)).toBe("#/tickets/15");
  await expect(heading(page, "Ticket #15")).toBeVisible();
  await expect(dialogOf(page)).toHaveCount(0);
  expect(api.requests.find((r) => r.method === "POST").body).toEqual({
    client_id: 11,
    first_message: "No enciende",
    product_ids: [21],
  });
  expect(ticket(15, "New", "2026-01-01T12:00:00+00:00").id).toBe(15);
});
