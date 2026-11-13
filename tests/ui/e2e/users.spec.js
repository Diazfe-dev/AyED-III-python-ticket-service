import { expect, test } from "@playwright/test";
import { installFakeApi } from "./support/fake-api.js";
import { page as pageOf, USERS } from "./support/fixtures.js";

const USERS_PATH = "/users";
const MISMATCH = "La nueva contraseña y su confirmación no coinciden.";

const account = (id, name, role, isActive = true, channel = "mail") => ({
  id,
  name,
  email: `cuenta${id}@example.com`,
  role,
  preferred_channel: channel,
  is_active: isActive,
});

const LUIS = account(5, "Luis Mora", "Client");
const OLGA = account(6, "Olga Díaz", "Admin");
const INACTIVE = account(7, "Ines Vera", "Client", false);

const usersCalls = (api) =>
  api.requests.filter((r) => r.method === "GET" && new URL(r.url).pathname === USERS_PATH);
const lastCall = (api) => new URL(usersCalls(api).at(-1).url).searchParams;
const writes = (api, method, path) =>
  api.requests.filter((r) => r.method === method && new URL(r.url).pathname === path);
const rowFor = (page, name) => page.getByRole("row").filter({ hasText: name });
const byPage = (items, total) => (record) => ({
  status: 200,
  body: pageOf(items, Number(new URL(record.url).searchParams.get("page")), total),
});

async function openUsers(page, listing = { status: 200, body: pageOf([LUIS, OLGA]) }) {
  const api = await installFakeApi(page);
  api.on("GET", "/me", { status: 200, body: USERS.Admin });
  api.on("GET", USERS_PATH, listing);
  await page.goto("/#/users");
  return api;
}

const createForm = (page) => page.getByRole("dialog", { name: "Nuevo usuario" });
const editForm = (page) => page.getByRole("dialog", { name: "Editar usuario" });
const resetForm = (page) => page.getByRole("dialog", { name: "Restablecer contraseña" });
const openCreateDialog = (page) => page.getByRole("main").getByRole("button", { name: "Nuevo usuario" }).click();

async function fillCreate(page, values) {
  await openCreateDialog(page);
  const form = createForm(page);
  await form.getByLabel("Nombre").fill(values.name ?? "");
  await form.getByLabel("Email").fill(values.email ?? "");
  if (values.role) {
    await form.getByLabel("Rol").selectOption({ label: values.role });
  }
  await form.getByLabel("Contraseña", { exact: true }).fill(values.password ?? "");
  if (values.channel) {
    await form.getByLabel("Canal").selectOption({ label: values.channel });
  }
}

test("SPEC-UI-44 shows name, email, role and state labels of each account (TC-UI-44a)", async ({
  page,
}) => {
  await openUsers(page, { status: 200, body: pageOf([OLGA, INACTIVE]) });
  const admin = rowFor(page, "Olga Díaz");
  await expect(admin).toContainText("cuenta6@example.com");
  await expect(admin).toContainText("Administrador");
  await expect(admin).toContainText("Activo");
  const client = rowFor(page, "Ines Vera");
  await expect(client).toContainText("Cliente");
  await expect(client).toContainText("Inactivo");
});

test("SPEC-UI-26 requests GET /users with page and page_size 20 (TC-UI-26c)", async ({ page }) => {
  const api = await openUsers(page);
  await expect(rowFor(page, "Luis Mora")).toBeVisible();
  const params = lastCall(api);
  expect(params.get("page")).toBe("1");
  expect(params.get("page_size")).toBe("20");
});

test("SPEC-UI-82 requests the listing with the encoded search text (TC-UI-82a)", async ({
  page,
}) => {
  const api = await openUsers(page);
  await expect(rowFor(page, "Luis Mora")).toBeVisible();
  api.on("GET", USERS_PATH, { status: 200, body: pageOf([OLGA]) });
  await page.getByLabel("Buscar", { exact: true }).fill("gómez");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(rowFor(page, "Olga Díaz")).toBeVisible();
  expect(usersCalls(api).at(-1).url).toContain("q=g%C3%B3mez");
  await expect(rowFor(page, "Luis Mora")).toHaveCount(0);
});

