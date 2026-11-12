# 05 — Gestión de hitos · Test plan

Cada test cita en su docstring la spec y el caso: `"""SPEC-MLS-05 · TC-MLS-05a"""`. Los casos de `04-tickets` que se completan o agregan acá citan su propia spec: `"""SPEC-TKT-09 · TC-TKT-09b"""`, `"""SPEC-TKT-27 · TC-TKT-27f"""`. Los casos que verifican una decisión de [spec.md](spec.md) la citan como **(dec. N)**.

Fixtures existentes (`tests/conftest.py`): `app`, `client`, `schema`, `db_session`, `make_user`, `login_as`, `admin`, `admin_client`, `make_category`, `make_product_type`, `make_product` y `make_ticket` (ver [04-tickets](../04-tickets/test-plan.md)).

Fixture nuevo (`tests/integration/milestones/conftest.py`):
- `world`: `ana` y `beto` (clientes), `raul` y `rosa` (representantes), el producto `xps` y el ticket de `ana` y `raul` creado con `make_ticket(ana, raul, [xps])` (estado `New`, con su primer hito). Mismos datos que el `world` de `tests/integration/tickets/test_tickets_permissions.py`, sin importarlo.

Helpers existentes: `count_statements(session)` (`tests/integration/catalog/queries.py`) y `run_fresh(script)` (`tests/integration/tickets/test_schema_registration.py`, se importa sin editarlo).

Dobles para tests unitarios (sin Flask ni base):
- `FakeTicketRepository` (`tests/unit/tickets/fakes.py`, existente): suma `get_visible_with_milestones(ticket_id, actor)` con el mismo contrato que `get_visible`, y registra la llamada en `visible_lookups` (los casos de formato comprueban que quedó vacío, dec. 4).
- `FakeClock` y `CommitSpy` (`tests/unit/fakes.py`), `FakeUserRepository` y `FakeProductRepository`: sin cambios.
- Reloj que cuenta sus lecturas: una función local del test que envuelve un `FakeClock`, avanza 1 s y suma 1 en cada llamada (TC-MLS-03e).
- `FakeTicketNotifier` (existente): esta área no lo usa para verificar llamadas; `06-notifications` sí lo hace (`TicketService` ya llama a `notify` después del `commit`).

Datos de referencia: `"Ana"` (cliente) y `"Raúl"` (representante asignado) son los participantes; `"Beto"` (otro cliente) y `"Rosa"` (otro representante) son los ajenos. Todas las fechas son `datetime` con `tzinfo=UTC`. Para verificar "sin cambios" se relee con `db_session.expire_all()` y se cuentan las filas de `milestones` y `state_changes` y el `state_name` del ticket.

Archivos de test nuevos: `tests/unit/milestones/` (`__init__.py`, `test_milestone.py`, `test_milestone_service.py`) y `tests/integration/milestones/` (`__init__.py`, `conftest.py`, `test_milestone_model.py`, `test_milestone_immutability.py`, `test_milestone_repository.py`, `test_milestones_api.py`, `test_milestones_permissions.py`). Archivos de 04 que se editan: `tests/unit/tickets/fakes.py`, `tests/integration/tickets/test_tickets_permissions.py` y, en el seguimiento de G-21 (T-MLS-20 y 22), `tests/unit/tickets/test_ticket_service.py` y `tests/integration/tickets/test_tickets_api.py`.

## Matriz spec → casos

