import { expect } from "@playwright/test";
import { USERS } from "./fixtures.js";

const JSON_HEADERS = { "content-type": "application/json" };

function isServedByFlask(url) {
  const { pathname } = new URL(url);
  return pathname === "/" || pathname.startsWith("/static/");
}

function parseBody(text) {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function matches(route, request) {
  if (route.method !== request.method) return false;
  const url = new URL(request.url);
  const target = route.path;
  if (target instanceof RegExp) return target.test(url.pathname + url.search);
  return target.includes("?") ? target === url.pathname + url.search : target === url.pathname;
}

function toResponse(reply) {
  const { status = 200, body, headers = {} } = reply;
  if (body === undefined) return { status, headers };
  if (typeof body === "string") return { status, headers, body };
  return { status, headers: { ...JSON_HEADERS, ...headers }, body: JSON.stringify(body) };
}

export const ABORT = Symbol("abort");

export async function installFakeApi(page) {
  const routes = [];
  const requests = [];
  const api = {
    requests,
    on(method, path, responder) {
      routes.unshift({ method: method.toUpperCase(), path, responder, calls: 0 });
      return api;
    },
    defer(method, path) {
      let settle;
      const outcome = new Promise((resolve) => {
        settle = resolve;
      });
      let arrived;
      const requested = new Promise((resolve) => {
        arrived = resolve;
      });
      api.on(method, path, () => {
        arrived();
        return outcome;
      });
      return {
        requested,
        release: (status = 200, body) => settle({ status, body }),
        abort: () => settle(ABORT),
      };
    },
  };

  await page.route("**/*", async (route) => {
    const request = route.request();
    if (isServedByFlask(request.url())) {
      await route.continue();
      return;
    }
    const record = {
      method: request.method(),
      url: request.url(),
      headers: request.headers(),
      body: parseBody(request.postData()),
      at: Date.now(),
      status: undefined,
      aborted: false,
    };
    requests.push(record);
    const match = routes.find((candidate) => matches(candidate, record));
    if (!match) {
      expect.soft(false, `unhandled API request ${record.method} ${record.url}`).toBe(true);
      record.aborted = true;
      await route.abort("failed");
      return;
    }
    const { responder } = match;
    const index = match.calls;
    match.calls += 1;
    const chosen = Array.isArray(responder)
      ? responder[Math.min(index, responder.length - 1)]
      : responder;
    const reply = typeof chosen === "function" ? await chosen(record) : chosen;
    if (reply === ABORT) {
      record.aborted = true;
      await route.abort("failed");
      return;
    }
    const response = toResponse(reply);
    await route.fulfill(response);
    record.status = response.status;
  });

  return api;
}

export async function loginAs(page, api, role) {
  api.on("GET", "/me", { status: 200, body: USERS[role] });
  await page.goto("/");
}
