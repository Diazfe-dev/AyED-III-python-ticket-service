const WRITE_METHODS = new Set(["POST", "PATCH", "DELETE"]);

export function initialRequests() {
  return { screen: 0, seq: 0, latest: {} };
}

export function openScreen(state) {
  return { screen: state.screen + 1, seq: state.seq, latest: {} };
}

export function issue(state, method, key) {
  const seq = state.seq + 1;
  const write = WRITE_METHODS.has(method);
  if (write) {
    return {
      state: { ...state, seq },
      tag: { screen: state.screen, key: null, seq, write: true },
    };
  }
  const resourceKey = key === undefined ? `anonymous-${seq}` : key;
  return {
    state: { ...state, seq, latest: { ...state.latest, [resourceKey]: seq } },
    tag: { screen: state.screen, key: resourceKey, seq, write: false },
  };
}

export function verdict(state, tag, status) {
  if (status === 401) {
    return "deliver";
  }
  if (tag.screen !== state.screen) {
    return "ignore";
  }
  if (!tag.write && state.latest[tag.key] !== tag.seq) {
    return "ignore";
  }
  return "deliver";
}