### Registro de hitos

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| MLS-01 | TC-MLS-01a | unit | `Ticket.open(ana, raul, [], "Hola", t0)` y `ticket.add_milestone("Revisando", raul, t1)` | Devuelve un `Milestone` que queda último en `ticket.milestones` (2 hitos), con `content == "Revisando"` y `author is raul` | `tests/unit/milestones/test_milestone.py` |
| MLS-01 | TC-MLS-01b | unit | `add_milestone(ticket.id, "Revisando", raul)` con fakes, sobre un ticket `New` y otro `InProgress` | Devuelve el hito, que está en `ticket.milestones`; `commit` se llamó una vez en cada caso | `tests/unit/milestones/test_milestone_service.py` |
| MLS-01 | TC-MLS-01c | unit | Ticket en `InProgress`; `ticket.request_progress(raul, t1)` **(dec. 5)** | No hace nada: `state_name == "InProgress"` y `state_history` no cambia (sin `InvalidTransitionError`) | `tests/unit/milestones/test_milestone.py` |
| MLS-01 | TC-MLS-01d | unit | Ticket en `InProgress`; `add_milestone(ticket.id, "Sigo", raul, start_progress=True)` **(dec. 5)** | Se guarda el hito, el ticket sigue en `InProgress`, no se agrega `StateChange` y hay un `commit` | `tests/unit/milestones/test_milestone_service.py` |
| MLS-01 | TC-MLS-01e | unit | Ticket `New`; `add_milestone(..., raul)` sin `start_progress` y con `start_progress=False` | Se guarda el hito y el ticket sigue en `New`, sin `StateChange` nuevo | `tests/unit/milestones/test_milestone_service.py` |
| MLS-01 | TC-MLS-01f | integration | Sesión de `raul`; `POST /tickets/{id}/milestones` con `{"content": "Revisando"}` | `201` `{"id": <int>, "content": "Revisando", "author": {"id": <raul>, "name": "Raúl", "role": "Representative"}, "created_at": <ISO UTC>}` **(G-03)**; la fila existe y el ticket sigue en `New` | `tests/integration/milestones/test_milestones_api.py` |
| MLS-01 | TC-MLS-01g | integration | Ticket pasado a `InProgress`; sesión de `raul`; `POST` con `{"content": "Sigo", "start_progress": true}` **(dec. 5)** | `201`; el ticket sigue en `InProgress` y la cantidad de filas de `state_changes` no cambia | `tests/integration/milestones/test_milestones_api.py` |
| MLS-01 | TC-MLS-01h | integration | Sesión de `raul`; `POST` con un contenido de 20 000 caracteres y con `"  Hola  "` **(dec. 8, G-04)** | `201` en los dos; el contenido se guarda completo y sin recortar (caso "permitido", sin fase roja propia) | `tests/integration/milestones/test_milestones_api.py` |
| MLS-02 | TC-MLS-02a | unit | `ticket.add_milestone("Gracias", ana, t1)` | El hito queda en el ticket con `author is ana` | `tests/unit/milestones/test_milestone.py` |
| MLS-02 | TC-MLS-02b | unit | `add_milestone(ticket.id, "Gracias", ana)` con fakes | Devuelve el hito de `ana`; un `commit` | `tests/unit/milestones/test_milestone_service.py` |
| MLS-02 | TC-MLS-02c | unit | Ticket `New`; `add_milestone(ticket.id, "Gracias", ana, start_progress=True)` **(dec. 6)** | Se guarda el hito, el ticket sigue en `New`, sin `StateChange` nuevo y sin error | `tests/unit/milestones/test_milestone_service.py` |
| MLS-02 | TC-MLS-02d | integration | Sesión de `ana`; `POST` con `{"content": "Gracias"}` | `201` con `author == {"id": <ana>, "name": "Ana", "role": "Client"}`; la fila existe | `tests/integration/milestones/test_milestones_api.py` |
| MLS-02 | TC-MLS-02e | integration | Ticket `New`; sesión de `ana`; `POST` con `{"content": "Gracias", "start_progress": true}` **(dec. 6)** | `201`; `GET /tickets/{id}` con `ana` responde `state == "New"` y no hay filas nuevas en `state_changes` | `tests/integration/milestones/test_milestones_api.py` |
| MLS-03 | TC-MLS-03a | unit | `ticket.add_milestone("Revisando", raul, t1)` con `t1` en UTC | `milestone.created_at == t1` (con `tzinfo` UTC) y `milestone.author is raul` | `tests/unit/milestones/test_milestone.py` |
| MLS-03 | TC-MLS-03b | integration | `world.ticket.add_milestone("Revisando", raul, t1)`, `commit` y lectura en una sesión nueva | La fila tiene `ticket_id`, `author_id == raul.id`, el contenido y `created_at == t1` con `tzinfo` UTC (puede pasar sin fase roja) | `tests/integration/milestones/test_milestone_model.py` |
| MLS-03 | TC-MLS-03c | unit | `FakeClock` en `t0`; `add_milestone(ticket.id, "Hola", ana)` | `created_at == t0` y `author is ana` (el autor es quien llama, no un dato del pedido) | `tests/unit/milestones/test_milestone_service.py` |
| MLS-03 | TC-MLS-03d | integration | Sesión de `raul`; `POST` con `{"content": "Hola", "author_id": <ana>, "created_at": "2000-01-01T00:00:00Z"}` | `201`; `author.id == raul.id` y `created_at` es el instante del servidor en UTC, igual al de la fila (las claves extra se ignoran) | `tests/integration/milestones/test_milestones_api.py` |
| MLS-03 | TC-MLS-03e | unit | Reloj que cuenta sus lecturas; ticket `New`; `add_milestone(..., raul, start_progress=True)` | El reloj se leyó una sola vez; `milestone.created_at` es igual al `timestamp` del `StateChange` nuevo (SPEC-TKT-14) | `tests/unit/milestones/test_milestone_service.py` |

