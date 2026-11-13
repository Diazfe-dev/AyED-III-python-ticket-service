const CONTROLS = "button, input, select, textarea";
const LINKS = "a";
const CANCELLED_EVENTS = ["click", "submit", "change", "input"];

let active = false;
let snapshot = new Map();

function scoped(containers, selector) {
  return containers.flatMap((container) => [...container.querySelectorAll(selector)]);
}

function cancel(event) {
  event.preventDefault();
  event.stopImmediatePropagation();
  const control = event.target;
  if (snapshot.has(control)) {
    control.value = snapshot.get(control);
  }
}

function listen(enabled) {
  for (const type of CANCELLED_EVENTS) {
    if (enabled) {
      document.addEventListener(type, cancel, true);
    } else {
      document.removeEventListener(type, cancel, true);
    }
  }
}

export function setInert(containers, inert) {
  if (inert === active) {
    return;
  }
  active = inert;
  listen(inert);
  if (!inert) {
    snapshot = new Map();
    return;
  }
  for (const control of scoped(containers, CONTROLS)) {
    control.disabled = true;
    snapshot.set(control, control.value);
  }
  for (const link of scoped(containers, LINKS)) {
    link.setAttribute("aria-disabled", "true");
  }
}
