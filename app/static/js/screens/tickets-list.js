import { formatDateTime } from "../core/dates.js";
import { stateLabel } from "../core/labels.js";
import { createListing, fillOptions, searchField, selectField } from "../dom/listing.js";
import { el } from "../dom/render.js";

const COLUMNS = ["Número", "Cliente", "Estado", "Creado"];
const STATES = ["New", "InProgress", "Closed"];

export function title() {
  return "Tickets";
}

function ticketRow(item) {
  return [
    el("a", { href: `#/tickets/${item.id}` }, [`#${item.id}`]),
    item.client.name,
    stateLabel(item.state),
    formatDateTime(item.created_at),
  ];
}

function stateOptions() {
  return [
    { value: "", label: "Todos" },
    ...STATES.map((code) => ({ value: code, label: stateLabel(code) })),
  ];
}

const ORDER_OPTIONS = [
  { value: "", label: "Más recientes primero" },
  { value: "asc", label: "Más antiguos primero" },
];

function personFilter({ id, label, allLabel, listing, field }) {
  return selectField({
    id,
    label,
    options: [{ value: "", label: allLabel }],
    onChange: (value) => listing.apply({ [field]: value }),
  });
}

export function mount({ root, user, request, showError }) {
  const listing = createListing({
    request,
    showError,
    path: "/tickets",
    columns: COLUMNS,
    row: ticketRow,
  });
  const stateFilter = selectField({
    id: "filter-state",
    label: "Estado",
    options: stateOptions(),
    onChange: (value) => listing.apply({ state: value }),
  });
  const order = selectField({
    id: "filter-order",
    label: "Orden",
    options: ORDER_OPTIONS,
    onChange: (value) => listing.apply({ order: value }),
  });
  const searchForm = searchField({
    id: "filter-q",
    label: "Buscar",
    submitLabel: "Buscar",
    onSubmit: (value) => listing.apply({ q: value }),
  });
  const controls = [stateFilter.element, order.element, searchForm];
  const selectors = [];
  if (user.role !== "Client") {
    const clients = personFilter({
      id: "filter-client",
      label: "Cliente",
      allLabel: "Todos los clientes",
      listing,
      field: "client_id",
    });
    controls.push(clients.element);
    selectors.push({ select: clients.select, path: "/clients", key: "clients" });
  }
  if (user.role === "Admin") {
    const representatives = personFilter({
      id: "filter-representative",
      label: "Representante",
      allLabel: "Todos los representantes",
      listing,
      field: "representative_id",
    });
    controls.push(representatives.element);
    selectors.push({
      select: representatives.select,
      path: "/representatives",
      key: "representatives",
    });
  }
  root.append(
    el("h1", {}, [title()]),
    el("div", { class: "filters" }, controls),
    listing.element,
  );
  listing.load();
  for (const selector of selectors) {
    fillOptions({ ...selector, request, showError });
  }
}
