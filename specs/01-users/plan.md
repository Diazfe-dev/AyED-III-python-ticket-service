# 01 — Usuarios y accesos · Plan de implementación

Specs cubiertas: SPEC-USR-01 a SPEC-USR-26 ([spec.md](spec.md)). RNF: 2 (autenticación), 3 (usuarios únicos) y 7 (API documentada).

## Enfoque

Primera área de negocio. Agrega la entidad `User` con sus tres roles, el caso de uso `UserService` (alta, modificación, baja lógica, listados y autenticación), su repositorio sobre SQLAlchemy, los decoradores de autenticación y autorización, los endpoints JSON de login y de gestión de usuarios, y el comando `create-admin`. Se monta sobre la base de `00-platform`: `create_app`, `get_session()`, `Base`, `create_schema` y el contrato `docs/openapi.json`.

## Componentes por capa

| Capa | Archivo | Responsabilidad | Specs |
|------|---------|-----------------|-------|
| Dominio | `app/domain/users.py` | `User` mapeado con herencia de tabla única (tabla `users`, discriminador `role`) y las subclases `Admin`, `Representative` y `Client`. `normalize_email(email)` y un `@validates("email")` que normaliza al asignar. `deactivate()`. Registro `ROLE_CLASSES = {"Admin": Admin, ...}`, canales válidos `NOTIFICATION_CHANNELS = {"mail", "whatsapp"}` y `DEFAULT_CHANNEL = "mail"` | USR-01, 03, 06, 09, 23 |
| Dominio | `app/domain/errors.py` | `DomainError` y las subclases `ValidationError(fields)`, `DuplicateUserError`, `InvalidCredentialsError`, `UserNotFoundError` y `SelfDeactivationError` | USR-04, 05, 08, 15, 19, 21, 22, 23 |
| Services | `app/services/passwords.py` | Protocolo `PasswordHasher` (`hash(password) -> str`, `verify(password_hash, password) -> bool` y `dummy_hash() -> str`) y su implementación `WerkzeugPasswordHasher`, que envuelve `generate_password_hash` y `check_password_hash` y calcula el hash de relleno una sola vez por proceso | USR-02, 14, 15, 24 |
| Services | `app/services/user_service.py` | `UserService(repository, hasher, commit)`: `create_user`, `update_user`, `deactivate_user`, `list_by_role` y `authenticate`. Valida los datos del alta y de la modificación (incluido el tipo de dato), verifica el email duplicado antes de insertar y, en el login, verifica contra el hash de relleno cuando el email no existe o el usuario está inactivo | USR-01 a 09, 11, 12, 14, 15, 19, 21 a 25 |
| Repositories | `app/repositories/user_repository.py` | `SqlAlchemyUserRepository(session)`: `add`, `get`, `find_by_email` y `list_by_role`. `add` hace `flush()` y traduce `IntegrityError` a `DuplicateUserError`. `get` devuelve `None` para un id que SQLite no puede guardar (`fits_integer_column`) | USR-01, 03, 04, 08, 11, 12, 26 |
| App | `app/auth.py` | `get_user_service()` (arma el service del request con `get_session()`), `current_user()` (lee `session["user_id"]`; un usuario inexistente o inactivo cuenta como sin sesión), y los decoradores `login_required` (`401`) y `admin_required` (`403`) | USR-16, 18 |
| Controllers | `app/controllers/auth.py` | Blueprint `auth`: `POST /login` y `POST /logout` | USR-14, 15, 17 |
| Controllers | `app/controllers/users.py` | Blueprint `users`: `POST /users`, `PATCH /users/<int:user_id>`, `POST /users/<int:user_id>/deactivate`, `GET /clients` y `GET /representatives` | USR-01, 04 a 09, 11 a 13, 18, 19, 21 a 23 |
| Controllers | `app/controllers/errors.py` | `register_error_handlers(app)`: traduce cada `DomainError` a su respuesta HTTP con una tabla `{clase: (status, código)}`, sin `if`/`elif` | USR-04, 05, 08, 15, 21, 22, 23 |
| App | `app/cli.py` | Comando `create-admin` (`@with_appcontext`) que usa `get_user_service()` y pide la contraseña con `click.prompt` oculto y confirmado | USR-20 |
| App | `app/__init__.py` | Registra los blueprints `auth` y `users`, los manejadores de errores y el comando `create-admin` | — |
| Contrato | `docs/openapi.json` | Las 7 operaciones nuevas, el esquema de seguridad por cookie y los esquemas `User`, `Error` y `ValidationErrorResponse` | RNF 7 |

