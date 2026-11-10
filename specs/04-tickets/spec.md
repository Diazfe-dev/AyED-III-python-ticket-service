# 04 — Ciclo de vida del ticket

Origen: RF 1.4 · Relacionados: RNF 4, RNF 6 · Diagramas: [secuencias](../../diagrams/sequences/04-tickets.md), [clases](../../diagrams/classes.md)

Estados: `New` (Nuevo), `InProgress` (En Progreso), `Closed` (Cerrado).

Transiciones válidas:

| Desde | `in_progress` | `close` | `reopen` |
|-------|---------------|---------|----------|
| `New` | → `InProgress` | → `Closed` | ❌ |
| `InProgress` | ❌ | → `Closed` | ❌ |
| `Closed` | ❌ | ❌ | → `InProgress` |

## Creación

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-01 | Por evento | **Cuando** un representante crea un ticket indicando un cliente, un primer mensaje y opcionalmente productos, **el sistema deberá** registrar el ticket asociado a ese cliente. | RF 1.4.1, RF 1.4.2 |
| SPEC-TKT-02 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** asignar como responsable al representante autenticado que lo creó. | RF 1.4.3 |
| SPEC-TKT-03 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** dejarlo en estado `New`. | RF 1.4.4, Seq. tickets §1 |
| SPEC-TKT-04 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** registrar el primer mensaje como el hito inicial, con el representante como autor. | RF 1.4.1, Seq. tickets §1 |
| SPEC-TKT-05 | No deseado | **Si** quien intenta crear un ticket no tiene rol `Representative`, **entonces el sistema deberá** rechazar la creación. | RF 1.4.1 |
| SPEC-TKT-06 | No deseado | **Si** el cliente indicado no existe, no tiene rol `Client` o está inactivo, **entonces el sistema deberá** rechazar la creación. | RF 1.4.2, RF 1.1.1 |

## Productos asociados

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-07 | Por evento | **Cuando** el representante asignado asocia uno o más productos a un ticket, **el sistema deberá** registrar la asociación. | RF 1.4.6 |
| SPEC-TKT-08 | No deseado | **Si** alguno de los productos indicados no existe o está inactivo, **entonces el sistema deberá** rechazar la asociación completa. | RF 1.4.6, RF 1.3.1 |
| SPEC-TKT-21 | Por evento | **Cuando** el representante asignado quita un producto asociado a un ticket, **el sistema deberá** eliminar esa asociación. | RF 1.4.7 |
| SPEC-TKT-22 | No deseado | **Si** quien intenta asociar o quitar productos no es el representante asignado, **entonces el sistema deberá** rechazar la operación. | RF 1.4.6, RF 1.4.7 |

## Transiciones de estado

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-09 | Complejo | **Mientras** el ticket está en `New`, **cuando** el representante asignado registra un hito indicando que comienza a trabajarlo, **el sistema deberá** pasar el ticket a `InProgress`. | RF 1.4.4, Seq. hitos §1 |
| SPEC-TKT-10 | Complejo | **Mientras** el ticket está en `New` o `InProgress`, **cuando** el cliente dueño o el representante asignado lo cierra, **el sistema deberá** pasarlo a `Closed`. | RF 1.4.4 |
| SPEC-TKT-11 | Complejo | **Mientras** el ticket está en `Closed`, **cuando** el cliente dueño o el representante asignado lo reabre, **el sistema deberá** pasarlo directamente a `InProgress`. | RF 1.4.5 |
| SPEC-TKT-12 | Por evento | **Cuando** se reabre un ticket, **el sistema deberá** reasignarlo al mismo representante que lo gestionó antes del cierre. | RF 1.4.5 |
| SPEC-TKT-13 | No deseado | **Si** se solicita una transición que el estado actual no permite (según la tabla de transiciones), **entonces el sistema deberá** rechazarla sin modificar el ticket. | RF 1.4.4 |
| SPEC-TKT-14 | Por evento | **Cuando** un ticket cambia de estado, **el sistema deberá** registrar un cambio de estado con el usuario que lo realizó, el nuevo estado y la fecha y hora exactas en UTC. | RNF 6 |
| SPEC-TKT-15 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** registrar el cambio de estado inicial a `New` con el representante como autor. | RNF 6, Seq. tickets §1 |
| SPEC-TKT-16 | Ubicuo | **El sistema deberá** conservar el historial completo de cambios de estado de cada ticket, sin permitir modificarlo ni borrarlo. | RNF 5, RNF 6 |

## Privacidad y acceso

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-17 | Por evento | **Cuando** un cliente solicita su listado de tickets, **el sistema deberá** devolver únicamente los tickets en los que él es el cliente. | RNF 4 |
| SPEC-TKT-18 | Por evento | **Cuando** un representante solicita su listado de tickets, **el sistema deberá** devolver únicamente los tickets que tiene asignados. | RF 1.4.3 |
| SPEC-TKT-19 | No deseado | **Si** un cliente intenta ver, cerrar, reabrir o responder un ticket de otro cliente, **entonces el sistema deberá** responder como si el ticket no existiera. | RNF 4 |
| SPEC-TKT-20 | No deseado | **Si** un representante intenta ver o modificar un ticket que no tiene asignado, **entonces el sistema deberá** responder como si el ticket no existiera. | RF 1.4.3 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. Un ticket reabierto vuelve a `InProgress`.
2. La reapertura por parte del cliente es directa, sin aprobación del representante.
3. Los representantes solo ven los tickets que tienen asignados.
4. El representante asignado puede quitar productos de un ticket (RF 1.4.7).
5. Patrón State: `State` define `close`, `reopen` e `in_progress`, y por defecto lanzan `InvalidTransitionError`. Cada estado concreto sobrescribe solo sus transiciones válidas (ver la tabla).
