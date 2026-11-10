# 00 — Plataforma · Plan de implementación

Specs cubiertas: SPEC-PLT-01 a SPEC-PLT-11 ([spec.md](spec.md)).

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
| `create_all()` sin `drop_all()` | `create_all` solo crea las tablas que faltan, así que `init-db` es idempotente (PLT-09). |

## Dependencias con otras áreas

- Todas las áreas usan `get_session()` y `Base`.
- `01-users` agrega `create-admin` a la CLI y `login_required`, que protege todo salvo `/login` y `/health`.

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Tests que comparten estado a través de la base | Fixture `app` nueva por test, con su propio engine en memoria. |
| Arrancar en producción con una clave insegura | PLT-03: sin `SECRET_KEY`, la app no arranca. |
