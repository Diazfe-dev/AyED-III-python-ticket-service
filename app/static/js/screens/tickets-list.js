import { formatDateTime } from "../core/dates.js";
import { stateLabel } from "../core/labels.js";
import { pageHeader, surface, toolbar } from "../dom/layout.js";
import { createListing, fillOptions, searchField, selectField } from "../dom/listing.js";
import { el } from "../dom/render.js";
import { openTicketDialog } from "./ticket-create-dialog.js";

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

const LIST_ROUTE = "tickets-list";
const CREATE_ROUTE = "ticket-new";
const LIST_HASH = "#/tickets";

export function mount({ root, user, request, showError, navigate, replaceHash, route = LIST_ROUTE }) {
  let current = route;
  let dialog = null;
  let header = null;
  const listing = createListing({
    request,
    showError,
    path: "/tickets",
    label: title(),
    columns: COLUMNS,
    row: ticketRow,
  });

  function openCreate(opener = null) {
    dialog = openTicketDialog({
      root,
      request,
      opener,
      fallback: () => header.button,
      navigate,
      onCancel: () => {
        if (current === CREATE_ROUTE) {
          current = LIST_ROUTE;
          replaceHash(LIST_HASH);
        }
      },
    });
  }
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
  const canCreate = user.role === "Representative";
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
  header = pageHeader({
    title: title(),
    action: canCreate ? { label: "Nuevo ticket", onClick: openCreate } : null,
  });
  root.append(header.element, surface({ toolbar: toolbar(controls), table: listing.element }));
  listing.load();
  for (const selector of selectors) {
    fillOptions({ ...selector, request, showError });
  }
  if (canCreate && current === CREATE_ROUTE) {
    openCreate();
  }
  return {
    holdsFocus: () => dialog !== null && dialog.isOpen(),
    setRoute(next) {
      current = next;
      if (next === CREATE_ROUTE && canCreate && !(dialog?.isOpen() ?? false)) {
        openCreate();
      } else if (next === LIST_ROUTE && dialog?.isOpen()) {
        dialog.close();
      }
    },
  };
}
