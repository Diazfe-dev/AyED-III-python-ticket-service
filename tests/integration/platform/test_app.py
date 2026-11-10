from flask import Flask, session
from sqlalchemy import Column, Integer, MetaData, Table, inspect

from app import create_app
from app.db import get_engine


def test_testing_app_uses_in_memory_database(app: Flask) -> None:
    """SPEC-PLT-04 · TC-PLT-04a"""
    with app.app_context():
        engine = get_engine()

    assert str(engine.url) == "sqlite://"


def test_testing_apps_do_not_share_their_database(app: Flask) -> None:
    """SPEC-PLT-04 · TC-PLT-04b"""
    second = create_app({"TESTING": True})
    metadata = MetaData()
    Table("only_in_first", metadata, Column("id", Integer, primary_key=True))

    with app.app_context():
        metadata.create_all(get_engine())
    with second.app_context():
        second_tables = inspect(get_engine()).get_table_names()
        get_engine().dispose()

    assert second_tables == []


def test_session_cookie_is_configured_http_only_and_same_site_lax(app: Flask) -> None:
    """SPEC-PLT-10 · TC-PLT-10a"""
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_session_cookie_is_emitted_http_only_and_same_site_lax(app: Flask) -> None:
    """SPEC-PLT-10 · TC-PLT-10b"""

    @app.get("/test/write-session")
    def write_session() -> str:
        session["visited"] = True
        return "ok"

    response = app.test_client().get("/test/write-session")

    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
