# Secuencias — 06 Notificaciones

Spec: [specs/06-notifications/spec.md](../../specs/06-notifications/spec.md)

`NotificationService.notify(recipient, actor, ticket, message)` es el único punto de entrada. Lo llaman los services de tickets e hitos **después** del `commit()` de la operación del ticket.

## Matriz de eventos

| Evento | Quién actúa | Destinatario | Spec |
|--------|-------------|--------------|------|
| Ticket creado | Representante | Cliente | SPEC-NTF-05 |
| Nuevo hito | Representante | Cliente | SPEC-NTF-06 |
| Cambio de estado | Representante | Cliente | SPEC-NTF-07 |
| Hito y cambio de estado juntos | Representante | Cliente (una sola notificación) | SPEC-NTF-08 |
| Respuesta (hito) | Cliente | Representante | SPEC-NTF-09 |
| Reapertura | Cliente | Representante | SPEC-NTF-10 |
| Cierre | Cliente | Representante | SPEC-NTF-13 |

## 1. Envío con patrón Strategy

Specs: SPEC-NTF-01, 02, 03, 11, 12

```mermaid
sequenceDiagram
    autonumber
    participant TS as TicketService
    participant NS as NotificationService
    participant ST as NotificationStrategy (Mail / Whatsapp)
    participant NR as NotificationRepository

    TS->>NS: notify(recipient, actor, ticket, message)
    alt recipient es el mismo usuario que actor
        NS-->>TS: omitir envío (SPEC-NTF-11)
    else recipient distinto de actor
        NS->>NS: strategy = strategies[recipient.preferred_channel]
        Note over NS: "mail" → MailNotification (SPEC-NTF-01)<br/>"whatsapp" → WhatsappNotification (SPEC-NTF-02)
        NS->>ST: send(recipient, message)
        Note over ST: Envío simulado: no hay SMTP ni API externa (SPEC-NTF-12)
        ST-->>NS: ok
        NS->>NR: add(Notification(ticket, recipient, channel, message, clock.now(), status="sent"))
        NS->>NR: commit() (SPEC-NTF-03)
        NS-->>TS: ok
    end
```

## 2. Falla en el envío

Specs: SPEC-NTF-04

```mermaid
sequenceDiagram
    autonumber
    participant TS as TicketService
    participant TR as TicketRepository
    participant NS as NotificationService
    participant ST as NotificationStrategy
    participant NR as NotificationRepository

    TS->>TR: commit() de la operación del ticket
    Note over TS,TR: El cambio del ticket ya quedó persistido
    TS->>NS: notify(recipient, actor, ticket, message)
    NS->>ST: send(recipient, message)
    ST-->>NS: raise NotificationError
    NS->>NR: add(Notification(..., status="failed", error))
    NS->>NR: commit()
    NS-->>TS: retorna sin propagar la excepción
    Note over TS: La operación del ticket no se revierte (SPEC-NTF-04)
```
