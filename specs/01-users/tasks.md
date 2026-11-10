# 01 — Usuarios y accesos · Tasks

Estados: `[ ]` pendiente · `[~]` en curso · `[x]` hecha. Cada task es un ciclo TDD con los casos de [test-plan.md](test-plan.md). La tabla está en orden de ejecución: T-USR-27 y 28 se agregaron después (SPEC-USR-22 y 23) y se ubican donde corresponden, sin renumerar las demás.

Las tasks de endpoints (T-USR-18 a 23) agregan la operación a `docs/openapi.json` y la ruta en el mismo ciclo: en la fase roja fallan el test del endpoint y TC-PLT-14b, y en la verde pasan los dos (ver [plan.md](plan.md#decisiones-técnicas)).

| Estado | ID | Task | Specs | Capa | Terminado cuando |
|--------|----|------|-------|------|------------------|
| [ ] | T-USR-01 | `normalize_email` y `@validates("email")` en `User` | USR-03 | Dominio | TC-USR-03a y 03b en verde |
| [ ] | T-USR-02 | `User` con herencia de tabla única, subclases `Admin`, `Representative` y `Client`, y registro `ROLE_CLASSES` | USR-01 | Dominio | TC-USR-01b en verde |
| [ ] | T-USR-03 | `User.deactivate()` | USR-09 | Dominio | TC-USR-09a en verde |
| [ ] | T-USR-04 | Fixtures `schema` y `db_session` en `conftest.py`. `SqlAlchemyUserRepository` con `add` y `get` (devuelve la subclase correcta) y sin métodos de borrado | USR-01, 10 | Repositories / tests | TC-USR-01c y 10b en verde |
| [ ] | T-USR-05 | `find_by_email` con el email normalizado | USR-03 | Repositories | TC-USR-03c en verde |
| [ ] | T-USR-06 | `UNIQUE` en `email`; `add` hace `flush()` y traduce `IntegrityError` a `DuplicateUserError` (crea `app/domain/errors.py`) | USR-04, 08 | Repositories / Dominio | TC-USR-04c y 08c en verde |
| [ ] | T-USR-07 | `list_by_role` ordenado por `id` | USR-11, 12 | Repositories | TC-USR-11a y 12a en verde |
| [ ] | T-USR-08 | Protocolo `PasswordHasher` y `WerkzeugPasswordHasher` | USR-02 | Services | TC-USR-02a en verde |
| [ ] | T-USR-09 | `UserService.create_user`, caso feliz: subclase según el rol, usuario activo, hash, canal por defecto y un commit. Fakes en `tests/unit/users/fakes.py` | USR-01, 02, 06 | Services / tests | TC-USR-01a, 02b, 06a y 06b en verde |
| [ ] | T-USR-10 | Validación del alta con `ValidationError(fields)`: nombre, email, rol y contraseña | USR-05 | Services | TC-USR-05a a 05e en verde |
| [ ] | T-USR-11 | Rechazo de contraseñas de menos de 8 caracteres | USR-19 | Services | TC-USR-19a y 19b en verde |
| [ ] | T-USR-27 | Rechazo de un canal preferido distinto de `mail` o `whatsapp` en el alta (`NOTIFICATION_CHANNELS` en el dominio) | USR-23 | Services / Dominio | TC-USR-23a en verde |
| [ ] | T-USR-12 | Verificación de email duplicado antes de insertar (sin distinguir mayúsculas, incluidos los inactivos) | USR-03, 04 | Services | TC-USR-04a y 04b en verde |
| [ ] | T-USR-13 | `UserService.update_user` (nombre, email y canal), con el propio email permitido y `UserNotFoundError` | USR-07, 08 | Services | TC-USR-07a, 07b, 07c y 08a en verde |
| [ ] | T-USR-28 | Validación de la modificación con `ValidationError(fields)`: nombre vacío, email inválido y canal inválido, sin modificar el usuario ni hacer commit | USR-22, 23 | Services | TC-USR-22a, 22b, 22c y 23b en verde |
| [ ] | T-USR-14 | `UserService.deactivate_user` con rechazo de la autobaja | USR-09, 21 | Services | TC-USR-09b y 21a en verde |
| [ ] | T-USR-15 | `UserService.list_by_role` | USR-11, 12 | Services | TC-USR-11b y 12b en verde |
| [ ] | T-USR-16 | `UserService.authenticate` con `InvalidCredentialsError` genérico | USR-14, 15 | Services | TC-USR-14a, 15a, 15b y 15c en verde |
| [ ] | T-USR-17 | `app/auth.py`: `get_user_service`, `current_user`, `login_required` y `admin_required`. Fixtures `make_user`, `login_as` y `admin_client` | USR-16, 18 | App / tests | TC-USR-16a, 16b, 16c, 18a y 18d en verde |
| [ ] | T-USR-18 | Contrato + `POST /login`, y `register_error_handlers` en `app/controllers/errors.py` | USR-14, 15 | Contrato / Controllers | TC-USR-14b, 14c, 15d, 15e, TC-PLT-14a y 14b en verde |
| [ ] | T-USR-19 | Contrato + `POST /logout` | USR-17 | Contrato / Controllers | TC-USR-17a, 17b, TC-PLT-14a y 14b en verde |
| [ ] | T-USR-20 | Contrato (con `sessionCookie` y los esquemas `User`, `Error` y `ValidationErrorResponse`) + `POST /users` | USR-01, 02, 04, 05, 06, 18, 19, 23 | Contrato / Controllers | TC-USR-01d, 02c, 04d, 05f, 06c, 19c, 23c, TC-USR-18b y 18c para `POST /users`, TC-PLT-14a y 14b en verde |
| [ ] | T-USR-21 | Contrato + `PATCH /users/{user_id}` | USR-07, 08, 18, 22, 23 | Contrato / Controllers | TC-USR-07d, 07e, 08b, 22d, 23d, TC-PLT-14a y 14b en verde |
| [ ] | T-USR-22 | Contrato + `POST /users/{user_id}/deactivate` | USR-09, 10, 18, 21 | Contrato / Controllers | TC-USR-09c, 09d, 10a, 10c, 21b, TC-PLT-14a y 14b en verde |
| [ ] | T-USR-23 | Contrato + `GET /clients` y `GET /representatives` | USR-11, 12, 13, 18 | Contrato / Controllers | TC-USR-11c, 12c, 13a, 18b, 18c (todos los endpoints), TC-PLT-14a y 14b en verde |
| [ ] | T-USR-24 | Test de guarda: toda ruta no pública responde `401` sin sesión | USR-16 | Tests | TC-USR-16d en verde, y en rojo si se quita temporalmente `login_required` de un endpoint |
| [ ] | T-USR-25 | Comando `create-admin` en `app/cli.py`, registrado en `create_app` | USR-20 | App | TC-USR-20a a 20d en verde |
| [ ] | T-USR-26 | Cierre del área: `ruff`, cobertura ≥ 90 %, diagramas sincronizados, README de specs y `MEMORY.md` actualizados | Todas | — | `ruff check`, `ruff format --check` y `pytest --cov=app --cov-fail-under=90` en verde; `diagrams/classes.md` y `diagrams/sequences/01-users.md` coinciden con el código |

Pendiente fuera de esta área: TC-USR-10d (un ticket de un usuario inactivo conserva sus hitos y su historial de estados) se implementa en `04-tickets`.