## Modelo de datos

Tabla `users` (herencia de tabla única; `Admin`, `Representative` y `Client` no tienen tabla propia):

| Columna | Tipo | Restricciones | Notas |
|---------|------|---------------|-------|
| `id` | `Integer` | PK | |
| `role` | `String(20)` | `NOT NULL` | Discriminador (`polymorphic_on`). Valores: `"Admin"`, `"Representative"`, `"Client"` (`polymorphic_identity` de cada subclase) |
| `name` | `String(120)` | `NOT NULL` | |
| `email` | `String(254)` | `NOT NULL`, `UNIQUE` | Siempre normalizado (`strip().lower()`) por el `@validates` del dominio |
| `password_hash` | `String(255)` | `NOT NULL` | Nunca la contraseña en texto plano |
| `preferred_channel` | `String(20)` | `NOT NULL`, `default="mail"` | Solo `"mail"` o `"whatsapp"`, validado por el service (SPEC-USR-23) |
| `is_active` | `Boolean` | `NOT NULL`, `default=True` | Baja lógica |

El diagrama de clases no tiene `phone` ni otros atributos de contacto, así que no se agregan. `assigned_tickets` y `tickets` se agregan en `04-tickets`, cuando exista `Ticket`.

## Interfaz HTTP

Todas las respuestas son JSON. Representación de un usuario (`User` en el contrato): `{"id", "name", "email", "role", "preferred_channel", "is_active"}`. Nunca incluye `password_hash`.

| Método y ruta | Acceso | Éxito | Errores | Specs |
|---------------|--------|-------|---------|-------|
| `POST /login` | público | `200` `{"id", "name", "email", "role"}` | `401` `invalid_credentials` | USR-14, 15 |
| `POST /logout` | sesión | `204` sin cuerpo | `401` | USR-17 |
| `POST /users` | admin | `201` `User` | `400`, `401`, `403`, `409` `duplicate_email` | USR-01 a 06, 18, 19, 23 |
| `PATCH /users/{user_id}` | admin | `200` `User` | `400`, `401`, `403`, `404`, `409` `duplicate_email` | USR-07, 08, 18, 22, 23, 26 |
| `POST /users/{user_id}/deactivate` | admin | `200` `User` (con `is_active: false`) | `401`, `403`, `404`, `409` `self_deactivation` | USR-09, 10, 18, 21, 26 |
| `GET /clients` | admin | `200` lista de `User` con rol `Client` | `401`, `403` | USR-11, 13, 18 |
| `GET /representatives` | admin | `200` lista de `User` con rol `Representative` | `401`, `403` | USR-12, 13, 18 |

Cuerpos de error (`{"error": "<código>"}`):

| Excepción u origen | Status | Cuerpo |
|--------------------|--------|--------|
| `ValidationError` | `400` | `{"error": "validation_error", "fields": {"<campo>": "required" \| "invalid" \| "too_short"}}` |
| `InvalidCredentialsError` | `401` | `{"error": "invalid_credentials"}` (el mismo para los tres motivos) |
| `login_required` sin sesión | `401` | `{"error": "authentication_required"}` |
| `admin_required` sin rol `Admin` | `403` | `{"error": "forbidden"}` |
| `UserNotFoundError` | `404` | `{"error": "user_not_found"}` |
| `DuplicateUserError` | `409` | `{"error": "duplicate_email"}` |
| `SelfDeactivationError` | `409` | `{"error": "self_deactivation"}` |

Un login con el cuerpo vacío, sin alguno de los dos campos o con un campo que no es texto responde `401` `invalid_credentials`, igual que cualquier otro intento fallido (SPEC-USR-15 y 25).

## Patrones aplicados

