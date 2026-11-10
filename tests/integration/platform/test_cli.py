from flask.testing import FlaskCliRunner


def test_init_db_command_reports_initialized_database(runner: FlaskCliRunner) -> None:
    """SPEC-PLT-09 · TC-PLT-09c"""
    result = runner.invoke(args=["init-db"])

    assert result.exit_code == 0
    assert "Database initialized" in result.output