### Validación del contenido

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| MLS-04 | TC-MLS-04a | unit | Parametrizado: `add_milestone(ticket.id, v, raul)` con `v` en `None`, `""` y `"   "` | `ValidationError` con `fields == {"content": "required"}` **(dec. 8)**; `visible_lookups` vacío y sin `commit` | `tests/unit/milestones/test_milestone_service.py` |
| MLS-04 | TC-MLS-04b | unit | `add_milestone(ticket.id, "   ", raul, start_progress="yes")` | `fields == {"content": "required", "start_progress": "invalid"}` (se informan juntos); sin consulta ni `commit` | `tests/unit/milestones/test_milestone_service.py` |
| MLS-04 | TC-MLS-04c | unit | `add_milestone` con `content=""` sobre el ticket de `ana` con `beto` como actor, y con `ticket_id = 9999` **(dec. 4)** | `ValidationError` (no `TicketNotFoundError`) en los dos; `visible_lookups` vacío | `tests/unit/milestones/test_milestone_service.py` |
| MLS-04 | TC-MLS-04d | integration | Sesión de `raul`; `POST` sin cuerpo, con `{}`, con `{"content": ""}`, con `{"content": "   "}`, con `{"content": null}` y con un cuerpo que es una lista JSON | `400` `{"error": "validation_error", "fields": {"content": "required"}}` en todos; sin filas nuevas | `tests/integration/milestones/test_milestones_api.py` |
| MLS-04 | TC-MLS-04e | integration | `{"content": ""}` con la sesión de `raul` sobre su ticket, de `beto` y `rosa` sobre el ticket de `ana`, y de `raul` sobre `9999` y `2**63` **(dec. 4)** | El mismo `400` y el mismo cuerpo en los cinco; las tablas no cambian (no revela si el ticket existe, RNF 4) | `tests/integration/milestones/test_milestones_permissions.py` |
| MLS-11 | TC-MLS-11a | unit | Parametrizado: `add_milestone(ticket.id, v, raul)` con `v` en `123`, `True`, `["Hola"]` y `{"a": 1}` | `fields == {"content": "invalid"}` **(dec. 3 y 8)**; sin consulta ni `commit` | `tests/unit/milestones/test_milestone_service.py` |
| MLS-11 | TC-MLS-11b | integration | Sesión de `raul`; `POST` con `{"content": 123}` y con `{"content": ["Hola"]}` | `400` `validation_error` con `fields.content == "invalid"`; sin filas nuevas | `tests/integration/milestones/test_milestones_api.py` |

### Ticket cerrado

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| MLS-05 | TC-MLS-05a | unit | Ticket cerrado (`ticket.close(raul, t1)`); `ticket.add_milestone("Hola", ana, t2)` | Lanza `TicketClosedError`; `ticket.milestones` no cambia | `tests/unit/milestones/test_milestone.py` |
| MLS-05 | TC-MLS-05b | unit | Ticket cerrado y reabierto (`reopen`); `add_milestone("Hola", ana, t3)` | Se acepta: la guarda depende del estado actual, no de la historia (caso "permitido") | `tests/unit/milestones/test_milestone.py` |
| MLS-05 | TC-MLS-05c | unit | Ticket `Closed`; `add_milestone(ticket.id, "Hola", ana)` y `add_milestone(ticket.id, "Hola", raul, start_progress=True)` **(dec. 5)** | `TicketClosedError` en los dos; sin `commit`, el ticket sigue `Closed`, sin hitos ni `StateChange` nuevos | `tests/unit/milestones/test_milestone_service.py` |
| MLS-05 | TC-MLS-05d | unit | Ticket `Closed` de `ana`: `add_milestone` con `beto` y cuerpo válido; y con `ana` y `content=""` **(dec. 11)** | `TicketNotFoundError` para `beto` (el `404` precede al `409`) y `ValidationError` para `ana` (el `400` precede al `409`) | `tests/unit/milestones/test_milestone_service.py` |
| MLS-05 | TC-MLS-05e | integration | Ticket cerrado con `POST /tickets/{id}/close`; `POST /tickets/{id}/milestones` con la sesión de `ana` y con la de `raul` (esta con `"start_progress": true`) | `409` `{"error": "ticket_closed"}` **(dec. 9)** en los dos; sin filas nuevas en `milestones` ni en `state_changes`, el ticket sigue `Closed` | `tests/integration/milestones/test_milestones_api.py` |
| MLS-05 | TC-MLS-05f | integration | El mismo ticket después de `POST /tickets/{id}/reopen`; `POST` de `ana` | `201`: reabierto, vuelve a aceptar hitos | `tests/integration/milestones/test_milestones_api.py` |

