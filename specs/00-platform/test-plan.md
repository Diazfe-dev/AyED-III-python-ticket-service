# 00 — Plataforma · Test plan

Cada test cita en su docstring la spec y el caso: `"""SPEC-PLT-05 · TC-PLT-05a"""`.

Fixtures (`tests/conftest.py`):
- `app`: `create_app({"TESTING": True})`, nueva para cada test y con su propia base en memoria.
- `client`: `app.test_client()`.
- `runner`: `app.test_cli_runner()`.
- `unpropagated_app`: `create_app({"TESTING": True, "PROPAGATE_EXCEPTIONS": False})`. Con `TESTING`, Flask relanza las excepciones no manejadas; con la propagación apagada sigue el camino de producción y llama al manejador del `500` (SPEC-PLT-16, TC-PLT-08b).

Re-sincronización del 2026-11-12: SPEC-PLT-14 está reemplazada por SPEC-PLT-23 y sus casos pasan a TC-PLT-23a y 23b (T-PLT-22); se suman los casos de la paginación opcional (SPEC-PLT-17 a 22 y 24 a 26) y del `q` vacío (SPEC-PLT-27). Archivos de test nuevos: `tests/unit/platform/test_listing.py`, `tests/unit/platform/test_listing_response.py` y `tests/integration/platform/test_paging.py`.

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
| PLT-08 | TC-PLT-08b | integration | Igual que 08a sobre `unpropagated_app` (manejador del `500` activo, como en producción) | `500`; se invoca `rollback()` antes de `close()` y la fila no queda persistida | `tests/integration/platform/test_db.py` |
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
| PLT-14 | TC-PLT-14a | integration | **Reemplazado por TC-PLT-23a** (SPEC-PLT-14 reemplazada por SPEC-PLT-23, 2026-11-12) | — | — |
| PLT-14 | TC-PLT-14b | integration | **Reemplazado por TC-PLT-23b** (SPEC-PLT-14 reemplazada por SPEC-PLT-23, 2026-11-12) | — | — |
| PLT-15 | TC-PLT-15a | integration | `GET /no-such-route` sin sesión | `404` `{"error": "not_found"}` en JSON | `tests/integration/platform/test_errors.py` |
| PLT-15 | TC-PLT-15b | integration | Parametrizado: `PATCH /categories/abc`, `PATCH /users/abc` y `POST /users/abc/deactivate`, sin sesión | `404` `{"error": "not_found"}` en todos (el ruteo corre antes que la autenticación) | `tests/integration/platform/test_errors.py` |
| PLT-15 | TC-PLT-15c | integration | `DELETE /health` | `405` `{"error": "method_not_allowed"}` en JSON y el header `Allow` incluye `GET` | `tests/integration/platform/test_errors.py` |
| PLT-16 | TC-PLT-16a | integration | Ruta de prueba en `unpropagated_app` que lanza `RuntimeError("secret-detail")` | `500` `{"error": "internal_error"}` en JSON; el cuerpo no contiene `secret-detail` ni `Traceback` | `tests/integration/platform/test_errors.py` |
| PLT-16 | TC-PLT-16b | integration | Ruta de prueba en `unpropagated_app` que lanza `UserNotFoundError` | `404` `{"error": "user_not_found"}`: el manejador del `500` no se traga las `DomainError` | `tests/integration/platform/test_errors.py` |
| PLT-16 | TC-PLT-16c | integration | `GET /no-such-route` en `unpropagated_app` | `404` `{"error": "not_found"}`: el manejador del `500` no se traga las `HTTPException` | `tests/integration/platform/test_errors.py` |
| PLT-23 | TC-PLT-23a | integration | Cada regla de `app.url_map` (sin `HEAD` ni `OPTIONS`, **sin** ignorar el endpoint `static` por nombre) convertida al formato OpenAPI (antes TC-PLT-14a) | Está en los `paths` del contrato con el mismo método o en el conjunto explícito de la UI `{("GET", "/"), ("GET", "/static/<path:filename>")}` | `tests/integration/platform/test_api_docs.py` |
| PLT-23 | TC-PLT-23b | integration | Cada par ruta-método de los `paths` del contrato (antes TC-PLT-14b) | Existe en `app.url_map` | `tests/integration/platform/test_api_docs.py` |
| PLT-23 | TC-PLT-23c | integration | `app.url_map` | Existe la regla `GET /static/<path:filename>` (la ruta de archivos de la UI, SPEC-UI-02) y no figura en los `paths` del contrato | `tests/integration/platform/test_api_docs.py` |
| PLT-23 | TC-PLT-23d | integration | `app.url_map` (hecho en `07-ui`: se escribió en la task que creó `GET /`, como TC-PRD-06d en `04-tickets`) | Existe la regla `GET /` y no figura en los `paths` del contrato | `tests/integration/platform/test_api_docs.py` |