- **Capas Controller → Service → Repository**: los controllers leen el JSON, llaman al service y serializan; no validan reglas de negocio.
- **Herencia de tabla única**: los tres roles comparten columnas, así que una tabla con discriminador evita joins y deja `select(Client)` filtrado por rol de forma automática.
- **Registro en lugar de condicionales**: `ROLE_CLASSES` resuelve la clase a partir del rol (alta y listados) y la tabla de `errors.py` resuelve el status a partir de la excepción.
- **Inyección de dependencias por constructor**: `UserService` recibe el repositorio, el hasher y la función de commit. Los tests unitarios usan fakes en memoria.
- **Repository**: el service nunca toca la `Session`; el repositorio la encapsula.

## Decisiones técnicas

| Decisión | Motivo |
|----------|--------|
| Endpoints de gestión: `POST /users`, `PATCH /users/{user_id}`, `POST /users/{user_id}/deactivate`, `GET /clients` y `GET /representatives` | Sigue 1 a 1 los métodos de `UserController` del diagrama de capas y la ruta de baja del diagrama de secuencia 3. La baja es una acción de dominio (no borra nada), por eso no se usa `DELETE`. Se descartaron `DELETE /users/{id}` (sugiere baja física, lo opuesto a SPEC-USR-09 y 10) y `GET /users?role=` (obliga a definir qué pasa sin `role` o con un rol inválido, comportamiento que no está en la spec). **A revisar por el equipo.** |
| El service recibe una función `commit: Callable[[], None]`; en producción es `session.commit` | AGENTS.md pide que el service maneje la transacción sin usar la `Session` y que el repositorio no haga commit. Una función es la unidad de trabajo más chica posible y en los tests se reemplaza por un contador. Se descartaron `repository.commit()` (el diagrama de secuencia lo muestra, pero pone la transacción en el repositorio) y una clase `UnitOfWork` (más código para el mismo resultado). **A revisar por el equipo.** |
| El hash de contraseñas vive en `services/passwords.py` detrás del protocolo `PasswordHasher` | El dominio solo puede importar `sqlalchemy`, así que no puede llamar a `werkzeug`. El protocolo permite tests unitarios rápidos con un hasher falso. Se descartó `User.check_password(password)` del diagrama de clases porque obliga al dominio a importar `werkzeug`. |
| La normalización del email está en el dominio (`normalize_email` + `@validates("email")`) | Cualquier camino que asigne un email (service, CLI, tests) lo normaliza, así que el `UNIQUE` de la base compara emails normalizados (RNF 3). |
| Las validaciones del alta (campos obligatorios, email válido, rol válido, contraseña de 8 caracteres o más, canal válido) están en el service y se informan todas juntas en un `ValidationError(fields)` | SPEC-USR-05 y 23 piden indicar todos los campos inválidos. El email válido se chequea con una expresión simple (`^[^@\s]+@[^@\s]+\.[^@\s]+$`), sin dependencias nuevas. Un nombre o una contraseña solo con espacios cuentan como faltantes (`required`); un valor que no es texto cuenta como `invalid`. Un `preferred_channel` ausente toma el valor por defecto; cualquier otro valor fuera de `NOTIFICATION_CHANNELS` es `invalid`. |
| La modificación valida con las mismas reglas de formato los campos que recibe: nombre no vacío, email válido y canal válido (SPEC-USR-22 y 23), y los informa juntos en un `ValidationError(fields)` sin modificar el usuario | Un campo ausente o `null` no se modifica. Se valida antes del chequeo de email duplicado y antes de asignar, así un rechazo no deja cambios a medio aplicar en la entidad. |
| `repository.add(user)` hace `session.add` + `flush()` y traduce `IntegrityError` a `DuplicateUserError`. `update_user` también llama a `add(user)` después de modificar | El `flush` hace que la violación de `UNIQUE` aparezca dentro del repositorio, que es donde AGENTS.md pide traducirla, y no recién en el commit. En un objeto ya persistido, `session.add` no hace nada y el `flush` cubre el caso de una carrera en la modificación del email. El repositorio no hace rollback: la sesión del request se descarta en el teardown. |
| `get_user_service()` y `current_user()` viven en `app/auth.py` | Es el único lugar que conoce Flask y además arma el service, así los controllers no usan la `Session` (prohibición de AGENTS.md) y la CLI reutiliza el mismo armado. Se descartó armar el service en cada controller con `get_session()`. |
| Los decoradores responden JSON: `401` `authentication_required` y `403` `forbidden` | La interfaz es una API JSON (RNF 7 y decisión del 2026-11-10 sobre SPEC-USR-16). |
| Una sesión con el `user_id` de un usuario inactivo o inexistente cuenta como sin sesión (`401`) | Una baja tiene efecto inmediato aunque el usuario tenga una cookie vigente (SPEC-USR-15 y 16). |
| El login hace `session.clear()` antes de guardar `user_id` | Evita reutilizar datos de una sesión anterior (fijación de sesión, RNF 2). |
| Test de guarda: recorre `app.url_map` y verifica que toda ruta fuera de la lista pública (`auth.login`, `health.health`, `api_docs.openapi_contract`, `api_docs.swagger_ui` y `static`) responde `401` sin sesión | Evita olvidarse de `login_required` en un endpoint nuevo, en esta área o en las siguientes (SPEC-USR-16). Los parámetros de ruta se completan con `1`. |
| Cada task de endpoint agrega la operación a `docs/openapi.json` **y** la ruta en el mismo ciclo TDD | El test de SPEC-PLT-14 falla si el contrato y `app.url_map` difieren en cualquiera de los dos sentidos. En la fase roja fallan el test del endpoint y TC-PLT-14b (operación sin ruta); en la verde pasan los dos. Nunca se commitea uno sin el otro. |
| El contrato suma `components.securitySchemes.sessionCookie` (cookie `session`) como `security` global. Las operaciones públicas mantienen `"security": []` | Swagger UI muestra qué operaciones piden sesión, y las públicas existentes no cambian. |
| `PATCH /users/{user_id}` acepta solo `name`, `email` y `preferred_channel`; el controller ignora cualquier otra clave (`role`, `password`, `is_active`) | SPEC-USR-07 solo permite modificar esos tres datos. La baja va por su propio endpoint. |
| Los listados incluyen a los usuarios inactivos y se ordenan por `id` | SPEC-USR-13 pide mostrar el estado, lo que solo tiene sentido si aparecen los inactivos. El orden fijo hace que los tests sean determinísticos. |
| `create-admin` pide `--name` y `--email` como opciones y la contraseña con un prompt oculto con confirmación (`click.option(..., prompt=True, hide_input=True, confirmation_prompt=True)`). **Reemplazada por la fila de prompt-only (2026-11-10)**: esa opción también aceptaba `--password` | La contraseña no queda en el historial de la shell. Usa el mismo `create_user` con `role="Admin"`, así que aplica las mismas validaciones. Si falla, informa el error y termina con código distinto de 0. |
| `create-admin` pide la contraseña dentro del comando con `click.prompt("Password", hide_input=True, confirmation_prompt=True)` y no declara ninguna opción `--password` (decisión 6 de la spec) | Con `click.password_option` el comando aceptaba `--password x`, que deja la contraseña en el historial de la shell y en la lista de procesos. Sin la opción, click rechaza el flag con "No such option". Se descartó mantener `--password` para scripts: el prompt también se alimenta por la entrada estándar. SPEC-USR-20 no cambia de comportamiento. |
| Hash de relleno (SPEC-USR-24): el protocolo `PasswordHasher` suma `dummy_hash() -> str`. `WerkzeugPasswordHasher` lo calcula con `generate_password_hash` sobre una constante una sola vez por proceso (`functools.cache` a nivel de módulo). `authenticate` llama a `verify(hasher.dummy_hash(), password)` cuando el email no existe o el usuario está inactivo, y después lanza `InvalidCredentialsError` | El service se arma en cada request (`get_user_service()`), así que calcularlo de forma perezosa por instancia del service haría un `hash` más un `verify` en cada login fallido: el camino del email inexistente seguiría siendo distinguible, ahora por lento. Con el hash cacheado por proceso, los tres caminos cuestan un solo `verify`. El hash lo produce el hasher inyectado, así que tiene el mismo costo que uno real, el dominio no importa werkzeug y los tests unitarios usan el fake. Los tests cuentan las llamadas a `verify` en lugar de medir tiempos, que serían frágiles. Se descartaron un hash fijo escrito en el código (queda atado a los parámetros de werkzeug de hoy) y el cálculo perezoso por instancia del service. |
| Tipos de dato (SPEC-USR-25): un valor que no es texto en `name`, `email`, `password`, `role` o `preferred_channel` se informa como `invalid` en el `ValidationError`; en el login, un `email` o `password` que no es texto lanza el mismo `InvalidCredentialsError` | El JSON puede traer números, listas u objetos; sin el chequeo romperían con `AttributeError` o `TypeError` (`500`). El comportamiento ya existía en el código sin spec propia y ahora queda trazado. |
| SPEC-USR-10 se verifica ahora de forma parcial y se completa en `04-tickets` | Todavía no existen tickets, hitos ni `StateChange`. Hoy se prueba que la baja conserva la fila con todos sus datos, que el repositorio no tiene métodos de borrado y que ninguna ruta de usuarios acepta `DELETE`. El caso completo (un ticket de un usuario inactivo conserva sus hitos y su historial) se agrega al `test-plan.md` de `04-tickets`. |
| Sin reloj inyectable en esta área | Ninguna spec de usuarios registra fechas. El reloj se incorpora en `04-tickets` con `StateChange`. |
| Usuario inexistente (SPEC-USR-26): `SqlAlchemyUserRepository.get` devuelve `None` para un id mayor que `2**63 - 1` con `fits_integer_column`, igual que los repositorios del catálogo. El service no cambia: `None` ya se traduce a `UserNotFoundError` (`404` `user_not_found`) | `sqlite3` lanza `OverflowError` al enlazar un entero más grande y el conversor `<int:...>` de Flask no tiene límite, así que `PATCH /users/{id}` y `POST /users/{id}/deactivate` respondían `500`. El límite es del motor, así que la guarda vive en la persistencia (decisión del 2026-11-10 de `02-product-types`). Para el cliente es un id válido que no existe. `find_active_user` usa el mismo `get`, así que también queda cubierto. Los casos de usuario inexistente que eran bordes de USR-07 y 09 (TC-USR-07c, 07e y 09d) pasan a SPEC-USR-26 como TC-USR-26a, 26c y 26d, sin duplicar tests. |

