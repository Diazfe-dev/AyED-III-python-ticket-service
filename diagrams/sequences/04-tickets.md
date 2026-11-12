# Secuencias — 04 Ciclo de vida del ticket

Spec: [specs/04-tickets/spec.md](../../specs/04-tickets/spec.md)

Convención de transacción: el service hace `commit()` de la operación del ticket **antes** de notificar. Así, si falla una notificación, el cambio no se revierte (SPEC-NTF-04). El detalle del envío está en [06-notifications.md](06-notifications.md).

Convenciones del código actual:

- El `TicketController` solo lee el cuerpo JSON y delega con `actor=current_user`; todas las reglas, incluido el `403`, las decide el `TicketService`. Los errores de dominio se traducen en `controllers/errors.py`: `400` `validation_error`, `invalid_client` e `invalid_product`; `403` `forbidden`; `404` `ticket_not_found` y `product_not_in_ticket`; `409` `invalid_transition`.
- El service lee `clock()` una vez y pasa `now` al dominio. El dominio no lee el reloj, y toda transición pasa por `Ticket._enter`, que cambia `state_name` y agrega el `StateChange`.
- Los pasos `NS.notify` son de [06-notifications](../../specs/06-notifications/spec.md): `TicketService` recibe un `NotificationService` (`app/wiring.py`) y lo llama como última acción, después del `commit()`; el mensaje sale de `app/services/notification_messages.py`. Si la operación no termina con éxito (`4xx` o `500`), no se notifica (SPEC-NTF-15). El destinatario del cierre y de la reapertura es la contraparte del actor (`_notify_counterpart`).

## 1. Creación de ticket

Specs: SPEC-TKT-01, 02, 03, 04, 05, 06, 08, 15, 23, 24, 27, 31 · SPEC-NTF-05, 15

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
    TC->>TS: create_ticket(client_id, product_ids, first_message, actor=current_user)
    Note over TS: formato de client_id, product_ids y first_message, todos juntos, antes del rol (decisión 19, G-01 de 05)
    alt algún campo es inválido
        TS-->>TC: raise ValidationError con todos los campos
        TC-->>Rep: 400 validation_error, también para el Admin y el Client (SPEC-TKT-05, 23, 24, 27)
    else formato válido
        alt actor no es Representative
            TS-->>TC: raise PermissionDeniedError
            TC-->>Rep: 403 forbidden, antes de verificar cliente y productos (SPEC-TKT-05, 27)
        else actor es Representative
            TS->>UR: get(client_id)
            UR-->>TS: User o None
            alt no existe, no es Client o está inactivo
                TS-->>TC: raise InvalidClientError
                TC-->>Rep: 400 invalid_client (SPEC-TKT-06)
            else cliente válido
                TS->>PR: get_many(product_ids sin repetir)
                PR-->>TS: products
                alt falta alguno o alguno está inactivo
                    TS-->>TC: raise InvalidProductError
                    TC-->>Rep: 400 invalid_product (SPEC-TKT-08)
                else productos válidos
                    TS->>T: Ticket.open(client, actor, products, first_message, now=clock())
                    Note over T: estado New (SPEC-TKT-02, 03) y productos asociados (SPEC-TKT-31)
                    T->>T: <<create>> Milestone(first_message, representative, now) (SPEC-TKT-04)
                    T->>T: <<create>> StateChange(representative, New, now) (SPEC-TKT-15)
                    TS->>TR: add(ticket)
                    TS->>TS: commit()
                    TS->>NS: notify(recipient=client, actor=representative, ticket, ticket_created(ticket)) (06, SPEC-NTF-05)
                    TC-->>Rep: 201 Created (SPEC-TKT-01)
                end
            end
        end
    end
```

## 2. Cierre de ticket (patrón State)

Specs: SPEC-TKT-10, 13, 14, 16, 19, 20, 27, 30 · SPEC-NTF-07, 13, 15

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
    alt actor es Admin
        TS-->>TC: raise PermissionDeniedError
        TC-->>U: 403 forbidden (SPEC-TKT-27)
    else actor es Client o Representative
        TS->>TR: get_visible(ticket_id, actor)
        TR-->>TS: ticket o None
        alt no existe, está fuera de rango o no es visible para el actor
            TS-->>TC: raise TicketNotFoundError
            TC-->>U: 404 ticket_not_found (SPEC-TKT-19, 20, 30, ver diagrama 4)
        else visible
            TS->>T: close(actor, now=clock())
            T->>S: close(ticket, actor, now)
            alt state es New o InProgress
                S->>T: _enter(ClosedState, actor, now)
                T->>T: <<create>> StateChange(actor, Closed, now) (SPEC-TKT-14, 16)
                TS->>TS: commit()
                alt actor es el Representante
                    TS->>NS: notify(recipient=client, actor, ticket, ticket_closed(ticket)) (06, SPEC-NTF-07)
                else actor es el Cliente
                    TS->>NS: notify(recipient=representative, actor, ticket, ticket_closed(ticket)) (06, SPEC-NTF-13)
                end
                TC-->>U: 200 OK con el ticket (SPEC-TKT-10)
            else state es Closed
                S-->>TS: raise InvalidTransitionError (comportamiento por defecto de State)
                TC-->>U: 409 invalid_transition, sin cambios (SPEC-TKT-13)
            end
        end
    end
```

## 3. Reapertura de ticket

