const CLIENT_ACTIONS = ["milestone", "close", "reopen"];

const ROLE_ACTIONS = {
  Admin: [],
  Client: CLIENT_ACTIONS,
  Representative: [...CLIENT_ACTIONS, "associate", "remove", "startWork"],
};

const STATE_BLOCKED = {
  New: ["reopen"],
  InProgress: ["reopen", "startWork"],
  Closed: ["close", "milestone", "startWork"],
};

export function ticketActions(role, state) {
  const blocked = STATE_BLOCKED[state] ?? [];
  return (ROLE_ACTIONS[role] ?? []).filter((action) => !blocked.includes(action));
}