### Privacidad

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| MLS-06 | TC-MLS-06a | integration | `get_visible_with_milestones` con el ticket de `ana` para `beto`, `rosa`, `ana` y `raul`, y con `9999` y `2**63` | `None` para `beto`, `rosa`, `9999` y `2**63` (sin `OverflowError`); el ticket para `ana` y `raul` | `tests/integration/milestones/test_milestone_repository.py` |
| MLS-06 | TC-MLS-06b | unit | `add_milestone` con cuerpo válido: `beto` y `rosa` sobre el ticket de `ana`, y `ana` con `ticket_id = 9999` | `TicketNotFoundError` en los tres; sin `commit` ni hitos nuevos | `tests/unit/milestones/test_milestone_service.py` |
| MLS-06 | TC-MLS-06c | unit | `list_milestones` con `beto`, `rosa` y `ticket_id = 9999` | `TicketNotFoundError` en los tres | `tests/unit/milestones/test_milestone_service.py` |
| MLS-06 | TC-MLS-06d | integration | `POST` con `{"content": "Hola"}`: sesión de `beto` (cliente ajeno: "responder" de SPEC-TKT-19 y RNF 4) y de `rosa` sobre el ticket de `ana`; comparación con `POST /tickets/9999/milestones` y con `2**63` | `404` `{"error": "ticket_not_found"}` en todos, con el mismo cuerpo que el inexistente (no `500`); sin filas nuevas | `tests/integration/milestones/test_milestones_permissions.py` |
| MLS-06 | TC-MLS-06e | integration | `GET /tickets/{id}/milestones` con `beto` y `rosa` sobre el ticket de `ana`, y con `ana` sobre `9999` y `2**63` | `404` `ticket_not_found` idéntico en todos (no `500`) | `tests/integration/milestones/test_milestones_permissions.py` |

### Listado

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| MLS-07 | TC-MLS-07a | unit | Ticket con el primer hito y dos agregados; `list_milestones(ticket.id, ana)` y `list_milestones(ticket.id, raul)` | Los tres hitos en el orden de `ticket.milestones` (el inicial primero), para los dos participantes | `tests/unit/milestones/test_milestone_service.py` |
| MLS-07 | TC-MLS-07b | integration | `world.ticket` (primer hito en `t0`); agregar `"B"` en `t2`, `"C"` en `t1` y `"D"` en `t2`; `commit` y lectura en una sesión nueva | `[primer hito, "C", "B", "D"]`: ascendente por `created_at` y, con el mismo instante, por `id` | `tests/integration/milestones/test_milestone_model.py` |
| MLS-07 | TC-MLS-07c | integration | Los mismos datos; `get_visible_with_milestones(ticket.id, ana)` en una sesión nueva | `ticket.milestones` en el mismo orden que 07b | `tests/integration/milestones/test_milestone_repository.py` |
| MLS-07 | TC-MLS-07d | unit | Ticket `Closed`; `list_milestones(ticket.id, ana)` **(G-05)** | Devuelve los hitos (listar no tiene condición de estado) | `tests/unit/milestones/test_milestone_service.py` |
| MLS-07 | TC-MLS-07e | integration | Hitos registrados por la API con `ana` y `raul`, más el inicial; `GET /tickets/{id}/milestones` con cada sesión | `200` con los hitos en orden ascendente, el inicial primero, igual para los dos | `tests/integration/milestones/test_milestones_api.py` |
| MLS-07 | TC-MLS-07f | integration | Ticket cerrado con `POST /tickets/{id}/close`; `GET` de `ana` **(G-05)** | `200` con los hitos | `tests/integration/milestones/test_milestones_api.py` |
| MLS-08 | TC-MLS-08a | integration | Ticket con 1 hito y otro con 6 hitos de `ana` y `raul` alternados; `count_statements` alrededor de `get_visible_with_milestones` y del recorrido de `content`, `author.name`, `author.role` y `created_at` | La misma cantidad de sentencias para los dos tickets y como máximo 8 (sin N+1) | `tests/integration/milestones/test_milestone_repository.py` |
| MLS-08 | TC-MLS-08b | integration | Hitos de `ana` y `raul`; `GET` con la sesión de `raul` | Cada elemento es exactamente `{"id", "content", "author": {"id", "name", "role"}, "created_at"}` con `role` `"Client"` o `"Representative"` y `created_at` ISO UTC; sin email | `tests/integration/milestones/test_milestones_api.py` |
| MLS-08 | TC-MLS-08c | integration | `ana` registra un hito; el admin la da de baja (`POST /users/{id}/deactivate`); `GET` con la sesión de `raul` | `200`; el hito sigue con `author == {"id": <ana>, "name": "Ana", "role": "Client"}` (coherente con TC-USR-10d) | `tests/integration/milestones/test_milestones_api.py` |