### Paginación opcional y `q` vacío (re-sincronización del 2026-11-12)

Los helpers se prueban acá sin entidades de negocio; cada área verifica la convención sobre sus listados con casos propios (TC-USR-47*, TC-PRD-29*, TC-TKT-45*). Tabla de prueba para `fetch`: una `MetaData` propia con la tabla `items (id, key)` creada con `create_schema`, y un `statement` `select(...).order_by(key, id)`.

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| PLT-17 | TC-PLT-17a | unit | `page_request("2", "10")` | `PageRequest(page=2, page_size=10)` con `offset == 10` y `limit == 10` | `tests/unit/platform/test_listing.py` |
| PLT-17 | TC-PLT-17b | unit | `listing_json(Page(items=[a, b], page=2, page_size=2, total=5), item_json)` | `{"items": [item_json(a), item_json(b)], "page": 2, "page_size": 2, "total": 5}` con exactamente esas cuatro claves | `tests/unit/platform/test_listing_response.py` |
| PLT-17 | TC-PLT-17c | integration | 5 filas en `items`, `statement` filtrado a 4 de ellas; `fetch(session, statement, PageRequest(2, 3))` | `Page` con `page == 2`, `page_size == 3`, `total == 4` (las que cumplen el filtro) y 1 ítem | `tests/integration/platform/test_paging.py` |
| PLT-18 | TC-PLT-18a | unit | `page_request(None, None)` | `None` (sin paginar) | `tests/unit/platform/test_listing.py` |
| PLT-18 | TC-PLT-18b | integration | `fetch(session, statement, None)` con 5 filas | Una `list` con las 5, en el orden del `statement` | `tests/integration/platform/test_paging.py` |
| PLT-18 | TC-PLT-18c | unit | `listing_json([a, b], item_json)` | `[item_json(a), item_json(b)]` (arreglo plano, no objeto) | `tests/unit/platform/test_listing_response.py` |
| PLT-19 | TC-PLT-19a | unit | `page_request("1", "5")` | `offset == 0`: la página 1 es la primera | `tests/unit/platform/test_listing.py` |
| PLT-20 | TC-PLT-20a | unit | Parametrizado: `page_request(v, None)` con `v` en `"0"`, `"-1"`, `"abc"`, `""`, `"1.5"`, `" 1"`, `"+1"` y `"١"` (dígito no ASCII) | `ValidationError` con `fields == {"page": "invalid"}` | `tests/unit/platform/test_listing.py` |
| PLT-20 | TC-PLT-20b | unit | Parametrizado: `page_request(None, v)` con los mismos valores y `"101"` | `ValidationError` con `fields == {"page_size": "invalid"}` | `tests/unit/platform/test_listing.py` |
| PLT-20 | TC-PLT-20c | unit | `page_request("x", "0")` | `fields == {"page": "invalid", "page_size": "invalid"}` (se informan juntos) | `tests/unit/platform/test_listing.py` |
| PLT-21 | TC-PLT-21a | integration | 7 filas con `key` repetidas (tres con `"a"`, dos con `"b"`, dos con `"c"`); `fetch` de las páginas 1 a 3 con `page_size` 3 | La concatenación de las tres páginas es igual a `fetch(..., None)`: sin solapes ni faltantes, empates resueltos por `id` | `tests/integration/platform/test_paging.py` |
| PLT-22 | TC-PLT-22a | integration | 5 filas; `fetch(session, statement, PageRequest(3, 5))` | `items == []` y `total == 5` | `tests/integration/platform/test_paging.py` |
| PLT-22 | TC-PLT-22b | integration | 5 filas; `fetch` con `PageRequest(page=10**18, page_size=100)` (el `offset` no entra en `INTEGER`) | `items == []`, `total == 5` y sin `OverflowError`; no se ejecuta la consulta de ítems | `tests/integration/platform/test_paging.py` |
| PLT-24 | TC-PLT-24a | unit | `page_request(None, "5")` | `PageRequest(page=1, page_size=5)` | `tests/unit/platform/test_listing.py` |
| PLT-25 | TC-PLT-25a | unit | `page_request("3", None)` | `PageRequest(page=3, page_size=20)` | `tests/unit/platform/test_listing.py` |
| PLT-26 | TC-PLT-26a | unit | `page_request(None, "100")` y `page_request(None, "101")` | El primero es válido (límite); el segundo lanza `ValidationError` `{"page_size": "invalid"}` | `tests/unit/platform/test_listing.py` |
| PLT-27 | TC-PLT-27a | unit | Parametrizado: `search_text(v)` con `v` en `None`, `""`, `"   "` y `"\t"`; y `search_text("ana")` y `search_text(" an a ")` | `None` en los cuatro primeros; `"ana"` y `" an a "` sin cambios (no se recorta un `q` no vacío) | `tests/unit/platform/test_listing.py` |

