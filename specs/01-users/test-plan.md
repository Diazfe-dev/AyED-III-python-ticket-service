# 01 — Usuarios y accesos · Test plan

Cada test cita en su docstring la spec y el caso: `"""SPEC-USR-05 · TC-USR-05a"""`.

Fixtures existentes (`tests/conftest.py`): `app`, `client` y `runner` (ver [00-platform](../00-platform/test-plan.md)).

Fixtures nuevas (`tests/conftest.py`):
- `schema`: crea las tablas de `Base.metadata` en la base en memoria de la `app` del test.
- `db_session`: sesión creada directamente desde el `sessionmaker` de `app.extensions`, **sin** abrir un app context, para que cada request del test client tenga su propia sesión y su teardown (ver riesgos en [plan.md](plan.md#riesgos)). Depende de `schema`.
- `make_user`: fábrica `make_user(role="Client", email=..., password="password1", is_active=True)` que persiste un usuario con `WerkzeugPasswordHasher` y hace commit.
- `login_as`: `login_as(client, user)` guarda `user_id` con `client.session_transaction()`, sin pasar por `POST /login`.
- `admin_client`: `client` con la sesión de un `Admin` creado con `make_user`.

Dobles para tests unitarios (`tests/unit/users/fakes.py`, sin Flask ni base):
- `FakeUserRepository`: diccionario en memoria que asigna ids y busca por email normalizado.
- `FakePasswordHasher`: `hash(p)` devuelve `"hashed:" + p`; `verify` compara con ese formato y registra cada llamada en `verify_calls`; `dummy_hash()` devuelve `hash("dummy-password")`.
- `CommitSpy`: función que cuenta cuántas veces se llamó.

Contraseña válida de referencia en los casos: `"password1"` (9 caracteres).

Re-sincronización del 2026-11-12: casos nuevos para SPEC-USR-27 a 50 (sección [Identidad, activación, contraseñas y listados](#identidad-activación-contraseñas-y-listados-re-sincronización-del-2026-11-12)). Los casos de las specs reemplazadas no se borran ni se renumeran: TC-USR-11a a 11c pasan a TC-USR-34a a 34c, TC-USR-13a a TC-USR-36a y TC-USR-16a a 16d a TC-USR-49c, 49d, 49e y 49a. TC-USR-12a y 12b se reescriben sobre `search` y `list_users` (mismo comportamiento) y TC-USR-18b deja de incluir `GET /clients`. `FakeUserRepository` suma `search` y pierde `list_by_role` (T-USR-42).

## Matriz spec → casos

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| USR-01 | TC-USR-01a | unit | `create_user("Ana", "ana@x.com", "Representative", "password1")` con fakes | Devuelve un `Representative` activo, guardado en el repositorio, y `commit` se llamó una vez | `tests/unit/users/test_user_service.py` |
| USR-01 | TC-USR-01b | unit | Cada par `(rol, clase)` de `ROLE_CLASSES` | La instancia es de esa clase y su `role` es el nombre del rol | `tests/unit/users/test_user.py` |
| USR-01 | TC-USR-01c | integration | `add(Client(...))`, commit y `get(id)` en una sesión nueva | Devuelve una instancia de `Client` con `role == "Client"` | `tests/integration/users/test_user_repository.py` |
| USR-01 | TC-USR-01d | integration | `admin_client` hace `POST /users` con datos válidos | `201` con `id`, `role` y `is_active: true` | `tests/integration/users/test_users_api.py` |
| USR-02 | TC-USR-02a | unit | `WerkzeugPasswordHasher().hash("password1")` | El hash es distinto de la contraseña; `verify(hash, "password1")` es `True` y `verify(hash, "otra-clave")` es `False` | `tests/unit/users/test_passwords.py` |
| USR-02 | TC-USR-02b | unit | `create_user` con `FakePasswordHasher` | `password_hash == "hashed:password1"` y ningún atributo guarda la contraseña en texto plano | `tests/unit/users/test_user_service.py` |
| USR-02 | TC-USR-02c | integration | `POST /users` y lectura de la fila en la base | La respuesta no tiene `password` ni `password_hash`; la columna no es la contraseña y `check_password_hash` la valida | `tests/integration/users/test_users_api.py` |
| USR-03 | TC-USR-03a | unit | `normalize_email("  Ana@X.COM ")` | `"ana@x.com"` | `tests/unit/users/test_user.py` |
| USR-03 | TC-USR-03b | unit | `Client(email=" Ana@X.com ")` | `client.email == "ana@x.com"` | `tests/unit/users/test_user.py` |
| USR-03 | TC-USR-03c | integration | Usuario guardado con `ana@x.com`; `find_by_email(" ANA@x.com ")` | Devuelve ese usuario | `tests/integration/users/test_user_repository.py` |
| USR-04 | TC-USR-04a | unit | Existe `ana@x.com`; alta con `"ANA@x.com "` | Lanza `DuplicateUserError`; no se agrega nada y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-04 | TC-USR-04b | unit | Existe `ana@x.com` inactivo; alta con el mismo email | Lanza `DuplicateUserError` | `tests/unit/users/test_user_service.py` |
| USR-04 | TC-USR-04c | integration | Dos `add` con el mismo email, sin pasar por el service | El segundo lanza `DuplicateUserError` (no `IntegrityError`) | `tests/integration/users/test_user_repository.py` |
| USR-04 | TC-USR-04d | integration | `POST /users` con un email existente en otra combinación de mayúsculas | `409` `{"error": "duplicate_email"}` | `tests/integration/users/test_users_api.py` |
| USR-05 | TC-USR-05a | unit | Alta sin nombre | `ValidationError` con `fields["name"] == "required"` | `tests/unit/users/test_user_service.py` |
| USR-05 | TC-USR-05b | unit | Alta con email `"ana-at-x"` | `ValidationError` con `fields["email"] == "invalid"` | `tests/unit/users/test_user_service.py` |
| USR-05 | TC-USR-05c | unit | Alta con rol `"Superuser"` | `ValidationError` con `fields["role"] == "invalid"` | `tests/unit/users/test_user_service.py` |
| USR-05 | TC-USR-05d | unit | Alta sin contraseña | `ValidationError` con `fields["password"] == "required"` | `tests/unit/users/test_user_service.py` |
| USR-05 | TC-USR-05e | unit | Nombre `"   "`, email vacío, sin rol y sin contraseña | `fields` informa los cuatro campos a la vez; no hay commit | `tests/unit/users/test_user_service.py` |
| USR-05 | TC-USR-05f | integration | `POST /users` con email inválido y sin nombre | `400` `{"error": "validation_error", "fields": {"name": "required", "email": "invalid"}}` | `tests/integration/users/test_users_api.py` |
| USR-06 | TC-USR-06a | unit | Alta sin `preferred_channel` | `preferred_channel == "mail"` | `tests/unit/users/test_user_service.py` |
| USR-06 | TC-USR-06b | unit | Alta con `preferred_channel="whatsapp"` | Se conserva `"whatsapp"` | `tests/unit/users/test_user_service.py` |
| USR-06 | TC-USR-06c | integration | `POST /users` sin `preferred_channel` | La respuesta tiene `preferred_channel: "mail"` | `tests/integration/users/test_users_api.py` |
| USR-07 | TC-USR-07a | unit | `update_user(id, name=..., email=..., preferred_channel=...)` | Los tres datos cambian (email normalizado) y hay un commit | `tests/unit/users/test_user_service.py` |
| USR-07 | TC-USR-07b | unit | `update_user` con el propio email en mayúsculas | No lanza y el email queda normalizado | `tests/unit/users/test_user_service.py` |
| USR-07 | TC-USR-07c | unit | **Reemplazado por TC-USR-26a** (SPEC-USR-26, 2026-11-10): el usuario inexistente tiene spec propia | — | — |
| USR-07 | TC-USR-07d | integration | `PATCH /users/{id}` con `name`, `email`, `preferred_channel` y además `role: "Admin"` | `200` con los datos nuevos; el `role` no cambia | `tests/integration/users/test_users_api.py` |
| USR-07 | TC-USR-07e | integration | **Reemplazado por TC-USR-26c** (SPEC-USR-26, 2026-11-10) | — | — |
| USR-08 | TC-USR-08a | unit | Existen A y B; `update_user(A, email=B.email.upper())` | Lanza `DuplicateUserError` y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-08 | TC-USR-08b | integration | `PATCH /users/{A}` con el email de B | `409` `{"error": "duplicate_email"}` | `tests/integration/users/test_users_api.py` |
| USR-08 | TC-USR-08c | integration | Se cambia el email de un usuario persistido por el de otro y se llama a `add` | Lanza `DuplicateUserError` (carrera cubierta por el `flush`) | `tests/integration/users/test_user_repository.py` |
| USR-09 | TC-USR-09a | unit | `user.deactivate()` | `is_active is False` | `tests/unit/users/test_user.py` |
| USR-09 | TC-USR-09b | unit | `deactivate_user(id, actor=admin)` sobre otro usuario | Queda inactivo, sigue en el repositorio y hay un commit | `tests/unit/users/test_user_service.py` |
| USR-09 | TC-USR-09c | integration | `POST /users/{id}/deactivate` | `200` con `is_active: false` | `tests/integration/users/test_users_api.py` |
| USR-09 | TC-USR-09d | integration | **Reemplazado por TC-USR-26d** (SPEC-USR-26, 2026-11-10) | — | — |
| USR-10 | TC-USR-10a | integration | Baja por API y lectura con `db_session` después de `expire_all()` | La fila existe con el mismo nombre, email, rol y hash | `tests/integration/users/test_users_api.py` |
| USR-10 | TC-USR-10b | integration | Atributos públicos de `SqlAlchemyUserRepository` | No existe ningún método `delete` ni `remove` | `tests/integration/users/test_user_repository.py` |
| USR-10 | TC-USR-10c | integration | Reglas de `app.url_map` que empiezan con `/users`, `/clients` o `/representatives` | Ninguna acepta `DELETE` | `tests/integration/users/test_users_api.py` |
| USR-10 | TC-USR-10d | integration | Ticket de un usuario que después se da de baja (cubierto en `04-tickets`, T-TKT-36) | El ticket, sus hitos y sus `StateChange` siguen existiendo y se pueden leer | `tests/integration/tickets/test_cross_area.py` |
| USR-11 | TC-USR-11a | integration | **Reemplazado por TC-USR-34b** (SPEC-USR-11 reemplazada, 2026-11-12; T-USR-40) | — | — |
| USR-11 | TC-USR-11b | unit | **Reemplazado por TC-USR-34a** (SPEC-USR-11 reemplazada; el test se borra con `list_by_role` en T-USR-42) | — | — |
| USR-11 | TC-USR-11c | integration | **Reemplazado por TC-USR-34c** (SPEC-USR-11 reemplazada; T-USR-50) | — | — |
| USR-12 | TC-USR-12a | integration | Un usuario de cada rol; `search(role="Representative")` (antes `list_by_role`, reescrito en T-USR-40) | Solo devuelve el `Representative` | `tests/integration/users/test_user_repository.py` |
| USR-12 | TC-USR-12b | unit | `list_users(role="Representative")` con fakes (antes `list_by_role`, reescrito en T-USR-42) | Devuelve solo los representantes | `tests/unit/users/test_user_service.py` |
| USR-12 | TC-USR-12c | integration | `GET /representatives` con usuarios de los tres roles | `200` y todos los elementos tienen `role: "Representative"` | `tests/integration/users/test_users_api.py` |
| USR-13 | TC-USR-13a | integration | **Reemplazado por TC-USR-36a** (SPEC-USR-13 reemplazada por SPEC-USR-36; T-USR-50) | — | — |
| USR-14 | TC-USR-14a | unit | Usuario activo; `authenticate(" ANA@x.com ", "password1")` | Devuelve ese usuario | `tests/unit/users/test_user_service.py` |
| USR-14 | TC-USR-14b | integration | `POST /login` con credenciales válidas | `200` `{"id", "name", "email", "role"}`, `session["user_id"]` es el id y una ruta protegida responde `200` | `tests/integration/users/test_auth_api.py` |
| USR-14 | TC-USR-14c | integration | Sesión con una clave previa (`"stale": 1`) y `POST /login` válido | La clave previa ya no está en la sesión | `tests/integration/users/test_auth_api.py` |
| USR-15 | TC-USR-15a | unit | `authenticate` con un email inexistente | Lanza `InvalidCredentialsError` | `tests/unit/users/test_user_service.py` |
| USR-15 | TC-USR-15b | unit | `authenticate` con una contraseña incorrecta | Lanza `InvalidCredentialsError` | `tests/unit/users/test_user_service.py` |
| USR-15 | TC-USR-15c | unit | `authenticate` de un usuario inactivo con la contraseña correcta | Lanza `InvalidCredentialsError` | `tests/unit/users/test_user_service.py` |
| USR-15 | TC-USR-15d | integration | `POST /login` con email inexistente, con contraseña incorrecta y con usuario inactivo | Los tres responden `401` con el mismo cuerpo `{"error": "invalid_credentials"}` y no crean sesión | `tests/integration/users/test_auth_api.py` |
| USR-15 | TC-USR-15e | integration | `POST /login` con cuerpo vacío y sin `password` | `401` `{"error": "invalid_credentials"}` | `tests/integration/users/test_auth_api.py` |
| USR-16 | TC-USR-16a | integration | **Reemplazado por TC-USR-49c** (SPEC-USR-16 reemplazada por SPEC-USR-49, 2026-11-12; T-USR-54) | — | — |
| USR-16 | TC-USR-16b | integration | **Reemplazado por TC-USR-49d** (T-USR-54) | — | — |
| USR-16 | TC-USR-16c | integration | **Reemplazado por TC-USR-49e** (T-USR-54) | — | — |
| USR-16 | TC-USR-16d | integration | **Reemplazado por TC-USR-49a** (T-USR-54) | — | — |
| USR-17 | TC-USR-17a | integration | Login y después `POST /logout` | `204`; un `GET /clients` posterior responde `401` | `tests/integration/users/test_auth_api.py` |
| USR-17 | TC-USR-17b | integration | Login, `POST /logout` y lectura con `client.session_transaction()` | La sesión no tiene `user_id` | `tests/integration/users/test_auth_api.py` |
| USR-18 | TC-USR-18a | integration | Ruta de prueba con `admin_required` y la sesión de un `Client` | `403` `{"error": "forbidden"}` | `tests/integration/users/test_auth.py` |
| USR-18 | TC-USR-18b | integration | Parametrizado por endpoint de gestión (`POST /users`, `PATCH`, `deactivate`, `GET /representatives`) con la sesión de un `Representative`. **Reescrito en T-USR-50**: `GET /clients` sale de la lista, porque el representante ahora recibe `200` (SPEC-USR-32) | `403` en todos | `tests/integration/users/test_users_api.py` |
| USR-18 | TC-USR-18c | integration | Igual que 18b con la sesión de un `Client` | `403` en todos | `tests/integration/users/test_users_api.py` |
| USR-18 | TC-USR-18d | integration | Ruta de prueba con `admin_required` y la sesión de un `Admin` | `200` | `tests/integration/users/test_auth.py` |
| USR-19 | TC-USR-19a | unit | Alta con contraseña de 7 caracteres | `ValidationError` con `fields["password"] == "too_short"` | `tests/unit/users/test_user_service.py` |
| USR-19 | TC-USR-19b | unit | Alta con contraseña de exactamente 8 caracteres | Se crea el usuario (límite) | `tests/unit/users/test_user_service.py` |
| USR-19 | TC-USR-19c | integration | `POST /users` con contraseña de 7 caracteres | `400` con `fields.password == "too_short"` y sin usuario creado | `tests/integration/users/test_users_api.py` |
| USR-20 | TC-USR-20a | integration | `runner.invoke(args=["create-admin", "--name", "Ana", "--email", "ana@x.com"], input="password1\npassword1\n")` | Código 0, mensaje de admin creado y existe un `Admin` activo con ese email | `tests/integration/users/test_cli.py` |
| USR-20 | TC-USR-20b | integration | `create-admin` con un email que ya existe | Código distinto de 0, mensaje de email duplicado y sigue habiendo un solo usuario con ese email | `tests/integration/users/test_cli.py` |
| USR-20 | TC-USR-20c | integration | `create-admin` con contraseña de 7 caracteres | Código distinto de 0 y no se crea ningún usuario | `tests/integration/users/test_cli.py` |
| USR-20 | TC-USR-20d | integration | `create-admin` y después `POST /login` con esas credenciales | `200` con `role: "Admin"` | `tests/integration/users/test_cli.py` |
| USR-20 | TC-USR-20e | integration | `runner.invoke(args=["create-admin", "--name", "Ana", "--email", "ana@x.com", "--password", "password1"])` | Código distinto de 0, mensaje `No such option` y no se crea ningún usuario | `tests/integration/users/test_cli.py` |
| USR-21 | TC-USR-21a | unit | `deactivate_user(admin.id, actor=admin)` | Lanza `SelfDeactivationError`; el admin sigue activo y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-21 | TC-USR-21b | integration | `admin_client` hace `POST /users/{su_propio_id}/deactivate` | `409` `{"error": "self_deactivation"}` | `tests/integration/users/test_users_api.py` |
| USR-22 | TC-USR-22a | unit | `update_user(id, name="   ")` | `ValidationError` con `fields["name"] == "required"`; el nombre no cambia y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-22 | TC-USR-22b | unit | `update_user(id, email="ana-at-x")` | `ValidationError` con `fields["email"] == "invalid"`; el email no cambia y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-22 | TC-USR-22c | unit | `update_user(id, name="", email="")` | `fields` informa `name` y `email` como `"required"` a la vez; el usuario no cambia | `tests/unit/users/test_user_service.py` |
| USR-22 | TC-USR-22d | integration | `PATCH /users/{id}` con `name: ""` y `email: "ana-at-x"` | `400` `{"error": "validation_error", "fields": {"name": "required", "email": "invalid"}}` y la fila no cambia | `tests/integration/users/test_users_api.py` |
| USR-23 | TC-USR-23a | unit | Alta con `preferred_channel="sms"` | `ValidationError` con `fields["preferred_channel"] == "invalid"`; no se agrega nada y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-23 | TC-USR-23b | unit | `update_user(id, preferred_channel="telegram")` | `ValidationError` con `fields["preferred_channel"] == "invalid"`; el canal no cambia y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-23 | TC-USR-23c | integration | `POST /users` con `preferred_channel: "sms"` | `400` con `fields.preferred_channel == "invalid"` y sin usuario creado | `tests/integration/users/test_users_api.py` |
| USR-23 | TC-USR-23d | integration | `PATCH /users/{id}` con `preferred_channel: "sms"` | `400` con `fields.preferred_channel == "invalid"` y el canal no cambia | `tests/integration/users/test_users_api.py` |
| USR-24 | TC-USR-24a | unit | `authenticate("nobody@x.com", "password1")` con `FakePasswordHasher` | Lanza `InvalidCredentialsError` y `verify` se llamó exactamente una vez, con `hasher.dummy_hash()` | `tests/unit/users/test_user_service.py` |
| USR-24 | TC-USR-24b | unit | Usuario inactivo; `authenticate` con su contraseña correcta | Lanza `InvalidCredentialsError` y `verify` se llamó exactamente una vez, con `hasher.dummy_hash()` (no con el hash del usuario) | `tests/unit/users/test_user_service.py` |
| USR-24 | TC-USR-24c | unit | `WerkzeugPasswordHasher().dummy_hash()` en dos instancias | Es un hash de werkzeug (no verifica `"password1"` ni el texto vacío) y es el mismo valor en las dos instancias (se calcula una vez por proceso) | `tests/unit/users/test_passwords.py` |
| USR-25 | TC-USR-25a | unit | `create_user(name=123, email=123, role=1, password=12345678, preferred_channel=["mail"])` | `ValidationError` con los cinco campos en `"invalid"`; no se agrega nada y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-25 | TC-USR-25b | unit | `update_user(id, name=1, email=["ana@x.com"], preferred_channel={"mail": 1})` | `ValidationError` con los tres campos en `"invalid"`; el usuario no cambia y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-25 | TC-USR-25c | unit | `authenticate` con `email=123`, con `password=12345678` y con los dos en listas | Lanza `InvalidCredentialsError` en los tres casos | `tests/unit/users/test_user_service.py` |
| USR-25 | TC-USR-25d | integration | `POST /users` con `name: 123` y `preferred_channel: ["mail"]` | `400` `{"error": "validation_error", "fields": {"name": "invalid", "preferred_channel": "invalid"}}` y sin usuario creado | `tests/integration/users/test_users_api.py` |
| USR-25 | TC-USR-25e | integration | `PATCH /users/{id}` con `email: 123` | `400` con `fields == {"email": "invalid"}` y la fila no cambia | `tests/integration/users/test_users_api.py` |
| USR-25 | TC-USR-25f | integration | `POST /login` con `email: 123` y con `password: ["password1"]` | `401` `{"error": "invalid_credentials"}` en los dos casos y sin sesión | `tests/integration/users/test_auth_api.py` |
| USR-26 | TC-USR-26a | unit | `update_user` con un id inexistente (antes TC-USR-07c) | Lanza `UserNotFoundError` y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-26 | TC-USR-26b | unit | `deactivate_user(999, actor=admin)` | Lanza `UserNotFoundError` y no hay commit | `tests/unit/users/test_user_service.py` |
| USR-26 | TC-USR-26c | integration | `PATCH /users/9999` (antes TC-USR-07e) | `404` `{"error": "user_not_found"}` | `tests/integration/users/test_users_api.py` |
| USR-26 | TC-USR-26d | integration | `POST /users/9999/deactivate` (antes TC-USR-09d) | `404` `{"error": "user_not_found"}` | `tests/integration/users/test_users_api.py` |
| USR-26 | TC-USR-26e | integration | `SqlAlchemyUserRepository.get(2**63)` | Devuelve `None` (no lanza `OverflowError`) | `tests/integration/users/test_user_repository.py` |
| USR-26 | TC-USR-26f | integration | Parametrizado: `PATCH /users/9223372036854775808` y `POST /users/9223372036854775808/deactivate` (`2**63`) | `404` `{"error": "user_not_found"}` en los dos (antes `500`) | `tests/integration/users/test_users_api.py` |

Además, cada task de endpoint deja en verde TC-PLT-14a y 14b (sincronización entre las rutas y el contrato; desde T-PLT-22, TC-PLT-23a y 23b).

### Identidad, activación, contraseñas y listados (re-sincronización del 2026-11-12)

Datos de referencia de los listados: clientes `"ana"` (`ana@x.com`, activa), `"Beto"` (`beto@x.com`, inactivo), `"Ana"` (`otra@x.com`, activa, creada después que `"ana"`) y `"Raúl"` (`raul@mail.com`, activo, rol `Client`); representante `"Rosa"`; admin `"Admin"`. `FakeUserRepository.search` sigue el mismo contrato que el repositorio real: filtra por rol, `is_active` y `q` (con `str.casefold`), ordena por `(name.casefold(), id)` y con ventana devuelve `Page`. Contraseña nueva de referencia: `"newpassword"`.

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| USR-27 | TC-USR-27a | integration | Parametrizado por rol (`Admin`, `Representative`, `Client`): sesión con `login_as`; `GET /me` | `200` con exactamente `{"id", "name", "email", "role"}` del usuario de la sesión (sin `password_hash`, `preferred_channel` ni `is_active`) | `tests/integration/users/test_auth_api.py` |
| USR-28 | TC-USR-28a | unit | Usuario con `is_active=False`; `user.activate()` | `is_active is True` | `tests/unit/users/test_user.py` |
| USR-28 | TC-USR-28b | unit | Usuario inactivo; `activate_user(id)` con fakes | Devuelve el usuario activo y hay un `commit` | `tests/unit/users/test_user_service.py` |
| USR-28 | TC-USR-28c | integration | `admin_client`; `POST /users/{id}/activate` de un usuario inactivo | `200` con la representación de `User` e `is_active: true`; la fila queda activa | `tests/integration/users/test_users_api.py` |
| USR-28 | TC-USR-28d | integration | Usuario dado de baja y reactivado por la API; `POST /login` con sus credenciales | `200`: puede volver a iniciar sesión (antes de reactivarlo, `401` `invalid_credentials`) | `tests/integration/users/test_users_api.py` |
| USR-29 | TC-USR-29a | unit | Usuario activo; `activate_user(id)` | No lanza; sigue activo (idempotente) | `tests/unit/users/test_user_service.py` |
| USR-29 | TC-USR-29b | integration | `POST /users/{id}/activate` de un usuario activo | `200` con `is_active: true` | `tests/integration/users/test_users_api.py` |
| USR-30 | TC-USR-30a | unit | `activate_user(9999)` | Lanza `UserNotFoundError` y no hay `commit` | `tests/unit/users/test_user_service.py` |
| USR-30 | TC-USR-30b | integration | Parametrizado: `POST /users/9999/activate` y `POST /users/9223372036854775808/activate` (`2**63`) | `404` `{"error": "user_not_found"}` en los dos (no `500`) | `tests/integration/users/test_users_api.py` |
| USR-18 | TC-USR-18e | integration | Parametrizado por los endpoints de gestión nuevos (`GET /users`, `POST /users/{id}/activate`, `POST /users/{id}/password` con `{"new_password": "newpassword"}`), con la sesión de un `Representative` y con la de un `Client`, sobre un usuario inactivo | `403` `{"error": "forbidden"}` en todos; el usuario sigue inactivo y su hash no cambia | `tests/integration/users/test_users_api.py` |
| USR-37 | TC-USR-37a | unit | `change_own_password(ana, "password1", "newpassword")` con `FakePasswordHasher` | `password_hash == "hashed:newpassword"` y un `commit` | `tests/unit/users/test_user_service.py` |
| USR-37 | TC-USR-37b | integration | Sesión de `ana`; `POST /me/password` con `{"current_password": "password1", "new_password": "newpassword"}` | `204`; la columna no guarda `"newpassword"` y `check_password_hash` la valida; `POST /login` con la nueva responde `200` y con la anterior `401`; la sesión vigente sigue valiendo (`GET /me` `200`, decisión 12) | `tests/integration/users/test_auth_api.py` |
| USR-38 | TC-USR-38a | unit | `change_own_password(ana, "wrong-pass", "newpassword")` | Lanza `InvalidCurrentPasswordError`; el hash no cambia y no hay `commit` | `tests/unit/users/test_user_service.py` |
| USR-38 | TC-USR-38b | integration | `POST /me/password` con una contraseña actual incorrecta | `400` `{"error": "invalid_current_password"}` (no `401`); el hash no cambia y la sesión sigue valiendo (`GET /me` `200`) | `tests/integration/users/test_auth_api.py` |
| USR-39 | TC-USR-39a | unit | `change_own_password(ana, "password1", "short12")` (7 caracteres) | `ValidationError` con `fields == {"new_password": "too_short"}`; sin `commit` | `tests/unit/users/test_user_service.py` |
| USR-39 | TC-USR-39b | unit | `reset_password(ana.id, "short12")` | `ValidationError` con `fields == {"new_password": "too_short"}`; sin `commit` | `tests/unit/users/test_user_service.py` |
| USR-39 | TC-USR-39c | unit | `change_own_password(ana, "password1", "12345678")` y `reset_password(ana.id, "12345678")` (exactamente 8) | Se guardan las dos (límite) | `tests/unit/users/test_user_service.py` |
| USR-39 | TC-USR-39d | integration | `POST /me/password` y `POST /users/{id}/password` con una contraseña nueva de 7 caracteres | `400` con `fields.new_password == "too_short"` en los dos; el hash no cambia | `tests/integration/users/test_auth_api.py`, `tests/integration/users/test_users_api.py` |
| USR-40 | TC-USR-40a | unit | Parametrizado: `change_own_password(ana, c, n)` con `(None, "newpassword")`, `("password1", None)`, `(123, "newpassword")`, `("password1", ["x"])` y `(None, 5)` | `fields` `{"current_password": "required"}`, `{"new_password": "required"}`, `{"current_password": "invalid"}`, `{"new_password": "invalid"}` y los dos campos juntos; sin `commit` | `tests/unit/users/test_user_service.py` |
| USR-40 | TC-USR-40b | unit | `reset_password(ana.id, None)` y `reset_password(ana.id, 12345678)` | `fields == {"new_password": "required"}` y `{"new_password": "invalid"}`; sin `commit` | `tests/unit/users/test_user_service.py` |
| USR-40 | TC-USR-40c | integration | `POST /me/password` con `{}` y con `{"current_password": 1, "new_password": "newpassword"}`; `POST /users/{id}/password` con `{}` | `400` `validation_error` con `{"current_password": "required", "new_password": "required"}`, `{"current_password": "invalid"}` y `{"new_password": "required"}` | `tests/integration/users/test_auth_api.py`, `tests/integration/users/test_users_api.py` |
| USR-40 | TC-USR-40d | unit | `change_own_password(ana, "wrong-pass", "short12")` | `ValidationError` (`new_password: too_short`), no `InvalidCurrentPasswordError`: el formato se valida antes de verificar la actual; `verify` no se llamó | `tests/unit/users/test_user_service.py` |
| USR-41 | TC-USR-41a | unit | `reset_password(ana.id, "newpassword")` | `password_hash == "hashed:newpassword"`, un `commit`, sin `verify` de la anterior | `tests/unit/users/test_user_service.py` |
| USR-41 | TC-USR-41b | integration | `admin_client`; `POST /users/{ana}/password` con `{"new_password": "newpassword"}` | `204`; `ana` inicia sesión con la nueva (`200`) y no con la anterior (`401`) | `tests/integration/users/test_users_api.py` |
| USR-42 | TC-USR-42a | unit | `reset_password(9999, "newpassword")` | Lanza `UserNotFoundError` y no hay `commit` | `tests/unit/users/test_user_service.py` |
| USR-42 | TC-USR-42b | integration | Parametrizado: `POST /users/9999/password` y `POST /users/9223372036854775808/password` con un cuerpo válido | `404` `{"error": "user_not_found"}` en los dos (no `500`) | `tests/integration/users/test_users_api.py` |
| USR-31 | TC-USR-31a | unit | Un usuario de cada rol, uno inactivo; `list_users()` | Devuelve los cuatro, incluidos el `Admin` y el inactivo | `tests/unit/users/test_user_service.py` |
| USR-31 | TC-USR-31b | integration | Mismos datos; `search()` sin filtros | Devuelve los cuatro | `tests/integration/users/test_user_repository.py` |
| USR-31 | TC-USR-31c | integration | `admin_client`; `GET /users` | `200` con usuarios de los tres roles, activos e inactivos, cada uno con la representación de `User` | `tests/integration/users/test_users_api.py` |
| USR-32 | TC-USR-32a | unit | Datos de referencia; `list_clients(rosa)` | Solo los clientes activos (`"ana"`, `"Ana"`, `"Raúl"`), sin `"Beto"` ni usuarios de otros roles | `tests/unit/users/test_user_service.py` |
| USR-32 | TC-USR-32b | integration | Sesión de `rosa`; `GET /clients` | `200` con los ids de los tres clientes activos | `tests/integration/users/test_users_api.py` |
| USR-33 | TC-USR-33a | integration | Sesión de `rosa`; `GET /clients` | Cada elemento tiene exactamente las claves `{"id", "name"}` | `tests/integration/users/test_users_api.py` |
| USR-33 | TC-USR-33b | integration | Sesión de `rosa`; `GET /clients?page=1&page_size=2` | Cada elemento de `items` tiene exactamente `{"id", "name"}` | `tests/integration/users/test_users_api.py` |
| USR-34 | TC-USR-34a | unit | Datos de referencia; `list_clients(admin)` (antes TC-USR-11b) | Los cuatro clientes, activos e inactivos, solo de rol `Client` | `tests/unit/users/test_user_service.py` |
| USR-34 | TC-USR-34b | integration | Un usuario de cada rol; `search(role="Client")` (antes TC-USR-11a) | Solo devuelve el `Client` | `tests/integration/users/test_user_repository.py` |
| USR-34 | TC-USR-34c | integration | `admin_client`; `GET /clients` con usuarios de los tres roles (antes TC-USR-11c) | `200`; todos los elementos tienen `role: "Client"`, las claves del esquema `User` del contrato y ninguna `password` ni `password_hash` | `tests/integration/users/test_users_api.py` |
| USR-35 | TC-USR-35a | unit | `list_clients(ana)` con un `Client` como actor, con y sin parámetros (incluido `page="x"`) | `PermissionDeniedError` en todos (el rol va antes que el formato, G-01 del plan) | `tests/unit/users/test_user_service.py` |
| USR-35 | TC-USR-35b | integration | `GET /clients` con la sesión de un `Client`; `GET /users` y `GET /representatives` con la de un `Client` y la de un `Representative` | `403` `{"error": "forbidden"}` en todos | `tests/integration/users/test_users_api.py` |
| USR-36 | TC-USR-36a | integration | Un cliente activo y uno inactivo; `admin_client` hace `GET /users`, `GET /clients` y `GET /representatives` (antes TC-USR-13a) | Cada elemento de los tres listados tiene `role` e `is_active` (`true` y `false` donde corresponde) | `tests/integration/users/test_users_api.py` |
| USR-43 | TC-USR-43a | unit | Datos de referencia; `list_users(q="ANA")` y `list_users(q="mail.com")` | `"ana"` y `"Ana"` (por nombre) en el primero; `"Raúl"` (por email) en el segundo | `tests/unit/users/test_user_service.py` |
| USR-43 | TC-USR-43b | integration | Datos de referencia; `search(q="RAÚL")`, `search(q="ana")` y `search(q="OTRA@")` | `"Raúl"` (mayúsculas fuera de ASCII); `"ana"` y `"Ana"`; `"Ana"` por email | `tests/integration/users/test_user_repository.py` |
| USR-43 | TC-USR-43c | integration | `admin_client`; `GET /users?q=ana`, `GET /clients?q=ana` y `GET /representatives?q=ros` | Solo los usuarios cuyo nombre o email contiene el texto, en cada listado | `tests/integration/users/test_users_api.py` |
| USR-43 | TC-USR-43d | integration | Usuarios `"50% off"` y `"5000"`, `"a_b"` y `"axb"`; `search(q="%")` y `search(q="a_b")` | Solo `"50% off"` y solo `"a_b"`: `%` y `_` se buscan literalmente (`autoescape`) | `tests/integration/users/test_user_repository.py` |
| USR-43 | TC-USR-43e | integration | `admin_client`; `GET /users?q=` y `GET /users?q=%20%20` (SPEC-PLT-27) | `200` con todos los usuarios, igual que sin `q` | `tests/integration/users/test_users_api.py` |
| USR-43 | TC-USR-43f | integration | Conexión nueva del engine; `SELECT casefold('RAÚL')` y `SELECT casefold(NULL)` | `'raúl'` y `NULL`: la función está registrada en cada conexión | `tests/integration/platform/test_db.py` |
| USR-44 | TC-USR-44a | unit | Datos de referencia; `list_users(role="Client", is_active="false")` y `is_active="true"` | Solo `"Beto"`; los tres activos | `tests/unit/users/test_user_service.py` |
| USR-44 | TC-USR-44b | integration | `search(is_active=False)`, `search(is_active=True)` y `search(is_active=None)` | Inactivos, activos y todos | `tests/integration/users/test_user_repository.py` |
| USR-44 | TC-USR-44c | integration | `admin_client`; `GET /users?is_active=false`, `GET /clients?is_active=true` y `GET /representatives?is_active=false` | Solo los usuarios con ese estado en cada listado | `tests/integration/users/test_users_api.py` |
| USR-45 | TC-USR-45a | unit | Parametrizado: `bool_query_error(v)` con `v` en `None`, `"true"` y `"false"`; y en `""`, `"True"`, `"1"`, `"yes"` y `"false "` | `None` en los tres primeros; `"invalid"` en el resto. `parse_bool_query("true") is True`, `("false") is False`, `(None) is None` | `tests/unit/platform/test_listing.py` |
| USR-45 | TC-USR-45b | unit | `list_users(is_active="yes")` y `list_users(is_active="yes", page="0")` | `ValidationError` con `{"is_active": "invalid"}` y con `{"is_active": "invalid", "page": "invalid"}` (juntos) | `tests/unit/users/test_user_service.py` |
| USR-45 | TC-USR-45c | integration | `admin_client`; `GET /users?is_active=yes`, `GET /clients?is_active=` y `GET /representatives?is_active=1` | `400` `{"error": "validation_error", "fields": {"is_active": "invalid"}}` en los tres | `tests/integration/users/test_users_api.py` |
| USR-46 | TC-USR-46a | unit | Datos de referencia; `list_clients(rosa, q="ana")` y `list_clients(rosa, q="mail.com")` | `"ana"` y `"Ana"`; `[]` (el representante no busca en el email) | `tests/unit/users/test_user_service.py` |
| USR-46 | TC-USR-46b | integration | Sesión de `rosa`; `GET /clients?q=OTRA`, `GET /clients?q=ana` y `GET /clients?q=beto` | `[]` (`otra` solo está en un email); `"ana"` y `"Ana"`; `[]` (`"Beto"` está inactivo) | `tests/integration/users/test_users_api.py` |
| USR-46 | TC-USR-46c | integration | `search(role="Client", q="otra", search_email=False)` | `[]`; con `search_email=True`, `"Ana"` | `tests/integration/users/test_user_repository.py` |
| USR-47 | TC-USR-47a | unit | Datos de referencia; `list_users(role="Client", page="1")` | Un `Page` con `page == 1`, `page_size == 20` y `total == 4` | `tests/unit/users/test_user_service.py` |
| USR-47 | TC-USR-47b | integration | `admin_client`; `GET /users?page=2&page_size=2`, `GET /clients?page_size=3` y `GET /representatives?page=1` | Objetos `{items, page, page_size, total}` con los valores pedidos o por defecto y el `total` del listado; sin `page` ni `page_size`, arreglo plano (TC-USR-31c) | `tests/integration/users/test_users_api.py` |
| USR-47 | TC-USR-47c | integration | Sesión de `rosa`; `GET /clients?page=1&page_size=1` | `{"items": [<1 cliente activo>], "page": 1, "page_size": 1, "total": 3}` | `tests/integration/users/test_users_api.py` |
| USR-47 | TC-USR-47d | integration | `admin_client`; `GET /users?page=0`, `GET /users?page_size=101` y `GET /clients?page=abc&page_size=0` | `400` `validation_error` con `{"page": "invalid"}`, `{"page_size": "invalid"}` y los dos campos | `tests/integration/users/test_users_api.py` |
| USR-47 | TC-USR-47e | integration | `admin_client`; `GET /users?page=99&page_size=10` | `200` con `items: []` y el `total` real (SPEC-PLT-22) | `tests/integration/users/test_users_api.py` |
| USR-47 | TC-USR-47f | integration | 5 usuarios; `search(window=PageRequest(2, 2))` | `Page` con 2 ítems (el 3.º y el 4.º del orden por nombre) y `total == 5` | `tests/integration/users/test_user_repository.py` |
| USR-48 | TC-USR-48a | integration | Usuarios creados en el orden `"beto"`, `"Ana"`, `"ana"`, `"Carla"`; `search()` | `"Ana"`, `"ana"` (empate de nombre resuelto por `id`), `"beto"`, `"Carla"`: por nombre sin distinguir mayúsculas, no por `id` | `tests/integration/users/test_user_repository.py` |
| USR-48 | TC-USR-48b | unit | Mismos datos con fakes; `list_users()` | El mismo orden que TC-USR-48a | `tests/unit/users/test_user_service.py` |
| USR-48 | TC-USR-48c | integration | Mismos datos; `admin_client` hace `GET /clients`, `GET /representatives` y `GET /users`; y `GET /users?page=1&page_size=2` y `?page=2&page_size=2` | Cada listado ordenado por nombre e `id`; las dos páginas no se solapan ni omiten usuarios (SPEC-PLT-21) | `tests/integration/users/test_users_api.py` |
| USR-49 | TC-USR-49a | integration | Cada par método-ruta de `app.url_map` (sin `HEAD` ni `OPTIONS`) que no está en la lista cerrada `{POST /login, GET /, GET /static/<path:filename>, GET /health, GET /docs, GET /openapi.json}`, con los parámetros en `1` y sin sesión (antes TC-USR-16d) | Todos responden `401` `{"error": "authentication_required"}` | `tests/integration/users/test_route_guard.py` |
| USR-49 | TC-USR-49b | integration | Sin sesión: `POST /login` con cuerpo vacío, `GET /health`, `GET /docs`, `GET /openapi.json`, `GET /static/<archivo existente>` (si 07-ui todavía no creó archivos, se omite) y `GET /` (**pendiente de 07-ui**) | Ninguno responde `{"error": "authentication_required"}` (el login responde su `401` `invalid_credentials`, los demás `200`) | `tests/integration/users/test_route_guard.py` |
| USR-49 | TC-USR-49c | integration | Ruta de prueba con `login_required`, sin sesión (antes TC-USR-16a) | `401` `{"error": "authentication_required"}` | `tests/integration/users/test_auth.py` |
| USR-49 | TC-USR-49d | integration | Misma ruta con la sesión de un usuario que después se dio de baja (antes TC-USR-16b) | `401` | `tests/integration/users/test_auth.py` |
| USR-49 | TC-USR-49e | integration | Misma ruta con `user_id` inexistente en la sesión (antes TC-USR-16c) | `401` | `tests/integration/users/test_auth.py` |
| USR-50 | TC-USR-50a | unit | `list_clients(rosa, is_active="true")`, `list_clients(rosa, is_active="false")` y `list_clients(rosa, is_active="yes")` | `PermissionDeniedError` en los dos primeros (no se ignora el parámetro); `ValidationError` `{"is_active": "invalid"}` en el tercero (el `400` precede al `403`) | `tests/unit/users/test_user_service.py` |
| USR-50 | TC-USR-50b | integration | Sesión de `rosa`; `GET /clients?is_active=true` y `GET /clients?is_active=maybe` | `403` `{"error": "forbidden"}` y `400` `validation_error` con `{"is_active": "invalid"}` | `tests/integration/users/test_users_api.py` |

## Casos borde

- Email duplicado con otra combinación de mayúsculas y espacios: TC-USR-04a y 04d.
- Email duplicado de un usuario inactivo (el email sigue reservado): TC-USR-04b.
- Modificar el email por el propio, en otra combinación de mayúsculas: TC-USR-07b.
- Carrera en la modificación del email (dos usuarios con el mismo email nuevo): TC-USR-08c.
- Contraseña de exactamente 8 caracteres: TC-USR-19b.
- Nombre solo con espacios: TC-USR-05e.
- Login de un usuario inactivo con la contraseña correcta: TC-USR-15c y 15d.
- Cookie vigente de un usuario dado de baja o inexistente: TC-USR-16b y 16c.
- Autobaja del administrador: TC-USR-21a y 21b.
- Claves que `PATCH` no admite (`role`): TC-USR-07d.
- Usuario inexistente en la modificación y en la baja: TC-USR-26a a 26d.
- Id mayor que el entero más grande de SQLite (`2**63`): TC-USR-26e y 26f.
- Modificación con nombre solo con espacios o email vacío: TC-USR-22a y 22c.
- Canal preferido desconocido en el alta y en la modificación: TC-USR-23a a 23d.
- Login con email inexistente o usuario inactivo: igual cantidad de `verify` que un login real (TC-USR-24a y 24b).
- Valores JSON que no son texto (números, listas, objetos): TC-USR-25a a 25f.
- `create-admin` con `--password` en la línea de comandos: TC-USR-20e.
- Reactivar un usuario activo (idempotente), inexistente o fuera de rango: TC-USR-29a, 29b, 30a y 30b.
- Contraseña actual incorrecta: `400` y no `401`, sin cerrar la sesión: TC-USR-38b.
- Contraseña actual incorrecta **y** nueva demasiado corta: gana el formato: TC-USR-40d.
- Contraseña nueva de exactamente 8 caracteres en el cambio y en el restablecimiento: TC-USR-39c.
- Restablecer la contraseña de un usuario inexistente o fuera de rango: TC-USR-42a y 42b.
- El representante no ve clientes inactivos ni el email de ningún cliente, tampoco en la página ni buscando por email: TC-USR-32a, 33a, 33b, 46a a 46c.
- `is_active` del representante: `403` con un valor válido y `400` con uno inválido: TC-USR-50a y 50b.
- `is_active` con mayúsculas, vacío o con espacios: TC-USR-45a y 45c.
- `q` con mayúsculas fuera de ASCII, con `%` o `_`, vacío o solo espacios: TC-USR-43b, 43d y 43e.
- Nombres iguales con distinta capitalización en el orden y en páginas consecutivas: TC-USR-48a y 48c.
- Página más allá de la última: TC-USR-47e.
- Lista cerrada de rutas públicas, también para las rutas de la UI: TC-USR-49a y 49b.

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 2 (autenticación robusta) | TC-USR-02a, 02b, 02c, 14b, 14c, 15a a 15e, 17a, 17b, 18a a 18e, 19a a 19c, 20e, 24a a 24c, 25a a 25f, 27a, 33a, 33b, 35a, 35b, 37a a 42b, 46a a 46c, 49a a 49e, 50a, 50b (16a a 16d reemplazados por 49a y 49c a 49e) |
| RNF 3 (usuarios únicos) | TC-USR-03a a 03c, 04a a 04d, 08a a 08c |
| RNF 5 y 6 (conservación del historial, parcial) | TC-USR-10a, 10b, 10c (TC-USR-10d en `tests/integration/tickets/test_cross_area.py`, hecho en `04-tickets`) |
| RNF 7 (documentación de la API) | TC-PLT-14a y 14b en cada task de endpoint (T-USR-18 a 23); TC-PLT-23a y 23b en T-USR-48 a 53 |
| RNF 10 (listados paginables) | TC-USR-33b, 47a a 47f y 48c |
