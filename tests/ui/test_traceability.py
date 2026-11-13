import json
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
