export const ENGLISH_WORDS = [
  "Save",
  "Cancel",
  "Delete",
  "Loading",
  "Search",
  "Login",
  "Logout",
  "Close",
  "Reopen",
  "Submit",
  "Name",
  "Password",
  "Next",
  "Previous",
];

export const SEEDED_PASSWORD = "Clave-segura-123";
export const SEEDED_ADMIN = { email: "marta.ruiz@example.com", password: SEEDED_PASSWORD };
export const SEEDED_REP = { email: "raul.perez@example.com", password: SEEDED_PASSWORD };
export const SEEDED_CLIENT = { email: "ana.gomez@example.com", password: SEEDED_PASSWORD };

export const ADMIN = { id: 1, name: "Marta Ruiz", email: "marta.ruiz@example.com", role: "Admin" };
export const REP = {
  id: 2,
  name: "Raúl Pérez",
  email: "raul.perez@example.com",
  role: "Representative",
};
export const CLIENT = { id: 4, name: "Ana Gómez", email: "ana.gomez@example.com", role: "Client" };

export const USERS = { Admin: ADMIN, Representative: REP, Client: CLIENT };

export function ticket(id, state, createdAt) {
  return {
    id,
    state,
    client: { id: CLIENT.id, name: CLIENT.name },
    representative: { id: REP.id, name: REP.name },
    products: [],
    created_at: createdAt,
  };
}

export const TICKET_NEW = ticket(1, "New", "2026-01-01T12:00:00+00:00");
export const TICKET_IN_PROGRESS = ticket(2, "InProgress", "2026-01-02T12:00:00+00:00");
export const TICKET_CLOSED = ticket(3, "Closed", "2026-01-03T12:00:00+00:00");

export function page(items, n = 1, total = items.length) {
  return { items, page: n, page_size: 20, total };
}

export function hexToRgb(color) {
  const hex = color.replace("#", "");
  const full = hex.length === 3 ? [...hex].map((c) => c + c).join("") : hex;
  return [0, 2, 4].map((start) => parseInt(full.slice(start, start + 2), 16));
}

function luminance(color) {
  const [r, g, b] = (Array.isArray(color) ? color : hexToRgb(color)).map((channel) => {
    const value = channel / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(fg, bg) {
  const [lighter, darker] = [luminance(fg), luminance(bg)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

export function historyLength(page) {
  return page.evaluate(() => window.history.length);
}