### Inmutabilidad de los hitos (RNF 5)

Tres barreras, como en `StateChange` (TC-TKT-16a a 16k): (a) listeners del ORM, (b) triggers de SQLite, (c) relación sin `delete-orphan`. Los casos de triggers usan SQL que no pasa por los listeners (`text()` con parámetros enlazados y `update()`/`delete()` masivos).

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| MLS-09 | TC-MLS-09a | integration | Primer hito de `world.ticket`; `milestone.content = "otro"` y `flush()` | Lanza `ImmutableRecordError`; después de `rollback()` la fila no cambió | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-09 | TC-MLS-09b | integration | `count_statements` alrededor de 09a y de 10a | Se lanza `ImmutableRecordError` y no se ejecutó ningún `UPDATE` ni `DELETE` sobre `milestones`: el listener corta antes del SQL | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-09 | TC-MLS-09c | integration | `session.execute(text("UPDATE milestones SET content = :c WHERE id = :id"), {...})` | `DBAPIError` con `immutable` en el mensaje (trigger); la fila no cambió | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-09 | TC-MLS-09d | integration | `session.execute(update(Milestone).values(content="otro"))` (masivo) | `DBAPIError` con `immutable`; las filas siguen iguales | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-09 | TC-MLS-09e | integration | `schema` y consulta a `sqlite_master` | Existen `milestones_no_update` y `milestones_no_delete` sobre `milestones` | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-09 | TC-MLS-09f | integration | `run_fresh` (intérprete nuevo que solo importa `app.domain.base` y `app.db` y llama a `create_schema`): triggers en `sqlite_master` y, con el mapper de `milestones` de `Base.registry.mappers`, `event.contains(<clase>, "before_update", reject_update)` y lo mismo con `"before_delete"` / `reject_delete` | Código de salida `0`; existen los dos triggers y los dos listeners están registrados en el camino normal de `init-db` (parte de hitos que TC-TKT-16k dejó para 05) | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-09 | TC-MLS-09g | integration | Sesión de `raul`; `PATCH` y `PUT /tickets/{id}/milestones` con `{"content": "otro"}`, y `PATCH /tickets/{id}/milestones/{milestone_id}` **(dec. 10)** | `405` `{"error": "method_not_allowed"}` en los dos primeros y `404` `{"error": "not_found"}` en el tercero (SPEC-PLT-15); el hito no cambió | `tests/integration/milestones/test_milestones_api.py` |
| MLS-09 | TC-MLS-09h | integration | Atributos públicos de `SqlAlchemyTicketRepository` y reglas de `app.url_map` que contienen `/milestones` | El repositorio no tiene métodos `update`, `delete` ni `remove` (de hitos ni de tickets); la ruta de hitos solo acepta `GET` y `POST` (sin contar `HEAD`/`OPTIONS`) | `tests/integration/milestones/test_milestones_api.py` |
| MLS-10 | TC-MLS-10a | integration | `session.delete(milestone)` y `flush()` | Lanza `ImmutableRecordError`; la fila sigue | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-10 | TC-MLS-10b | integration | `world.ticket.milestones.remove(milestone)` y `flush()` | Lanza `ImmutableRecordError` (sin `delete-orphan`, el ORM intenta poner `ticket_id` en `NULL`); la fila sigue ligada al ticket | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-10 | TC-MLS-10c | integration | `session.execute(text("DELETE FROM milestones WHERE id = :id"), {...})` | `DBAPIError` con `immutable`; la fila sigue | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-10 | TC-MLS-10d | integration | `session.execute(delete(Milestone))` (masivo) | `DBAPIError` con `immutable`; las filas siguen | `tests/integration/milestones/test_milestone_immutability.py` |
| MLS-10 | TC-MLS-10e | integration | Sesión de `raul`; `DELETE /tickets/{id}/milestones` y `DELETE /tickets/{id}/milestones/{milestone_id}` **(dec. 10)** | `405` `method_not_allowed` y `404` `not_found` en JSON (SPEC-PLT-15); la cantidad de hitos no cambió | `tests/integration/milestones/test_milestones_api.py` |

