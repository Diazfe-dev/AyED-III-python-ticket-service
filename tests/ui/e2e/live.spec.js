import { expect, test } from "@playwright/test";
import { SEEDED_ADMIN, SEEDED_CLIENT, SEEDED_REP } from "./support/fixtures.js";

const heading = (page, name) =>
  page.getByRole("heading", { name, exact: true });
const currentHash = (page) => page.evaluate(() => window.location.hash);

async function login(page, credentials) {
  await page.goto("/");
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await page.getByLabel("Email").fill(credentials.email);
  await page.getByLabel("Contraseña").fill(credentials.password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
}

test("SPEC-UI-09 the seeded admin logs in and sees the real accounts (TC-UI-09c)", async ({
  page,
}) => {
  await login(page, SEEDED_ADMIN);
  await expect(heading(page, "Usuarios")).toBeVisible();
  await expect.poll(() => currentHash(page)).toBe("#/users");
  for (const name of [
    "Marta Ruiz",
    "Raúl Pérez",
    "Lucía Sosa",
    "Ana Gómez",
    "Diego Paz",
  ]) {
    await expect(page.getByRole("row").filter({ hasText: name })).toHaveCount(
      1,
    );
  }
});

test("SPEC-UI-22 the seeded representative sees the real tickets (TC-UI-22b)", async ({
  page,
}) => {
  await login(page, SEEDED_REP);
  await expect(heading(page, "Tickets")).toBeVisible();
  await expect(
    page.getByRole("row").filter({ hasText: "Ana Gómez" }),
  ).toHaveCount(20);
  await expect(page.locator(".page-total")).toHaveText("25 resultados");
});

test("SPEC-UI-27 the real detail shows the milestones and the state change (TC-UI-27b)", async ({
  page,
}) => {
  await login(page, SEEDED_CLIENT);
  await expect(heading(page, "Tickets")).toBeVisible();
  await page.goto("/#/tickets/26");
  await expect(heading(page, "Ticket #26")).toBeVisible();
  await expect(page.locator("#app")).toContainText("Lucía Sosa");
  await expect(page.locator("ol.milestones > li")).toHaveCount(3);
  await expect(page.locator("ol.milestones")).toContainText(
    "No enciende el equipo",
  );
  await expect(page.locator("ol.milestones")).toContainText(
    "Revisamos el cargador",
  );
  await expect(page.locator("ol.milestones")).toContainText(
    "Sigue sin encender",
  );
  await expect(page.locator("ol.state-changes")).toContainText("En curso");
  await expect(page.locator("ol.state-changes")).toContainText("Nuevo");
  await expect(page.locator(".ticket-state")).toHaveText("En curso");
});

test("SPEC-UI-129 the real logout ends the session without a notice (TC-UI-129f)", async ({
  page,
}) => {
  await login(page, SEEDED_REP);
  await expect(heading(page, "Tickets")).toBeVisible();
  await page
    .getByRole("button", { name: "Cerrar sesión", exact: true })
    .click();
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
  await expect(page.locator("#status")).not.toContainText("Tu sesión venció");
  expect(await currentHash(page)).toBe("#/login");
  const me = await page.request.get("/me");
  expect(me.status()).toBe(401);
  await page.goto("/");
  await expect(heading(page, "Iniciar sesión")).toBeVisible();
});
