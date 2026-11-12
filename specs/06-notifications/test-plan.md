# 06 — Gestión de notificaciones · Test plan

Cada test cita en su docstring la spec y el caso: `"""SPEC-NTF-08 · TC-NTF-08b"""`. Los casos que además verifican una decisión de [spec.md](spec.md) la citan como **(dec. N)**. Cubre las 19 specs (SPEC-NTF-01 a 19); todas tienen al menos un caso. Re-sincronizado el 2026-11-12 tras resolver G-01 a G-07: los casos reemplazados figuran en [Casos retirados](#casos-retirados) y sus IDs no se reutilizan.

Fixtures existentes (`tests/conftest.py`): `app`, `client`, `schema`, `db_session`, `make_user` (suma `preferred_channel`, por defecto `"mail"`; T-NTF-13), `login_as`, `admin`, `admin_client`, `make_category`, `make_product_type`, `make_product` y `make_ticket` (abre el ticket con `Ticket.open`, sin notificaciones).

Fixtures nuevos (`tests/integration/notifications/conftest.py`):
- `world`: `ana` (cliente, `mail`), `wanda` (cliente, `whatsapp`), `raul` (representante, `mail`), el producto `xps` y el ticket de `ana` y `raul` creado con `make_ticket(ana, raul, [xps])` (estado `New`, sin notificaciones).
- `notification_rows(db_session)`: helper que hace `expire_all()` y devuelve las filas de `notifications` ordenadas por `id`.

Helpers existentes: `run_fresh(script)` (`tests/integration/tickets/test_schema_registration.py`, se importa sin editarlo).

Dobles para tests unitarios (sin Flask ni base):
- `RecordingStrategy` (`tests/unit/notifications/fakes.py`, nuevo): registra cada `send(recipient, message)` en `sent`.
- `FailingStrategy(reason)` (mismo archivo): lanza `NotificationError(reason)` en cada `send`.
- `FakeTicketNotifier`, `FakeTicketRepository` (`tests/unit/tickets/fakes.py`), `FakeUserRepository` (`tests/unit/users/fakes.py`), `FakeProductRepository` (`tests/unit/catalog/fakes.py`), `FakeClock` y `CommitSpy` (`tests/unit/fakes.py`): sin cambios.
- Notificador que mira el orden: clase local del test que, en `notify`, guarda `commit.calls` en ese momento (TC-NTF-15c).
- `commit` que lanza: clase local del test que lanza `RuntimeError` al llamarse (TC-NTF-15d).

Datos de referencia: `"Ana"` (cliente dueño) y `"Raúl"` (representante asignado). Todas las fechas son `datetime` con `tzinfo=UTC`. "El mensaje identifica el ticket y el evento" (SPEC-NTF-18, dec. 10) se verifica así: contiene `#<ticket.id>` y la palabra del evento (`created`, `milestone`, `closed`, `reopened`) y, si hay cambio de estado, el nuevo `state_name` (`InProgress`, `Closed`); nunca se compara la frase entera.

Archivos de test nuevos: `tests/unit/notifications/` (`__init__.py`, `fakes.py`, `test_notification.py`, `test_notification_strategies.py`, `test_progress_change.py`, `test_notification_messages.py`, `test_notification_service.py`, `test_ticket_notifications.py`, `test_notification_failure.py`) y `tests/integration/notifications/` (`__init__.py`, `conftest.py`, `test_notification_model.py`, `test_notifications_api.py`, `test_notification_failure.py`, `test_notifications_rejected.py`). Archivo compartido que se edita: `tests/conftest.py` (`make_user`).

## Matriz spec → casos

### Canal de envío

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| NTF-01 | TC-NTF-01a | unit | `NotificationService({"mail": mail_spy, "whatsapp": wa_spy}, clock, commit)`; `notify(ana_mail, raul, ticket, "m")` | `mail_spy.sent == [(ana_mail, "m")]`, `wa_spy.sent == []`; la notificación registrada tiene `channel == "mail"` | `tests/unit/notifications/test_notification_service.py` |
| NTF-01 | TC-NTF-01b | unit | `default_strategies()` | Sus claves son exactamente `NOTIFICATION_CHANNELS`; `["mail"]` es un `MailNotification` | `tests/unit/notifications/test_notification_strategies.py` |
| NTF-01 | TC-NTF-01c | integration | Sesión de `raul`; `POST /tickets` para `ana` (`mail`) | `201`; una fila en `notifications` con `recipient_id == ana.id` y `channel == "mail"` | `tests/integration/notifications/test_notifications_api.py` |
| NTF-02 | TC-NTF-02a | unit | Como 01a con un destinatario `whatsapp` | `wa_spy.sent == [(wanda, "m")]`, `mail_spy.sent == []`; `channel == "whatsapp"` | `tests/unit/notifications/test_notification_service.py` |
| NTF-02 | TC-NTF-02b | unit | `default_strategies()` | `["whatsapp"]` es un `WhatsappNotification` | `tests/unit/notifications/test_notification_strategies.py` |
| NTF-02 | TC-NTF-02c | integration | `wanda` creada con `make_user(preferred_channel="whatsapp")`; sesión de `raul`; `POST /tickets` para `wanda` | `201`; una fila con `recipient_id == wanda.id` y `channel == "whatsapp"` | `tests/integration/notifications/test_notifications_api.py` |
| NTF-12 | TC-NTF-12a | unit | `MailNotification().send(ana, "m")` y `WhatsappNotification().send(wanda, "m")` | Devuelven `None` sin lanzar | `tests/unit/notifications/test_notification_strategies.py` |
| NTF-12 | TC-NTF-12b | unit | Árbol sintáctico (`ast`) de `app/domain/notifications.py` | Solo importa `sqlalchemy`, módulos de `app.domain` y de la biblioteca estándar sin red (`collections.abc`, `datetime`, `typing`); ningún `smtplib`, `socket`, `http`, `urllib`, `requests` | `tests/unit/notifications/test_notification_strategies.py` |
| NTF-12 | TC-NTF-12c | integration | Sesión de `raul`; `POST /tickets` para `ana`; lectura en una sesión nueva | La notificación quedó registrada con `status == "sent"` y `error is None`: enviar es registrar | `tests/integration/notifications/test_notifications_api.py` |

### Registro y mensaje

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| NTF-03 | TC-NTF-03a | unit | `Ticket.open(ana, raul, [], "Hola", t0)`; `ticket.record_notification(ana, "mail", "m", t1)` | Devuelve una `Notification` que queda en `ticket.notifications` con `recipient is ana`, `channel == "mail"`, `message == "m"`, `created_at == t1` y `status == "sent"` | `tests/unit/notifications/test_notification.py` |
| NTF-03 | TC-NTF-03b | unit | `ticket.record_failed_notification(ana, "mail", "m", t1, "SMTP down")` | Queda en `ticket.notifications` con `status == "failed"` y el resto de los campos de NTF-03 como en 03a | `tests/unit/notifications/test_notification.py` |
| NTF-03 | TC-NTF-03c | unit | `FakeClock` en `t0`; `notify(ana, raul, ticket, "m")` con `RecordingStrategy` | Una notificación nueva en `ticket.notifications` con `created_at == t0`, `channel == ana.preferred_channel`, `message == "m"`, `status == "sent"`; `commit.calls == 1` | `tests/unit/notifications/test_notification_service.py` |
| NTF-03 | TC-NTF-03d | integration | `world.ticket.record_notification(ana, "mail", "m", t1)` y `record_failed_notification(raul, "mail", "m2", t2, "boom")`; `commit`; lectura en una sesión nueva | Dos filas con `ticket_id`, `recipient_id`, `channel`, `message`, `created_at` con `tzinfo` UTC y `status` (`sent`/`failed`); la columna `error` (de NTF-04) queda `NULL`/`"boom"`; `ticket.notifications` en orden `(created_at, id)` (puede pasar sin fase roja) | `tests/integration/notifications/test_notification_model.py` |
| NTF-03 | TC-NTF-03e | integration | `run_fresh`: tablas en `sqlite_master` | Código de salida `0`; existe `notifications` en el camino normal de `init-db` | `tests/integration/notifications/test_notification_model.py` |
| NTF-03 | TC-NTF-03f | integration | `session.execute(text("INSERT INTO notifications (...) VALUES (..., :status, ...)"), {"status": "pending", ...})` con parámetros enlazados | `IntegrityError` (`CHECK` `notifications_status_valid`); la tabla no cambia | `tests/integration/notifications/test_notification_model.py` |
| NTF-18 | TC-NTF-18a | unit | Parametrizado sobre las cinco funciones de `notification_messages` con un ticket de `id = 7` en el estado que corresponde **(dec. 10)** | Cada texto contiene `#7` y su evento: `created`; `milestone`; `milestone` e `InProgress`; `closed` y `Closed`; `reopened` e `InProgress`. Los cinco textos son distintos | `tests/unit/notifications/test_notification_messages.py` |
| NTF-18 | TC-NTF-18b | integration | Con `world`, por HTTP: `POST /tickets` (raul, para `ana`), un hito de `raul`, un hito con `start_progress`, `POST /tickets/{id}/close` (raul) y `POST /tickets/{id}/reopen` (raul) **(dec. 10)** | Cada fila nueva contiene `#<id>` de su ticket y la palabra de su evento en el orden de las operaciones; las que cambian el estado incluyen el nuevo (`InProgress`, `Closed`, `InProgress`) | `tests/integration/notifications/test_notifications_api.py` |

### Fallo de envío

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| NTF-04 | TC-NTF-04a | unit | `NotificationService` con `FailingStrategy("SMTP down")` para `mail`; `notify(ana, raul, ticket, "m")` | No lanza; una notificación con `status == "failed"`, `error == "SMTP down"`, `recipient is ana`, `channel == "mail"`, `message == "m"` y `created_at` del reloj; `commit.calls == 1` | `tests/unit/notifications/test_notification_service.py` |
| NTF-04 | TC-NTF-04b | unit | `NotificationError("SMTP down")` | Es un `DomainError` y `str(error) == "SMTP down"` | `tests/unit/notifications/test_notification_strategies.py` |
| NTF-04 | TC-NTF-04c | integration | `monkeypatch.setattr(wiring, "notification_strategies", lambda: {"mail": FailingStrategy("SMTP down"), "whatsapp": FailingStrategy("SMTP down")})`; sesión de `raul`; `POST /tickets/{id}/close` | Una fila nueva con `status == "failed"`, `error == "SMTP down"`, `recipient_id == ana.id` | `tests/integration/notifications/test_notification_failure.py` |
| NTF-04 | TC-NTF-04d | unit | `ticket.record_failed_notification(ana, "mail", "m", t1, "SMTP down")` y `ticket.record_notification(ana, "mail", "m", t1)` | La `failed` tiene `error == "SMTP down"`; la `sent` tiene `error is None` | `tests/unit/notifications/test_notification.py` |
| NTF-14 | TC-NTF-14a | unit | `TicketService` con fakes y un `NotificationService` real con `FailingStrategy` y el mismo `CommitSpy`; `close_ticket(ticket.id, raul)` | `commit.calls == 2` (operación primero, notificación después); el ticket queda en `Closed` con su `StateChange` en `state_history` y hay una notificación `failed` | `tests/unit/notifications/test_notification_failure.py` |
| NTF-14 | TC-NTF-14c | integration | App con `FailingStrategy` (`monkeypatch`); `POST /tickets` (raul), `POST /tickets/{id}/milestones` (raul) y `POST /tickets/{id}/close` (ana) | En una sesión nueva: el ticket, el hito y el cierre (estado `Closed` y su `StateChange`) están persistidos, y hay tres filas `failed` | `tests/integration/notifications/test_notification_failure.py` |
| NTF-19 | TC-NTF-19a | integration | Dos apps: una con las estrategias por defecto y otra con `FailingStrategy` (`monkeypatch`); en cada una, la misma secuencia de 14c | En las dos apps, el mismo status (`201`, `201`, `200`) y el mismo cuerpo salvo ids y fechas | `tests/integration/notifications/test_notification_failure.py` |
| NTF-19 | TC-NTF-19b | unit | Dos `TicketService` con fakes: uno con `NotificationService` + `RecordingStrategy` y otro con `NotificationService` + `FailingStrategy`; `close_ticket(ticket.id, raul)` en cada uno | Ninguno lanza; los dos devuelven el ticket en `Closed` con el mismo `state_name` y el mismo `state_history` (salvo fechas e ids) | `tests/unit/notifications/test_notification_failure.py` |

### Operaciones que no terminan con éxito

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| NTF-15 | TC-NTF-15a | unit | Parametrizado con `FakeTicketNotifier`: `create_ticket` con cuerpo inválido, por un `Client` y con cliente inexistente; `close_ticket` de un ticket ajeno, del `Admin` y de uno ya cerrado; `reopen_ticket` de uno abierto; `add_milestone` con contenido vacío, en un ticket cerrado y ajeno | Se lanza la excepción de cada caso (`ValidationError`, `PermissionDeniedError`, `InvalidClientError`, `TicketNotFoundError`, `InvalidTransitionError`, `TicketClosedError`); `notifier.calls == []` y `commit.calls == 0` en todos | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-15 | TC-NTF-15b | integration | Con `world`: `POST /tickets/{id}/milestones` `{"content": ""}` (`400`); `POST /tickets/{id}/close` sin sesión (`401`); `POST /tickets` como `ana` y cualquier `POST` como `admin` (`403`); `POST /tickets/9999/close` (`404`); `POST /tickets/{id}/reopen` de un ticket abierto (`409` `invalid_transition`) y un hito en un ticket cerrado (`409` `ticket_closed`) | El status esperado en cada uno y la cantidad de filas de `notifications` igual a la anterior a cada pedido (las filas del cierre previo se descuentan) | `tests/integration/notifications/test_notifications_rejected.py` |
| NTF-15 | TC-NTF-15c | unit | Notificador que guarda `commit.calls` al recibir `notify`; `create_ticket`, `close_ticket`, `reopen_ticket` y `add_milestone` exitosos | En cada operación, `notify` se llamó con `commit.calls == 1`: la notificación va después del `commit` | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-15 | TC-NTF-15d | unit | Parametrizado sobre `create_ticket`, `close_ticket`, `reopen_ticket` y `add_milestone` válidos, con `FakeTicketNotifier` y un `commit` que lanza `RuntimeError` | La `RuntimeError` se propaga y `notifier.calls == []` en todos | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-15 | TC-NTF-15e | integration | Con `world`, `app.config["PROPAGATE_EXCEPTIONS"] = False`; sesión de `raul`; dentro de `monkeypatch.context()`, `Session.commit` lanza `RuntimeError` y se hace `POST /tickets/{id}/close`; después, lectura en una sesión nueva | `500` `{"error": "internal_error"}`; el ticket sigue `New` (rollback de SPEC-PLT-08) y `notifications` no tiene filas | `tests/integration/notifications/test_notifications_rejected.py` |

### Notificaciones al cliente

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| NTF-05 | TC-NTF-05a | unit | `create_ticket(ana.id, [], "Hola", raul)` con `FakeTicketNotifier` **(dec. 4)** | `notifier.calls == [(ana, raul, ticket, msg)]` (exactamente una), con `msg` de creación (`#<id>`, `created`) | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-05 | TC-NTF-05b | integration | Sesión de `raul`; `POST /tickets` para `ana` **(dec. 4)** | `201`; exactamente una fila para el ticket, con `recipient_id == ana.id`, `status == "sent"` y el mensaje de creación (ninguna por el hito ni el estado iniciales) | `tests/integration/notifications/test_notifications_api.py` |
| NTF-06 | TC-NTF-06a | unit | Ticket `New`; `add_milestone(ticket.id, "Revisando", raul)` | Una llamada `(ana, raul, ticket, msg)` con `msg` de hito (`milestone`) y sin `InProgress` | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-06 | TC-NTF-06b | unit | Ticket `InProgress`; `add_milestone(ticket.id, "Sigo", raul, start_progress=True)` **(dec. 5)** | Una sola llamada, con el mensaje de hito (no el combinado) | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-06 | TC-NTF-06c | integration | Sesión de `raul`; `POST /tickets/{id}/milestones` `{"content": "Revisando"}` | `201`; una fila nueva para `ana` con el mensaje de hito | `tests/integration/notifications/test_notifications_api.py` |
| NTF-07 | TC-NTF-07a | unit | `close_ticket(ticket.id, raul)` | Una llamada `(ana, raul, ticket, msg)` con `closed` y `Closed` | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-07 | TC-NTF-07b | unit | Ticket cerrado; `reopen_ticket(ticket.id, raul)` | Una llamada `(ana, raul, ticket, msg)` con `reopened` e `InProgress` | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-07 | TC-NTF-07c | integration | Sesión de `raul`: `POST /tickets/{id}/close` y después `POST /tickets/{id}/reopen` | Dos filas nuevas para `ana`: la del cierre (`Closed`) y la de la reapertura (`InProgress`), en ese orden | `tests/integration/notifications/test_notifications_api.py` |
| NTF-08 | TC-NTF-08a | unit | `ticket.request_progress(raul, t1)` en `New`, y otra vez (ya en `InProgress`) | `True` la primera (pasa a `InProgress`) y `False` la segunda (sin cambios) | `tests/unit/notifications/test_progress_change.py` |
| NTF-08 | TC-NTF-08b | unit | Ticket `New`; `add_milestone(ticket.id, "Empiezo", raul, start_progress=True)` **(dec. 5)** | Exactamente una llamada `(ana, raul, ticket, msg)` con `milestone` e `InProgress` | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-08 | TC-NTF-08c | integration | Sesión de `raul`; `POST /tickets/{id}/milestones` `{"content": "Empiezo", "start_progress": true}` | `201`; exactamente una fila nueva para `ana` con el mensaje combinado; el ticket quedó `InProgress` | `tests/integration/notifications/test_notifications_api.py` |

### Notificaciones al representante

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| NTF-09 | TC-NTF-09a | unit | `add_milestone(ticket.id, "Gracias", ana)` y, en otro test, con `start_progress=True` (dec. 6 de 05) | Una llamada `(raul, ana, ticket, msg)` con el mensaje de hito en los dos (sin `InProgress`) | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-09 | TC-NTF-09b | integration | Sesión de `ana`; `POST /tickets/{id}/milestones` `{"content": "Gracias"}` | `201`; una fila nueva para `raul` con el mensaje de hito | `tests/integration/notifications/test_notifications_api.py` |
| NTF-10 | TC-NTF-10a | unit | Ticket cerrado; `reopen_ticket(ticket.id, ana)` | Una llamada `(raul, ana, ticket, msg)` con `reopened` | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-10 | TC-NTF-10b | integration | Ticket cerrado por `raul`; sesión de `ana`; `POST /tickets/{id}/reopen` | `200`; la última fila es para `raul` con el mensaje de reapertura | `tests/integration/notifications/test_notifications_api.py` |
| NTF-13 | TC-NTF-13a | unit | `close_ticket(ticket.id, ana)` | Una llamada `(raul, ana, ticket, msg)` con `closed` | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-13 | TC-NTF-13b | integration | Sesión de `ana`; `POST /tickets/{id}/close` | `200`; una fila nueva para `raul` con el mensaje de cierre | `tests/integration/notifications/test_notifications_api.py` |

### Exclusiones

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| NTF-11 | TC-NTF-11a | unit | `notify(ana, ana, ticket, "m")` con `RecordingStrategy` **(dec. 11)** | La estrategia no se llamó (`sent == []`); `ticket.notifications` no cambia (ninguna `Notification`, de ningún estado) y `commit.calls == 0` | `tests/unit/notifications/test_notification_service.py` |
| NTF-11 | TC-NTF-11b | unit | `notify(raul, raul, ticket, "m")` con `FailingStrategy` **(dec. 11)** | No lanza; la estrategia no se llamó; `ticket.notifications` no cambia (no hay fila `failed`) y `commit.calls == 0` | `tests/unit/notifications/test_notification_service.py` |
| NTF-16 | TC-NTF-16a | integration | El admin da de baja a `ana` (`POST /users/{id}/deactivate`); sesión de `raul`; `POST` de un hito **(dec. 9)** | `201`; una fila `sent` para `ana` aunque esté inactiva | `tests/integration/notifications/test_notifications_api.py` |
| NTF-16 | TC-NTF-16b | integration | El admin da de baja a `raul`; sesión de `ana`; `POST` de un hito **(dec. 9)** | `201`; una fila `sent` para `raul` aunque esté inactivo | `tests/integration/notifications/test_notifications_api.py` |
| NTF-16 | TC-NTF-16c | unit | `ana.is_active = False`; `notify(ana, raul, ticket, "m")` con `RecordingStrategy` | La estrategia se llamó con `(ana, "m")` y hay una notificación `sent` para `ana`; `commit.calls == 1` | `tests/unit/notifications/test_notification_service.py` |
| NTF-17 | TC-NTF-17a | unit | `add_products(ticket.id, [p.id], raul)` y `remove_product(ticket.id, p.id, raul)` exitosos con `FakeTicketNotifier` **(dec. 12)** | `notifier.calls == []` en los dos (sí hubo `commit`) | `tests/unit/notifications/test_ticket_notifications.py` |
| NTF-17 | TC-NTF-17b | integration | Sesión de `raul`: `POST /tickets/{id}/products` y `DELETE /tickets/{id}/products/{xps}` **(dec. 12)** | `200` en el `POST` y `204` en el `DELETE`; `notifications` sigue sin filas | `tests/integration/notifications/test_notifications_api.py` |

## Casos retirados

IDs que no se reutilizan (re-sincronización del 2026-11-12):

| Caso retirado | Motivo | Reemplazo |
|---------------|--------|-----------|
| TC-NTF-03g | El contenido del mensaje pasó de SPEC-NTF-03 a SPEC-NTF-18 (G-04) | TC-NTF-18a (mismo contenido) |
| TC-NTF-14b | SPEC-NTF-14 se dividió en NTF-14 (el cambio persiste) y NTF-19 (la misma respuesta) (G-05) | TC-NTF-14c y TC-NTF-19a |
| TC-NTF-06d | El destinatario inactivo tiene spec propia (G-03) | TC-NTF-16a |
| TC-NTF-09c | Ídem | TC-NTF-16b |
| TC-NTF-07d | Agregar o quitar productos tiene spec propia (G-03) | TC-NTF-17a |
| TC-NTF-07e | Ídem | TC-NTF-17b |

## Casos existentes de otras áreas que se tocan

- TC-MLS-01c y TC-TKT-09c (`request_progress`): siguen en verde con el retorno `bool` (T-NTF-04); no se editan.
- TC-PLT-14a y 14b: siguen en verde sin cambios en el contrato (decisión 3).
- Los tests de integración de 04 y 05 empiezan a escribir filas en `notifications` al conectar el wiring (T-NTF-13); no se editan.

## Casos borde

- Canal `mail` y `whatsapp`, y un registro que cubre todos los canales: TC-NTF-01a a 02c.
- Envío que falla: registro `failed` con el error (TC-NTF-04a, 04c, 04d), la operación no se revierte (TC-NTF-14a, 14c) y la respuesta es la misma (TC-NTF-19a, 19b), con el `commit` de la operación antes del de la notificación (TC-NTF-14a, 15c).
- Estado fuera de `sent`/`failed` rechazado por la base: TC-NTF-03f.
- Destinatario igual al actor, con estrategia que funciona y con una que falla: sin envío, sin fila y sin `commit` (TC-NTF-11a y 11b).
- Hito con `start_progress` redundante en `InProgress` (solo NTF-06): TC-NTF-06b. Hito que cambia el estado (una sola notificación combinada): TC-NTF-08a a 08c. `start_progress` enviado por el cliente (solo NTF-09): TC-NTF-09a.
- Creación: una sola notificación, sin las del hito ni el estado iniciales: TC-NTF-05a y 05b.
- Cierre y reapertura por cada participante (destinatario = el otro): TC-NTF-07a a 07c, 10a, 10b, 13a, 13b.
- Destinatario inactivo, cliente y representante: TC-NTF-16a, 16b y 16c.
- Productos agregados o quitados no notifican: TC-NTF-17a y 17b.
- Operaciones que no terminan con éxito con `400`, `401`, `403`, `404`, `409` y `500` con rollback: TC-NTF-15a, 15b, 15d y 15e.
- Mensajes de un flujo completo que identifican ticket y evento: TC-NTF-18a y 18b.
- Tabla registrada en un intérprete nuevo: TC-NTF-03e.
- Sin conexión a servicios externos: TC-NTF-12a y 12b.

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 1 (TDD; notificaciones nunca enviadas de verdad en los tests) | Todos los unitarios usan `RecordingStrategy`, `FailingStrategy` o `FakeTicketNotifier`; TC-NTF-12a y 12b (estrategias simuladas, sin red) |
| RNF 2 (autenticación y permisos) | TC-NTF-15b (`401` sin sesión y `403` del `Admin` y del `Client` al crear no notifican) |
| RNF 4 (privacidad de tickets) | TC-NTF-15a y 15b (un ticket ajeno o inexistente responde `404` y no genera notificación) |
| RNF 6 (auditoría de estado) | TC-NTF-14a y 14c (el `StateChange` del cierre persiste aunque la notificación falle); TC-NTF-15e (un `500` revierte el cierre y no notifica) |
| RNF 7 (documentación de la API) | TC-PLT-14a y 14b sin cambios: el área no agrega endpoints (decisión 3) |

## Resumen

54 casos activos (32 unit, 22 integration) sobre 19 specs; 6 casos retirados. Antes de la re-sincronización eran 47.
