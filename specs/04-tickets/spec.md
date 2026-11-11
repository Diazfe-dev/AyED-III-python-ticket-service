# 04 — Ciclo de vida del ticket

Origen: RF 1.4 · Relacionados: RNF 4, RNF 5, RNF 6 · Diagramas: [secuencias](../../diagrams/sequences/04-tickets.md), [clases](../../diagrams/classes.md)

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
| SPEC-TKT-31 | Por evento | **Cuando** un representante crea un ticket indicando productos válidos, **el sistema deberá** asociar esos productos al ticket. | RF 1.4.1, RF 1.4.6 |
| SPEC-TKT-02 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** asignar como responsable al representante autenticado que lo creó. | RF 1.4.3 |
| SPEC-TKT-03 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** dejarlo en estado `New`. | RF 1.4.4, Seq. tickets §1 |
| SPEC-TKT-04 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** registrar el primer mensaje como el hito inicial, con el representante como autor. | RF 1.4.1, Seq. tickets §1 |
| SPEC-TKT-05 | No deseado | **Si** quien intenta crear un ticket no tiene rol `Representative`, **entonces el sistema deberá** rechazar la creación. | RF 1.4.1 |
| SPEC-TKT-06 | No deseado | **Si** el cliente indicado no existe, no tiene rol `Client` o está inactivo, **entonces el sistema deberá** rechazar la creación. | RF 1.4.2, RF 1.1.1 |
| SPEC-TKT-23 | No deseado | **Si** el primer mensaje de un ticket está vacío, tiene solo espacios o no es texto, **entonces el sistema deberá** rechazar la creación e indicar que el mensaje es inválido. | RF 1.4.1, RF 1.5.1 |
| SPEC-TKT-24 | No deseado | **Si** el identificador del cliente no es un entero positivo, o la lista de productos no es una lista de enteros positivos, **entonces el sistema deberá** rechazar la solicitud e indicar qué campo es inválido (`400`). | RF 1.4.2, RF 1.4.6 |
| SPEC-TKT-27 | No deseado | **Si** un usuario con rol `Admin` intenta operar sobre tickets, **entonces el sistema deberá** denegar la operación (`403`). | RF 1.1.5 |

## Productos asociados

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-07 | Por evento | **Cuando** el representante asignado asocia uno o más productos a un ticket, **el sistema deberá** registrar la asociación. | RF 1.4.6 |
| SPEC-TKT-08 | No deseado | **Si** alguno de los productos indicados al crear el ticket o al asociar productos no existe o está inactivo, **entonces el sistema deberá** rechazar la operación completa. | RF 1.4.6, RF 1.3.1 |
| SPEC-TKT-21 | Por evento | **Cuando** el representante asignado quita un producto asociado a un ticket, **el sistema deberá** eliminar esa asociación. | RF 1.4.7 |
| SPEC-TKT-22 | No deseado | **Si** quien intenta asociar o quitar productos no es el representante asignado, **entonces el sistema deberá** rechazar la operación. | RF 1.4.6, RF 1.4.7 |
| SPEC-TKT-25 | Por evento | **Cuando** el representante asignado asocia un producto que ya estaba asociado al ticket, **el sistema deberá** mantener una única asociación, sin duplicarla. | RF 1.4.6 |
| SPEC-TKT-26 | No deseado | **Si** el representante asignado intenta quitar un producto que no está asociado al ticket, **entonces el sistema deberá** responder que la asociación no existe (`404`). | RF 1.4.7 |

## Transiciones de estado

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-09 | Complejo | **Mientras** el ticket está en `New`, **cuando** el representante asignado registra un hito con la indicación de comenzar a trabajarlo (`start_progress`), **el sistema deberá** pasar el ticket a `InProgress`. | RF 1.4.4, Seq. hitos §1 |
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
| SPEC-TKT-28 | Por evento | **Cuando** el cliente dueño o el representante asignado solicita un ticket, **el sistema deberá** devolver su estado, su cliente, su representante y sus productos. | RF 1.4.2, RF 1.4.6 |
| SPEC-TKT-29 | Ubicuo | **El sistema deberá** devolver los listados de tickets ordenados del más reciente al más antiguo. | RF 1.4.3 |
| SPEC-TKT-30 | No deseado | **Si** el ticket solicitado no existe o su identificador excede el rango admitido, **entonces el sistema deberá** responder `404`. | RF 1.4, RNF 4 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. Un ticket reabierto vuelve a `InProgress`.
2. La reapertura por parte del cliente es directa, sin aprobación del representante.
3. Los representantes solo ven los tickets que tienen asignados.
4. El representante asignado puede quitar productos de un ticket (RF 1.4.7).
5. Patrón State: `State` define `close`, `reopen` e `in_progress`, y por defecto lanzan `InvalidTransitionError`. Cada estado concreto sobrescribe solo sus transiciones válidas (ver la tabla).