## Dependencias con otras áreas

- Usa de `00-platform`: `create_app`, `get_session()`, `Base`, `create_schema`, el contrato `docs/openapi.json` y su test de sincronización (SPEC-PLT-14).
- `04-tickets` agrega las relaciones `Representative.assigned_tickets` y `Client.tickets`, usa `current_user()` para tomar el representante de la sesión y completa la verificación de SPEC-USR-10.
- `02-product-types` y `03-products` usan `admin_required` para el ABM del catálogo.
- `06-notifications` usa `preferred_channel` para elegir la estrategia.
- Todo endpoint nuevo de cualquier área queda cubierto por el test de guarda de SPEC-USR-16.

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Un fixture que mantiene un app context abierto hace que el test client reutilice ese contexto: `get_session()` devolvería la misma sesión que el test y el teardown no correría al final de cada request | El fixture `db_session` crea la sesión directamente desde el `sessionmaker` de `app.extensions`, sin abrir un app context. Después de un request, el test vuelve a consultar con `expire_all()`. |
| El hash de werkzeug (scrypt) hace lentos los tests que crean muchos usuarios | Los tests unitarios usan `FakePasswordHasher`. Los de integración crean pocos usuarios por test. |
| ~~La respuesta `404` ante un usuario inexistente no tiene una spec propia~~ | ~~Se trata como el error HTTP estándar de `UserNotFoundError` y se prueba como caso borde de SPEC-USR-07 y 09.~~ **Resuelto el 2026-11-10** con SPEC-USR-26 (TC-USR-26a a 26f). |
| Olvidar `login_required` o `admin_required` en un endpoint | Test de guarda sobre `app.url_map` (TC-USR-16d) y casos `403` parametrizados por endpoint (TC-USR-18b y 18c). |