test("SPEC-UI-83 requests the listing with the active filter (TC-UI-83a)", async ({ page }) => {
  const api = await openUsers(page);
  await expect(rowFor(page, "Luis Mora")).toBeVisible();
  api.on("GET", USERS_PATH, { status: 200, body: pageOf([INACTIVE]) });
  await page.getByLabel("Estado", { exact: true }).selectOption({ label: "Inactivo" });
  await expect(rowFor(page, "Ines Vera")).toBeVisible();
  expect(lastCall(api).get("is_active")).toBe("false");
  api.on("GET", USERS_PATH, { status: 200, body: pageOf([OLGA]) });
  await page.getByLabel("Estado", { exact: true }).selectOption({ label: "Activo" });
  await expect(rowFor(page, "Olga Díaz")).toBeVisible();
  expect(lastCall(api).get("is_active")).toBe("true");
});

test("SPEC-UI-84 offers the three roles in the create form (TC-UI-84a)", async ({ page }) => {
  await openUsers(page);
  await openCreateDialog(page);
  const options = createForm(page).getByLabel("Rol").locator("option");
  await expect(options.filter({ hasText: "Administrador" })).toHaveAttribute("value", "Admin");
  await expect(options.filter({ hasText: "Representante" })).toHaveAttribute(
    "value",
    "Representative",
  );
  await expect(options.filter({ hasText: "Cliente" })).toHaveAttribute("value", "Client");
});

test("SPEC-UI-45 creates the account with name, email, role, password and channel (TC-UI-45a)", async ({
  page,
}) => {
  const api = await openUsers(page);
  api.on("POST", USERS_PATH, { status: 201, body: account(9, "Rosa Paz", "Representative") });
  await fillCreate(page, {
    name: "Rosa Paz",
    email: "rosa@example.com",
    role: "Representante",
    password: "clave-larga-1",
    channel: "WhatsApp",
  });
  await createForm(page).getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => writes(api, "POST", USERS_PATH).length).toBe(1);
  expect(writes(api, "POST", USERS_PATH)[0].body).toEqual({
    name: "Rosa Paz",
    email: "rosa@example.com",
    role: "Representative",
    password: "clave-larga-1",
    preferred_channel: "whatsapp",
  });
});

test("SPEC-UI-45 omits preferred_channel when no channel is chosen (TC-UI-45b)", async ({
  page,
}) => {
  const api = await openUsers(page);
  api.on("POST", USERS_PATH, { status: 201, body: account(9, "Rosa Paz", "Client") });
  await fillCreate(page, {
    name: "Rosa Paz",
    email: "rosa@example.com",
    role: "Cliente",
    password: "clave-larga-1",
  });
  await createForm(page).getByRole("button", { name: "Crear" }).click();
  await expect.poll(() => writes(api, "POST", USERS_PATH).length).toBe(1);
  expect(writes(api, "POST", USERS_PATH)[0].body).not.toHaveProperty("preferred_channel");
});

test("SPEC-UI-85 confirms the creation with Usuario creado (TC-UI-85a)", async ({ page }) => {
  const api = await openUsers(page);
  api.on("POST", USERS_PATH, { status: 201, body: account(9, "Rosa Paz", "Client") });
  await fillCreate(page, {
    name: "Rosa Paz",
    email: "rosa@example.com",
    role: "Cliente",
    password: "clave-larga-1",
  });
  await createForm(page).getByRole("button", { name: "Crear" }).click();
  await expect(page.locator("#status")).toHaveText("Usuario creado.");
  await expect(createForm(page)).toHaveCount(0);
  await openCreateDialog(page);
  await expect(createForm(page).getByLabel("Nombre")).toHaveValue("");
});

test("SPEC-UI-57 marks each invalid field next to it on the create form (TC-UI-57b)", async ({
  page,
}) => {
  const api = await openUsers(page);
  api.on("POST", USERS_PATH, {
    status: 400,
    body: { error: "validation_error", fields: { name: "required", email: "invalid" } },
  });
  await fillCreate(page, { name: "", email: "no-es-email", role: "Cliente", password: "x" });
  await createForm(page).getByRole("button", { name: "Crear" }).click();
  const form = createForm(page);
  await expect(form.getByLabel("Nombre")).toHaveAttribute("aria-invalid", "true");
  await expect(form.locator(".field", { has: page.getByLabel("Nombre") })).toContainText(
    "Este campo es obligatorio",
  );
  await expect(form.locator(".field", { has: page.getByLabel("Email") })).toContainText(
    "El valor ingresado no es válido",
  );
  await expect(form.getByLabel("Email")).toHaveValue("no-es-email");
});