## Casos de 04-tickets que se completan o agregan acá

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| TKT-09 | TC-TKT-09b | integration | Pendiente desde [04-tickets](../04-tickets/test-plan.md). Ticket `New`; sesión de `raul`; `POST /tickets/{id}/milestones` con `{"content": "Empiezo", "start_progress": true}` | `201` con el hito; `GET /tickets/{id}` responde `state == "InProgress"`; hay un `StateChange` nuevo `InProgress` con `user_id == raul.id` y `timestamp` igual al `created_at` del hito, en la misma operación | `tests/integration/milestones/test_milestones_api.py` |
| TKT-09 | TC-TKT-09c | unit | Ticket `New`; `ticket.request_progress(raul, t1)` | `state_name == "InProgress"` y un `StateChange(raul, "InProgress", t1)` nuevo | `tests/unit/milestones/test_milestone.py` |
| TKT-09 | TC-TKT-09d | unit | Parametrizado: `add_milestone(ticket.id, "Hola", raul, start_progress=v)` con `v` en `None`, `"yes"`, `"true"`, `1` y `0` **(dec. 7)** | `ValidationError` con `fields == {"start_progress": "invalid"}`; `visible_lookups` vacío y sin `commit` | `tests/unit/milestones/test_milestone_service.py` |
| TKT-09 | TC-TKT-09e | unit | Ticket `New`; `add_milestone(ticket.id, "Empiezo", raul, start_progress=True)` con `FakeClock` | El ticket pasa a `InProgress` con un `StateChange` de `raul` en el instante del reloj; el hito se guarda; un solo `commit` | `tests/unit/milestones/test_milestone_service.py` |
| TKT-09 | TC-TKT-09f | integration | Sesión de `raul`; `POST` con `"start_progress"` en `null`, `"yes"` y `1`; y otro `POST` sin `start_progress` **(dec. 7)** | `400` `validation_error` con `fields.start_progress == "invalid"` y sin filas nuevas en los tres primeros; `201` y el ticket sigue `New` en el último | `tests/integration/milestones/test_milestones_api.py` |
| TKT-27 | TC-TKT-27f | unit | `Admin` como actor: `add_milestone(9999, "Hola", admin)` y `add_milestone(ticket.id, "Hola", admin)`; `list_milestones(9999, admin)` y `list_milestones(ticket.id, admin)` **(dec. 9 y 12)** | `PermissionDeniedError` en todos (también con el id inexistente: el `403` precede al `404`); `visible_lookups` vacío y sin `commit` | `tests/unit/milestones/test_milestone_service.py` |
| TKT-27 | TC-TKT-27g | unit | `Admin`: `add_milestone(ticket.id, "", admin)` y `add_milestone(ticket.id, "Hola", admin, start_progress="yes")` **(dec. 9, G-21)** | `ValidationError` (el formato precede al `403` del `Admin`) | `tests/unit/milestones/test_milestone_service.py` |
| TKT-27 | TC-TKT-27h | integration | `admin_client`: `POST /tickets/9999/milestones` con `{"content": "Hola"}`, `POST /tickets/{id}/milestones` con `{"content": ""}`, `GET /tickets/9999/milestones` y `GET /tickets/{id}/milestones` **(dec. 9, 11 y 12)** | `403` `forbidden`, `400` `validation_error` (`content: required`), `403` y `403`; las tablas no cambian | `tests/integration/milestones/test_milestones_permissions.py` |
| TKT-24 | TC-TKT-24k | unit | **Seguimiento de G-21 (T-MLS-20, espera la aprobación del texto de T-MLS-19).** `Admin`: `add_products(ticket.id, "abc", admin)` y `add_products(9999, None, admin)` | `ValidationError` (`invalid` y `required`); `visible_lookups` vacío | `tests/unit/tickets/test_ticket_service.py` |
| TKT-24 | TC-TKT-24l | integration | **Seguimiento de G-21 (T-MLS-20).** `admin_client`: `POST /tickets/9999/products` con `{"product_ids": "abc"}` y `POST /tickets/{id}/products` con `{"product_ids": []}` | `400` `validation_error` con `fields.product_ids == "invalid"` en los dos; sin cambios | `tests/integration/tickets/test_tickets_permissions.py` |
| TKT-05 | TC-TKT-05c | unit | **Seguimiento de G-21 y G-01 opción B (T-MLS-22).** `Client` (`ana`) como actor: `create_ticket(None, [], "", ana)` y `create_ticket(ana.id, "abc", "Hola", ana)`; además `create_ticket(9999, [], "Hola", ana)` (formato válido, cliente inexistente) | `ValidationError` en los dos primeros (`{"client_id": "required", "first_message": "required"}` y `{"product_ids": "invalid"}`): el formato precede al `403` de SPEC-TKT-05; `PermissionDeniedError` (no `InvalidClientError`) en el tercero: el rol precede a la verificación del cliente (G-06). Sin ticket guardado y sin `commit` en los tres | `tests/unit/tickets/test_ticket_service.py` |
| TKT-05 | TC-TKT-05d | integration | **T-MLS-22.** Sesión de `ana` (`Client`): `POST /tickets` con `{"first_message": ""}` y con `{"client_id": 9999, "first_message": "Hola"}` | `400` `{"error": "validation_error", "fields": {"client_id": "required", "first_message": "required"}}` en el primero; `403` `{"error": "forbidden"}` (no `invalid_client`) en el segundo; sin tickets creados | `tests/integration/tickets/test_tickets_api.py` |
| TKT-27 | TC-TKT-27i | unit | **T-MLS-22.** `Admin` como actor: `create_ticket(ana.id, [], "", admin)`, `create_ticket("abc", [], "Hola", admin)` y `create_ticket(9999, [], "Hola", admin)` | `ValidationError` en los dos primeros (`first_message: required`, `client_id: invalid`): el formato precede al `403` de SPEC-TKT-27; `PermissionDeniedError` en el tercero (el rol precede a `invalid_client`, G-06). Sin ticket guardado y sin `commit` | `tests/unit/tickets/test_ticket_service.py` |
| TKT-27 | TC-TKT-27j | integration | **T-MLS-22.** `admin_client`: `POST /tickets` con `{"first_message": ""}` y con un cuerpo válido `{"client_id": <ana>, "first_message": "Hola"}` | `400` `validation_error` (`client_id: required`, `first_message: required`) en el primero y `403` `{"error": "forbidden"}` en el segundo; la tabla `tickets` no cambia | `tests/integration/tickets/test_tickets_permissions.py` |

