# Secuencias — 04 Ciclo de vida del ticket

Spec: [specs/04-tickets/spec.md](../../specs/04-tickets/spec.md)

Convención de transacción: el service hace `commit()` de la operación del ticket **antes** de notificar. Así, si falla una notificación, el cambio no se revierte (SPEC-NTF-04). El detalle del envío está en [06-notifications.md](06-notifications.md).

## 1. Creación de ticket

Specs: SPEC-TKT-01, 02, 03, 04, 05, 06, 08, 15 · SPEC-NTF-05

```mermaid
sequenceDiagram
    autonumber
    actor Rep as Representante
    participant TC as TicketController
    participant TS as TicketService
    participant UR as UserRepository
    participant PR as ProductRepository
    participant T as Ticket
    participant TR as TicketRepository
    participant NS as NotificationService

    Rep->>TC: POST /tickets (client_id, product_ids, first_message)
    alt current_user no es Representative
        TC-->>Rep: 403 Forbidden (SPEC-TKT-05)
    else current_user es Representative
        TC->>TS: create_ticket(client_id, product_ids, first_message, representative=current_user)
        TS->>UR: get(client_id)
        UR-->>TS: User o None
        alt no existe, no es Client o está inactivo
            TS-->>TC: raise InvalidClientError
            TC-->>Rep: 400 Bad Request (SPEC-TKT-06)
        else cliente válido
            TS->>PR: get_many(product_ids)
            PR-->>TS: products
            alt falta alguno o alguno está inactivo
                TS-->>TC: raise InvalidProductError
                TC-->>Rep: 400 Bad Request (SPEC-TKT-08)
            else productos válidos
                TS->>T: <<create>> Ticket(client, representative, products)
                T->>T: state = NewState (SPEC-TKT-02, 03)
                T->>T: <<create>> StateChange(representative, New, clock.now()) (SPEC-TKT-15)
                T->>T: <<create>> Milestone(first_message, representative) (SPEC-TKT-04)
                TS->>TR: add(ticket) y commit()
                TS->>NS: notify(recipient=client, actor=representative, ticket, "Nuevo ticket") (SPEC-NTF-05)
                TC-->>Rep: 201 Created (SPEC-TKT-01)
            end
        end
    end
```

## 2. Cierre de ticket (patrón State)

Specs: SPEC-TKT-10, 13, 14 · SPEC-NTF-07, 13

```mermaid
sequenceDiagram
    autonumber
    actor U as Cliente dueño o Representante asignado
    participant TC as TicketController
    participant TS as TicketService
    participant TR as TicketRepository
    participant T as Ticket
    participant S as state (State actual)
    participant NS as NotificationService

    U->>TC: POST /tickets/{id}/close
    TC->>TS: close_ticket(ticket_id, actor=current_user)
    TS->>TR: get_visible(ticket_id, actor)
    Note over TS,TR: Si no es visible para el actor → 404 (ver diagrama 4)
    TR-->>TS: ticket
    TS->>T: close(actor)
    T->>S: close(ticket, actor)
    alt state es New o InProgress
        S->>T: state = ClosedState
        S->>T: <<create>> StateChange(actor, Closed, clock.now()) (SPEC-TKT-14)
        TS->>TR: commit()
        alt actor es el Representante
            TS->>NS: notify(recipient=client, actor, ticket, "Ticket cerrado") (SPEC-NTF-07)
        else actor es el Cliente
            TS->>NS: notify(recipient=representative, actor, ticket, "El cliente cerró el ticket") (SPEC-NTF-13)
        end
        TC-->>U: 200 OK (SPEC-TKT-10)
    else state es Closed
        S-->>TS: raise InvalidTransitionError (comportamiento por defecto de State)
        TC-->>U: 409 Conflict, sin cambios (SPEC-TKT-13)
    end
```

## 3. Reapertura de ticket

Specs: SPEC-TKT-11, 12, 13, 14 · SPEC-NTF-07, 10