Specs: SPEC-TKT-11, 12, 13, 14, 16, 19, 20, 27, 30 · SPEC-NTF-07, 10, 15

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
    alt actor es Admin
        TS-->>TC: raise PermissionDeniedError
        TC-->>U: 403 forbidden (SPEC-TKT-27)
    else actor es Client o Representative
        TS->>TR: get_visible(ticket_id, actor)
        TR-->>TS: ticket o None
        alt no existe, está fuera de rango o no es visible para el actor
            TS-->>TC: raise TicketNotFoundError
            TC-->>U: 404 ticket_not_found (SPEC-TKT-19, 20, 30)
        else visible
            TS->>T: reopen(actor, now=clock())
            T->>S: reopen(ticket, actor, now)
            alt state es Closed
                S->>T: _enter(InProgressState, actor, now) (SPEC-TKT-11)
                Note over T: representative no cambia: sigue el mismo<br/>que lo gestionó antes del cierre (SPEC-TKT-12)
                T->>T: <<create>> StateChange(actor, InProgress, now) (SPEC-TKT-14, 16)
                TS->>TS: commit()
                alt actor es el Cliente
                    TS->>NS: notify(recipient=representative, actor, ticket, ticket_reopened(ticket)) (06, SPEC-NTF-10)
                else actor es el Representante
                    TS->>NS: notify(recipient=client, actor, ticket, ticket_reopened(ticket)) (06, SPEC-NTF-07)
                end
                TC-->>U: 200 OK con el ticket
            else state es New o InProgress
                S-->>TS: raise InvalidTransitionError
                TC-->>U: 409 invalid_transition, sin cambios (SPEC-TKT-13)
            end
        end
    end
```

## 4. Acceso y privacidad

Specs: SPEC-TKT-17, 18, 19, 20, 27, 28, 29, 30

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
        alt actor es Admin
            TS-->>TC: raise PermissionDeniedError
            TC-->>U: 403 forbidden (SPEC-TKT-27)
        else actor es Client
            TS->>TR: list_by_client(actor.id) (SPEC-TKT-17)
            TR-->>TS: tickets por created_at desc, id desc (SPEC-TKT-29)
            TC-->>U: 200 OK
        else actor es Representative
            TS->>TR: list_by_representative(actor.id) (SPEC-TKT-18)
            TR-->>TS: tickets por created_at desc, id desc (SPEC-TKT-29)
            TC-->>U: 200 OK
        end
    else detalle o cualquier operación sobre un ticket
        U->>TC: GET /tickets/{id}
        TC->>TS: get_ticket(ticket_id, actor=current_user)
        alt actor es Admin
            TS-->>TC: raise PermissionDeniedError
            TC-->>U: 403 forbidden (SPEC-TKT-27)
        else actor es Client o Representative
            TS->>TR: get_visible(ticket_id, actor)
            Note over TR: WHERE id = :id AND (client_id = :actor<br/>OR representative_id = :actor)<br/>un id que no entra en el INTEGER de SQLite devuelve None sin consultar
            alt no existe, está fuera de rango o no pertenece al actor
                TR-->>TS: None
                TS-->>TC: raise TicketNotFoundError
                TC-->>U: 404 ticket_not_found, igual que si no existiera (SPEC-TKT-19, 20, 30)
            else visible
                TR-->>TS: ticket
                TC-->>U: 200 OK con el detalle (SPEC-TKT-28)
            end
        end
    end
```

## 5. Asociar y quitar productos

Specs: SPEC-TKT-07, 08, 19, 20, 21, 22, 24, 25, 26, 27, 30 · SPEC-NTF-17

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
    TC->>TS: add_products(ticket_id, product_ids, actor) o remove_product(ticket_id, product_id, actor)
    opt asociar con product_ids inválido
        Note over TS: formato de product_ids antes del rol y de buscar el ticket (decisión 19, G-21)
        TS-->>TC: raise ValidationError
        TC-->>Rep: 400 validation_error, también para el Admin (SPEC-TKT-24)
    end
    alt actor es Admin
        TS-->>TC: raise PermissionDeniedError
        TC-->>Rep: 403 forbidden (SPEC-TKT-27)
    else actor no es Admin
        TS->>TR: get_visible(ticket_id, actor)
        TR-->>TS: ticket o None
        alt no existe, está fuera de rango o no es visible
            TS-->>TC: raise TicketNotFoundError
            TC-->>Rep: 404 ticket_not_found (SPEC-TKT-19, 20, 30)
        else visible
            alt actor no es el representante asignado
                TS-->>TC: raise PermissionDeniedError
                TC-->>Rep: 403 forbidden (SPEC-TKT-22)
            else actor es el representante asignado
                alt asociar
                    TS->>PR: get_many(product_ids sin repetir)
                    PR-->>TS: products
                    alt falta alguno o alguno está inactivo
                        TS-->>TC: raise InvalidProductError
                        TC-->>Rep: 400 invalid_product, no se asocia ninguno (SPEC-TKT-08)
                    else todos válidos
                        TS->>T: add_products(products)
                        Note over T: no duplica los que ya estaban asociados (SPEC-TKT-25)
                        TS->>TS: commit()
                        Note over TS: no se notifica (SPEC-NTF-17)
                        TC-->>Rep: 200 OK con el ticket (SPEC-TKT-07)
                    end
                else quitar
                    TS->>T: remove_product(product)
                    alt el producto no está asociado al ticket
                        TS-->>TC: raise ProductNotInTicketError
                        TC-->>Rep: 404 product_not_in_ticket (SPEC-TKT-26)
                    else asociado
                        TS->>TS: commit()
                        Note over TS: no se notifica (SPEC-NTF-17)
                        TC-->>Rep: 204 No Content (SPEC-TKT-21)
                    end
                end
            end
        end
    end
```