Casos existentes de 04 que crecen con esta área (sin IDs nuevos):

- TC-TKT-27b, 27d y 27e (`tests/integration/tickets/test_tickets_permissions.py`): `ALL_ENDPOINTS` suma `POST` (T-MLS-13) y `GET` (T-MLS-14) `/tickets/{ticket}/milestones`; los conteos pasan de 7 a 8 y a 9. Las dos operaciones nuevas del contrato referencian `TicketForbidden`.
- TC-TKT-19c, 20c, 30c y 30d: `TICKET_ENDPOINTS` suma los dos endpoints de hitos, el `POST` con `{"content": "Hola"}` (formato válido, para que la respuesta sea `404`; dec. 4) (T-MLS-15).
- TC-TKT-27c (se ajusta en T-MLS-22, G-01 opción B): la entrada `POST /tickets` con cuerpo inválido sale de la lista (ese caso pasa a TC-TKT-27j y espera `400`) y la reemplaza `POST /tickets` con `{"client_id": 9999, "first_message": "Hola"}`. Resultado: `403` `forbidden` en los tres (`GET /tickets/9999`, ese `POST /tickets` y `POST /tickets/9999/close`): el `Admin` gana al `404` y a `invalid_client`, ya no al `400` de formato.
- TC-TKT-05b (T-MLS-22): el código no cambia (ya envía un cuerpo de formato válido); en T-MLS-21 su descripción en 04 pasa a "con un cuerpo de formato válido" porque, con formato inválido, el `Client` recibe `400` (TC-TKT-05d).
- TC-TKT-27a: no cambia; su `_create_ticket` usa un cuerpo de formato válido y sigue esperando `PermissionDeniedError`.
- TC-USR-16d: cubre las 2 rutas nuevas sin editarse.

