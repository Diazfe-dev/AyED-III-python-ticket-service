import assert from "node:assert/strict";
import { test } from "node:test";

import { createApiClient } from "../../../app/static/js/net/api-client.js";

function jsonResponse(status, body) {
  return {
    status,
    headers: { get: (name) => (name.toLowerCase() === "content-type" ? "application/json" : null) },
    json: async () => body,
  };
}

function recordingFetch(response) {
  const calls = [];
  const fakeFetch = async (url, init) => {
    calls.push({ url, init });
    return response;
  };
  return { fakeFetch, calls };
}

function poisonGlobals() {
  const saved = {};
  for (const name of ["fetch", "document", "window"]) {
    saved[name] = Object.getOwnPropertyDescriptor(globalThis, name);
    Object.defineProperty(globalThis, name, {
      configurable: true,
      get() {
        throw new Error("global " + name + " must not be used");
      },
    });
  }
  return () => {
    for (const name of Object.keys(saved)) {
      if (saved[name]) {
        Object.defineProperty(globalThis, name, saved[name]);
      } else {
        delete globalThis[name];
      }
    }
  };
}

test("SPEC-UI-59 classifies network failures, 204 and non JSON errors (TC-UI-59c)", async () => {
  const failing = createApiClient(async () => {
    throw new TypeError("failed to fetch");
  });
  const network = await failing.request("GET", "/me");
  assert.equal(network.networkError, true);
  assert.equal(network.ok, false);
  assert.equal(network.status, null);
  assert.equal(network.body, null);

  const noContent = createApiClient(async () => ({ status: 204, headers: { get: () => null } }));
  const empty = await noContent.request("POST", "/logout");
  assert.equal(empty.ok, true);
  assert.equal(empty.status, 204);
  assert.equal(empty.body, null);
  assert.equal(empty.networkError, false);

  const html = createApiClient(async () => ({
    status: 502,
    headers: { get: () => "text/html" },
    json: async () => {
      throw new Error("not json");
    },
  }));
  const bad = await html.request("GET", "/me");
  assert.equal(bad.ok, false);
  assert.equal(bad.status, 502);
  assert.equal(bad.body, null);
  assert.equal(bad.networkError, false);
});

test("SPEC-UI-60 sends no Authorization header and keeps the cookie (TC-UI-60a)", async () => {
  const { fakeFetch, calls } = recordingFetch(jsonResponse(200, { id: 1 }));
  const client = createApiClient(fakeFetch);
  await client.request("GET", "/me");
  await client.request("POST", "/login", { email: "a@b.c", password: "x" });
  for (const { url, init } of calls) {
    assert.equal(init.credentials, "same-origin");
    const names = Object.keys(init.headers ?? {}).map((name) => name.toLowerCase());
    assert.equal(names.includes("authorization"), false);
    assert.equal(url.includes("token"), false);
  }
  assert.equal(calls[0].init.headers?.["Content-Type"], undefined);
  assert.equal(calls[1].init.headers["Content-Type"], "application/json");
});

test("SPEC-UI-75 passes the request to the injected function and classifies it (TC-UI-75a)", async () => {
  const { fakeFetch, calls } = recordingFetch(jsonResponse(401, { error: { code: "invalid_credentials" } }));
  const client = createApiClient(fakeFetch, { epoch: () => 3 });
  const body = { email: "a@b.c", password: "x" };
  const result = await client.request("POST", "/login", body);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "/login");
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), body);
  assert.deepEqual(result, {
    ok: false,
    status: 401,
    body: { error: { code: "invalid_credentials" } },
    networkError: false,
    epoch: 3,
  });
});

test("SPEC-UI-75 works with poisoned globals (TC-UI-75b)", async () => {
  const restore = poisonGlobals();
  try {
    const { fakeFetch } = recordingFetch(jsonResponse(200, { items: [] }));
    const client = createApiClient(fakeFetch);
    const result = await client.request("GET", "/tickets");
    assert.equal(result.ok, true);
    assert.deepEqual(result.body, { items: [] });
  } finally {
    restore();
  }
});

test("SPEC-UI-05 rejects paths that are not same-origin relative (TC-UI-59c)", async () => {
  const { fakeFetch, calls } = recordingFetch(jsonResponse(200, {}));
  const client = createApiClient(fakeFetch);
  for (const path of ["me", "//host/me", "http://host/me", ""]) {
    await assert.rejects(client.request("GET", path));
  }
  assert.equal(calls.length, 0);
});

test("SPEC-UI-133 does not call the function when sending is not allowed (TC-UI-75a)", async () => {
  const { fakeFetch, calls } = recordingFetch(jsonResponse(200, {}));
  const client = createApiClient(fakeFetch, { epoch: () => 7, canSend: () => false });
  const result = await client.request("GET", "/tickets");
  assert.equal(calls.length, 0);
  assert.equal(result.ok, false);
  assert.equal(result.networkError, true);
  assert.equal(result.epoch, 7);
});

test("SPEC-UI-130 tags the answer with the epoch read when the request left (TC-UI-75a)", async () => {
  let epoch = 1;
  const { fakeFetch } = recordingFetch(jsonResponse(200, {}));
  const client = createApiClient(fakeFetch, { epoch: () => epoch });
  const pending = client.request("GET", "/tickets");
  epoch = 2;
  const result = await pending;
  assert.equal(result.epoch, 1);
});
