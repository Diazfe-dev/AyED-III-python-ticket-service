import { mount as mountTicketList } from "./tickets-list.js";

export function title() {
  return "Nuevo ticket";
}

export function mount(context) {
  return mountTicketList({ ...context, route: "ticket-new" });
}
