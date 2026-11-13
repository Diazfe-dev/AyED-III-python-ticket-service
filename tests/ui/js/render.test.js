import assert from "node:assert/strict";
import { test } from "node:test";

import { el } from "../../../app/static/js/dom/render.js";

function fakeNode(tag) {
  return {
    tag,
    attributes: {},
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    append() {},
  };
}

function withFakeDocument(run) {
  const saved = Object.getOwnPropertyDescriptor(globalThis, "document");
  globalThis.document = {
    createElement: fakeNode,
    createTextNode: (text) => ({ text }),
  };
  try {
    run();
  } finally {
    if (saved) {
      Object.defineProperty(globalThis, "document", saved);
    } else {
      delete globalThis.document;
    }
  }
}

test("SPEC-UI-65 el rejects inline handler and style attributes (TC-UI-65c)", () => {
  withFakeDocument(() => {
    for (const name of ["onclick", "onerror", "onload", "style", "srcdoc"]) {
      assert.throws(() => el("a", { [name]: "x" }), /Attribute not allowed/, name);
    }
  });
});

test("SPEC-UI-65 el accepts class, aria-* and listed attributes (TC-UI-65c)", () => {
  withFakeDocument(() => {
    const node = el("a", { class: "c", "aria-label": "l", href: "#/x", disabled: true, id: false });
    assert.deepEqual(node.attributes, { class: "c", "aria-label": "l", href: "#/x", disabled: "" });
  });
});
