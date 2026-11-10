# Secuencias — 05 Hitos

Spec: [specs/05-milestones/spec.md](../../specs/05-milestones/spec.md)

## 1. Registro de hito por el representante (con transición opcional)

Specs: SPEC-MLS-01, 03, 04, 05, 06 · SPEC-TKT-09, 14 · SPEC-NTF-06, 08

```mermaid
sequenceDiagram
    autonumber
    actor Rep as Representante asignado
    participant MC as MilestoneController
    participant TS as TicketService
    participant TR as TicketRepository
    participant T as Ticket
    participant S as state (State actual)
    participant NS as NotificationService

    Rep->>MC: POST /tickets/{id}/milestones (content, start_progress)
    MC->>TS: add_milestone(ticket_id, content, actor=current_user, start_progress)
    TS->>TR: get_visible(ticket_id, actor)
    Note over TS,TR: Si no es el cliente dueño ni el representante asignado → 404 (SPEC-MLS-06)
    TR-->>TS: ticket
    alt content vacío o solo espacios
        TS-->>MC: raise ValidationError
        MC-->>Rep: 400 Bad Request (SPEC-MLS-04)
    else state es Closed
        TS-->>MC: raise TicketClosedError
        MC-->>Rep: 409 Conflict "Reabrí el ticket primero" (SPEC-MLS-05)
    else ticket abierto y contenido válido
        TS->>T: add_milestone(content, actor)
        T->>T: <<create>> Milestone(content, author=actor, created_at=clock.now()) (SPEC-MLS-01, 03)
        opt start_progress y state es New
            TS->>T: start_progress(actor)
            T->>S: in_progress(ticket, actor)
            S->>T: state = InProgressState (SPEC-TKT-09)
            S->>T: <<create>> StateChange(actor, InProgress, clock.now()) (SPEC-TKT-14)
        end
        TS->>TR: commit()
        alt hubo cambio de estado
            TS->>NS: notify(client, actor, ticket, "Nuevo hito y ticket En Progreso") (SPEC-NTF-08)
        else solo hito
            TS->>NS: notify(client, actor, ticket, "Nuevo hito") (SPEC-NTF-06)
        end
        MC-->>Rep: 201 Created
    end
```

## 2. Respuesta del cliente

Specs: SPEC-MLS-02, 03, 04, 05 · SPEC-NTF-09

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente dueño
    participant MC as MilestoneController
    participant TS as TicketService
    participant TR as TicketRepository
    participant T as Ticket
    participant NS as NotificationService

    C->>MC: POST /tickets/{id}/milestones (content)
    MC->>TS: add_milestone(ticket_id, content, actor=current_user)
    TS->>TR: get_visible(ticket_id, actor)
    TR-->>TS: ticket
    alt content vacío
        MC-->>C: 400 Bad Request (SPEC-MLS-04)
    else state es Closed
        MC-->>C: 409 Conflict "Reabrí el ticket primero" (SPEC-MLS-05)
    else válido
        TS->>T: add_milestone(content, actor)
        T->>T: <<create>> Milestone(content, author=cliente, created_at=clock.now()) (SPEC-MLS-02, 03)
        TS->>TR: commit()
        TS->>NS: notify(recipient=representative, actor=cliente, ticket, "Nueva respuesta del cliente") (SPEC-NTF-09)
        MC-->>C: 201 Created
    end
```

## 3. Listado cronológico de hitos

Specs: SPEC-MLS-07, 08

```mermaid
sequenceDiagram
    autonumber
    actor U as Cliente dueño o Representante asignado
    participant MC as MilestoneController
    participant TS as TicketService
    participant TR as TicketRepository

    U->>MC: GET /tickets/{id}/milestones
    MC->>TS: list_milestones(ticket_id, actor=current_user)
    TS->>TR: get_visible(ticket_id, actor) con selectinload(milestones.author)
    Note over TR: relationship(order_by=(Milestone.created_at, Milestone.id))
    TR-->>TS: ticket.milestones en orden ascendente (SPEC-MLS-07)
    TS-->>MC: hitos con autor, rol y created_at (SPEC-MLS-08)
    MC-->>U: 200 OK
```

## 4. Intento de modificar o borrar un hito

Specs: SPEC-MLS-09, 10

No existe ninguna ruta ni método de service que modifique o borre hitos. Este diagrama muestra las dos barreras que actúan si alguien lo intenta por código o con SQL directo.

```mermaid
sequenceDiagram
    autonumber
    participant X as Código o SQL directo
    participant ORM as SQLAlchemy Session
    participant L as Listener before_update / before_delete
    participant DB as SQLite (trigger)

    alt vía ORM
        X->>ORM: milestone.content = "otro" y flush()
        ORM->>L: before_update(Milestone)
        L-->>X: raise ImmutableRecordError, sin cambios (SPEC-MLS-09)
        X->>ORM: session.delete(milestone) y flush()
        ORM->>L: before_delete(Milestone)
        L-->>X: raise ImmutableRecordError, sin cambios (SPEC-MLS-10)
    else vía SQL directo
        X->>DB: UPDATE milestones ... o DELETE FROM milestones ...
        DB-->>X: RAISE(ABORT) del trigger, sin cambios (SPEC-MLS-09, 10)
    end
    Note over X,DB: Las mismas barreras protegen a StateChange (SPEC-TKT-16)
```
