# 00 — Plataforma · Plan de implementación

Specs cubiertas: SPEC-PLT-01 a SPEC-PLT-16 ([spec.md](spec.md)).

## Enfoque

Application factory de Flask (`create_app`) que arma la configuración, el engine de SQLAlchemy, la sesión por request, los comandos de CLI y los blueprints. No hay lógica de negocio: esta área es la base sobre la que se montan las demás.

## Componentes por capa

| Capa | Archivo | Responsabilidad | Specs |
|------|---------|-----------------|-------|
| App | `app/__init__.py` | `create_app(overrides=None)`: carga config, inicializa la base, registra la CLI y los blueprints | PLT-04, 10 |
| App | `app/config.py` | `load_config(environ, overrides, instance_path)` → `dict`. Lanza `ConfigError` si falta `SECRET_KEY` fuera de testing o debug | PLT-01, 02, 03 |
| Infra | `app/db.py` | `init_app(app)`: crea el engine y el `sessionmaker` y los guarda en `app.extensions`. `get_session()`: sesión del request en `flask.g`. Teardown: rollback si hubo excepción y después `close()`. `create_schema(engine, metadata)`. Comando `init-db` | PLT-04 a 09 |
| Dominio | `app/domain/base.py` | `class Base(DeclarativeBase)`. Por ahora sin entidades | PLT-09 |
| Controllers | `app/controllers/health.py` | Blueprint `health` con `GET /health` | PLT-11 |
| Controllers | `app/controllers/api_docs.py` | Blueprint `api_docs`: `GET /openapi.json` sirve `docs/openapi.json`; `GET /docs` devuelve el HTML de Swagger UI | PLT-12, 13 |
| Controllers | `app/controllers/errors.py` | `register_error_handlers(app)` suma a la tabla de `DomainError` (de `01-users`) una segunda tabla `HTTP_ERROR_RESPONSES = {NotFound: "not_found", MethodNotAllowed: "method_not_allowed", InternalServerError: "internal_error"}` con un único manejador que responde `{"error": "<código>"}` | PLT-15, 16 |
| Contrato | `docs/openapi.json` | Contrato OpenAPI 3.1 escrito a mano. Por ahora documenta `/health`, `/openapi.json` y `/docs`. `info.description` explica las respuestas de error comunes a toda la API (`404`, `405` y `500`) | PLT-12, 14, 15, 16 |

Carpetas que se crean vacías (con `__init__.py`) para respetar la estructura de [AGENTS.md](../../AGENTS.md): `app/services/`, `app/repositories/`.

## Configuración

| Clave | Fuente | Valor por defecto |
|-------|--------|-------------------|
| `SECRET_KEY` | env `SECRET_KEY` | testing: valor fijo de test · debug: aleatorio (`secrets.token_hex`) · producción: **obligatorio** |
| `DATABASE_URL` | env `DATABASE_URL` | testing: `sqlite://` (memoria) · resto: `sqlite:///<instance_path>/tickets.db` |
| `SESSION_COOKIE_HTTPONLY` | fijo | `True` |
| `SESSION_COOKIE_SAMESITE` | fijo | `"Lax"` |

Los `overrides` de `create_app` tienen prioridad sobre el entorno. Los tests los usan para no depender de variables globales.

## Decisiones técnicas

