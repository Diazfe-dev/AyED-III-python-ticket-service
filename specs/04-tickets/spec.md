# 04 — Ciclo de vida del ticket

Origen: RF 1.4 · Relacionados: RNF 4, RNF 5, RNF 6, RNF 10 · Diagramas: [secuencias](../../diagrams/sequences/04-tickets.md), [clases](../../diagrams/classes.md)

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
| SPEC-TKT-27 | No deseado | **Reemplazada por SPEC-TKT-32, SPEC-TKT-33 y SPEC-TKT-34.** **Si** un usuario con rol `Admin` intenta operar sobre tickets, **entonces el sistema deberá** denegar la operación (`403`). | RF 1.1.5 |

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

## Acceso del Administrador (solo lectura)

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-32 | No deseado | **Si** un usuario con rol `Admin` intenta crear un ticket, asociar o quitar productos, registrar un hito, cerrar o reabrir un ticket, **entonces el sistema deberá** denegar la operación (`403`, código `forbidden`). | RF 1.1.5, RF 1.4.8 |
| SPEC-TKT-33 | Por evento | **Cuando** un administrador solicita el listado de tickets, **el sistema deberá** devolver todos los tickets, de cualquier cliente y representante. | RF 1.4.8 |
| SPEC-TKT-34 | Por evento | **Cuando** un administrador solicita un ticket, **el sistema deberá** devolver su estado, su cliente, su representante y sus productos (como SPEC-TKT-28). | RF 1.4.8 |

## Historial de cambios de estado

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-35 | Por evento | **Cuando** el cliente dueño, el representante asignado o un administrador solicita los cambios de estado de un ticket (`GET /tickets/{id}/state-changes`), **el sistema deberá** devolverlos en orden cronológico ascendente por fecha, desempatando por orden de registro. | RF 1.4.10, RNF 6 |
| SPEC-TKT-36 | Por evento | **Cuando** se devuelve un cambio de estado, **el sistema deberá** incluir el estado nuevo, el usuario que lo realizó (identificador, nombre y rol) y la fecha y hora en UTC. | RF 1.4.10, RNF 6 |
| SPEC-TKT-37 | No deseado | **Si** un cliente que no es el dueño o un representante que no es el asignado solicita los cambios de estado de un ticket, o el ticket no existe, **entonces el sistema deberá** responder como si el ticket no existiera (`404`, `ticket_not_found`, SPEC-TKT-19, 20 y 30). | RNF 4 |

## Filtros del listado y paginación

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-TKT-38 | Por evento | **Cuando** el request al listado de tickets incluye `state` (`New`, `InProgress` o `Closed`), **el sistema deberá** devolver solo los tickets en ese estado. | RF 1.4.9 |
| SPEC-TKT-39 | Por evento | **Cuando** un administrador o un representante envía `client_id` en el listado de tickets, **el sistema deberá** devolver solo los tickets de ese cliente que puede ver, y una lista vacía si no tiene ninguno. | RF 1.4.9 |
| SPEC-TKT-40 | Por evento | **Cuando** un administrador envía `representative_id` en el listado de tickets, **el sistema deberá** devolver solo los tickets asignados a ese representante. | RF 1.4.9 |
| SPEC-TKT-41 | Por evento | **Cuando** el request al listado de tickets incluye `q`, **el sistema deberá** devolver solo los tickets cuyo nombre de cliente o primer mensaje contiene ese texto, sin distinguir mayúsculas. | RF 1.4.9 |
| SPEC-TKT-42 | Por evento | **Cuando** el request al listado de tickets incluye `order` (`asc` o `desc`), **el sistema deberá** ordenarlo por fecha de creación en ese sentido y, ante igualdad, por identificador en el mismo sentido; sin `order` rige `desc` (SPEC-TKT-29). | RF 1.4.9 |
| SPEC-TKT-43 | No deseado | **Si** `state` no es un estado válido, `client_id` o `representative_id` no es un entero positivo, o `order` no es `asc` ni `desc`, **entonces el sistema deberá** rechazar el listado con `400` y el código `validation_error`, indicando el parámetro inválido. | RF 1.4.9 |
| SPEC-TKT-44 | Ubicuo | **El sistema deberá** combinar los filtros del listado de tickets con AND y aplicarlos solo sobre los tickets que el usuario puede ver, sin ampliar nunca su visibilidad (SPEC-TKT-17, 18 y 33). | RF 1.4.9, RNF 4 |
| SPEC-TKT-45 | Opcional | **Donde** se solicita el listado de tickets con `page` o `page_size`, **el sistema deberá** paginarlo según SPEC-PLT-17 a SPEC-PLT-22. | RNF 10 |
| SPEC-TKT-46 | No deseado | **Si** un cliente envía `client_id` o `representative_id`, o un representante envía `representative_id`, en el listado de tickets, **entonces el sistema deberá** denegar la operación (`403`, código `forbidden`). | RF 1.4.9, RNF 4 |

