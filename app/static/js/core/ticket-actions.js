const CLIENT_ACTIONS = ["milestone", "close", "reopen"];

const ROLE_ACTIONS = {
  Admin: [],
  Client: CLIENT_ACTIONS,
  Representative: [...CLIENT_ACTIONS, "associate", "remove", "startProgress"],
};

const STATE_BLOCKED = {
  New: ["reopen"],
  InProgress: ["reopen"],
  Closed: ["close", "milestone", "startProgress"],
};

export function ticketActions(role, state) {
  const blocked = STATE_BLOCKED[state] ?? [];
  return (ROLE_ACTIONS[role] ?? []).filter((action) => !blocked.includes(action));
}