| Decisión | Motivo |
|----------|--------|
| El engine y el `sessionmaker` viven en `app.extensions` y no son globales del módulo | Cada instancia de la app tiene su propia base, lo que permite aislar los tests (PLT-04). |
| En testing: `sqlite://` + `StaticPool` + `check_same_thread=False` | Una base en memoria se pierde al cerrar la conexión. `StaticPool` reutiliza una sola conexión durante toda la vida del engine. |
| `PRAGMA foreign_keys = ON` en un listener `connect` del engine | SQLite lo trae desactivado y se configura por conexión (PLT-05). |
| `get_session()` crea la sesión de forma diferida en `g` | Los requests que no tocan la base (por ejemplo `/health`) no abren conexión. |
| Teardown: `rollback()` si `exc` no es `None` y siempre `close()` | Garantiza que no queden transacciones a medias (PLT-07, 08). El commit es responsabilidad del service, nunca del teardown. |
| `create_schema(engine, metadata)` separado del comando de CLI | El comando usa `Base.metadata`. Los tests pasan una `MetaData` propia, sin contaminar el modelo real. |
| Contrato OpenAPI escrito a mano en `docs/openapi.json` (*contract-first*) | Va con spec-as-source: primero se define la interfaz y después el código. No suma dependencias. Se descartaron `flask-smorest` (dos dependencias y contrato derivado del código) y `flasgger` (docstrings YAML en los controllers y soporte parcial de OpenAPI 3). |
| Swagger UI desde jsDelivr (`swagger-ui-dist@5.17.14`), con versión fija | Evita versionar los assets en el repo. La versión fija hace que la UI no cambie sola. |
| Un test compara `app.url_map` con los `paths` del contrato, en los dos sentidos | Es lo que impide que el contrato escrito a mano se desincronice del código (PLT-14). Se ignoran la ruta `static` y los métodos `HEAD` y `OPTIONS`. Las rutas con parámetros de Flask (`<int:ticket_id>`) se convierten al formato OpenAPI (`{ticket_id}`). |
| `create_all()` sin `drop_all()` | `create_all` solo crea las tablas que faltan, así que `init-db` es idempotente (PLT-09). |
| Errores HTTP en JSON (PLT-15): el manejador parte de `error.get_response()` y solo reemplaza el cuerpo por `{"error": "<código>"}` con `mimetype` `application/json` | Conserva el status y los headers que arma werkzeug, por ejemplo `Allow` en un `405`. Un id no numérico (`/categories/abc`) no coincide con el conversor `<int:...>`, así que es un `404` de ruteo y no necesita código propio. El ruteo corre antes que `login_required`, así que el `404` o `405` se responde también sin sesión: no revela nada que el contrato público no diga. |
| Solo `NotFound` y `MethodNotAllowed`, no toda `HTTPException` | Son los dos casos de PLT-15. Un manejador para toda `HTTPException` daría formato a errores que ninguna spec define (hoy no ocurren: `json_body()` usa `get_json(silent=True)`). Si aparece otro error HTTP, se agrega su spec y su fila en la tabla. |
| El `500` genérico (PLT-16) se registra sobre `InternalServerError` y **no** sobre `Exception` | Flask llama al manejador de `InternalServerError` desde `handle_exception`, cuando la excepción ya salió de `full_dispatch_request`: `wsgi_app` guarda el error original y se lo pasa a `ctx.pop(error)`, así que el teardown recibe `exc` y hace el rollback de PLT-08. Un manejador sobre `Exception` corre dentro de `handle_user_exception`: el request termina "manejado", el teardown recibe `exc=None` y no hay rollback explícito. Además capturaría las `HTTPException` (heredan de `Exception`) y convertiría un `404` en `500`. Las `DomainError` se resuelven antes, por su propia clase, así que su tabla no cambia. El cuerpo es fijo, sin el mensaje ni la traza; Flask registra la excepción en el log (`log_exception`). |
| El `500` JSON se ve con la configuración de producción (sin `TESTING` ni `DEBUG`) | Con `TESTING` o `DEBUG`, `PROPAGATE_EXCEPTIONS` vale `True` por defecto y Flask relanza la excepción (al test o al debugger) en lugar de llamar al manejador. Los tests de PLT-16 y TC-PLT-08b usan una app con `PROPAGATE_EXCEPTIONS: False`, que sigue el camino real de producción. TC-PLT-08a mantiene la propagación por defecto. |
| PLT-15 y 16 se documentan en `info.description` del contrato, sin un `404`, `405` o `500` en cada operación | Un `404` o `405` de PLT-15 corresponde a pares ruta-método que justamente **no** están en `paths`, así que no hay operación donde describirlos. El `500` vale igual para todas las operaciones y OpenAPI 3.1 no tiene respuestas globales: repetirlo en cada operación agrega ruido sin información. El test de PLT-14 no cambia porque `paths` no cambia. |

## Dependencias con otras áreas

- Todas las áreas usan `get_session()` y `Base`.
- `01-users` agrega `create-admin` a la CLI y `login_required`, que protege todo salvo `/login`, `/health`, `/openapi.json` y `/docs`.
- Cada área que agregue un endpoint lo documenta antes en `docs/openapi.json`. Si no, el test de PLT-14 falla.

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Tests que comparten estado a través de la base | Fixture `app` nueva por test, con su propio engine en memoria. |
| Sin conexión a internet, `/docs` no carga los assets del CDN | Solo afecta a la UI. `/openapi.json` sigue funcionando y se puede abrir con cualquier visor. |
| Arrancar en producción con una clave insegura | PLT-03: sin `SECRET_KEY`, la app no arranca. |
| Un manejador de errores que se trague el rollback de PLT-08 | TC-PLT-08b verifica el rollback con el manejador del `500` activo (propagación apagada). |
