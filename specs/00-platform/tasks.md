# 00 — Plataforma · Tasks

Estados: `[ ]` pendiente · `[~]` en curso · `[x]` hecha. Cada task es un ciclo TDD con los casos de [test-plan.md](test-plan.md). T-PLT-14 a 16 se agregaron el 2026-11-10 (SPEC-PLT-15 y 16) sin renumerar las demás.

| Estado | ID | Task | Specs | Capa | Terminado cuando |
|--------|----|------|-------|------|------------------|
| [x] | T-PLT-01 | Carga de configuración desde el entorno y valores por defecto | PLT-01, 02 | App | TC-PLT-01a, 01b y 02a en verde |
| [x] | T-PLT-02 | Validación de `SECRET_KEY` según el modo | PLT-03 | App | TC-PLT-03a y 03b en verde |
| [x] | T-PLT-03 | `create_app` con base en memoria aislada en testing y fixtures `app`/`client` en `conftest.py` | PLT-04 | App / tests | TC-PLT-04a y 04b en verde |
| [x] | T-PLT-04 | Engine con `PRAGMA foreign_keys = ON` | PLT-05 | Infra | TC-PLT-05a y 05b en verde |
| [x] | T-PLT-05 | `get_session()`: una sesión por request | PLT-06 | Infra | TC-PLT-06a y 06b en verde |
| [x] | T-PLT-06 | Teardown: rollback ante una excepción y cierre siempre | PLT-07, 08 | Infra | TC-PLT-07a y 08a en verde |
| [x] | T-PLT-07 | `Base`, `create_schema` y comando `init-db` | PLT-09 | Dominio / Infra | TC-PLT-09a, 09b y 09c en verde |
| [x] | T-PLT-08 | Atributos de la cookie de sesión | PLT-10 | App | TC-PLT-10a y 10b en verde |
| [x] | T-PLT-09 | Blueprint `health` | PLT-11 | Controllers | TC-PLT-11a y 11b en verde |
| [x] | T-PLT-11 | `docs/openapi.json` inicial y `GET /openapi.json` | PLT-12 | Contrato / Controllers | TC-PLT-12a y 12b en verde |
| [x] | T-PLT-12 | `GET /docs` con Swagger UI | PLT-13 | Controllers | TC-PLT-13a y 13b en verde |
| [x] | T-PLT-13 | Test de sincronización entre las rutas de Flask y el contrato | PLT-14 | Tests | TC-PLT-14a y 14b en verde |
| [x] | T-PLT-14 | Respuestas JSON para rutas y métodos que la API no expone: tabla `HTTP_ERROR_RESPONSES` en `app/controllers/errors.py` | PLT-15 | Controllers | TC-PLT-15a, 15b y 15c en verde |
| [x] | T-PLT-15 | `500` JSON genérico sobre `InternalServerError`, sin tragarse las `DomainError` ni las `HTTPException`, y rollback de PLT-08 con el manejador activo. Fixture `unpropagated_app` | PLT-08, 16 | Controllers / tests | TC-PLT-16a, 16b, 16c y 08b en verde, y TC-PLT-08a sigue en verde |
| [x] | T-PLT-16 | Contrato (`info.description` con los errores comunes) y cierre: `ruff`, cobertura ≥ 90 % y `MEMORY.md` | PLT-15, 16 | Contrato | TC-PLT-14a y 14b siguen en verde; `ruff check`, `ruff format --check` y `pytest --cov=app --cov-fail-under=90` en verde |
| [x] | T-PLT-10 | Cierre del área: `ruff`, cobertura ≥ 90 % y README de specs actualizado | Todas | — | `ruff check`, `ruff format --check` y `pytest --cov=app --cov-fail-under=90` en verde |
