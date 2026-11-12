# 00 — Plataforma · Plan de implementación

Specs cubiertas: SPEC-PLT-01 a SPEC-PLT-27 ([spec.md](spec.md)). SPEC-PLT-14 está reemplazada por SPEC-PLT-23 (2026-11-12). RNF: 1, 2, 7, 8 (rutas de la UI fuera del contrato) y 10 (paginación).

> **Re-sincronización del 2026-11-12** (nueva área [07-ui](../07-ui/spec.md)): agrega la convención común de paginación opcional y de `q` vacío (SPEC-PLT-17 a 22 y 24 a 27) como helpers compartidos por los listados de 01 a 04, y rehace el test de paridad con el contrato para SPEC-PLT-23. Ver [Paginación y búsqueda](#paginación-y-búsqueda-2026-11-12) y las tasks T-PLT-17 a 24. Esta área **no** implementa `GET /` ni los archivos de la UI (son de 07-ui); solo los excluye del contrato.

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
| Un test compara `app.url_map` con los `paths` del contrato, en los dos sentidos | **Desde el 2026-11-12 rige SPEC-PLT-23** (ver [Paginación y búsqueda](#paginación-y-búsqueda-2026-11-12)): el test ya no ignora `static` por nombre, sino que compara contra el contrato más las rutas de la UI. Texto original: es lo que impide que el contrato escrito a mano se desincronice del código (PLT-14). Se ignoran la ruta `static` y los métodos `HEAD` y `OPTIONS`. Las rutas con parámetros de Flask (`<int:ticket_id>`) se convierten al formato OpenAPI (`{ticket_id}`). |
| `create_all()` sin `drop_all()` | `create_all` solo crea las tablas que faltan, así que `init-db` es idempotente (PLT-09). |
| Errores HTTP en JSON (PLT-15): el manejador parte de `error.get_response()` y solo reemplaza el cuerpo por `{"error": "<código>"}` con `mimetype` `application/json` | Conserva el status y los headers que arma werkzeug, por ejemplo `Allow` en un `405`. Un id no numérico (`/categories/abc`) no coincide con el conversor `<int:...>`, así que es un `404` de ruteo y no necesita código propio. El ruteo corre antes que `login_required`, así que el `404` o `405` se responde también sin sesión: no revela nada que el contrato público no diga. |
| Solo `NotFound` y `MethodNotAllowed`, no toda `HTTPException` | Son los dos casos de PLT-15. Un manejador para toda `HTTPException` daría formato a errores que ninguna spec define (hoy no ocurren: `json_body()` usa `get_json(silent=True)`). Si aparece otro error HTTP, se agrega su spec y su fila en la tabla. |
| El `500` genérico (PLT-16) se registra sobre `InternalServerError` y **no** sobre `Exception` | Flask llama al manejador de `InternalServerError` desde `handle_exception`, cuando la excepción ya salió de `full_dispatch_request`: `wsgi_app` guarda el error original y se lo pasa a `ctx.pop(error)`, así que el teardown recibe `exc` y hace el rollback de PLT-08. Un manejador sobre `Exception` corre dentro de `handle_user_exception`: el request termina "manejado", el teardown recibe `exc=None` y no hay rollback explícito. Además capturaría las `HTTPException` (heredan de `Exception`) y convertiría un `404` en `500`. Las `DomainError` se resuelven antes, por su propia clase, así que su tabla no cambia. El cuerpo es fijo, sin el mensaje ni la traza; Flask registra la excepción en el log (`log_exception`). |
| El `500` JSON se ve con la configuración de producción (sin `TESTING` ni `DEBUG`) | Con `TESTING` o `DEBUG`, `PROPAGATE_EXCEPTIONS` vale `True` por defecto y Flask relanza la excepción (al test o al debugger) en lugar de llamar al manejador. Los tests de PLT-16 y TC-PLT-08b usan una app con `PROPAGATE_EXCEPTIONS: False`, que sigue el camino real de producción. TC-PLT-08a mantiene la propagación por defecto. |
| PLT-15 y 16 se documentan en `info.description` del contrato, sin un `404`, `405` o `500` en cada operación | Un `404` o `405` de PLT-15 corresponde a pares ruta-método que justamente **no** están en `paths`, así que no hay operación donde describirlos. El `500` vale igual para todas las operaciones y OpenAPI 3.1 no tiene respuestas globales: repetirlo en cada operación agrega ruido sin información. El test de PLT-14 no cambia porque `paths` no cambia. |

## Paginación y búsqueda (2026-11-12)

### Componentes por capa

| Capa | Archivo | Responsabilidad | Specs |
|------|---------|-----------------|-------|
| Dominio | `app/domain/paging.py` (nuevo) | `PageRequest(page, page_size)` (propiedades `offset` y `limit`) y `Page(items, page, page_size, total)`, dataclasses congeladas sin SQLAlchemy. Constantes `DEFAULT_PAGE_SIZE = 20` y `MAX_PAGE_SIZE = 100` | PLT-17, 19, 25, 26 |
| Services | `app/services/listing.py` (nuevo) | `page_request(page, page_size) -> PageRequest \| None` (lee el texto del query string, aplica los valores por defecto y lanza `ValidationError` con los campos inválidos juntos) y `search_text(q) -> str \| None` (blanco → `None`). 01-users suma acá el lector de `is_active` (`true`/`false`) | PLT-17 a 20, 24 a 27 |
| Repositories | `app/repositories/paging.py` (nuevo) | `fetch(session, statement, window) -> list \| Page`: sin ventana devuelve la lista; con ventana cuenta el total sobre el mismo `statement` (sin `ORDER BY`, como subconsulta) y trae la página con `limit`/`offset` | PLT-17, 18, 21, 22 |
| Controllers | `app/controllers/listing.py` (nuevo) | `listing_json(result, item_json)`: lista → arreglo plano; `Page` → `{"items", "page", "page_size", "total"}` | PLT-17, 18 |
| Contrato | `docs/openapi.json` | Parámetros reutilizables `Page`, `PageSize` y `Q`; la convención en `info.description`. Cada área declara el esquema de página de su listado (`UserPage`, `ClientSummaryPage`, `ProductPage`, `TicketPage`) y la respuesta `200` como `oneOf` arreglo / página | PLT-17 a 22, 24 a 27, RNF 7 |
| Tests | `tests/integration/platform/test_api_docs.py` | El test de paridad pasa de SPEC-PLT-14 a SPEC-PLT-23: `url_map` = `paths` del contrato ∪ `{GET /, GET /static/<path:filename>}` | PLT-23 |

### Flujo de un listado paginable

1. El controller lee `request.args` y pasa al service los valores **crudos** (`page`, `page_size`, `q`, filtros), sin convertir.
2. El service valida todo el formato junto (`page_request`, filtros del área) → `400`; recién después aplica las reglas de rol (`403`, SPEC-TKT-48 y USR-50) y las de existencia.
3. El service llama al repositorio con los filtros ya convertidos y la ventana (`PageRequest` o `None`).
4. El repositorio arma su `statement` con su orden propio y el `id` como último criterio (SPEC-PLT-21) y llama a `fetch`.
5. El controller responde `listing_json(resultado, <serializador>)`. Que la respuesta sea arreglo o página lo decide un solo lugar: `page_request` devuelve `None` cuando no llega ninguno de los dos parámetros (SPEC-PLT-18).

### Decisiones técnicas

| Decisión | Motivo y alternativas descartadas |
|----------|-----------------------------------|
| `PageRequest` y `Page` viven en `app/domain/paging.py` | Son objetos de valor sin SQLAlchemy que usan los services (validan y devuelven) y los repositorios (paginan): el dominio es la única capa que todas pueden importar sin romper `controllers → services → domain` y `services → repositories`. Se descartaron `app/services/` (el repositorio importaría un service: dirección prohibida) y `app/repositories/` (los services y los fakes dependerían de un módulo de infraestructura). |
| La validación de `page`, `page_size` y `q` es del service (`app/services/listing.py`), no del controller | Mismo criterio que `category_id` en `GET /products`: el controller no valida. Así los tests unitarios con fakes cubren el `400` y la precedencia `400` → `403` (SPEC-TKT-48, USR-50) sin Flask. Se descartó un decorador de controller que parsee la paginación (sacaría el `400` del orden de validación del service). |
| Módulo nuevo `listing.py` y no `validation.py` | `validation.py` lo editan muchas tasks de varias áreas; un módulo propio deja las tasks de paginación en archivos disjuntos. `listing.py` reutiliza `INVALID` y `raise_if_invalid` de `validation.py`. |
| Un valor válido es texto de dígitos ASCII mayor que 0 (`"007"` vale 7); signo, espacios, decimales, dígitos no ASCII y vacío son `invalid` | SPEC-PLT-20 ("entero positivo") leído como en `id_error`. El query string siempre trae texto. |
| Un `page` válido pero enorme se acota a `10**18` antes de construir el `PageRequest`, y `fetch` no consulta los ítems si el `offset` no entra en `INTEGER` | SPEC-PLT-22: una página más allá de la última es `items` vacío con el `total` real, no un `400` ni un `500` (`OverflowError` de `sqlite3`, errores a evitar en Engram `tp-final/pitfall/*`). El acotado evita el límite de conversión de `int()` (4300 dígitos). Se descartó rechazar páginas grandes con `400`: SPEC-PLT-20 solo rechaza lo que no es un entero positivo. |
| El `total` se cuenta con `select(func.count()).select_from(statement.order_by(None).subquery())` sobre el mismo `statement` filtrado | Un solo lugar define los filtros del listado, así el `total` no puede desincronizarse de los ítems (SPEC-PLT-17: "total de resultados que cumplen los filtros"). Dos consultas por página; se descartó `COUNT(*) OVER ()` (repite el total en cada fila y no da el total cuando la página está vacía, SPEC-PLT-22). |
| `fetch` no ordena: cada repositorio termina su `ORDER BY` con el `id` (en el mismo sentido) | El orden propio es del listado (nombre, fecha); el desempate por `id` es lo que garantiza SPEC-PLT-21. TC-PLT-21a lo prueba con empates; cada área lo prueba sobre su listado. |
| `listing_json` decide arreglo o página por el tipo del resultado (`Page` o lista) | La regla "sin `page` ni `page_size`, arreglo plano" (SPEC-PLT-18) queda en `page_request`; el controller no vuelve a mirar `request.args`. Se descartó que el controller ramifique por los parámetros (duplicaría la regla). |
| `search_text` no recorta un `q` que no está en blanco | SPEC-PLT-27 solo define el `q` en blanco; recortar uno con contenido sería comportamiento sin spec. La búsqueda sin distinguir mayúsculas de cada área usa `casefold` (ver [01-users](../01-users/plan.md#re-sincronización-del-2026-11-12)). |
| Contrato: parámetros reutilizables en `components.parameters` y un esquema de página por listado, con la respuesta `200` como `oneOf` `[arreglo, página]` | OpenAPI 3.1 no tiene esquemas genéricos; un `Page` con `items: {}` no documentaría el tipo de los ítems. Los parámetros se suben primero (T-PLT-21, sin rutas nuevas, no rompe la paridad) y cada área los referencia en la task de su listado. |
| SPEC-PLT-23: el test de paridad compara con un conjunto **explícito** de rutas de la UI y deja de ignorar el endpoint `static` por nombre | La decisión 9 de la spec pide excluirlas "de forma explícita y exacta (sin comodines)". `GET /static/<path:filename>` ya existe (Flask la registra con `Flask(__name__)` y `app/static`); `GET /` llega con 07-ui, así que su caso (TC-PLT-23d) queda pendiente de esa área. Sin esa task, TC-PLT-23a ya pasa porque 23a solo exige que cada ruta expuesta esté en el contrato o en el conjunto de la UI. |
| Las tasks de endpoints nuevos agregan la operación al contrato **y** la ruta en el mismo ciclo (como desde 01-users); las de parámetros nuevos sobre rutas existentes pueden ir antes | SPEC-PLT-23 exige que toda operación del contrato exista en la app (TC-PLT-23b), así que una task de contrato con un `path` nuevo antes de su ruta rompería la suite. Los componentes reutilizables sí van en tasks propias, antes (T-PLT-21). |

### Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Un listado ordena sin `id` al final y las páginas se solapan con empates | Casos de orden con empates en cada área (TC-USR-48*, TC-PRD-29*, TC-TKT-45*) además de TC-PLT-21a. |
| La subconsulta del `count` arrastra opciones de carga (`selectinload`) o `ORDER BY` y falla o es lenta | `order_by(None)` antes de la subconsulta; las opciones de carga no se aplican en subconsultas. TC-PLT-17c usa un `statement` con filtro. |
| Un área devuelve el arreglo cuando llegó solo `page_size` (o la página cuando no llegó ninguno) | `page_request` es el único que decide (TC-PLT-18a, 24a y 25a) y cada área tiene un caso HTTP con cada combinación. |

## Dependencias con otras áreas

- Todas las áreas usan `get_session()` y `Base`.
- `01-users` agrega `create-admin` a la CLI y `login_required`, que protege todo salvo las rutas públicas de SPEC-USR-49 (`POST /login`, `GET /`, `GET /static/<ruta>`, `GET /health`, `GET /docs` y `GET /openapi.json`).
- Cada área que agregue un endpoint lo documenta en `docs/openapi.json` en el mismo ciclo que la ruta. Si no, el test de SPEC-PLT-23 (antes PLT-14) falla.
- `01-users`, `03-products` y `04-tickets` usan `page_request`, `search_text`, `fetch` y `listing_json` para SPEC-USR-47, PRD-29 y TKT-45; `02-product-types` usa `search_text` (SPEC-PTY-21 a 23, sin paginar). `01-users` suma a `app/services/listing.py` el lector de `is_active` y a `app/db.py` la función SQL `casefold`.
- `07-ui` crea `GET /` y completa TC-PLT-23d.

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Tests que comparten estado a través de la base | Fixture `app` nueva por test, con su propio engine en memoria. |
| Sin conexión a internet, `/docs` no carga los assets del CDN | Solo afecta a la UI. `/openapi.json` sigue funcionando y se puede abrir con cualquier visor. |
| Arrancar en producción con una clave insegura | PLT-03: sin `SECRET_KEY`, la app no arranca. |
| Un manejador de errores que se trague el rollback de PLT-08 | TC-PLT-08b verifica el rollback con el manejador del `500` activo (propagación apagada). |
