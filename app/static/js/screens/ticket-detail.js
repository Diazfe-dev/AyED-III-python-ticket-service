import { formatDateTime } from "../core/dates.js";
import { roleLabel, stateLabel } from "../core/labels.js";
import { translateError } from "../core/messages.js";
import { clear, el, loadingIndicator } from "../dom/render.js";

export function title({ id }) {
  return `Ticket #${id}`;
}

function summary(ticket) {
  const products = ticket.products.map((product) => el("li", {}, [product.name]));
  return el("section", { "aria-label": "Datos del ticket" }, [
    el("p", {}, ["Estado: ", el("span", { class: "ticket-state" }, [stateLabel(ticket.state)])]),
    el("p", {}, [`Cliente: ${ticket.client.name}`]),
    el("p", {}, [`Representante: ${ticket.representative.name}`]),
    el("p", {}, [`Creado: ${formatDateTime(ticket.created_at)}`]),
    el("h2", {}, ["Productos"]),
    products.length > 0 ? el("ul", { class: "products" }, products) : el("p", {}, ["Sin productos"]),
  ]);
}

function milestoneItem(milestone) {
  const { author } = milestone;
  return el("li", {}, [
    el("p", {}, [milestone.content]),
    el("p", {}, [
      `${author.name} (${roleLabel(author.role)}) · ${formatDateTime(milestone.created_at)}`,
    ]),
  ]);
}

function changeItem(change) {
  const { user } = change;
  return el("li", {}, [
    el("p", {}, [stateLabel(change.state)]),
    el("p", {}, [`${user.name} (${roleLabel(user.role)}) · ${formatDateTime(change.timestamp)}`]),
  ]);
}

function timeline(heading, className, items, render) {
  return el("section", { "aria-label": heading }, [
    el("h2", {}, [heading]),
    el("ol", { class: className }, items.map(render)),
  ]);
}

export function mount({ root, params, request, showError }) {
  const content = el("div", {}, [loadingIndicator()]);
  root.append(el("h1", {}, [title(params)]), content);
  const base = `/tickets/${params.id}`;

  Promise.all([
    request("GET", base),
    request("GET", `${base}/milestones`),
    request("GET", `${base}/state-changes`),
  ]).then((responses) => {
    clear(content);
    const failed = responses.find((response) => !response.ok);
    if (failed) {
      showError(translateError(failed).message);
      return;
    }
    const [ticket, milestones, changes] = responses.map((response) => response.body);
    content.append(
      summary(ticket),
      timeline("Hitos", "milestones", milestones, milestoneItem),
      timeline("Cambios de estado", "state-changes", changes, changeItem),
    );
  });
}
