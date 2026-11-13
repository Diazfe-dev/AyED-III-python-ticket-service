import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
AREA_DIR = TESTS / "ui"
SPEC_REF = re.compile(r"SPEC-UI-\d+")
TITLE_FORMAT = re.compile(r"SPEC-UI-\d+(, SPEC-UI-\d+)* [\x20-\x7E]+")
JS_CALL = re.compile(
    r"(?<![\w.$])(?:test|it)(?:\.(?:only|skip|todo|fixme))?\(\s*"
    r"(?:(?P<quote>[\"'])(?P<text>(?:\\.|(?!(?P=quote)).)*)(?P=quote)\s*,"
    r"|(?P<template>`(?:\\.|[^`\\])*`)"
    r"|(?P<other>[^\s,)]*))",
    re.DOTALL,
)


@dataclass(frozen=True)
class JsTitle:
    """A test title found in JavaScript source; text is None when it is not a literal."""

    text: str | None
    raw: str


def extract_js_titles(source: str) -> list[JsTitle]:
    """Return the titles of `test(...)` and `it(...)` calls, skipping group titles."""
    titles = []
    for match in JS_CALL.finditer(source):
        if match.group("quote"):
            titles.append(JsTitle(match.group("text"), match.group("text")))
        else:
            raw = match.group("template") or match.group("other")
            titles.append(JsTitle(None, raw))
    return titles


def _js_files() -> list[Path]:
    return sorted(
        path
        for pattern in ("*.js", "*.mjs")
        for path in TESTS.rglob(pattern)
        if "node_modules" not in path.parts
    )


def _python_test_docstrings(path: Path) -> list[tuple[str, str | None]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        (node.name, ast.get_docstring(node))
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test")
    ]


def _in_area(path: Path) -> bool:
    return AREA_DIR in path.parents


def title_format_errors(label: str, text: str | None, raw: str, in_area: bool) -> list[str]:
    """Return the SPEC-UI-99 violations of one test title or docstring."""
    cites_area = text is not None and SPEC_REF.search(text) is not None
    if text is None:
        if in_area or SPEC_REF.search(raw):
            return [f"{label}: the title must be a plain quoted string, got {raw!r}"]
        return []
    if not (in_area or cites_area):
        return []
    if TITLE_FORMAT.fullmatch(text) is None:
        return [f"{label}: {text!r} does not match 'SPEC-UI-NN <ASCII description>'"]
    return []


def area_format_errors() -> list[str]:
    errors = []
    for path in _js_files():
        rel = path.relative_to(ROOT)
        for title in extract_js_titles(path.read_text(encoding="utf-8")):
            errors += title_format_errors(str(rel), title.text, title.raw, _in_area(path))
    for path in sorted(TESTS.rglob("*.py")):
        rel = path.relative_to(ROOT)
        for name, doc in _python_test_docstrings(path):
            label = f"{rel}::{name}"
            if doc is None:
                if _in_area(path):
                    errors.append(f"{label}: the test has no docstring")
                continue
            errors += title_format_errors(label, doc, doc, _in_area(path))
    return errors


def _package() -> dict:
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))


def test_package_json_declares_no_runtime_dependencies():
    """SPEC-UI-76 keeps package.json free of the dependencies key (TC-UI-76a)"""
    assert "dependencies" not in _package()


def test_package_json_runs_pure_module_tests_with_node_test():
    """SPEC-UI-76 runs the pure module tests with node --test (TC-UI-76b)"""
    assert "node --test" in _package()["scripts"]["test:js"]


def test_playwright_config_names_the_e2e_folder_and_a_spec_exists():
    """SPEC-UI-98 ships a versioned Playwright suite with its configuration (TC-UI-98a)"""
    config = (ROOT / "playwright.config.js").read_text(encoding="utf-8")
    assert re.search(r"testDir:\s*[\"']tests/ui/e2e[\"']", config)
    assert list((ROOT / "tests" / "ui" / "e2e").glob("*.spec.js"))


def test_every_area_test_title_follows_the_spec_ui_format():
    """SPEC-UI-99 cites the specs of every area test in the required format (TC-UI-99a)"""
    assert area_format_errors() == []


def test_extractor_takes_only_test_titles_and_reports_templates():
    """SPEC-UI-99 extracts test and it titles, skips groups, reports templates (TC-UI-99b)"""
    source = """
    describe('SPEC-UI-01 group', () => {
      it('SPEC-UI-02 first', () => {});
    });
    test.describe("SPEC-UI-03 group", () => {
      test("SPEC-UI-04 second", async () => {});
      test.skip('SPEC-UI-05 third', () => {});
    });
    test(`SPEC-UI-06 ${name}`, () => {});
    submit('SPEC-UI-07 not a test');
    """
    titles = extract_js_titles(source)
    assert [t.text for t in titles] == [
        "SPEC-UI-02 first",
        "SPEC-UI-04 second",
        "SPEC-UI-05 third",
        None,
    ]
    assert titles[-1].raw == "`SPEC-UI-06 ${name}`"


def test_format_check_rejects_titles_outside_the_format():
    """SPEC-UI-99 rejects a missing ID, a non ASCII text and a template (TC-UI-99b)"""
    assert title_format_errors("f", "SPEC-UI-01 ok", "", True) == []
    assert title_format_errors("f", "SPEC-UI-01, SPEC-UI-02 ok", "", True) == []
    assert title_format_errors("f", "does not cite", "", True)
    assert title_format_errors("f", "SPEC-UI-01 caf\u00e9", "", True)
    assert title_format_errors("f", "SPEC-UI-01", "", True)
    assert title_format_errors("f", None, "`SPEC-UI-01 ${x}`", True)
    assert title_format_errors("f", "plain other area", "", False) == []
    assert title_format_errors("f", "bad but cites SPEC-UI-01", "", False)


SPEC_TABLE_ROW = re.compile(r"^\| (SPEC-UI-\d+) \|", re.MULTILINE)


def spec_ids() -> list[str]:
    """Return the SPEC-UI IDs defined in the rows of the spec tables, not in the decisions."""
    text = (ROOT / "specs" / "07-ui" / "spec.md").read_text(encoding="utf-8")
    return SPEC_TABLE_ROW.findall(text)


def cited_ids() -> set[str]:
    """Return the SPEC-UI IDs cited by any test title or docstring in the repository."""
    cited: set[str] = set()
    for path in _js_files():
        for title in extract_js_titles(path.read_text(encoding="utf-8")):
            cited.update(SPEC_REF.findall(title.text or ""))
    for path in sorted(TESTS.rglob("*.py")):
        for _name, doc in _python_test_docstrings(path):
            cited.update(SPEC_REF.findall(doc or ""))
    return cited


def test_spec_md_yields_138_unique_ids_from_the_table_rows():
    """SPEC-UI-121 reads the 138 IDs from the table rows only (TC-UI-121b)"""
    ids = spec_ids()
    assert len(ids) == 138
    assert len(set(ids)) == 138


def test_every_spec_is_cited_by_at_least_one_test():
    """SPEC-UI-121 requires a test citing every spec of the area (TC-UI-121a)"""
    missing = [spec for spec in spec_ids() if spec not in cited_ids()]
    assert missing == []
