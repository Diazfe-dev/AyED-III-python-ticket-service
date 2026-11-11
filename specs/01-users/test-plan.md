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
| USR-11 | TC-USR-11a | integration | Un usuario de cada rol; `list_by_role("Client")` | Solo devuelve el `Client` | `tests/integration/users/test_user_repository.py` |
| USR-11 | TC-USR-11b | unit | `list_by_role("Client")` con fakes | Devuelve solo los clientes del repositorio | `tests/unit/users/test_user_service.py` |
| USR-11 | TC-USR-11c | integration | `admin_client` hace `GET /clients` con usuarios de los tres roles | `200` y todos los elementos tienen `role: "Client"` | `tests/integration/users/test_users_api.py` |
| USR-12 | TC-USR-12a | integration | Un usuario de cada rol; `list_by_role("Representative")` | Solo devuelve el `Representative` | `tests/integration/users/test_user_repository.py` |
| USR-12 | TC-USR-12b | unit | `list_by_role("Representative")` con fakes | Devuelve solo los representantes | `tests/unit/users/test_user_service.py` |
| USR-12 | TC-USR-12c | integration | `GET /representatives` con usuarios de los tres roles | `200` y todos los elementos tienen `role: "Representative"` | `tests/integration/users/test_users_api.py` |
| USR-13 | TC-USR-13a | integration | Un cliente activo y uno inactivo; `GET /clients` | Aparecen los dos, cada uno con `role` e `is_active` (`true` y `false`) | `tests/integration/users/test_users_api.py` |
| USR-14 | TC-USR-14a | unit | Usuario activo; `authenticate(" ANA@x.com ", "password1")` | Devuelve ese usuario | `tests/unit/users/test_user_service.py` |
| USR-14 | TC-USR-14b | integration | `POST /login` con credenciales válidas | `200` `{"id", "name", "email", "role"}`, `session["user_id"]` es el id y una ruta protegida responde `200` | `tests/integration/users/test_auth_api.py` |
| USR-14 | TC-USR-14c | integration | Sesión con una clave previa (`"stale": 1`) y `POST /login` válido | La clave previa ya no está en la sesión | `tests/integration/users/test_auth_api.py` |
| USR-15 | TC-USR-15a | unit | `authenticate` con un email inexistente | Lanza `InvalidCredentialsError` | `tests/unit/users/test_user_service.py` |
| USR-15 | TC-USR-15b | unit | `authenticate` con una contraseña incorrecta | Lanza `InvalidCredentialsError` | `tests/unit/users/test_user_service.py` |
| USR-15 | TC-USR-15c | unit | `authenticate` de un usuario inactivo con la contraseña correcta | Lanza `InvalidCredentialsError` | `tests/unit/users/test_user_service.py` |
| USR-15 | TC-USR-15d | integration | `POST /login` con email inexistente, con contraseña incorrecta y con usuario inactivo | Los tres responden `401` con el mismo cuerpo `{"error": "invalid_credentials"}` y no crean sesión | `tests/integration/users/test_auth_api.py` |
| USR-15 | TC-USR-15e | integration | `POST /login` con cuerpo vacío y sin `password` | `401` `{"error": "invalid_credentials"}` | `tests/integration/users/test_auth_api.py` |
| USR-16 | TC-USR-16a | integration | Ruta de prueba con `login_required`, registrada en la app del fixture, sin sesión | `401` `{"error": "authentication_required"}` | `tests/integration/users/test_auth.py` |
| USR-16 | TC-USR-16b | integration | Misma ruta con la sesión de un usuario que después se dio de baja | `401` | `tests/integration/users/test_auth.py` |
| USR-16 | TC-USR-16c | integration | Misma ruta con `user_id` inexistente en la sesión | `401` | `tests/integration/users/test_auth.py` |
| USR-16 | TC-USR-16d | integration | Cada par ruta-método de `app.url_map` fuera de la lista pública, con los parámetros en `1` y sin sesión | Todos responden `401` | `tests/integration/users/test_route_guard.py` |
| USR-17 | TC-USR-17a | integration | Login y después `POST /logout` | `204`; un `GET /clients` posterior responde `401` | `tests/integration/users/test_auth_api.py` |
| USR-17 | TC-USR-17b | integration | Login, `POST /logout` y lectura con `client.session_transaction()` | La sesión no tiene `user_id` | `tests/integration/users/test_auth_api.py` |
| USR-18 | TC-USR-18a | integration | Ruta de prueba con `admin_required` y la sesión de un `Client` | `403` `{"error": "forbidden"}` | `tests/integration/users/test_auth.py` |
| USR-18 | TC-USR-18b | integration | Parametrizado por endpoint de gestión (`POST /users`, `PATCH`, `deactivate`, `GET /clients`, `GET /representatives`) con la sesión de un `Representative` | `403` en todos | `tests/integration/users/test_users_api.py` |
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

Además, cada task de endpoint deja en verde TC-PLT-14a y 14b (sincronización entre las rutas y el contrato).

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

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 2 (autenticación robusta) | TC-USR-02a, 02b, 02c, 14b, 14c, 15a a 15e, 16a a 16d, 17a, 17b, 18a a 18d, 19a a 19c, 20e, 24a a 24c, 25a a 25f |
| RNF 3 (usuarios únicos) | TC-USR-03a a 03c, 04a a 04d, 08a a 08c |
| RNF 5 y 6 (conservación del historial, parcial) | TC-USR-10a, 10b, 10c (TC-USR-10d en `tests/integration/tickets/test_cross_area.py`, hecho en `04-tickets`) |
| RNF 7 (documentación de la API) | TC-PLT-14a y 14b en cada task de endpoint (T-USR-18 a 23) |