## Casos borde

- `DATABASE_URL` definida en el entorno y también en los `overrides`: ganan los `overrides` (cubierto en TC-PLT-01b con una variante).
- Requests que no usan la base: no se abre sesión, así que el teardown no hace nada (cubierto en TC-PLT-11a, porque `/health` no llama `get_session()`).
- Rollback de PLT-08 con el manejador del `500` activo (configuración de producción): TC-PLT-08b.
- Identificador no numérico en la URL de un endpoint protegido, sin sesión: TC-PLT-15b.
- `405` conserva el header `Allow`: TC-PLT-15c.
- El `500` no se superpone con las `DomainError` ni con los errores HTTP: TC-PLT-16b y 16c.
- Rutas de la UI fuera del contrato, nombradas una por una (sin comodín): TC-PLT-23a, 23c y 23d.
- `page` o `page_size` vacío, con signo, con espacios, decimal, no ASCII o `0`: TC-PLT-20a y 20b. Los dos inválidos a la vez: TC-PLT-20c.
- Límite de `page_size` (100 válido, 101 inválido): TC-PLT-26a.
- Página más allá de la última y página tan grande que el `offset` no entra en `INTEGER`: TC-PLT-22a y 22b.
- Empates en el orden propio del listado: TC-PLT-21a.
- `q` vacío, solo espacios o tabulador: TC-PLT-27a.

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 1 (TDD, aislamiento) | TC-PLT-04a, 04b |
| RNF 2 (seguridad) | TC-PLT-03a, 10a, 10b, 16a |
| RNF 7 (documentación de la API) | TC-PLT-12a, 12b, 13a, 13b, 15a a 15c, 16a a 16c, 23a a 23d (antes 14a y 14b) |
| RNF 8 (interfaz web servida por la app) | TC-PLT-23c y 23d (las rutas de la UI existen y quedan fuera del contrato) |
| RNF 10 (listados paginables) | TC-PLT-17a a 17c, 18a a 18c, 19a, 20a a 20c, 21a, 22a, 22b, 24a, 25a, 26a y 27a |
