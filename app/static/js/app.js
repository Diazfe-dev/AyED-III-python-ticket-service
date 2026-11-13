import { initialRequests, issue, openScreen, verdict } from "./core/requests.js";
import { classify, routeOf, sharesScreenInstance } from "./core/routes.js";
import { canSend, currentUser, initialState, transition } from "./core/session.js";
import { closeDialogs } from "./dom/dialog.js";
import { setInert } from "./dom/inert.js";
import { clear,clearMessages, setTitle, showError, showStatus } from "./dom/render.js";
import { renderShell } from "./dom/shell.js";
import { createApiClient } from "./net/api-client.js";
import { screens } from "./screens/index.js";

const root = document.getElementById("app");
const header = document.getElementById("shell");

let state = initialState();
let requests = initialRequests();
let pendingCredentials;
let shown = { name: null, instance: null };

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
    replaceHash,
    showError,
    showStatus,
  };
}

function replaceHash(hash) {
  window.history.replaceState(null, "", hash);
  const route = classify(hash, currentUser(state)?.role);
  if (route.kind === "screen") {
    shown.name = route.screen;
    refreshChrome(route.screen, route.params ?? {});
  }
}

function refreshChrome(name, params) {
  renderShell(header, currentUser(state), () => dispatch({ type: "logoutClicked" }), routeOf(name));
  setTitle(screens[name].title(params));
}

function focusHeading() {
  const heading = root.querySelector("h1");
  if (heading) {
    heading.setAttribute("tabindex", "-1");
    heading.focus();
  }
}

function showScreen(name, params) {
  const screen = screens[name];
  clearMessages();
  clear(root);
  shown = { name, instance: null };
  refreshChrome(name, params);
  shown.instance = screen.mount(screenContext(params)) ?? null;
  if (shown.instance?.holdsFocus?.() !== true) {
    focusHeading();
  }
}

function continuesScreen(screen) {
  return (
    shown.name !== screen &&
    typeof shown.instance?.setRoute === "function" &&
    sharesScreenInstance(shown.name, screen)
  );
}

async function runRequest({ kind, method, path }) {
  const body = kind === "login" ? pendingCredentials : undefined;
  const api = kind === "logout" ? logoutClient : client;
  const response = await api.request(method, path, body);
  dispatch(ANSWER_EVENTS[kind](response));
}

const EFFECTS = {
  render: (effect) => {
    if (currentUser(state) !== null && continuesScreen(effect.screen)) {
      shown.name = effect.screen;
      refreshChrome(effect.screen, effect.params);
      shown.instance.setRoute(effect.screen);
      return;
    }
    if (currentUser(state) !== null) {
      requests = openScreen(requests);
    }
    showScreen(effect.screen, effect.params);
  },
  replaceHash: (effect) => window.history.replaceState(null, "", effect.hash),
  request: runRequest,
  showError: (effect) => showError(effect.message),
  setInert: (effect) => {
    if (effect.inert) {
      closeDialogs(root);
    }
    setInert([header, root], effect.inert);
  },
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
