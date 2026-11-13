const ALL_ROLES = ["Representative", "Admin", "Client"];
const MAX_TICKET_ID = 9223372036854775807n;
const TICKET_ID_PATTERN = /^[1-9][0-9]*$/;
const TICKET_DETAIL_PREFIX = "#/tickets/";

const HOMES = {
  Admin: "#/users",
  Representative: "#/tickets",
  Client: "#/tickets",
};

const ROUTES = {
  "#/tickets": { screen: "tickets-list", roles: ALL_ROLES },
  "#/tickets/new": { screen: "ticket-new", roles: ["Representative"] },
  "#/users": { screen: "users", roles: ["Admin"] },
  "#/categories": { screen: "categories", roles: ["Admin"] },
  "#/product-types": { screen: "product-types", roles: ["Admin"] },
  "#/products": { screen: "products", roles: ["Admin"] },
  "#/account": { screen: "account", roles: ALL_ROLES },
};

const LOGOUT = { label: "Cerrar sesión", action: "logout" };

const NAV = {
  Representative: [
    { label: "Tickets", route: "#/tickets" },
    { label: "Nuevo ticket", route: "#/tickets/new" },
    { label: "Mi cuenta", route: "#/account" },
    LOGOUT,
  ],
  Admin: [
    { label: "Usuarios", route: "#/users" },
    { label: "Categorías", route: "#/categories" },
    { label: "Tipos de producto", route: "#/product-types" },
    { label: "Productos", route: "#/products" },
    { label: "Tickets", route: "#/tickets" },
    { label: "Mi cuenta", route: "#/account" },
    LOGOUT,
  ],
  Client: [
    { label: "Mis tickets", route: "#/tickets" },
    { label: "Mi cuenta", route: "#/account" },
    LOGOUT,
  ],
};

export function homeOf(role) {
  return HOMES[role];
}

export function routeOf(screen) {
  const entry = Object.entries(ROUTES).find(([, route]) => route.screen === screen);
  return entry ? entry[0] : null;
}

export function navItems(role) {
  return (NAV[role] ?? []).map((item) => ({ ...item }));
}

export function isValidTicketId(text) {
  return TICKET_ID_PATTERN.test(text) && BigInt(text) <= MAX_TICKET_ID;
}

function classifyWithSession(hash, role) {
  const home = homeOf(role);
  if (hash === "" || hash === "#/login") {
    return { kind: "home", home };
  }
  const route = ROUTES[hash];
  if (route) {
    return route.roles.includes(role)
      ? { kind: "screen", screen: route.screen }
      : { kind: "forbidden", home };
  }
  if (hash.startsWith(TICKET_DETAIL_PREFIX)) {
    const id = hash.slice(TICKET_DETAIL_PREFIX.length);
    if (isValidTicketId(id)) {
      return { kind: "screen", screen: "ticket-detail", params: { id } };
    }
  }
  return { kind: "not_found", home };
}

export function classify(hash, role) {
  return role ? classifyWithSession(hash, role) : { kind: "login" };
}