```mermaid
sequenceDiagram
    autonumber
    actor U as Cliente dueño o Representante asignado
    participant TC as TicketController
    participant TS as TicketService
    participant TR as TicketRepository
    participant T as Ticket
    participant S as state (State actual)
    participant NS as NotificationService

    U->>TC: POST /tickets/{id}/reopen
    TC->>TS: reopen_ticket(ticket_id, actor=current_user)
    TS->>TR: get_visible(ticket_id, actor)
    TR-->>TS: ticket
    TS->>T: reopen(actor)
    T->>S: reopen(ticket, actor)
    alt state es Closed
        S->>T: state = InProgressState (SPEC-TKT-11)
        Note over T: representative no cambia: sigue el mismo<br/>que lo gestionó antes del cierre (SPEC-TKT-12)
        S->>T: <<create>> StateChange(actor, InProgress, clock.now()) (SPEC-TKT-14)
        TS->>TR: commit()
        alt actor es el Cliente
            TS->>NS: notify(recipient=representative, actor, ticket, "El cliente reabrió el ticket") (SPEC-NTF-10)
        else actor es el Representante
            TS->>NS: notify(recipient=client, actor, ticket, "Ticket reabierto") (SPEC-NTF-07)
        end
        TC-->>U: 200 OK
    else state es New o InProgress
        S-->>TS: raise InvalidTransitionError
        TC-->>U: 409 Conflict, sin cambios (SPEC-TKT-13)
    end
```

## 4. Acceso y privacidad

Specs: SPEC-TKT-17, 18, 19, 20

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario autenticado
    participant TC as TicketController
    participant TS as TicketService
    participant TR as TicketRepository

    alt listado
        U->>TC: GET /tickets
        TC->>TS: list_tickets(actor=current_user)
        alt actor es Client
            TS->>TR: list_by_client(actor.id) (SPEC-TKT-17)
        else actor es Representative
            TS->>TR: list_by_representative(actor.id) (SPEC-TKT-18)
        end
        TR-->>TS: tickets
        TC-->>U: 200 OK
    else detalle o cualquier operación sobre un ticket
        U->>TC: GET /tickets/{id}
        TC->>TS: get_ticket(ticket_id, actor=current_user)
        TS->>TR: get_visible(ticket_id, actor)
        Note over TR: WHERE id = :id AND (client_id = :actor<br/>OR representative_id = :actor)
        alt no existe o no pertenece al actor
            TR-->>TS: None
            TS-->>TC: raise TicketNotFoundError
            TC-->>U: 404 Not Found, igual que si no existiera (SPEC-TKT-19, 20)
        else visible
            TR-->>TS: ticket
            TC-->>U: 200 OK
        end
    end
```

## 5. Asociar y quitar productos

Specs: SPEC-TKT-07, 08, 21, 22

```mermaid
sequenceDiagram
    autonumber
    actor Rep as Representante
    participant TC as TicketController
    participant TS as TicketService
    participant TR as TicketRepository
    participant PR as ProductRepository
    participant T as Ticket

    Rep->>TC: POST /tickets/{id}/products (product_ids) o DELETE /tickets/{id}/products/{pid}
    TC->>TS: add_products(...) o remove_product(...) con actor=current_user
    TS->>TR: get_visible(ticket_id, actor)
    TR-->>TS: ticket
    alt actor no es el representante asignado
        TS-->>TC: raise PermissionDeniedError
        TC-->>Rep: 403 Forbidden (SPEC-TKT-22)
    else actor es el representante asignado
        alt asociar
            TS->>PR: get_many(product_ids)
            PR-->>TS: products
            alt falta alguno o alguno está inactivo
                TS-->>TC: raise InvalidProductError
                TC-->>Rep: 400 Bad Request, no se asocia ninguno (SPEC-TKT-08)
            else todos válidos
                TS->>T: add_products(products)
                TS->>TR: commit()
                TC-->>Rep: 200 OK (SPEC-TKT-07)
            end
        else quitar
            TS->>T: remove_product(product_id)
            TS->>TR: commit()
            TC-->>Rep: 204 No Content (SPEC-TKT-21)
        end
    end
```
