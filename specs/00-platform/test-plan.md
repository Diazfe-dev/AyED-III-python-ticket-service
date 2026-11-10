# 00 — Plataforma · Test plan

Cada test cita en su docstring la spec y el caso: `"""SPEC-PLT-05 · TC-PLT-05a"""`.

Fixtures (`tests/conftest.py`):
- `app`: `create_app({"TESTING": True})`, nueva para cada test y con su propia base en memoria.
- `client`: `app.test_client()`.
- `runner`: `app.test_cli_runner()`.

## Matriz spec → casos

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| PLT-01 | TC-PLT-01a | unit | `environ={"SECRET_KEY": "s3cret"}` | `config["SECRET_KEY"] == "s3cret"` | `tests/unit/platform/test_config.py` |
| PLT-01 | TC-PLT-01b | unit | `environ` con `DATABASE_URL=sqlite:///x.db` | `config["DATABASE_URL"] == "sqlite:///x.db"` | `tests/unit/platform/test_config.py` |
| PLT-02 | TC-PLT-02a | unit | Sin `DATABASE_URL` y sin testing | URL `sqlite:///<instance_path>/tickets.db` | `tests/unit/platform/test_config.py` |
| PLT-03 | TC-PLT-03a | unit | Sin `SECRET_KEY`, sin testing ni debug | Lanza `ConfigError` y el mensaje menciona `SECRET_KEY` | `tests/unit/platform/test_config.py` |
| PLT-03 | TC-PLT-03b | unit | Sin `SECRET_KEY`, con debug | No lanza, y la clave no está vacía | `tests/unit/platform/test_config.py` |
| PLT-04 | TC-PLT-04a | integration | `create_app({"TESTING": True})` | La URL del engine es `sqlite://` (memoria) | `tests/integration/platform/test_app.py` |
| PLT-04 | TC-PLT-04b | integration | Dos apps; se crea una tabla en la primera | La tabla no existe en la segunda | `tests/integration/platform/test_app.py` |
| PLT-05 | TC-PLT-05a | integration | Conexión nueva del engine | `PRAGMA foreign_keys` devuelve `1` | `tests/integration/platform/test_db.py` |
| PLT-05 | TC-PLT-05b | integration | Tablas de prueba `parent`/`child` e insert de un `child` con FK inexistente | Lanza `IntegrityError` | `tests/integration/platform/test_db.py` |
| PLT-06 | TC-PLT-06a | integration | Ruta de prueba que llama `get_session()` dos veces | Las dos llamadas devuelven el mismo objeto | `tests/integration/platform/test_db.py` |
| PLT-06 | TC-PLT-06b | integration | Dos requests a la misma ruta de prueba | Cada request recibe una sesión distinta | `tests/integration/platform/test_db.py` |
| PLT-07 | TC-PLT-07a | integration | Espía sobre `Session.close` en un request que usa la sesión | `close()` se invocó una vez al terminar el request | `tests/integration/platform/test_db.py` |
| PLT-08 | TC-PLT-08a | integration | Ruta de prueba que hace `add()` de una fila y lanza una excepción | Se invoca `rollback()` antes de `close()` y la fila no queda persistida | `tests/integration/platform/test_db.py` |
| PLT-09 | TC-PLT-09a | integration | `create_schema(engine, metadata_de_prueba)` | Las tablas de la metadata existen | `tests/integration/platform/test_db.py` |
| PLT-09 | TC-PLT-09b | integration | Insertar una fila y volver a ejecutar `create_schema` | La fila sigue existiendo | `tests/integration/platform/test_db.py` |
| PLT-09 | TC-PLT-09c | integration | `runner.invoke(args=["init-db"])` | Termina con código 0 e informa que la base se inicializó | `tests/integration/platform/test_cli.py` |
| PLT-10 | TC-PLT-10a | integration | `app.config` | `SESSION_COOKIE_HTTPONLY is True` y `SESSION_COOKIE_SAMESITE == "Lax"` | `tests/integration/platform/test_app.py` |
| PLT-10 | TC-PLT-10b | integration | Ruta de prueba que escribe en `session` | El header `Set-Cookie` incluye `HttpOnly` y `SameSite=Lax` | `tests/integration/platform/test_app.py` |
| PLT-11 | TC-PLT-11a | integration | `GET /health` | `200` con JSON `{"status": "ok"}` | `tests/integration/platform/test_health.py` |
| PLT-11 | TC-PLT-11b | integration | `GET /health` sin sesión | `200` (no redirige ni pide autenticación) | `tests/integration/platform/test_health.py` |
| PLT-12 | TC-PLT-12a | integration | `GET /openapi.json` | `200`, `Content-Type: application/json` y el campo `openapi` empieza con `3.1` | `tests/integration/platform/test_api_docs.py` |
| PLT-12 | TC-PLT-12b | integration | `GET /openapi.json` sin sesión | `200` (no pide autenticación) | `tests/integration/platform/test_api_docs.py` |
| PLT-13 | TC-PLT-13a | integration | `GET /docs` sin sesión | `200`, `text/html` y el HTML apunta a `/openapi.json` | `tests/integration/platform/test_api_docs.py` |
| PLT-13 | TC-PLT-13b | integration | `GET /docs` | Los assets de Swagger UI se cargan con la versión fija `swagger-ui-dist@5.17.14` | `tests/integration/platform/test_api_docs.py` |
| PLT-14 | TC-PLT-14a | integration | Cada regla de `app.url_map` (sin `static`, `HEAD` ni `OPTIONS`) | Existe en los `paths` del contrato con el mismo método | `tests/integration/platform/test_api_docs.py` |
| PLT-14 | TC-PLT-14b | integration | Cada par ruta-método de los `paths` del contrato | Existe en `app.url_map` | `tests/integration/platform/test_api_docs.py` |

## Casos borde

- `DATABASE_URL` definida en el entorno y también en los `overrides`: ganan los `overrides` (cubierto en TC-PLT-01b con una variante).
- Requests que no usan la base: no se abre sesión, así que el teardown no hace nada (cubierto en TC-PLT-11a, porque `/health` no llama `get_session()`).

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 1 (TDD, aislamiento) | TC-PLT-04a, 04b |
| RNF 2 (seguridad) | TC-PLT-03a, 10a, 10b |
| RNF 7 (documentación de la API) | TC-PLT-12a, 12b, 13a, 13b, 14a, 14b |