test("SPEC-UI-64 empties the password fields after success and after error (TC-UI-64c)", async ({
  page,
}) => {
  const api = await openUsers(page);
  api.on("POST", USERS_PATH, [
    { status: 409, body: { error: "duplicate_email" } },
    { status: 201, body: account(9, "Rosa Paz", "Client") },
  ]);
  await fillCreate(page, {
    name: "Rosa Paz",
    email: "rosa@example.com",
    role: "Cliente",
    password: "clave-larga-1",
  });
  const password = createForm(page).getByLabel("Contraseña", { exact: true });
  await createForm(page).getByRole("button", { name: "Crear" }).click();
  await expect(createForm(page).getByRole("alert").filter({ hasText: "Ya existe un usuario" })).toBeVisible();
  await expect(password).toHaveValue("");
  await password.fill("clave-larga-1");
  await createForm(page).getByRole("button", { name: "Crear" }).click();
  await expect(page.locator("#status")).toHaveText("Usuario creado.");
  await expect(createForm(page)).toHaveCount(0);

  api.on("POST", "/users/5/password", [
    { status: 400, body: { error: "validation_error", fields: { new_password: "too_short" } } },
    { status: 204 },
  ]);
  await rowFor(page, "Luis Mora").getByRole("button", { name: "Restablecer contraseña" }).click();
  const fresh = resetForm(page).getByLabel("Nueva contraseña", { exact: true });
  const confirmation = resetForm(page).getByLabel("Confirmar nueva contraseña");
  await fresh.fill("corta");
  await confirmation.fill("corta");
  await resetForm(page).getByRole("button", { name: "Restablecer" }).click();
  await expect(resetForm(page)).toContainText("El valor ingresado no es válido");
  await expect(fresh).toHaveValue("");
  await expect(confirmation).toHaveValue("");
  await fresh.fill("clave-nueva-1");
  await confirmation.fill("clave-nueva-1");
  await resetForm(page).getByRole("button", { name: "Restablecer" }).click();
  await expect.poll(() => writes(api, "POST", "/users/5/password").length).toBe(2);
  await expect(resetForm(page)).toHaveCount(0);
});

test("SPEC-UI-46 edits name, email and channel with PATCH (TC-UI-46a)", async ({ page }) => {
  const api = await openUsers(page);
  api.on("PATCH", "/users/5", { status: 200, body: { ...LUIS, name: "Luis Mora Paz" } });
  await rowFor(page, "Luis Mora").getByRole("button", { name: "Editar" }).click();
  const form = editForm(page);
  await expect(form.getByLabel("Nombre")).toHaveValue("Luis Mora");
  await form.getByLabel("Nombre").fill("Luis Mora Paz");
  await form.getByRole("button", { name: "Guardar" }).click();
  await expect.poll(() => writes(api, "PATCH", "/users/5").length).toBe(1);
  expect(writes(api, "PATCH", "/users/5")[0].body).toEqual({
    name: "Luis Mora Paz",
    email: "cuenta5@example.com",
    preferred_channel: "mail",
  });
  await expect(editForm(page)).toHaveCount(0);
});

test("SPEC-UI-47 deactivates an active account (TC-UI-47a)", async ({ page }) => {
  const api = await openUsers(page);
  api.on("POST", "/users/5/deactivate", { status: 200, body: { ...LUIS, is_active: false } });
  await rowFor(page, "Luis Mora").getByRole("button", { name: "Dar de baja" }).click();
  await expect.poll(() => writes(api, "POST", "/users/5/deactivate").length).toBe(1);
  await expect(rowFor(page, "Luis Mora").getByRole("button", { name: "Reactivar" })).toHaveCount(0);
});

test("SPEC-UI-110 reactivates an inactive account (TC-UI-110a)", async ({ page }) => {
  const api = await openUsers(page, { status: 200, body: pageOf([account(5, "Luis Mora", "Client", false)]) });
  api.on("POST", "/users/5/activate", { status: 200, body: LUIS });
  const row = rowFor(page, "Luis Mora");
  await expect(row.getByRole("button", { name: "Dar de baja" })).toHaveCount(0);
  await row.getByRole("button", { name: "Reactivar" }).click();
  await expect.poll(() => writes(api, "POST", "/users/5/activate").length).toBe(1);
});

