import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SCRIPT_PREAMBLE = """
import os
import sys

sys.path.insert(0, os.getcwd())
import app
from pathlib import Path
from sqlalchemy import create_engine, text
from app.domain.base import Base
from app.db import create_schema

assert Path(app.__file__).resolve().is_relative_to(Path(os.getcwd()).resolve()), app.__file__
engine = create_engine("sqlite://")
create_schema(engine, Base.metadata)
"""


def run_fresh(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-c", SCRIPT_PREAMBLE + script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_models_are_registered_in_a_fresh_interpreter():
    """SPEC-TKT-01 · TC-TKT-01f"""
    script = """
with engine.connect() as conn:
    rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'")).scalars()
    print(" ".join(rows))
"""
    result = run_fresh(script)

    assert result.returncode == 0, result.stderr
    for table in ("tickets", "ticket_products", "milestones", "state_changes"):
        assert table in result.stdout.split()


def test_state_change_barriers_are_active_in_a_fresh_interpreter():
    """SPEC-TKT-16 · TC-TKT-16k"""
    script = """
from sqlalchemy import event
from app.domain.immutable import reject_delete, reject_update

with engine.connect() as conn:
    triggers = conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'trigger'")).scalars()
    print("TRIGGERS", " ".join(triggers))
cls = next(m.class_ for m in Base.registry.mappers if m.local_table.name == "state_changes")
print("UPDATE", event.contains(cls, "before_update", reject_update))
print("DELETE", event.contains(cls, "before_delete", reject_delete))
"""
    result = run_fresh(script)

    assert result.returncode == 0, result.stderr
    assert "state_changes_no_update" in result.stdout
    assert "state_changes_no_delete" in result.stdout
    assert "UPDATE True" in result.stdout
    assert "DELETE True" in result.stdout