Aprobadas el 2026-11-10 (revisión transversal de huecos):

6. Se agregan SPEC-TKT-23 a 29: validación del primer mensaje, identificadores mal formados → `400`, el Admin no opera tickets, asociación repetida sin duplicar, quitar un producto no asociado → `404`, detalle del ticket y orden de los listados.
7. SPEC-TKT-08 aplica también a los productos indicados al crear el ticket. SPEC-TKT-09 se dispara con el campo `start_progress` del alta del hito.
8. Limitación conocida: la reapertura reasigna al mismo representante aunque esté inactivo (SPEC-TKT-12). No existe la reasignación de tickets; si hiciera falta, se especifica como un cambio nuevo.

Resueltas el 2026-11-11 al planificar el área (huecos G-01 a G-07 de [plan.md](plan.md#huecos-y-preguntas-abiertas); el texto de las specs no cambia, estas decisiones fijan los detalles que no definían):

9. **Cliente y producto inexistentes al crear (SPEC-TKT-06 y 08, G-01)**: un `client_id` que no existe, no es `Client` o está inactivo responde `400` con el código `invalid_client`; un producto inexistente o inactivo responde `400` con `invalid_product`. Es una validación del cuerpo y no una búsqueda del recurso, y así no se confunde con el `404` de privacidad. Diverge a propósito del `404` de SPEC-PRD-02.
10. **Transición inválida (SPEC-TKT-13, G-02)**: responde `409` con el código `invalid_transition`.
11. **Permisos de escritura (SPEC-TKT-22, 05 y 27, G-03)**: quien puede ver el ticket pero no es el representante asignado (en la práctica, el cliente dueño) y asocia o quita productos recibe `403` con el código `forbidden` (`PermissionDeniedError`). Un ticket que el usuario no puede ver sigue respondiendo `404` (SPEC-TKT-19 y 20). Un `Admin` recibe `403` en toda operación (SPEC-TKT-27), antes de cualquier consulta. SPEC-TKT-05 (solo `Representative` crea) y SPEC-TKT-27 se superponen para el `Admin` que crea un ticket: es la misma excepción y el mismo `403`, con un caso de prueba por spec. Sobre la reapertura, ver la decisión 17.
12. **Primer mensaje inválido (SPEC-TKT-23, G-04)**: ausente, vacío o solo espacios → `required`; un valor que no es texto → `invalid` (misma convención que usuarios y productos).
13. **Asociar productos a un ticket existente (SPEC-TKT-24, 25 y 07, G-05)**: rigen las mismas reglas que en la creación. `product_ids` es obligatorio y es una lista no vacía de enteros positivos (un texto de dígitos se rechaza). Los ids repetidos en el pedido se colapsan en una sola asociación. Si algún id no existe o está inactivo, responde `400` `invalid_product` y no se agrega ninguno (todo o nada).
14. **Listados (SPEC-TKT-29, G-06)**: "más reciente" es `Ticket.created_at` (instante del reloj inyectado) descendente y, ante igualdad, `id` descendente. El diagrama de clases se actualiza con `Ticket.created_at` en la task de diagramas.
15. **Productos en un ticket cerrado (SPEC-TKT-07 y 21, G-07)**: asociar y quitar productos está permitido en cualquier estado, incluido `Closed`.

Aprobadas el 2026-11-11 (huecos G-18 y G-19 de [plan.md](plan.md#huecos-y-preguntas-abiertas) y revisión de requerimientos). Se agregan SPEC-TKT-30 (ticket inexistente o fuera de rango → `404` con el código `ticket_not_found`, igual que SPEC-USR-26) y SPEC-TKT-31 (asociación de los productos indicados en el alta):

16. **`client_id` como texto de dígitos (SPEC-TKT-24, G-19)**: `client_id` acepta un texto de dígitos (`"3"`), con la misma lectura de "entero positivo" que SPEC-PTY-20 y SPEC-PRD-15.
17. **Reapertura (SPEC-TKT-11, G-18)**: pueden reabrir el cliente dueño y el representante asignado; SPEC-TKT-11 no cambia. El `403` de la decisión 11 no aplica a la reapertura: el único `403` posible al reabrir es el del `Admin` (SPEC-TKT-27).
18. **`client_id` ausente o nulo (SPEC-TKT-24)**: al crear un ticket, un `client_id` ausente o `null` → `required`; un valor que no es un entero positivo → `invalid` (misma convención que la decisión 12 para el primer mensaje).
19. **Precedencia entre `400` y `404` (SPEC-TKT-24, 19, 20 y 30)**: en las operaciones sobre un ticket que reciben cuerpo (por ejemplo, asociar productos), el formato del cuerpo se valida antes de buscar el ticket. Un cuerpo con formato inválido responde `400` aunque el ticket no exista o sea ajeno, y no revela si existe (RNF 4). Con un cuerpo de formato válido, un ticket inexistente o ajeno responde `404`.