test("SPEC-UI-48 resets the password with only the new one (TC-UI-48a)", async ({ page }) => {
  const api = await openUsers(page);
  api.on("POST", "/users/5/password", { status: 204 });
  await rowFor(page, "Luis Mora").getByRole("button", { name: "Restablecer contraseña" }).click();
  await expect(resetForm(page).getByLabel("Contraseña actual")).toHaveCount(0);
  await resetForm(page).getByLabel("Nueva contraseña", { exact: true }).fill("clave-nueva-1");
  await resetForm(page).getByLabel("Confirmar nueva contraseña").fill("clave-nueva-1");
  await resetForm(page).getByRole("button", { name: "Restablecer" }).click();
  await expect.poll(() => writes(api, "POST", "/users/5/password").length).toBe(1);
  expect(writes(api, "POST", "/users/5/password")[0].body).toEqual({ new_password: "clave-nueva-1" });
});

test("SPEC-UI-172 closes the reset dialog and confirms the reset (TC-UI-172a)", async ({ page }) => {
  const api = await openUsers(page);
  api.on("POST", "/users/5/password", { status: 204 });
  await rowFor(page, "Luis Mora").getByRole("button", { name: "Restablecer contraseña" }).click();
  await resetForm(page).getByLabel("Nueva contraseña", { exact: true }).fill("clave-nueva-1");
  await resetForm(page).getByLabel("Confirmar nueva contraseña").fill("clave-nueva-1");
  await resetForm(page).getByRole("button", { name: "Restablecer" }).click();
  await expect(page.getByRole("status")).toHaveText("Contraseña restablecida.");
  await expect(page.locator("dialog[open]")).toHaveCount(0);
});

test("SPEC-UI-100 shows a mismatch in the reset form without a request (TC-UI-100a)", async ({
  page,
}) => {
  const api = await openUsers(page);
  await rowFor(page, "Luis Mora").getByRole("button", { name: "Restablecer contraseña" }).click();
  await resetForm(page).getByLabel("Nueva contraseña", { exact: true }).fill("clave-nueva-1");
  await resetForm(page).getByLabel("Confirmar nueva contraseña").fill("clave-nueva-2");
  await resetForm(page).getByRole("button", { name: "Restablecer" }).click();
  await expect(resetForm(page)).toContainText(MISMATCH);
  expect(writes(api, "POST", "/users/5/password")).toHaveLength(0);
});

test("SPEC-UI-120 reloads the current page with the same q and filter after an action (TC-UI-120a)", async ({
  page,
}) => {
  const api = await openUsers(page, byPage([LUIS], 45));
  api.on("POST", "/users/5/deactivate", { status: 200, body: { ...LUIS, is_active: false } });
  await page.getByLabel("Estado", { exact: true }).selectOption({ label: "Activo" });
  await page.getByLabel("Buscar", { exact: true }).fill("mora");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.getByText("Página 1")).toBeVisible();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 2")).toBeVisible();
  const before = usersCalls(api).length;
  api.on("GET", USERS_PATH, { status: 200, body: pageOf([OLGA], 2, 45) });
  await rowFor(page, "Luis Mora").getByRole("button", { name: "Dar de baja" }).click();
  await expect(rowFor(page, "Olga Díaz")).toBeVisible();
  expect(usersCalls(api)).toHaveLength(before + 1);
  const params = lastCall(api);
  expect(params.get("q")).toBe("mora");
  expect(params.get("is_active")).toBe("true");
  expect(params.get("page")).toBe("2");
  expect(params.get("page_size")).toBe("20");
});

test("SPEC-UI-125 asks for the last valid page when the reloaded page is empty (TC-UI-125b)", async ({
  page,
}) => {
  let deactivated = false;
  const api = await openUsers(page, (record) => {
    const n = Number(new URL(record.url).searchParams.get("page"));
    if (deactivated && n === 3) {
      return { status: 200, body: pageOf([], 3, 40) };
    }
    return { status: 200, body: pageOf(n === 2 ? [OLGA] : [LUIS], n, deactivated ? 40 : 60) };
  });
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 2")).toBeVisible();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByText("Página 3")).toBeVisible();
  api.on("POST", "/users/5/deactivate", () => {
    deactivated = true;
    return { status: 200, body: { ...LUIS, is_active: false } };
  });
  await rowFor(page, "Luis Mora").getByRole("button", { name: "Dar de baja" }).click();
  await expect(page.getByText("Página 2")).toBeVisible();
  await expect(rowFor(page, "Olga Díaz")).toBeVisible();
  expect(lastCall(api).get("page")).toBe("2");
  const pages = usersCalls(api).map((r) => new URL(r.url).searchParams.get("page"));
  expect(pages.slice(-2)).toEqual(["3", "2"]);
});
