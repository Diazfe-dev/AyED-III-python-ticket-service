# 06 — Gestión de notificaciones · Plan de implementación

Specs cubiertas: SPEC-NTF-01 a SPEC-NTF-19 ([spec.md](spec.md)), con las decisiones 1 a 12. RNF: 1 (TDD; las notificaciones nunca se envían de verdad en los tests, AGENTS.md) y 7 (la API no cambia: no hay endpoint, decisión 3).

> **Estado**: re-sincronizado el 2026-11-12 con la spec que resolvió G-01 a G-07 (aprobados por el usuario). No quedan huecos abiertos ni tasks bloqueadas. El desglose está en [tasks.md](tasks.md) (18 tasks, sin altas ni bajas) y los casos en [test-plan.md](test-plan.md).

## Enfoque

El área conecta el punto de extensión que dejó `04-tickets`: `TicketService` ya recibe un `TicketNotifier` (`notify(recipient, actor, ticket, message)`) y hoy se le inyecta `NullTicketNotifier`, que nadie llama. Lo que agrega esta área:

- Dominio: la entidad `Notification` (tabla `notifications`), la relación `Ticket.notifications` y los dos únicos constructores `Ticket.record_notification` y `Ticket.record_failed_notification` (composición, como `Milestone`); las estrategias `MailNotification` y `WhatsappNotification` (envío simulado, sin E/S) con el registro `default_strategies()`; `NotificationError`; y que `Ticket.request_progress` informe si cambió el estado (para SPEC-NTF-08).
- Services: `NotificationService` (implementa `TicketNotifier`: omite sin registrar si destinatario y actor son el mismo, elige la estrategia por `preferred_channel` con un diccionario, registra `sent` o `failed` y confirma con su `commit`), el módulo de mensajes `notification_messages` y las llamadas a `notify` en `TicketService` **después** del `commit` de cada operación que notifica.
- Wiring: `get_ticket_service` inyecta `NotificationService` en lugar de `NullTicketNotifier`, que se elimina.
- Sin repositorio nuevo, sin controller ni blueprint, sin cambios en `docs/openapi.json` (decisión 3).

## Componentes por capa