## Decisiones

Resueltas el 2026-11-09 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación):

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
11. **Permisos de escritura (SPEC-TKT-22, 05 y 27, G-03)**: quien puede ver el ticket pero no es el representante asignado (en la práctica, el cliente dueño) y asocia o quita productos recibe `403` con el código `forbidden` (`PermissionDeniedError`). Un ticket que el usuario no puede ver sigue respondiendo `404` (SPEC-TKT-19 y 20). Un `Admin` recibe `403` en toda operación (SPEC-TKT-27), antes de cualquier consulta a la base. En las operaciones que reciben cuerpo (crear un ticket, asociar productos y registrar un hito de [05-milestones](../05-milestones/spec.md)), el `400` de formato precede a ese `403` (decisión 19). SPEC-TKT-05 (solo `Representative` crea) y SPEC-TKT-27 se superponen para el `Admin` que crea un ticket: es la misma excepción y el mismo `403`, con un caso de prueba por spec; con un cuerpo de formato inválido, el `Admin` y el `Client` que intentan crear reciben `400`. Modificada el 2026-11-11 (G-21 y G-01 de 05-milestones): antes, el `403` del `Admin` y el de SPEC-TKT-05 precedían al formato. Sobre la reapertura, ver la decisión 17.
12. **Primer mensaje inválido (SPEC-TKT-23, G-04)**: ausente, vacío o solo espacios → `required`; un valor que no es texto → `invalid` (misma convención que usuarios y productos).
13. **Asociar productos a un ticket existente (SPEC-TKT-24, 25 y 07, G-05)**: rigen las mismas reglas que en la creación. `product_ids` es obligatorio y es una lista no vacía de enteros positivos (un texto de dígitos se rechaza). Los ids repetidos en el pedido se colapsan en una sola asociación. Si algún id no existe o está inactivo, responde `400` `invalid_product` y no se agrega ninguno (todo o nada).
14. **Listados (SPEC-TKT-29, G-06)**: "más reciente" es `Ticket.created_at` (instante del reloj inyectado) descendente y, ante igualdad, `id` descendente. El diagrama de clases se actualiza con `Ticket.created_at` en la task de diagramas.
15. **Productos en un ticket cerrado (SPEC-TKT-07 y 21, G-07)**: asociar y quitar productos está permitido en cualquier estado, incluido `Closed`.