## Casos borde

- Contenido ausente, `null`, vacío, solo espacios, o cuerpo que no es un objeto JSON: TC-MLS-04a y 04d. Contenido que no es texto (número, booleano, lista, objeto): TC-MLS-11a y 11b. Contenido muy largo o con espacios alrededor (se acepta tal cual): TC-MLS-01h.
- `start_progress` ausente (vale `false`), `null`, texto, número: TC-TKT-09d y 09f. Junto con un contenido inválido (se informan los dos): TC-MLS-04b.
- `start_progress: true` en `InProgress` (se ignora): TC-MLS-01c, 01d y 01g. Enviado por el cliente (se ignora): TC-MLS-02c y 02e. En `Closed` (`409` igual): TC-MLS-05c y 05e.
- Precedencia completa al registrar (dec. 11): formato antes que el ticket (TC-MLS-04c, 04e) y que el `Admin` (TC-TKT-27g, 27h); `Admin` antes que `404` (TC-TKT-27f, 27h); `404` antes que `409` y `400` antes que `409` (TC-MLS-05d). Al listar (dec. 12): `Admin` antes que `404` (TC-TKT-27f, 27h).
- Precedencia en 04 después del seguimiento de G-21: al asociar productos, formato antes que el `Admin` (TC-TKT-24k, 24l); al crear, formato antes que el `403` del `Admin` (TC-TKT-27i, 27j) y del `Client` (TC-TKT-05c, 05d), y el rol antes que `invalid_client` (TC-TKT-05c, 05d, 27c ajustado y 27i, G-06).
- Ticket ajeno, inexistente y fuera de rango (`2**63`) responden igual al registrar y al listar: TC-MLS-06a a 06e.
- Ticket cerrado y después reabierto: TC-MLS-05b y 05f. Listado de un ticket cerrado: TC-MLS-07d y 07f.
- Hitos con el mismo instante y registrados fuera de orden temporal: TC-MLS-07b y 07c.
- Autor dado de baja que sigue apareciendo en el listado: TC-MLS-08c.
- Claves extra en el cuerpo (`author_id`, `created_at`): TC-MLS-03d.
- Un solo instante para el hito y el cambio de estado: TC-MLS-03e y TC-TKT-09b.
- Intentos de modificar o borrar hitos por el ORM, por la colección, por SQL directo, por sentencias masivas y por la API: TC-MLS-09a a 09h y 10a a 10e.
- Esquema creado en un intérprete nuevo (barreras activas en `init-db`): TC-MLS-09f.
- Consultas N+1 al listar: TC-MLS-08a.

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 2 (autenticación y permisos) | TC-TKT-27f, 27g y 27h (el `Admin` no registra ni lista hitos, con la precedencia de la dec. 9), TC-TKT-27b con los endpoints nuevos, TC-TKT-24k, 24l, 27i, 27j, 05c, 05d y 27c ajustado (seguimiento de G-21: el formato precede al `403` del rol en 04, también al crear), TC-MLS-02c y 02e (el cliente no dispara la transición), TC-USR-16d (`401` sin sesión en las 2 rutas nuevas) |
| RNF 4 (privacidad de tickets) | TC-MLS-06a a 06e (responder y listar un ticket ajeno responde igual que uno inexistente: la parte "responder" que 04 dejó pendiente), TC-MLS-04c y 04e (el `400` de formato no revela si el ticket existe), TC-TKT-19c, 20c, 30c y 30d con los endpoints de hitos |
| RNF 5 (inmutabilidad, `Milestone`) | TC-MLS-09a a 09h y 10a a 10e (la parte de hitos que TC-TKT-16k dejó para 05: TC-MLS-09f) |
| RNF 6 (auditoría de estado) | TC-TKT-09b, 09c y 09e, TC-MLS-03e (el `StateChange` de `start_progress` con usuario e instante correctos); TC-MLS-01c, 01d, 01g, 02c, 02e y 05c (sin `StateChange` cuando el indicador se ignora o el ticket está cerrado) |
| RNF 7 (documentación de la API) | TC-PLT-14a y 14b en T-MLS-13 y 14, y TC-TKT-27e (el `403` de hitos documentado con `TicketForbidden`) |
