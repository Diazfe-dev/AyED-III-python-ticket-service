import { CONNECTION_ERROR_MESSAGE, translateError } from "./messages.js";
import { classify, homeOf } from "./routes.js";

const LOGIN_HASH = "#/login";
const STATUS_OK = 200;
const STATUS_UNAUTHENTICATED = 401;

const render = (screen, params = {}) => ({ type: "render", screen, params });
const replaceHash = (hash) => ({ type: "replaceHash", hash });
const request = (kind, method, path, epoch) => ({ type: "request", kind, method, path, epoch });
const meRequest = (epoch) => request("me", "GET", "/me", epoch);

const setInert = (inert) => ({ type: "setInert", inert });

const result = (state, effects = []) => ({ state, effects });

function pendingState(origin, epoch) {
  return { name: "mePending", origin, epoch };
}

function anonymousState(epoch, extra = {}) {
  return { name: "anonymous", notice: false, loginPending: false, epoch, ...extra };
}

export function initialState() {
  return pendingState("initial", 0);
}

function showLogin(epoch) {
  return result(anonymousState(epoch), [render("login", { notice: false }), replaceHash(LOGIN_HASH)]);
}

function homeEffects(role, epoch, user) {
  const home = homeOf(role);
  const homeRoute = classify(home, role);
  return result({ name: "open", user, route: home, epoch }, [
    render(homeRoute.screen),
    replaceHash(home),
  ]);
}

function openAt(hash, user, epoch) {
  const route = classify(hash, user.role);
  switch (route.kind) {
    case "screen":
      return result({ name: "open", user, route: hash, epoch }, [
        render(route.screen, route.params ?? {}),
      ]);
    case "not_found":
      return result({ name: "open", user, route: hash, epoch }, [
        render("not-found", { home: route.home }),
      ]);
    default:
      return homeEffects(user.role, epoch, user);
  }
}

function meError(state, response) {
  const error = response.ok ? CONNECTION_ERROR_MESSAGE : translateError(response).message;
  return result({ name: "meError", origin: state.origin, error, epoch: state.epoch }, [
    render("boot", { error }),
  ]);
}

function onMeAnswered(state, event) {
  const { response } = event;
  if (response.status === STATUS_UNAUTHENTICATED) {
    return showLogin(state.epoch);
  }
  const user = response.status === STATUS_OK ? response.body : null;
  if (!user || !homeOf(user.role)) {
    return meError(state, response);
  }
  return state.origin === "login"
    ? homeEffects(user.role, state.epoch, user)
    : openAt(event.hash, user, state.epoch);
}

function onRetry(state) {
  return result(pendingState(state.origin, state.epoch), [
    render("boot", { error: null }),
    meRequest(state.epoch),
  ]);
}

function onLoginAnswered(state, response) {
  if (response.ok) {
    return result(pendingState("login", state.epoch), [
      render("boot", { error: null }),
      meRequest(state.epoch),
    ]);
  }
  return result(anonymousState(state.epoch), [
    { type: "showError", message: translateError(response).message },
  ]);
}

function onAnonymousHash(state, hash) {
  if (hash === LOGIN_HASH) {
    return result(state);
  }
  return result({ ...state, notice: false }, [replaceHash(LOGIN_HASH)]);
}

function onLogoutClicked(state) {
  const epoch = state.epoch + 1;
  return result({ name: "closing", route: state.route, epoch }, [
    request("logout", "POST", "/logout", epoch),
    setInert(true),
  ]);
}

function onLogoutSettled(state) {
  return result(anonymousState(state.epoch), [
    render("login", { notice: false }),
    replaceHash(LOGIN_HASH),
    setInert(false),
  ]);
}

function onOpenApiAnswered(state, event) {
  if (event.response.status !== STATUS_UNAUTHENTICATED) {
    return result(state);
  }
  return result(anonymousState(state.epoch + 1, { notice: true }), [
    render("login", { notice: true }),
    replaceHash(LOGIN_HASH),
  ]);
}

const HANDLERS = {
  mePending: { meAnswered: onMeAnswered },
  meError: { retryClicked: onRetry },
  anonymous: {
    loginSubmitted: (state) =>
      state.loginPending
        ? result(state)
        : result({ ...state, loginPending: true }, [
            request("login", "POST", "/login", state.epoch),
          ]),
    loginAnswered: (state, event) => onLoginAnswered(state, event.response),
    hashChanged: (state, event) => onAnonymousHash(state, event.hash),
  },
  open: {
    hashChanged: (state, event) => openAt(event.hash, state.user, state.epoch),
    logoutClicked: onLogoutClicked,
    apiAnswered: onOpenApiAnswered,
  },
  closing: { logoutSettled: onLogoutSettled },
};

export function transition(state, event) {
  if (event.type === "apiAnswered" && event.epoch !== state.epoch) {
    return result(state);
  }
  const handler = HANDLERS[state.name]?.[event.type];
  return handler ? handler(state, event) : result(state);
}

export function canSend(state) {
  return state.name !== "closing";
}

export function isInert(state) {
  return state.name === "closing";
}

export function currentUser(state) {
  return state.name === "open" ? state.user : null;
}
