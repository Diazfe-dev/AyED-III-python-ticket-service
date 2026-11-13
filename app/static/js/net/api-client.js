function isSameOriginPath(path) {
  return typeof path === "string" && path.startsWith("/") && !path.startsWith("//");
}

function isJson(response) {
  const type = response.headers?.get?.("content-type") ?? "";
  return type.toLowerCase().includes("json");
}

async function readBody(response) {
  if (response.status === 204 || !isJson(response)) {
    return null;
  }
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export function createApiClient(fetchFn, { epoch = () => 0, canSend = () => true } = {}) {
  async function request(method, path, body) {
    if (!isSameOriginPath(path)) {
      throw new Error("API paths must be relative to the same origin");
    }
    const sentEpoch = epoch();
    if (!canSend()) {
      return { ok: false, status: null, body: null, networkError: true, epoch: sentEpoch };
    }
    const init = { method, credentials: "same-origin", headers: {} };
    if (body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    let response;
    try {
      response = await fetchFn(path, init);
    } catch {
      return { ok: false, status: null, body: null, networkError: true, epoch: sentEpoch };
    }
    return {
      ok: response.status >= 200 && response.status < 300,
      status: response.status,
      body: await readBody(response),
      networkError: false,
      epoch: sentEpoch,
    };
  }

  return { request };
}
