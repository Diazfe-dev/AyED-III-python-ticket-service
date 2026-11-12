# Secuencias — 06 Notificaciones

Spec: [specs/06-notifications/spec.md](../../specs/06-notifications/spec.md)

`NotificationService(strategies, clock, commit).notify(recipient, actor, ticket, message)` es el único punto de entrada. `TicketService` lo llama como última acción de la operación, **después** de su propio `commit()`, mediante `_notify_counterpart` (cierre, reapertura e hitos) o directo al cliente (creación). Los mensajes salen de las funciones de `app/services/notification_messages.py`.

No hay `NotificationRepository`: la `Notification` se crea solo a través del ticket (`Ticket.record_notification` y `Ticket.record_failed_notification`, ambas por `_append_notification`) y la persiste el `commit()` que recibe el `NotificationService`.

SPEC-NTF-15: se notifica solo después de un `commit()` exitoso del ticket; una operación que termina en `4xx` o `500` nunca llega a `notify`.

## Matriz de eventos

| Evento | Quién actúa | Destinatario | Spec |
|--------|-------------|--------------|------|
| Ticket creado (`ticket_created`) | Representante | Cliente | SPEC-NTF-05 |
| Nuevo hito (`milestone_added`) | Representante | Cliente | SPEC-NTF-06 |
| Cambio de estado (`ticket_closed` / `ticket_reopened`) | Representante | Cliente | SPEC-NTF-07 |
| Hito y cambio de estado juntos (`milestone_and_state_changed`) | Representante | Cliente (una sola notificación) | SPEC-NTF-08 |
| Respuesta (hito, `milestone_added`) | Cliente | Representante | SPEC-NTF-09 |
| Reapertura (`ticket_reopened`) | Cliente | Representante | SPEC-NTF-10 |
| Cierre (`ticket_closed`) | Cliente | Representante | SPEC-NTF-13 |

## 1. Envío con patrón Strategy

Specs: SPEC-NTF-01, 02, 03, 11, 12, 16, 18

```mermaid
sequenceDiagram
    autonumber
    participant TS as TicketService
    participant NS as NotificationService
    participant ST as NotificationStrategy (Mail / Whatsapp)
    participant T as Ticket

    TS->>TS: commit() de la operación del ticket
    TS->>NS: notify(recipient, actor, ticket, message)
    Note over TS,NS: message viene de notification_messages (ticket_created, milestone_added, ...) e identifica ticket y evento (SPEC-NTF-18)
    alt recipient es el mismo usuario que actor
        NS-->>TS: retorna sin enviar, sin leer el reloj, sin registrar y sin commit (SPEC-NTF-11)
    else recipient distinto de actor
        Note over NS: No se consulta is_active: un destinatario inactivo se notifica igual (SPEC-NTF-16)
        NS->>NS: strategy = strategies[recipient.preferred_channel]
        Note over NS: "mail" → MailNotification (SPEC-NTF-01)<br/>"whatsapp" → WhatsappNotification (SPEC-NTF-02)
        NS->>NS: now = clock() (una sola lectura)
        NS->>ST: send(recipient, message)
        Note over ST: Envío simulado: no hay SMTP ni API externa (SPEC-NTF-12)
        ST-->>NS: ok
        NS->>T: record_notification(recipient, channel, message, now)
        T->>T: _append_notification(...) crea Notification(status="sent", error=None) (SPEC-NTF-03)
        NS->>NS: commit() (el que recibe el service, no un repositorio)
        NS-->>TS: ok
    end
```

## 2. Falla en el envío

Specs: SPEC-NTF-04, 14, 19

```mermaid
sequenceDiagram
    autonumber
    participant TS as TicketService
    participant NS as NotificationService
    participant ST as NotificationStrategy
    participant T as Ticket

    TS->>TS: commit() de la operación del ticket
    Note over TS: El cambio del ticket ya quedó persistido (SPEC-NTF-14)
    TS->>NS: notify(recipient, actor, ticket, message)
    NS->>NS: now = clock() (una sola lectura)
    NS->>ST: send(recipient, message)
    ST-->>NS: raise NotificationError(reason) (app/domain/errors.py)
    NS->>T: record_failed_notification(recipient, channel, message, now, str(error))
    T->>T: _append_notification(...) crea Notification(status="failed", error=texto) (SPEC-NTF-04)
    NS->>NS: commit()
    NS-->>TS: retorna sin propagar la excepción
    Note over TS: La operación devuelve la misma respuesta exitosa que sin fallo (SPEC-NTF-19)
```
