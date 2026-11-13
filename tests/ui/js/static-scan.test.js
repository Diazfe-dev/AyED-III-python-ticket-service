import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, relative } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const STATIC_DIR = fileURLToPath(new URL("../../../app/static", import.meta.url));

function listFiles(dir) {
  const found = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      found.push(...listFiles(full));
    } else {
      found.push(full);
    }
  }
  return found.sort();
}

function loadFiles() {
  return listFiles(STATIC_DIR).map((full) => ({
    path: relative(STATIC_DIR, full),
    ext: extname(full),
    text: readFileSync(full, "utf8"),
  }));
}

const EXTERNAL = String.raw`(?:[a-zA-Z][a-zA-Z0-9+.-]*:)?\/\/[^\s"'<>)]`;

function externalReferences(file) {
  const hits = [];
  const attr = new RegExp(String.raw`\b(?:src|href|action|poster|srcset)\s*=\s*["']\s*${EXTERNAL}`, "gi");
  const cssUrl = new RegExp(String.raw`url\(\s*["']?\s*${EXTERNAL}`, "gi");
  const cssImport = new RegExp(String.raw`@import\s+(?:url\(\s*)?["']?\s*${EXTERNAL}`, "gi");
  const literal = /["'`]\s*(?:https?:)?\/\/[^\s"'`]/gi;
  for (const rule of [attr, cssUrl, cssImport]) {
    hits.push(...(file.text.match(rule) ?? []));
  }
  if (file.ext === ".js") {
    hits.push(...(file.text.match(literal) ?? []));
  } else {
    hits.push(...(file.text.match(/https?:\/\/[^\s"'<>)]*/gi) ?? []));
  }
  return hits;
}

const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/g,
  /AKIA[0-9A-Z]{16}/g,
  /(api_key|secret|token)\s*[:=]\s*["'][^"']+["']/gi,
  /Bearer\s+[A-Za-z0-9._-]+/g,
];

function secretHits(file) {
  return SECRET_PATTERNS.flatMap((rule) => file.text.match(rule) ?? []);
}

function storageHits(file) {
  return file.text.match(/\b(?:localStorage|sessionStorage)\b|document\.cookie/g) ?? [];
}

function htmlInsertionHits(file) {
  return file.text.match(/\b(?:innerHTML|outerHTML|insertAdjacentHTML)\b|document\.write/g) ?? [];
}

function inlineHits(file) {
  if (file.ext !== ".html" && file.ext !== ".js") {
    return [];
  }
  return [
    ...(file.text.match(/\s(?:on[a-z]+|style)\s*=\s*["']/gi) ?? []),
    ...(file.text.match(/javascript:/gi) ?? []),
    ...(file.text.match(/<script(?![^>]*\ssrc\s*=)[^>]*>/gi) ?? []),
  ];
}

function sample(ext, text) {
  return { path: `sample${ext}`, ext, text };
}

function jsFiles() {
  return loadFiles().filter((file) => file.ext === ".js");
}

function offenders(files, scan) {
  return files.flatMap((file) => scan(file).map((hit) => `${file.path}: ${hit}`));
}

test("SPEC-UI-05 flags absolute and protocol-relative URLs in sample files (TC-UI-05a)", () => {
  assert.ok(externalReferences(sample(".html", '<img src="https://x.test/a.png">')).length > 0);
  assert.ok(externalReferences(sample(".html", '<a href="//cdn.test/a">')).length > 0);
  assert.ok(externalReferences(sample(".js", 'import x from "https://x.test/m.js";')).length > 0);
  assert.ok(externalReferences(sample(".js", 'const u = "//host/api";')).length > 0);
  assert.ok(externalReferences(sample(".js", "const u = `http://host/api`;")).length > 0);
  assert.ok(externalReferences(sample(".css", "a { background: url(http://x.test/a.png); }")).length > 0);
  assert.equal(externalReferences(sample(".js", 'fetch("/api/tickets");')).length, 0);
  assert.equal(externalReferences(sample(".html", '<a href="/static/css/app.css">')).length, 0);
});

test("SPEC-UI-05 finds no absolute URL in any static file (TC-UI-05a)", () => {
  assert.deepEqual(offenders(loadFiles(), externalReferences), []);
});

test("SPEC-UI-06 flags external scripts, links and imports in sample files (TC-UI-06a)", () => {
  assert.ok(externalReferences(sample(".html", '<script src="https://cdn.test/x.js"></script>')).length > 0);
  assert.ok(externalReferences(sample(".html", '<link rel="stylesheet" href="//fonts.test/f.css">')).length > 0);
  assert.ok(externalReferences(sample(".css", '@import "https://fonts.test/f.css";')).length > 0);
  assert.ok(externalReferences(sample(".css", '@import url("//fonts.test/f.css");')).length > 0);
  assert.ok(
    externalReferences(sample(".css", '@font-face { src: url("https://fonts.test/f.woff2"); }')).length > 0,
  );
});

test("SPEC-UI-06 serves source files without a build step (TC-UI-06a)", () => {
  const index = readFileSync(join(STATIC_DIR, "index.html"), "utf8");
  assert.match(index, /<script type="module" src="\/static\/js\/app\.js"><\/script>/);
  assert.match(index, /<link rel="stylesheet" href="\/static\/css\/app\.css">/);
  const css = readFileSync(join(STATIC_DIR, "css/app.css"), "utf8");
  assert.doesNotMatch(css, /@import/);
  for (const source of css.match(/@font-face\s*{[^}]*}/g) ?? []) {
    assert.match(source, /url\(\s*["']?\.\.\/fonts\/[\w.-]+\.woff2["']?\s*\)/);
    assert.deepEqual(externalReferences(sample(".css", source)), []);
  }
});

test("SPEC-UI-61 flags secret patterns in sample text (TC-UI-61a)", () => {
  const begin = "-----BEGIN " + "RSA PRIVATE KEY-----";
  assert.ok(secretHits(sample(".js", begin)).length > 0);
  assert.ok(secretHits(sample(".js", "AKIA" + "ABCDEFGHIJKLMNOP")).length > 0);
  assert.ok(secretHits(sample(".js", 'const api_key = "abc";')).length > 0);
  assert.ok(secretHits(sample(".js", 'headers: "Bearer abc.def"')).length > 0);
  assert.equal(secretHits(sample(".js", "const label = 'Mesa de ayuda';")).length, 0);
});

test("SPEC-UI-61 finds no secret pattern in any static file (TC-UI-61a)", () => {
  assert.deepEqual(offenders(loadFiles(), secretHits), []);
});

test("SPEC-UI-62 flags browser storage access in sample text (TC-UI-62b)", () => {
  assert.ok(storageHits(sample(".js", 'localStorage.setItem("a", "b");')).length > 0);
  assert.ok(storageHits(sample(".js", "sessionStorage.clear();")).length > 0);
  assert.ok(storageHits(sample(".js", 'document.cookie = "a=b";')).length > 0);
  assert.equal(storageHits(sample(".js", "const state = {};")).length, 0);
});

test("SPEC-UI-62 finds no browser storage access in static scripts (TC-UI-62b)", () => {
  assert.deepEqual(offenders(jsFiles(), storageHits), []);
});

test("SPEC-UI-63 flags HTML insertion APIs in sample text (TC-UI-63b)", () => {
  assert.ok(htmlInsertionHits(sample(".js", "node.innerHTML = x;")).length > 0);
  assert.ok(htmlInsertionHits(sample(".js", "node.outerHTML = x;")).length > 0);
  assert.ok(htmlInsertionHits(sample(".js", 'node.insertAdjacentHTML("beforeend", x);')).length > 0);
  assert.ok(htmlInsertionHits(sample(".js", "document.write(x);")).length > 0);
  assert.equal(htmlInsertionHits(sample(".js", "node.textContent = x;")).length, 0);
});

test("SPEC-UI-63 finds no HTML insertion API in static scripts (TC-UI-63b)", () => {
  assert.deepEqual(offenders(jsFiles(), htmlInsertionHits), []);
});

test("SPEC-UI-65 flags inline handlers, styles and scripts in sample text (TC-UI-65a)", () => {
  assert.ok(inlineHits(sample(".html", '<button onclick="go()">x</button>')).length > 0);
  assert.ok(inlineHits(sample(".html", '<p style="color: red">x</p>')).length > 0);
  assert.ok(inlineHits(sample(".html", '<a href="javascript:void(0)">x</a>')).length > 0);
  assert.ok(inlineHits(sample(".html", "<script>run();</script>")).length > 0);
  assert.equal(
    inlineHits(sample(".html", '<script type="module" src="/static/js/app.js"></script>')).length,
    0,
  );
});

test("SPEC-UI-65 finds no inline handler, style or script in the page and scripts (TC-UI-65a)", () => {
  const files = loadFiles().filter((file) => file.path === "index.html" || file.ext === ".js");
  assert.deepEqual(offenders(files, inlineHits), []);
});
