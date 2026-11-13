# 05 — Gestión de hitos · Plan de implementación

Specs cubiertas: SPEC-MLS-01 a SPEC-MLS-11 ([spec.md](spec.md)), con las decisiones 1 a 12. También se completan casos que quedaron pendientes en [04-tickets](../04-tickets/test-plan.md): TC-TKT-09b (SPEC-TKT-09 de punta a punta, con `start_progress`), la parte de hitos de RNF 5 (la que TC-TKT-16k dejó para esta área) y la parte "responder" de RNF 4 y SPEC-TKT-19. RNF: 2 (permisos: el `Admin` y los participantes), 4 (privacidad: responder y listar hitos de un ticket ajeno), 5 (inmutabilidad de `Milestone`), 6 (el cambio de estado disparado por `start_progress`) y 7 (API documentada).

> **Estado**: la spec está validada (PASS) con las decisiones 1 a 12 y sin preguntas abiertas. G-01 y G-02 de este plan se resolvieron el 2026-11-11 (ver Engram: `tp-final/decision/milestones-plan-g01-g02-formato-antes-que-rol`): G-01 → opción B (el formato precede al `403` también en `create_ticket`) y G-02 → opción 1 (las decisiones 11 y 19 de 04 se editan en el lugar, con la inversión y la fecha). Las tasks propias de 05 (T-MLS-01 a 18) no están bloqueadas; las de seguimiento de 04 (T-MLS-19 a 22) esperan solo que el usuario apruebe el texto de [Seguimiento de 04](#seguimiento-de-04-por-g-21-decisión-9). G-03 a G-06 son comportamientos por defecto del plan que el usuario puede vetar. El desglose está en [tasks.md](tasks.md) (22 tasks).

> **Re-sincronización del 2026-11-12** (nueva área [07-ui](../07-ui/spec.md)): SPEC-MLS-12 (el `Admin` lista los hitos de cualquier ticket) y SPEC-MLS-13 (los hitos no se paginan). Specs cubiertas desde entonces: SPEC-MLS-01 a SPEC-MLS-13, con las decisiones 1 a 14. Donde este plan dice que el `Admin` que **lista** hitos recibe `403` (decisiones 9 y 12), desde ahora no aplica (decisión 13); el `403` al **registrar** sigue, por SPEC-TKT-32. Ver [Re-sincronización del 2026-11-12](#re-sincronización-del-2026-11-12) y las tasks T-MLS-23 a 26. RNF 10 se suma a los cubiertos.

## Enfoque

Área chica que se monta casi entera sobre `04-tickets`. No hay tablas ni columnas nuevas: la tabla `milestones`, la entidad `Milestone`, la relación `Ticket.milestones` (con `order_by=(created_at, id)`, sin `delete-orphan` y con `passive_deletes="all"`) y el helper `make_immutable` ya existen. Lo que agrega esta área:

- Dominio: `Ticket.add_milestone(content, author, now)` con la guarda de ticket cerrado delegada en el patrón State (SPEC-MLS-05), `Ticket.request_progress(user, now)` para el indicador `start_progress` (SPEC-TKT-09 y decisión 5), `TicketClosedError` y `make_immutable(Milestone)` (SPEC-MLS-09 y 10).
- Services: `TicketService.add_milestone` y `TicketService.list_milestones` (no hay `MilestoneService`, igual que en el diagrama de capas), y el validador `flag_error` para `start_progress`.
- Repositories: `SqlAlchemyTicketRepository.get_visible_with_milestones` con carga anticipada de los hitos y sus autores.
- Controllers: el blueprint nuevo `milestones` (el `MilestoneController` del diagrama), con `POST` y `GET /tickets/{ticket_id}/milestones`, los serializadores `milestone_json` y `author_json`, y la fila `TicketClosedError` → `409` `ticket_closed`.
- Contrato: esquemas `Milestone`, `MilestoneAuthor` y `AddMilestoneRequest`, la respuesta `TicketClosed` y las dos operaciones.
- Seguimiento de 04 por G-21 (decisión 9) y G-01 (opción B): reordenar `TicketService.add_products` y `TicketService.create_ticket` para que el formato del cuerpo preceda al `403` del rol (`Admin` en los dos; también `Client` al crear, SPEC-TKT-05), previa aprobación del texto de las decisiones 11 y 19 de la spec de 04.

Lo que **no** hace esta área: enviar notificaciones (SPEC-NTF-06, 08 y 09 son de `06-notifications`). El `NullTicketNotifier` sigue inyectado y **nadie llama a `notify`** en `add_milestone`, igual que en 04 (G-14 de 04).

## Componentes por capa

| Capa | Archivo | Responsabilidad | Specs |
|------|---------|-----------------|-------|
| Dominio | `app/domain/ticket.py` | `Ticket.add_milestone(content, author, now) -> Milestone`: delega en `self.state.add_milestone(self, content, author, now)`. `Ticket._append_milestone(content, author, now) -> Milestone`: el único lugar que crea un `Milestone` (también lo usa `Ticket.open` para el primer hito). `Ticket.request_progress(user, now)`: delega en `self.state.request_progress(self, user, now)` | MLS-01, 02, 03, 05, TKT-09 |
| Dominio | `app/domain/states.py` | `State.add_milestone(ticket, content, author, now)`: por defecto acepta y llama a `ticket._append_milestone`; `ClosedState.add_milestone` lo sobrescribe y lanza `TicketClosedError`. `State.request_progress(ticket, user, now)`: por defecto no hace nada; `NewState.request_progress` llama a `self.in_progress(ticket, user, now)` | MLS-05, TKT-09, dec. 5 |
| Dominio | `app/domain/milestone.py` | Suma `make_immutable(Milestone)` al final del módulo (listeners `before_update`/`before_delete` y triggers `milestones_no_update`/`milestones_no_delete`), como `state_change.py` | MLS-09, 10 |
| Dominio | `app/domain/errors.py` | Nueva subclase `TicketClosedError(DomainError)`, sin argumentos de constructor | MLS-05 |
| Services | `app/services/ticket_service.py` | `add_milestone(ticket_id, content, actor, start_progress=False) -> Milestone` y `list_milestones(ticket_id, actor) -> list[Milestone]`. El protocolo `TicketRepository` suma `get_visible_with_milestones`. Seguimiento de 04: `add_products` valida el formato antes de `_reject_admin` (T-MLS-20) y `create_ticket` llama a `_validate_creation` antes del chequeo de `Representative` (T-MLS-22) | MLS-01 a 08, 11, TKT-05, 09, 24, 27 |
| Services | `app/services/validation.py` | Suma `flag_error(value)`: `None` si es `bool`, `invalid` en cualquier otro caso (incluido `None`, que solo llega si el cliente envió `null`) | TKT-09, dec. 7 |
| Repositories | `app/repositories/ticket_repository.py` | `get_visible_with_milestones(ticket_id, actor)`: la misma guarda `fits_integer_column` y el mismo filtro por participante que `get_visible` (compartidos en un `_visible_statement` privado), más `selectinload(Ticket.milestones).selectinload(Milestone.author)`. Sin métodos de modificación ni de borrado | MLS-06, 07, 08 |
| Controllers | `app/controllers/milestones.py` (nuevo) | Blueprint `milestones` (el `MilestoneController` del diagrama de clases), registrado en `create_app`. `POST /tickets/<int:ticket_id>/milestones` pasa `body.get("content")` y `body.get("start_progress", False)`; `GET` pasa solo el id. Los dos con `login_required` y `wiring.get_ticket_service()` (sin wiring nuevo) | MLS-01 a 08, 11 |
| Controllers | `app/controllers/serializers.py` | Suma `author_json(user)` (los campos de `party_json` más `"role": user.role`) y `milestone_json(milestone)` | MLS-08 |
| Controllers | `app/controllers/errors.py` | Suma la fila `TicketClosedError: (409, "ticket_closed")` | MLS-05 |
| App | `app/__init__.py` | Registra el blueprint `milestones` | — |
| Contrato | `docs/openapi.json` | Esquemas `Milestone`, `MilestoneAuthor` y `AddMilestoneRequest`, respuesta `TicketClosed` y las operaciones `POST` y `GET /tickets/{ticket_id}/milestones` (con el `403` → `TicketForbidden`, como todo `/tickets`) | RNF 7 |

## Modelo de datos

Sin tablas ni columnas nuevas. Tabla `milestones` (creada en 04, sin cambios de columnas):

| Columna | Tipo | Restricciones | Notas |
|---------|------|---------------|-------|
| `id` | `Integer` | PK | Desempata el orden cronológico (SPEC-MLS-07) |
| `ticket_id` | `Integer` | `NOT NULL`, FK `tickets.id` `ON DELETE RESTRICT`, índice | |
| `author_id` | `Integer` | `NOT NULL`, FK `users.id` `ON DELETE RESTRICT` | Siempre el usuario autenticado (SPEC-MLS-03): el cliente dueño o el representante asignado |
| `content` | `Text` | `NOT NULL` | Solo texto, sin largo máximo (decisiones 1 y 8). Se guarda tal como llega, sin recortar (G-04) |
| `created_at` | `UtcDateTime` | `NOT NULL` | Instante del reloj inyectado (SPEC-MLS-03) |
| — | — | Triggers `milestones_no_update` y `milestones_no_delete` (nuevos) | `BEFORE UPDATE` / `BEFORE DELETE ... SELECT RAISE(ABORT, 'milestones rows are immutable')`, creados por `make_immutable` en el `after_create` de la tabla |

Relación `Ticket.milestones`: sin cambios. `Milestone.author`: `relationship()` hacia `User` (herencia de tabla única: el autor se carga como `Client` o `Representative` y su `role` sale del discriminador).

## Interfaz HTTP

Representación:

- `MilestoneAuthor`: `{"id", "name", "role"}`. `role` es `"Client"` o `"Representative"`. Sin email (mismo criterio que `TicketParty` en 04, G-12 de 04).
- `Milestone`: `{"id", "content", "author": MilestoneAuthor, "created_at"}`; `created_at` en ISO 8601 UTC.

| Método y ruta | Acceso | Éxito | Errores | Specs |
|---------------|--------|-------|---------|-------|
| `POST /tickets/{ticket_id}/milestones` `{"content", "start_progress"?}` | sesión; cliente dueño o representante asignado | `201` `Milestone` (el hito creado, G-03) | `400` `validation_error` (`content`: `required`/`invalid`; `start_progress`: `invalid`), `401`, `403` `forbidden` (`Admin`), `404` `ticket_not_found`, `409` `ticket_closed` | MLS-01 a 06, 11, TKT-09, 27 |
| `GET /tickets/{ticket_id}/milestones` | sesión; cliente dueño o representante asignado | `200` lista de `Milestone`, en orden cronológico ascendente | `401`, `403` `forbidden` (`Admin`), `404` `ticket_not_found` | MLS-06, 07, 08, TKT-27 |

`PATCH`, `PUT` y `DELETE` sobre `/tickets/{id}/milestones` responden `405` `method_not_allowed`, y cualquier ruta `/tickets/{id}/milestones/{milestone_id}` responde `404` `not_found`, los dos en JSON (SPEC-PLT-15, decisión 10). No se agrega código para eso.

**Precedencia al registrar un hito** (decisión 11, con las decisiones 4, 6, 7, 8 y 9). `401` lo resuelve antes `login_required`. Después, `TicketService.add_milestone`:

1. Formato del cuerpo → `400` `validation_error`, con `content` (`text_error`: ausente, `null`, vacío o solo espacios → `required`; otro tipo → `invalid`) y `start_progress` (`flag_error`: cualquier valor que no sea booleano → `invalid`; ausente vale `false`) informados juntos. Se decide **sin consultar el ticket** y **antes del rol** (G-21): el mismo cuerpo inválido da el mismo `400` para el `Admin`, para un ticket propio, ajeno, inexistente o fuera de rango (RNF 4).
2. `Admin` → `403` `forbidden` (SPEC-TKT-27).
3. Visibilidad (`get_visible`) → `404` `ticket_not_found` (SPEC-MLS-06, SPEC-TKT-19, 20 y 30), igual para inexistente, fuera de rango y ajeno.
4. Estado: `ticket.add_milestone` en un ticket `Closed` → `409` `ticket_closed` (SPEC-MLS-05), con o sin `start_progress`.
5. `start_progress`: solo si vale `true` **y** quien llama es el representante asignado, `ticket.request_progress(actor, now)`; en `New` pasa a `InProgress` con su `StateChange` (SPEC-TKT-09), en `InProgress` no hace nada (decisión 5). Si lo envía el cliente dueño, se ignora (decisión 6).
6. Un solo `commit` y `201`.

**Precedencia al listar** (decisión 12): `401` (`login_required`) → `Admin` → `403`, exista o no el ticket → visibilidad → `404`. Un ticket `Closed` se lista igual (SPEC-MLS-07 no tiene condición de estado, G-05).

Cuerpos de error nuevos o reutilizados:

| Excepción u origen | Status | Cuerpo |
|--------------------|--------|--------|
| `ValidationError` (existente) | `400` | `{"error": "validation_error", "fields": {"content": "required" \| "invalid", "start_progress": "invalid"}}` (solo los campos con error) |
| `PermissionDeniedError` (existente) | `403` | `{"error": "forbidden"}` |
| `TicketNotFoundError` (existente) | `404` | `{"error": "ticket_not_found"}` |
| `TicketClosedError` (**nueva**) | `409` | `{"error": "ticket_closed"}` (decisión 9) |

## Patrones aplicados

- **Capas Controller → Service → Repository**: el controller lee el JSON y serializa; el orden de chequeos, el rol, la visibilidad y el indicador `start_progress` viven en el service; el dominio decide si el estado acepta hitos.
- **State**: la guarda de ticket cerrado (SPEC-MLS-05) es un método del estado (`ClosedState.add_milestone` lanza `TicketClosedError`), no un `if state == "Closed"` (prohibición de AGENTS.md). El indicador `start_progress` usa otro método del estado (`request_progress`): solo `NewState` transiciona; los demás heredan el "no hacer nada" de `State` (decisión 5).
- **Composición**: el `Milestone` se crea solo a través de `Ticket.open` y `Ticket.add_milestone`, los dos por `Ticket._append_milestone`. No hay repositorio de hitos.
- **Inyección de dependencias y reloj inyectable**: `add_milestone` lee `clock()` una sola vez; el hito y, si hay transición, el `StateChange` comparten ese instante (SPEC-MLS-03, SPEC-TKT-14).
- **Tres barreras de inmutabilidad** (RNF 5) sobre `Milestone`: listeners, triggers de SQLite y relación sin `delete-orphan`, aplicadas con el mismo `make_immutable` que `StateChange`. Cada barrera se prueba por separado.
- **Registro en lugar de condicionales**: la fila nueva en `ERROR_RESPONSES`.

## Decisiones técnicas

| Decisión | Motivo y alternativas descartadas |
|----------|-----------------------------------|
| `Ticket.add_milestone(content, author, now)` recibe `now` | Convención de 04: el dominio no lee el reloj (AGENTS.md). El diagrama de clases dice `add_milestone(content, author)`; se sincroniza en T-MLS-17. |
| La guarda de cierre es `State.add_milestone` (acepta por defecto) con `ClosedState.add_milestone` que lanza `TicketClosedError` | AGENTS.md prohíbe `if` sobre el estado. A diferencia de las transiciones (rechazan por defecto), registrar un hito es lo normal y solo `Closed` lo rechaza, así que el valor por defecto es aceptar. Se descartó un atributo booleano `accepts_milestones` en cada estado (obliga a un `if` en `Ticket` sobre un dato del estado). |
| `Ticket._append_milestone(content, author, now)` es el único constructor de `Milestone`; `Ticket.open` lo reutiliza (refactor de T-MLS-01) | Un solo camino de creación (composición). TC-TKT-04a sigue en verde. |
| `start_progress` se resuelve con `Ticket.request_progress(user, now)` → `State.request_progress`: no hace nada por defecto, `NewState` llama a `in_progress` | Decisión 5: en `InProgress` el indicador se ignora (excepción explícita a SPEC-TKT-13). Se descartaron: atrapar `InvalidTransitionError` de `Ticket.start_progress` en el service (excepciones como control de flujo, y taparía errores reales), y preguntar el nombre del estado (prohibido). `Ticket.start_progress` no cambia (sigue rechazando en `InProgress` y `Closed`, TC-TKT-13a). |
| El service decide quién puede usar el indicador: `if start_progress and actor is ticket.representative` | Decisión 6: el permiso es del service (constitución, principio 3); el `if` es sobre el dato del pedido y el rol frente al ticket, no sobre el estado. |
| `request_progress` va **después** de `add_milestone` | Si el ticket está `Closed`, `add_milestone` ya lanzó `TicketClosedError` y no hubo transición (decisión 5, último punto). |
| `add_milestone` valida formato → `Admin` → visibilidad → estado | Decisiones 4, 9 y 11. El formato no consulta nada, así que no revela la existencia del ticket. Es el orden **inverso** al de `add_products` y `create_ticket` de 04 hoy (rol primero); el seguimiento de 04 (T-MLS-19 a 22) los alinea. |
| Seguimiento de 04: `create_ticket` valida formato (`client_id`, `first_message` y `product_ids` juntos, `400`) → rol (quien no es `Representative`, `403`) → cliente (`invalid_client`) → productos (`invalid_product`) | G-01, opción B. "Formato" es lo que se decide sin consultar la base (como `raise_if_invalid` en `add_milestone`); `invalid_client` e `invalid_product` consultan repositorios, así que quedan después del rol, igual que las referencias de `add_products` quedan después del `403` del asignado (G-06). Se descartó mover también esas verificaciones antes del rol: un `Admin` o un `Client` podría sondear qué clientes y productos existen. |
| Seguimiento de 04: dos tasks (T-MLS-20 para `add_products`, T-MLS-22 para `create_ticket`) | Un ciclo TDD por task. T-MLS-22 se agregó al re-sincronizar por G-01 (los IDs no se reutilizan); va después de T-MLS-20 porque comparten archivos. |
| `start_progress` ausente vale `false` en el controller (`body.get("start_progress", False)`) y `null` llega al service como `None` → `invalid` | Decisión 7: ausente y `null` se tratan distinto. Distinguirlos solo es posible donde está el JSON; el service recibe un valor y lo valida con `flag_error`. Se descartó un valor centinela propio en el service (más código para el mismo resultado). Un cuerpo que no es un objeto JSON es `{}` (`json_body`), así que da `content: required`. |
| `flag_error` en `validation.py` | Mismo estilo que `text_error`/`id_error` y reutilizable. `True`/`False` de JSON son `bool`; `1`, `"true"` y `null` no. |
| `list_milestones` usa `get_visible_with_milestones` (método nuevo) y no `get_visible` | AGENTS.md pide `selectinload` en los listados; el diagrama (§3) lo muestra. Se descartaron: agregar los hitos a `WITH_PARTICIPANTS_AND_PRODUCTS` (cargaría los hitos en cada listado y detalle de tickets) y un parámetro `with_milestones=True` en `get_visible` (bandera que cambia el comportamiento, criterio de 04). La guarda y el filtro se comparten en `_visible_statement` para no duplicar la regla de privacidad. Con los participantes ya en la sesión, el `selectinload` de autores suele no emitir consulta; el test de sentencias (TC-MLS-08a) lo fija igual. |
| `add_milestone` usa `get_visible` (sin cargar los hitos de antemano) | Agregar a la colección dispara una sola carga perezosa de los hitos de ese ticket; no es un listado. |
| `POST` responde `201` con el `Milestone` creado | La spec no fija el cuerpo (G-03). Con el hito en la respuesta, SPEC-MLS-03 se verifica sin otra consulta, y es la misma representación que el listado (una sola serialización). Se descartaron devolver el `Ticket` (no incluye hitos, G-12 de 04) y `201` sin cuerpo. |
| Blueprint propio `app/controllers/milestones.py` en lugar de sumar rutas a `tickets.py` | Coincide con el `MilestoneController` del diagrama de clases (no hay que cambiarlo) y evita que las tasks de endpoints de 05 compartan archivo con las de 04. Las rutas siguen bajo `/tickets/...`, así que las guardas de `/tickets` de 04 las ven. |
| `author_json` nuevo (`party_json` + `role`) en vez de cambiar `party_json` | SPEC-MLS-08 pide el rol del autor; agregarlo a `party_json` cambiaría la representación `TicketParty` de 04 sin spec. |
| Las rutas nuevas entran en `ALL_ENDPOINTS` y `TICKET_ENDPOINTS` de `tests/integration/tickets/test_tickets_permissions.py`, y los conteos de TC-TKT-27d y 27e pasan de 7 a 9 en las mismas tasks que agregan cada ruta | TC-TKT-27d compara `app.url_map` con la matriz y TC-TKT-27e cuenta las operaciones `/tickets` del contrato: una ruta nueva sin la matriz rompe la suite. Las matrices de 04 crecen como crecieron con cada endpoint de 04 (TC-TKT-19c, 20c, 27b, 30c y 30d). |
| Fixtures de 05 en `tests/integration/milestones/conftest.py` (nuevo) | Los fixtures `ana`, `raul`, etc. de 04 son locales de `test_tickets_api.py`. Se descartó moverlos a `tests/conftest.py` (tocaría tests de 04 sin necesidad). |
| `make_immutable(Milestone)` se prueba en un archivo propio (`tests/integration/milestones/test_milestone_immutability.py`), incluido el intérprete nuevo (equivalente a TC-TKT-16k para `milestones`) | No se tocan los tests de 04; el helper `run_fresh` se importa de `tests/integration/tickets/test_schema_registration.py`. |
| Nadie llama al notificador | SPEC-NTF-06, 08 y 09 son de `06-notifications`. El diagrama de secuencia mantiene los pasos `NS.notify` marcados como de 06 (mismo criterio que G-14 de 04). |
| `docs/openapi.json`: primero los componentes (T-MLS-12, sin rutas) y cada operación en la task de su endpoint, antes del código | SPEC-PLT-14 compara rutas y contrato en los dos sentidos (`tests/integration/platform/test_api_docs.py`); misma regla que 04. |

## Seguimiento de 04 por G-21 (decisión 9)

La decisión 9 de esta spec fija que, en `POST /tickets/{id}/milestones`, el formato precede al `403` del `Admin`, e indica que hay que alinear 04. El 2026-11-11 el usuario decidió el alcance y la forma: **G-01 → opción B** (rige para toda operación con cuerpo, incluida la creación del ticket, para el `Admin` y para el `Client`) y **G-02 → opción 1** (las decisiones 11 y 19 de 04 se editan en el lugar, anotando la inversión y la fecha; no se agrega una decisión 20). Como `spec.md` es la fuente de verdad y solo el equipo aprueba sus cambios, **este plan no edita la spec de 04**: T-MLS-19 la edita una vez que el usuario apruebe este texto. Propuesta:

- **Decisión 11** de 04, reemplazar *"Un `Admin` recibe `403` en toda operación (SPEC-TKT-27), antes de cualquier consulta. SPEC-TKT-05 (solo `Representative` crea) y SPEC-TKT-27 se superponen para el `Admin` que crea un ticket: es la misma excepción y el mismo `403`, con un caso de prueba por spec."* por: *"Un `Admin` recibe `403` en toda operación (SPEC-TKT-27), antes de cualquier consulta a la base. En las operaciones que reciben cuerpo (crear un ticket, asociar productos y registrar un hito de [05-milestones](../05-milestones/spec.md)), el `400` de formato precede a ese `403` (decisión 19). SPEC-TKT-05 (solo `Representative` crea) y SPEC-TKT-27 se superponen para el `Admin` que crea un ticket: es la misma excepción y el mismo `403`, con un caso de prueba por spec; con un cuerpo de formato inválido, el `Admin` y el `Client` que intentan crear reciben `400`. Modificada el 2026-11-11 (G-21 y G-01 de 05-milestones): antes, el `403` del `Admin` y el de SPEC-TKT-05 precedían al formato."* El resto de la decisión no cambia.
- **Decisión 19** de 04, reemplazar el texto por: *"**Precedencia entre `400`, `403` y `404` (SPEC-TKT-05, 19, 20, 24, 27 y 30)**: en toda operación que recibe cuerpo (crear un ticket, asociar productos y registrar un hito de [05-milestones](../05-milestones/spec.md)), el formato del cuerpo se valida antes que cualquier otra regla. Formato es lo que se decide sin consultar la base: campos ausentes, nulos, vacíos o de un tipo inválido (`required`/`invalid`). Un cuerpo con formato inválido responde `400` aunque quien llama sea `Admin` (o, al crear, `Client`) y aunque el ticket no exista o sea ajeno, y no revela si existe (RNF 4). Con un cuerpo de formato válido: al crear, quien no es `Representative` recibe `403` (SPEC-TKT-05 y 27) antes de que se verifiquen el cliente y los productos (`invalid_client` e `invalid_product`, decisión 9); en las operaciones sobre un ticket, un `Admin` recibe `403` (SPEC-TKT-27), un ticket inexistente o ajeno responde `404` y quien lo ve sin ser el representante asignado recibe `403` (decisión 11). Modificada el 2026-11-11 (G-21 y G-01 de 05-milestones): antes, el `403` del `Admin` y el de SPEC-TKT-05 precedían al formato, y esta decisión solo ordenaba el `400` frente al `404`."*

La fecha es la de la decisión del usuario (2026-11-11); si el texto se aprueba otro día, T-MLS-19 lo anota igual con la fecha de la decisión, salvo que el usuario indique otra.

Después de la aprobación:

- T-MLS-20 reordena `add_products` (formato → `Admin` → visibilidad → asignado → referencias) y agrega TC-TKT-24k y 24l.
- T-MLS-22 reordena `create_ticket` (formato → rol → cliente → productos), agrega TC-TKT-05c, 05d, 27i y 27j, y ajusta TC-TKT-27c (la entrada `POST /tickets` con cuerpo inválido pasa a un cuerpo de formato válido con un `client_id` inexistente, que sigue dando `403`: el rol precede a `invalid_client`). TC-TKT-05b no cambia de código (ya usa un cuerpo válido) y su descripción en 04 aclara que el `403` es con formato válido.
- T-MLS-21 actualiza `plan.md`, `tasks.md` y `test-plan.md` de 04 (la precedencia de `create_ticket` y de `add_products`, la fila G-21, la nota "El `Admin` primero", TC-TKT-05b, 27c y los casos nuevos) y las §1 y §5 de `diagrams/sequences/04-tickets.md`.

## Ajustes de redacción pendientes en la spec de 05 (para el equipo)

Detectados por el validador de requerimientos; no bloquean y este plan no los aplica:

- (a) Acotar SPEC-MLS-06 para que no cubra literalmente al `Admin` (hoy dice "quien no es el cliente dueño ni el representante asignado", y al `Admin` le corresponde `403` por la decisión 9). Redacción sugerida: *"**Si** un cliente que no es el dueño o un representante que no es el asignado intenta registrar el hito, …"*. El plan sigue la decisión 9 (`403`).
- (b) Citar SPEC-TKT-19 y 20 en la decisión 12, como lo hace la decisión 11.
- (c) Opcional: agregar `401` como paso 0 en las decisiones 11 y 12 y mencionar G-27 en el encabezado de las decisiones aprobadas el 2026-11-11.

## Re-sincronización del 2026-11-12

### Componentes (cambios)

| Capa | Archivo | Cambio | Specs |
|------|---------|--------|-------|
| Services | `app/services/ticket_service.py` | `list_milestones(ticket_id, actor)`: sin `_reject_admin`; el `Admin` usa `get_with_milestones(ticket_id)` y el resto `get_visible_with_milestones(ticket_id, actor)`, con la tabla por rol que `get_ticket` estrena en T-TKT-45; `None` → `TicketNotFoundError`. `add_milestone` no cambia | MLS-12 |
| Repositories | `app/repositories/ticket_repository.py` | `get_with_milestones(ticket_id)` lo agrega T-TKT-41 de 04 (sin filtro de participante, con la guarda de rango y la carga de hitos y autores) | MLS-12 |
| Controllers | `app/controllers/milestones.py` | Sin cambios: `GET` ya no lee `page` ni `page_size` | MLS-13 |
| Contrato | `docs/openapi.json` | `GET /tickets/{ticket_id}/milestones` deja de declarar `403` (lo hace T-TKT-48 de 04, que depende de T-MLS-23) | MLS-12, RNF 7 |

**Orden al listar** (decisión 13): (0) `401` sin sesión; (1) `404` `ticket_not_found` si el ticket no existe o es ajeno (un `Admin` nunca lo recibe por ajeno). **Orden al registrar** (decisión 11): sin cambios.

### Decisiones técnicas

| Decisión | Motivo y alternativas descartadas |
|----------|-----------------------------------|
| La lectura del `Admin` reutiliza la tabla por rol de `get_ticket` (04) en lugar de un `if isinstance` en `list_milestones` | Un solo lugar decide qué consulta usa cada rol para leer un ticket (detalle, hitos e historial). Se descartó que `get_visible_with_milestones` mire el rol (regla de negocio en el repositorio, ver el plan de 04). |
| Los casos de SPEC-TKT-27 de esta área se re-trazan: registrar → TC-TKT-32h a 32j; listar → TC-MLS-12a y 12c | La spec que trazaban está reemplazada; los IDs viejos quedan en el test-plan como registro y no se reutilizan. |
| SPEC-MLS-13 se verifica con un test sin código nuevo | El controller ya no lee `page` ni `page_size`; el test protege que nadie le agregue la convención de 00 por error. Pasa sin fase roja propia (se registra). |
| T-MLS-23 va después de T-TKT-46 y antes de T-TKT-48 y 49 | Las cuatro editan `app/services/ticket_service.py` o dependen del cambio de comportamiento (el contrato no debe quitar el `403` de la lectura antes de que el código lo haga). |

### Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Al quitar `_reject_admin` de `list_milestones` también se quita por error de `add_milestone` | TC-TKT-32h y 32j (re-trazados) siguen exigiendo `403` al registrar; TC-TKT-32a (04) incluye `add_milestone`. |
| Entre T-MLS-23 y T-TKT-48 el contrato todavía declara `403` en el `GET` de hitos | Transitorio y sin tests en rojo: TC-TKT-27e/32e exige el `403` hasta T-TKT-48, que lo invierte con su propio test en rojo. |

## Dependencias con otras áreas

- `00-platform`: `create_app`, `get_session`, `fits_integer_column`, `HTTP_ERROR_RESPONSES` (SPEC-PLT-15 para `PATCH`/`PUT`/`DELETE`), el contrato y su test de sincronización (SPEC-PLT-14).
- `01-users`: `login_required`, `authenticated_user`, `json_body`, `ValidationError`, `make_user`, `login_as`, `admin_client`, `CommitSpy`, `FakeUserRepository`, TC-USR-16d (cubre las 2 rutas nuevas sin cambios).
- `04-tickets`: `Ticket`, `Milestone`, `State` y sus subclases, `make_immutable`, `TicketService` (con `_reject_admin`, `_visible_ticket`, `commit`, `clock`), `SqlAlchemyTicketRepository`, `FakeTicketRepository`, `FakeClock`, `make_ticket`, `count_statements`, `party_json`, `TicketForbidden`, `TicketNotFound`, `ValidationFailed` y las matrices de `test_tickets_permissions.py`. Completa TC-TKT-09b. Modifica `add_products` y `create_ticket` (seguimiento G-21, condicionado a la aprobación del texto de las decisiones 11 y 19 de 04).
- `06-notifications`: usará `add_milestone` para SPEC-NTF-06, 08 y 09 (llamadas a `notify` después del `commit`, con o sin cambio de estado). Esta área no las agrega.

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Una base creada con `init-db` antes de esta área no tiene los triggers de `milestones` (`after_create` solo corre al crear la tabla; `create_all` no toca tablas existentes) | Los tests crean el esquema de cero. Para una base local vieja: borrar el archivo `.db` y correr `init-db` (sin migraciones, AGENTS.md). Se anota en el cierre (T-MLS-18) en `MEMORY.md`. |
| `make_immutable(Milestone)` se registra después de que algo ya creó la tabla, o el módulo no se importa en el camino normal | `app/domain/__init__.py` ya importa `milestone` (T-TKT-40). TC-MLS-09f lo verifica en un intérprete nuevo. |
| El listener rompe el flujo normal: agregar un hito a `ticket.milestones` hace `INSERT`, no `UPDATE`, pero un `flush` que toque un hito existente fallaría | Ningún camino modifica hitos. TC-MLS-01f y 07e ejercitan alta y listado con las barreras activas. |
| La guarda de cierre se implementa con un `if` sobre el estado | El diseño la pone en `ClosedState`; la revisión del PR lo controla y TC-MLS-05b (después de reabrir se acepta) prueba que depende del estado actual. |
| `start_progress` cambia el estado cuando lo envía el cliente, o rechaza un hito válido en `InProgress` | TC-MLS-01d, 01g, 02c y 02e (decisiones 5 y 6). |
| El hito y el `StateChange` quedan con instantes distintos | Una sola lectura de `clock()`: TC-MLS-03e con un reloj que cuenta sus lecturas, y TC-TKT-09b compara las fechas en la base. |
| Un N+1 al listar hitos con muchos autores | TC-MLS-08a compara las sentencias con 1 y con 6 hitos. |
| Un ticket ajeno se distingue de uno inexistente al responder o al listar | TC-MLS-06d y 06e comparan status y cuerpo; TC-MLS-04e, el `400` igual para todos con cuerpo inválido. |
| Agregar las rutas rompe TC-TKT-27d y 27e (cuentan 7) | Las tasks de cada endpoint (T-MLS-13 y 14) actualizan la matriz y los conteos en el mismo ciclo. |
| `add_milestone` queda con un orden distinto al de `add_products` y `create_ticket` (`400` antes o después del `403` del rol) mientras no se apruebe el texto de 04 | Es temporal y está registrado: T-MLS-19 a 22 lo cierran. Hasta entonces, un `Admin` con cuerpo inválido recibe `400` en hitos y `403` en productos y al crear. |
| Al mover el formato antes del rol en `create_ticket`, también se mueven las verificaciones de cliente y productos | T-MLS-22 deja `_find_client` y `_find_products` después del chequeo de `Representative`; TC-TKT-27c (ajustado), 27i y 05d fijan que un cuerpo de formato válido con un cliente inexistente sigue dando `403` para el `Admin` y el `Client`. |
| El contrato y las rutas se desincronizan | TC-PLT-14a y 14b en T-MLS-13 y 14. |

## Huecos y preguntas abiertas

Ninguno se resolvió en silencio. G-01 (alcance: opción B) y G-02 (forma: editar 11 y 19 en el lugar) los decidió el usuario el 2026-11-11 y salen de esta tabla; lo único pendiente para T-MLS-19 a 22 es que el usuario apruebe el texto de [Seguimiento de 04](#seguimiento-de-04-por-g-21-decisión-9). Los que siguen **no bloquean**: son comportamientos por defecto del plan, **a vetar por el usuario**; si alguno se veta, se re-sincroniza el plan y cambian los casos indicados.

| ID | Specs | Hueco | Comportamiento por defecto del plan (vetable) |
|----|-------|-------|-----------------------------------------------|
| G-03 | MLS-01, 02 | La spec no fija el cuerpo del `201` | `201` con el `Milestone` creado (ver decisiones técnicas). Casos: TC-MLS-01f, 02d, 03d y TC-TKT-09b |
| G-04 | MLS-01, 02, dec. 8 | No dice si el contenido se recorta | Se guarda tal como llega, sin recortar (mismo criterio que el primer mensaje, G-15 de 04). Caso: TC-MLS-01h |
| G-05 | MLS-07, 05 | No dice si se pueden listar los hitos de un ticket `Closed` | Sí: SPEC-MLS-07 no tiene condición de estado y SPEC-MLS-05 solo rechaza registrar. Casos: TC-MLS-07d y 07f |
| G-06 | TKT-05, 06, 08, 27, dec. 9 y 19 de 04 | Con G-01 opción B, "formato" podría leerse como incluyendo `invalid_client` e `invalid_product` (la decisión 9 de 04 los llama "validación del cuerpo") | Formato es solo lo que se decide sin consultar la base; cliente y productos se verifican después del rol (como las referencias de `add_products`). Va explícito en el texto propuesto de la decisión 19, así que la aprobación de T-MLS-19 lo cubre. Casos: TC-TKT-27c (ajustado), 27i y 05d |
