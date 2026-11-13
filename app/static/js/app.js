import { initialRequests, issue, verdict } from "./core/requests.js";
import { canSend, currentUser, initialState, transition } from "./core/session.js";
import { clear, clearMessages, setTitle, showError, showStatus } from "./dom/render.js";
import { renderShell } from "./dom/shell.js";
import { createApiClient } from "./net/api-client.js";
import { screens } from "./screens/index.js";

const root = document.getElementById("app");
const header = document.getElementById("shell");

let state = initialState();
let requests = initialRequests();
let pendingCredentials;

const browserFetch = (path, init) => window.fetch(path, init);
const client = createApiClient(browserFetch, {
  epoch: () => state.epoch,
  canSend: () => canSend(state),
});
const logoutClient = createApiClient(browserFetch, { epoch: () => state.epoch });

const ANSWER_EVENTS = {
  me: (response) => ({ type: "meAnswered", response, hash: window.location.hash }),
  login: (response) => ({ type: "loginAnswered", response }),
  logout: (response) => ({ type: "logoutSettled", response }),
};

function screenRequest(method, path, body, key) {
  const issued = issue(requests, method, key);
  requests = issued.state;
  return new Promise((resolve) => {
    client.request(method, path, body).then((response) => {
      dispatch({ type: "apiAnswered", epoch: response.epoch, response });
      const current = response.epoch === state.epoch && response.status !== 401;
      if (current && verdict(requests, issued.tag, response.status) === "deliver") {
        resolve(response);
      }
    });
  });
}

function screenContext(params) {
  return {
    root,
    params,
    user: currentUser(state),
    request: screenRequest,
    dispatch,
    navigate: (hash) => {
      window.location.hash = hash;
    },
    showError,
    showStatus,
  };
}

function showScreen(name, params) {
  const screen = screens[name];
  clearMessages();
  clear(root);
  renderShell(header, currentUser(state));
  setTitle(screen.title(params));
  screen.mount(screenContext(params));
}

async function runRequest({ kind, method, path }) {
  const body = kind === "login" ? pendingCredentials : undefined;
  const api = kind === "logout" ? logoutClient : client;
  const response = await api.request(method, path, body);
  dispatch(ANSWER_EVENTS[kind](response));
}

const EFFECTS = {
  render: (effect) => showScreen(effect.screen, effect.params),
  replaceHash: (effect) => window.history.replaceState(null, "", effect.hash),
  request: runRequest,
  showError: (effect) => showError(effect.message),
};

function dispatch(event) {
  if (event.type === "loginSubmitted") {
    pendingCredentials = event.credentials;
  }
  const result = transition(state, event);
  state = result.state;
  for (const effect of result.effects) {
    EFFECTS[effect.type]?.(effect);
  }
}

function start() {
  window.addEventListener("hashchange", () => {
    dispatch({ type: "hashChanged", hash: window.location.hash });
  });
  showScreen("boot", { error: null });
  runRequest({ kind: "me", method: "GET", path: "/me" });
}

start();
