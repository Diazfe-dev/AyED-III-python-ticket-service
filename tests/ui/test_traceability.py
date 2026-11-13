import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