Aprobadas el 2026-11-11 (huecos G-18 y G-19 de [plan.md](plan.md#huecos-y-preguntas-abiertas) y revisión de requerimientos). Se agregan SPEC-TKT-30 (ticket inexistente o fuera de rango → `404` con el código `ticket_not_found`, igual que SPEC-USR-26) y SPEC-TKT-31 (asociación de los productos indicados en el alta):

16. **`client_id` como texto de dígitos (SPEC-TKT-24, G-19)**: `client_id` acepta un texto de dígitos (`"3"`), con la misma lectura de "entero positivo" que SPEC-PTY-20 y SPEC-PRD-15.
17. **Reapertura (SPEC-TKT-11, G-18)**: pueden reabrir el cliente dueño y el representante asignado; SPEC-TKT-11 no cambia. El `403` de la decisión 11 no aplica a la reapertura: el único `403` posible al reabrir es el del `Admin` (SPEC-TKT-27).
18. **`client_id` ausente o nulo (SPEC-TKT-24)**: al crear un ticket, un `client_id` ausente o `null` → `required`; un valor que no es un entero positivo → `invalid` (misma convención que la decisión 12 para el primer mensaje).
19. **Precedencia entre `400`, `403` y `404` (SPEC-TKT-05, 19, 20, 24, 27 y 30)**: en toda operación que recibe cuerpo (crear un ticket, asociar productos y registrar un hito de [05-milestones](../05-milestones/spec.md)), el formato del cuerpo se valida antes que cualquier otra regla. Formato es lo que se decide sin consultar la base: campos ausentes, nulos, vacíos o de un tipo inválido (`required`/`invalid`). Un cuerpo con formato inválido responde `400` aunque quien llama sea `Admin` (o, al crear, `Client`) y aunque el ticket no exista o sea ajeno, y no revela si existe (RNF 4). Con un cuerpo de formato válido: al crear, quien no es `Representative` recibe `403` (SPEC-TKT-05 y 27) antes de que se verifiquen el cliente y los productos (`invalid_client` e `invalid_product`, decisión 9); en las operaciones sobre un ticket, un `Admin` recibe `403` (SPEC-TKT-27), un ticket inexistente o ajeno responde `404` y quien lo ve sin ser el representante asignado recibe `403` (decisión 11). Modificada el 2026-11-11 (G-21 y G-01 de 05-milestones): antes, el `403` del `Admin` y el de SPEC-TKT-05 precedían al formato, y esta decisión solo ordenaba el `400` frente al `404`.

Aprobadas el 2026-11-12 (huecos G-23 y G-24 de [plan.md](plan.md#huecos-y-preguntas-abiertas)); el texto de las specs no cambia, estas decisiones fijan detalles que no definía:

20. **`product_ids` sin productos al crear (SPEC-TKT-01, G-23)**: en el alta (`POST /tickets`), `product_ids` ausente, `null` o `[]` significa "sin productos" y el ticket se crea igual. En `POST /tickets/{id}/products` sigue siendo obligatorio y una lista no vacía (decisión 13).
21. **Código JSON de SPEC-TKT-26 (G-24)**: quitar un producto que no está asociado al ticket responde `404` con el código `product_not_in_ticket` (mismo estilo que `ticket_not_found` de SPEC-TKT-30).

Aprobadas el 2026-11-12 (nueva área [07-ui](../07-ui/spec.md)). Las specs 32 a 46 son nuevas y no estaban implementadas; solo SPEC-TKT-27 cambia de comportamiento:

22. **El Administrador lee todos los tickets (SPEC-TKT-27 reemplazada)**: SPEC-TKT-27 prohibía al `Admin` toda operación sobre tickets. Pasa a ser: toda **escritura** sigue respondiendo `403` (SPEC-TKT-32) y el `Admin` puede **leer**: el listado de todos los tickets (SPEC-TKT-33), el detalle (SPEC-TKT-34), los hitos (SPEC-MLS-12 en [05-milestones](../05-milestones/spec.md)) y el historial de estados (SPEC-TKT-35). El representante sigue viendo solo los asignados (SPEC-TKT-18 sin cambios) y el cliente solo los suyos (SPEC-TKT-17, 19; RNF 4). Las referencias a SPEC-TKT-27 en las decisiones 6, 11 y 19 se leen ahora como SPEC-TKT-32 (el `403` del `Admin` solo vale en escrituras); la precedencia del formato `400` sobre el `403` de las decisiones 11 y 19 no cambia. Un `Admin` que lee un ticket inexistente recibe `404` (SPEC-TKT-30), ya sin el `403` previo a la consulta de la decisión 11. **Impacto en lo implementado**: el servicio rechaza hoy al `Admin` en las lecturas y los tests de `403` del `Admin` en `GET` deben invertirse al implementar este cambio.
23. **El historial de estados vive en esta área (SPEC-TKT-35 a 37)** y no en 05-milestones: los cambios de estado son un registro de `Ticket` (SPEC-TKT-14 a 16, RNF 6), no un hito. Tiene las mismas reglas de visibilidad que los hitos (cliente dueño, representante asignado y, ahora, `Admin`) y no tiene escrituras: el historial solo se genera por transiciones.
24. **Filtros del listado (SPEC-TKT-38 a 46)**: `state`, `client_id`, `representative_id` (solo `Admin`), `q`, `order`, `page` y `page_size`. `q` busca en el nombre del cliente y en el primer mensaje del ticket (el hito inicial); es una definición de esta decisión, porque el ticket no tiene título. `order` ordena por `created_at` (la decisión 14 define el desempate). Un `client_id` o `representative_id` que no existe devuelve lista vacía y no `404`: es un filtro, no un recurso. `representative_id` para un no-`Admin` y `client_id` para un `Client` responden `403` (SPEC-TKT-46) en lugar de ignorarse, para que no parezcan filtrar. El cliente puede usar `state`, `q`, `order` y la paginación.