| Capa | Archivo | Responsabilidad | Specs |
|------|---------|-----------------|-------|
| Dominio | `app/domain/notifications.py` (nuevo) | `Notification` (mapeada, tabla `notifications`, relaciones `ticket` y `recipient`). `NotificationStrategy` (protocolo `send(recipient, message) -> None`), `MailNotification` y `WhatsappNotification` (no hacen E/S: el envío simulado es el registro que hace el service, decisión 2) y `default_strategies() -> dict[str, NotificationStrategy]` con una entrada por canal de `NOTIFICATION_CHANNELS`. Solo importa `sqlalchemy` y `app.domain` | NTF-01, 02, 03, 12 |
| Dominio | `app/domain/ticket.py` | `notifications: Mapped[list[Notification]]` (`back_populates="ticket"`, `order_by=(created_at, id)`, `passive_deletes="all"`). `record_notification(recipient, channel, message, now) -> Notification` (estado `sent`) y `record_failed_notification(recipient, channel, message, now, error) -> Notification` (estado `failed` con el texto del error), los dos por `_append_notification(...)`, el único lugar que crea una `Notification`. `request_progress(user, now) -> bool` devuelve lo que devuelve el estado | NTF-03, 04, 08 |
| Dominio | `app/domain/states.py` | `State.request_progress` devuelve `False`; `NewState.request_progress` transiciona y devuelve `True`. Sin otros cambios | NTF-08, dec. 5 |
| Dominio | `app/domain/errors.py` | `NotificationError(DomainError)` con `__init__(self, reason: str)`: el texto del error es `str(error)`. Sin fila en `ERROR_RESPONSES`: nunca sale de `NotificationService` (como `ImmutableRecordError`) | NTF-04 |
| Dominio | `app/domain/__init__.py` | Importa `notifications` (registro de la tabla en `create_schema`, como el resto de los modelos) | NTF-03 |
| Services | `app/services/notification_service.py` (nuevo) | `NotificationService(strategies, clock, commit)` con `notify(recipient, actor, ticket, message) -> None` (flujo abajo). No mira `is_active` (SPEC-NTF-16). Implementa estructuralmente `TicketNotifier` sin importar `ticket_service` | NTF-01 a 04, 11, 12, 14, 16, 19 |
| Services | `app/services/notification_messages.py` (nuevo) | Funciones puras que arman el texto en inglés: `ticket_created`, `milestone_added`, `milestone_and_state_changed`, `ticket_closed` y `ticket_reopened`. Cada una incluye `#<ticket.id>`, el evento y, si hay cambio de estado, el nuevo `state_name` | NTF-18 (dec. 10) |
| Services | `app/services/ticket_service.py` | `create_ticket`, `close_ticket`, `reopen_ticket` y `add_milestone` llaman a `self._notifier.notify(...)` después de `self._commit()`, con el destinatario de la [tabla de eventos](#destinatario-y-mensaje-por-evento). `_counterpart(ticket, actor)`: el otro participante. `add_products` y `remove_product` no notifican (SPEC-NTF-17). Se elimina `NullTicketNotifier` (queda sin uso); el protocolo `TicketNotifier` no cambia | NTF-05 a 10, 13, 15, 17 |
| Wiring | `app/wiring.py` | `notification_strategies()` (devuelve `default_strategies()`; es la costura que los tests de integración de NTF-04, 14 y 19 reemplazan con `monkeypatch`) y `get_ticket_service()` inyecta `NotificationService(notification_strategies(), utc_now, db_session.commit)` | NTF-01, 02, 12 |
| Repositories | — | Sin cambios. La `Notification` entra a la sesión por la cascada de `Ticket.notifications` (el ticket ya está en la sesión del request), igual que los hitos | — |
| Controllers | — | Sin cambios (decisión 3). La misma respuesta exitosa ante un fallo de envío (SPEC-NTF-19) sale de que `notify` no lanza | NTF-19 |
| Contrato | `docs/openapi.json` | Sin cambios (decisión 3); TC-PLT-14a y 14b siguen en verde | RNF 7 |

## Modelo de datos

Tabla nueva `notifications`:

| Columna | Tipo | Restricciones | Notas |
|---------|------|---------------|-------|
| `id` | `Integer` | PK | Desempata el orden de `Ticket.notifications` |
| `ticket_id` | `Integer` | `NOT NULL`, FK `tickets.id` `ON DELETE RESTRICT`, índice | El ticket que la originó (SPEC-NTF-03) |
| `recipient_id` | `Integer` | `NOT NULL`, FK `users.id` `ON DELETE RESTRICT` | Destinatario (puede estar inactivo, SPEC-NTF-16) |
| `channel` | `String(20)` | `NOT NULL` | El `preferred_channel` del destinatario al momento del envío (SPEC-NTF-03) |
| `message` | `Text` | `NOT NULL` | Texto en inglés que identifica ticket y evento (SPEC-NTF-18) |
| `created_at` | `UtcDateTime` | `NOT NULL` | Instante del reloj del `NotificationService` en UTC (SPEC-NTF-03, dec. 7) |
| `status` | `String(10)` | `NOT NULL`, `CHECK (status IN ('sent', 'failed'))` (`notifications_status_valid`) | SPEC-NTF-03. Sin tercer estado: la omisión de SPEC-NTF-11 no se registra |
| `error` | `Text` | nullable | Texto del error cuando `status = 'failed'` (SPEC-NTF-04); `NULL` si `sent` |

Relaciones: `Ticket.notifications` (composición, sin `delete-orphan`, `passive_deletes="all"`), `Notification.ticket` y `Notification.recipient` (`relationship()` hacia `User`; herencia de tabla única). La spec no pide inmutabilidad para `Notification`: no se aplica `make_immutable` y tampoco existe código que las modifique o borre.

## Flujo de `NotificationService.notify`

1. Si `recipient is actor` → retorna sin llamar a la estrategia, sin registrar y sin `commit` (SPEC-NTF-11, dec. 11).
2. `channel = recipient.preferred_channel`; `strategy = self._strategies[channel]` (búsqueda en diccionario, sin `if` por canal: SPEC-NTF-01 y 02, AGENTS.md). No se consulta `recipient.is_active` (SPEC-NTF-16).
3. `now = self._clock()` (una sola lectura).
4. `strategy.send(recipient, message)`:
   - sin excepción → `ticket.record_notification(recipient, channel, message, now)` (`sent`);
   - `NotificationError` → `ticket.record_failed_notification(recipient, channel, message, now, str(error))` (`failed`, SPEC-NTF-04). La excepción no se propaga (SPEC-NTF-14 y 19).
5. `self._commit()`.

**Quién construye y quién confirma**: la `Notification` la construye el `Ticket` (composición); el `NotificationService` decide el estado y confirma con su `commit` inyectado (en producción, el mismo `session.commit` del request). Los repositorios nunca confirman (AGENTS.md).

**Fallo y operación del ticket (SPEC-NTF-04, 14 y 19)**: `TicketService` ya hizo `commit` de la operación antes de llamar a `notify`, así que el fallo no la puede revertir (SPEC-NTF-14). La estrategia falla **antes** de tocar la sesión (la sesión está limpia después del `commit` del ticket), por eso registrar el fallo es un `INSERT` más en una transacción nueva y no hace falta un `rollback` ni un patrón especial. `notify` retorna normalmente y el controller responde lo mismo que sin fallo (SPEC-NTF-19).

## Destinatario y mensaje por evento

El destinatario es siempre el otro participante: `_counterpart(ticket, actor)` devuelve `ticket.client` si `actor is ticket.representative` y `ticket.representative` en otro caso (es un `if` sobre la identidad del actor frente al ticket, no sobre el estado ni el canal). El `Admin` nunca llega a notificar: recibe `403` antes (SPEC-TKT-27). El destinatario se notifica aunque esté inactivo (SPEC-NTF-16).

| Operación de `TicketService` | Actor | Destinatario | Mensaje | Spec |
|------------------------------|-------|--------------|---------|------|
| `create_ticket` | Representante | Cliente | `ticket_created` | NTF-05 (una sola; el hito y el estado iniciales no notifican, dec. 4) |
| `add_milestone` sin cambio de estado (también `start_progress` redundante en `InProgress`) | Representante | Cliente | `milestone_added` | NTF-06 (dec. 5) |
| `add_milestone` con `start_progress` que pasa de `New` a `InProgress` | Representante | Cliente | `milestone_and_state_changed` (una sola) | NTF-08 |
| `add_milestone` (su `start_progress` se ignora, dec. 6 de 05) | Cliente | Representante | `milestone_added` | NTF-09 |
| `close_ticket` | Representante | Cliente | `ticket_closed` (nuevo estado `Closed`) | NTF-07 |
| `close_ticket` | Cliente | Representante | `ticket_closed` | NTF-13 |
| `reopen_ticket` | Cliente | Representante | `ticket_reopened` (nuevo estado `InProgress`) | NTF-10 |
| `reopen_ticket` | Representante | Cliente | `ticket_reopened` (nuevo estado `InProgress`) | NTF-07 |
| `add_products`, `remove_product` | Representante | — | — | NTF-17 |
| Cualquier operación que no termina con éxito: excepción antes del `commit` (`400`, `401`, `403`, `404`, `409`) o falla del propio `commit` (`500` con rollback de SPEC-PLT-08) | — | — | — | NTF-15 |

**Regla de SPEC-NTF-08 frente a 06 y 07**: en `add_milestone`, `changed = bool(start_progress and actor is ticket.representative and ticket.request_progress(actor, now))`. `request_progress` devuelve `True` solo si `NewState` hizo la transición; en `InProgress` devuelve `False` (decisión 5). El mensaje se elige con `{True: milestone_and_state_changed, False: milestone_added}[changed]` y se envía **una** notificación. SPEC-NTF-07 ("cambio de estado sin hito") corresponde solo a `close_ticket` y `reopen_ticket` del representante: no existe otra forma de cambiar el estado sin hito.

**Mensajes** (SPEC-NTF-18 y decisión 10, en inglés por AGENTS.md; el texto exacto no es contrato): `"Ticket #<id> was created."`, `"Ticket #<id> has a new milestone."`, `"Ticket #<id> has a new milestone and its state changed to <state>."`, `"Ticket #<id> was closed. New state: Closed."`, `"Ticket #<id> was reopened. New state: InProgress."`. Los tests verifican los datos (`#<id>`, la palabra del evento y el estado nuevo), no la frase.

## Patrones aplicados

- **Strategy** (SPEC-NTF-01 y 02): `NotificationService` recibe por constructor `strategies: Mapping[str, NotificationStrategy]` y elige con `strategies[recipient.preferred_channel]`. Un canal nuevo es una clase nueva y una entrada en `default_strategies()`; no hay `if`/`elif` por canal (prohibición de AGENTS.md).
- **Composición**: `Notification` se crea solo por `Ticket._append_notification` (`classes.md` y AGENTS.md: "existen solo dentro de un `Ticket`"). No hay repositorio de notificaciones, como no lo hay de hitos.
- **State**: SPEC-NTF-08 se detecta con el valor que devuelve el estado (`request_progress`), no preguntando el nombre del estado.
- **Inyección de dependencias y reloj inyectable**: `NotificationService(strategies, clock, commit)`; los tests unitarios usan una estrategia que registra los envíos (AGENTS.md) y otra que falla a propósito (SPEC-NTF-04).
- **Null Object eliminado**: `NullTicketNotifier` deja de tener uso y se borra (nada de código huérfano).

## Decisiones técnicas

| Decisión | Motivo y alternativas descartadas |
|----------|-----------------------------------|
| `notify` se llama **después** del `commit` de la operación del ticket, con un segundo `commit` para la notificación | Es lo que fijaron los planes de 04 y 05 y los diagramas de secuencia. Una operación rechazada lanza antes del `commit`, y un `commit` que falla lanza en el propio `commit`: ninguna llega a `notify` (SPEC-NTF-15, incluidos el `401` y el `500` con rollback). Se descartó un único `commit` con la notificación adentro: obligaría a enviar antes de confirmar, y un envío real quedaría hecho aunque el `commit` del ticket fallara. |
| La omisión de SPEC-NTF-11 no registra nada ni confirma | Spec (G-01 resuelto, opción A): "omitir el envío y no registrar la notificación". Por eso no hay estado `skipped` y el `CHECK` queda en `sent`/`failed`. |
| La `Notification` la crea `Ticket.record_notification` / `record_failed_notification` y entra a la sesión por cascada; sin `NotificationRepository` | `classes.md` (composición, `Ticket.notifications`) y SPEC-NTF-03 ("asociada al ticket"). Misma solución que los hitos en 05. Se descartó `NotificationRepository.add` (diagrama de capas actual): una segunda vía de creación que contradice la composición del mismo diagrama. T-NTF-17 quita `NotificationRepository` de `classes.md` y del diagrama de secuencia. |
| `NotificationService` confirma con su propio `commit` inyectado | AGENTS.md: la transacción es del service, nunca del repositorio. El diagrama de secuencia de 06 muestra `NR.commit()`; se corrige en T-NTF-17. |
| Dos métodos (`record_notification` y `record_failed_notification`) en vez de un parámetro `status` | El estado sale del método elegido, sin `if error is None` ni un valor libre; el `CHECK` de la base es la segunda barrera. |
| Solo `NotificationError` cuenta como fallo de envío; otra excepción se propaga | Las estrategias declaran su fallo con `NotificationError` (una estrategia real traduciría sus errores). Atrapar `Exception` taparía bugs (por ejemplo, un `KeyError` por un canal sin estrategia). Riesgo anotado abajo. |
| `NotificationError(reason)` hereda de `DomainError` y vive en `app/domain/errors.py` | La lanzan las estrategias del dominio y el dominio no importa services. Sin respuesta HTTP: no sale del service. Se descartó una excepción en `notification_service.py` (las estrategias del dominio no podrían importarla). |
| Las estrategias viven en `app/domain/notifications.py` | AGENTS.md (estructura) y la vista de dominio de `classes.md` las ubican ahí; no hacen E/S, así que respetan la regla "el dominio solo importa `sqlalchemy`". Se descartó ponerlas en `services/` (contradice los dos documentos). |
| `default_strategies()` en el dominio y `notification_strategies()` en `wiring.py` | La primera garantiza una estrategia por canal de `NOTIFICATION_CHANNELS` (TC-NTF-01b y 02b); la segunda es la costura para que los tests de integración inyecten una estrategia que falla (`monkeypatch` sobre `wiring`), sin agregar configuración de producción solo para tests. Se descartó una clave de `app.config` con las estrategias. |
| `Ticket.request_progress` devuelve `bool` | SPEC-NTF-08 necesita saber si el hito cambió el estado. Se descartaron comparar `state_name` antes y después (un `if` sobre nombres de estado, contra el patrón State) y comparar el largo de `state_history` (carga perezosa extra y acopla el service a la auditoría). TC-MLS-01c y TC-TKT-09c siguen en verde. |
| Mensajes en un módulo propio `notification_messages.py`, en inglés | Funciones puras, testeables sin el service (SPEC-NTF-18); AGENTS.md pide código y textos de código en inglés y la spec dice que el texto no es contrato. Los diagramas pasan a mostrar el nombre de la función, no frases en español. |
| `NotificationService` compara `recipient is actor` | Mismo criterio que `actor is ticket.representative` en `TicketService`: en el request hay una sola sesión y un solo objeto por fila. Comparar `id` daría verdadero entre dos usuarios sin guardar (`None == None`) en los tests unitarios. |
| `make_user` suma `preferred_channel: str = "mail"` | SPEC-NTF-02 de punta a punta necesita un usuario `whatsapp`; el valor por defecto no cambia ningún test existente. |
| Fixtures de 06 en `tests/integration/notifications/conftest.py` | Mismo criterio que 05: no se tocan los fixtures locales de 04 ni de 05. `make_ticket` llama a `Ticket.open` sin pasar por el service, así que el ticket de partida no tiene notificaciones. |
| El `500` con rollback de SPEC-NTF-15 se provoca en el test haciendo fallar `Session.commit` durante el pedido, con `PROPAGATE_EXCEPTIONS` apagado en la app del test | Recorre el camino de producción (manejador del `500` y rollback de SPEC-PLT-08) sin agregar rutas de prueba ni código de producción. Se descartó una ruta de prueba como la de TC-PLT-08b: no pasa por `TicketService` ni por el notificador. |
| Se elimina `NullTicketNotifier` | Sin uso en producción ni en tests (los unitarios usan `FakeTicketNotifier`). |
| Sin cambios en `docs/openapi.json` ni tasks de contrato | Decisión 3: las notificaciones son internas y no tienen endpoint. |

## Dependencias con otras áreas

- `01-users`: `User.preferred_channel` (SPEC-USR-06 y 23), `NOTIFICATION_CHANNELS`, `is_active` (SPEC-NTF-16), `make_user` (se extiende), `login_as`, `admin_client`, `POST /users/{id}/deactivate` (SPEC-USR-09, solo para preparar los casos de destinatario inactivo).
- `04-tickets`: `Ticket`, `State`, `TicketService` (`create_ticket`, `close_ticket`, `reopen_ticket`, `add_products`, `remove_product`), `TicketNotifier`, `FakeTicketRepository`, `FakeTicketNotifier`, `FakeClock`, `CommitSpy`, `make_ticket`, `run_fresh`, los endpoints de `/tickets` y sus errores (SPEC-TKT-01, 04, 05, 07, 09, 10, 11, 12, 14, 15, 19, 20, 21, 24, 26, 27).
- `05-milestones`: `TicketService.add_milestone`, `Ticket.request_progress` (cambia su retorno), dec. 5 y 6 de 05, `POST /tickets/{id}/milestones` (SPEC-MLS-01, 02, 03, 05).
- `00-platform`: `create_schema`, `get_session`, `UtcDateTime`, el rollback y el `500` JSON (SPEC-PLT-08 y 16, para TC-NTF-15e), SPEC-PLT-14 (contrato sin cambios).

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| El `commit` de la notificación falla (error de base) después de confirmado el ticket: la respuesta sería `500` con el ticket ya cambiado | Fuera de las specs (no es un fallo de envío: SPEC-NTF-04, 14 y 19 hablan del envío). Se anota en `MEMORY.md` (T-NTF-18). La tabla no tiene restricciones que un caso normal pueda violar. |
| Una estrategia lanza algo que no es `NotificationError` | Las dos estrategias simuladas no lanzan; TC-NTF-12a lo fija. Una estrategia real debe traducir sus errores (nota en `classes.md`). |
| Al conectar `NotificationService`, los tests de integración de 04 y 05 empiezan a escribir filas en `notifications` | Ningún test existente cuenta tablas totales; T-NTF-13 y 14 corren la suite completa. |
| `notifications` no se registra en una base nueva (módulo no importado) | `app/domain/__init__.py` lo importa y `ticket.py` lo usa; TC-NTF-03e lo verifica en un intérprete nuevo. Una base local vieja no tiene la tabla: `create_all` la crea al correr `init-db` (tabla nueva, no columna nueva). |
| SPEC-NTF-11 solo se alcanza llamando al service directamente | Casos unitarios (TC-NTF-11a y 11b); decisión 11 de la spec. |
| SPEC-NTF-08 envía también la de SPEC-NTF-06 | TC-NTF-08b y 08c cuentan exactamente una llamada y una fila. |
| Se notifica una operación que no terminó con éxito | `notify` va después del `commit`; TC-NTF-15a y 15d (unit: excepciones de las operaciones y `commit` que falla) y 15b y 15e (HTTP `400`, `401`, `403`, `404`, `409` y `500` con rollback). |
| Monkeypatchear `Session.commit` en TC-NTF-15e afecta la sesión del propio test | El parche se limita al pedido (`monkeypatch.context()`) y las lecturas posteriores usan una sesión nueva. |
| Un filtro por `is_active` se cuela en `NotificationService` | TC-NTF-16a, 16b y 16c. |
| Un `if` por canal o por estado se cuela | Diccionario de estrategias y retorno de `request_progress`; la revisión del PR lo controla. |
| Los diagramas siguen diciendo "no implementado" o muestran `NR.commit()` | T-NTF-17. |

## Huecos y preguntas abiertas

Ninguno abierto. G-01 a G-07 los aprobó el usuario el 2026-11-12 y quedaron en `spec.md`:

| ID | Resolución en la spec | Efecto en este plan |
|----|-----------------------|---------------------|
| G-01 | SPEC-NTF-11: omitir el envío y no registrar la notificación (sin estado `skipped`; dec. 11) | T-NTF-08 desbloqueada; TC-NTF-11a y 11b esperan sin fila ni `commit` |
| G-02 | SPEC-NTF-15 cubre cualquier `4xx`/`5xx`, incluidos el `401` y un `500` con rollback (dec. 8) | TC-NTF-15b cita NTF-15 sin marca; casos nuevos TC-NTF-15d y 15e para el `500` |
| G-03 | SPEC-NTF-16 (destinatario inactivo) y SPEC-NTF-17 (productos no notifican) | TC-NTF-06d, 09c, 07d y 07e se retiran y los reemplazan TC-NTF-16a, 16b, 17a y 17b; se suma TC-NTF-16c |
| G-04 | SPEC-NTF-03 solo lista los campos; el texto del error es de SPEC-NTF-04; SPEC-NTF-18 para el contenido del mensaje | TC-NTF-03g se retira y lo reemplaza TC-NTF-18a; el texto del error pasa a TC-NTF-04d; se suma TC-NTF-18b |
| G-05 | SPEC-NTF-14 (el cambio persiste) y SPEC-NTF-19 (la misma respuesta exitosa) | TC-NTF-14b se retira y lo reemplazan TC-NTF-14c y TC-NTF-19a; se suma TC-NTF-19b |
| G-06 | Encabezado "Depende de" completado | Sin impacto en el diseño |
| G-07 | Decisión 5: "excluye a" | Sin impacto en el diseño |

Notas de sincronización fuera de la spec (las cubren T-NTF-17 y 18): los diagramas citan solo SPEC-NTF-04 para el fallo (faltan NTF-14 y 19) y no citan NTF-16 a 19; `MEMORY.md` cuenta 13 specs NTF (son 19).
