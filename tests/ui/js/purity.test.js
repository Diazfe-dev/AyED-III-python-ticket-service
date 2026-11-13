import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const CORE_DIR = fileURLToPath(new URL("../../../app/static/js/core", import.meta.url));
const INDEX_HTML = fileURLToPath(new URL("../../../app/static/index.html", import.meta.url));
const FORBIDDEN = ["fetch", "document", "window"];

function coreFiles(dir = CORE_DIR) {
  return readdirSync(dir)
    .filter((name) => name.endsWith(".js"))
    .sort()
    .map((name) => join(dir, name));
}

function violations(text) {
  return FORBIDDEN.filter((word) => new RegExp(String.raw`\b${word}\b`).test(text));
}

function foreignImports(text) {
  const specs = [...text.matchAll(/(?:from\s+|import\s*\(?\s*)["']([^"']+)["']/g)].map((m) => m[1]);
  return specs.filter((spec) => !/^\.\/[\w.-]+\.js$/.test(spec));
}

function poisonGlobals() {
  const saved = {};
  for (const name of [...FORBIDDEN, "localStorage", "sessionStorage"]) {
    saved[name] = Object.getOwnPropertyDescriptor(globalThis, name);
    Object.defineProperty(globalThis, name, {
      configurable: true,
      get() {
        throw new Error("global " + name + " must not be used");
      },
    });
  }
  return () => {
    for (const [name, descriptor] of Object.entries(saved)) {
      if (descriptor) {
        Object.defineProperty(globalThis, name, descriptor);
      } else {
        delete globalThis[name];
      }
    }
  };
}

async function importAndRunOne(file) {
  const loaded = await import(pathToFileURL(file).href + "?purity=" + Date.now());
  const names = Object.keys(loaded);
  assert.ok(names.length > 0, file + " exports nothing");
  const fn = names.map((n) => loaded[n]).find((value) => typeof value === "function");
  if (fn) {
    try {
      fn();
    } catch (error) {
      assert.doesNotMatch(String(error.message), /must not be used/, file);
    }
  }
}

test("SPEC-UI-73 imports and runs every core module with fetch, document and window poisoned (TC-UI-73a)", async () => {
  const files = coreFiles();
  assert.ok(files.length > 0);
  const restore = poisonGlobals();
  try {
    for (const file of files) {
      await importAndRunOne(file);
    }
  } finally {
    restore();
  }
});

test("SPEC-UI-73 poisoned globals throw when touched (TC-UI-73a)", () => {
  const restore = poisonGlobals();
  try {
    assert.throws(() => globalThis.fetch, /must not be used/);
    assert.throws(() => globalThis.document, /must not be used/);
    assert.throws(() => globalThis.window, /must not be used/);
  } finally {
    restore();
  }
});

test("SPEC-UI-73 scanner flags forbidden words and foreign imports in samples (TC-UI-73b)", () => {
  assert.deepEqual(violations("const x = window.location;"), ["window"]);
  assert.deepEqual(violations("fetch(url); document.title"), ["fetch", "document"]);
  assert.deepEqual(violations("export const windowSize = 1;"), []);
  assert.deepEqual(foreignImports('import { a } from "../net/api-client.js";'), ["../net/api-client.js"]);
  assert.deepEqual(foreignImports('import { a } from "./routes.js";'), []);
});

test("SPEC-UI-73 core files reference no fetch, document or window and import only from core (TC-UI-73b)", () => {
  for (const file of coreFiles()) {
    const text = readFileSync(file, "utf8");
    assert.deepEqual(violations(text), [], file);
    assert.deepEqual(foreignImports(text), [], file);
  }
});

test("SPEC-UI-74 loads app.js as a module script and core files are ES modules (TC-UI-74a)", async () => {
  const html = readFileSync(INDEX_HTML, "utf8");
  assert.match(html, /<script\s+type="module"\s+src="\/static\/js\/app\.js"\s*><\/script>/);
  for (const file of coreFiles()) {
    const loaded = await import(pathToFileURL(file).href);
    assert.ok(Object.keys(loaded).length > 0, file);
  }
});
