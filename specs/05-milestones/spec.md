# 05 — Gestión de hitos

Origen: RF 1.5 · Relacionados: RNF 4, RNF 5 · Diagramas: [secuencias](../../diagrams/sequences/05-milestones.md), [clases](../../diagrams/classes.md)

Depende de: SPEC-TKT-09, SPEC-TKT-19, SPEC-TKT-20, SPEC-TKT-30, SPEC-TKT-32, SPEC-TKT-33 ([04-tickets](../04-tickets/spec.md)) · SPEC-NTF-06, SPEC-NTF-08, SPEC-NTF-09 ([06-notifications](../06-notifications/spec.md))

Un hito (`Milestone`) es un mensaje o evento registrado en un ticket, con contenido, autor y fecha de creación.

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-MLS-01 | Complejo | **Mientras** el ticket no está en `Closed`, **cuando** el representante asignado registra un hito con contenido, **el sistema deberá** agregarlo al ticket. | RF 1.5.1 |
| SPEC-MLS-02 | Complejo | **Mientras** el ticket no está en `Closed`, **cuando** el cliente dueño responde con un mensaje, **el sistema deberá** agregarlo al ticket como hito. | RF 1.5.1, RF 1.6.3 |
| SPEC-MLS-03 | Por evento | **Cuando** se registra un hito, **el sistema deberá** guardar como autor al usuario autenticado y como fecha de creación el instante actual en UTC. | RF 1.5.1, Diagrama de clases |
| SPEC-MLS-04 | No deseado | **Si** el contenido del hito falta, está vacío o tiene solo espacios, **entonces el sistema deberá** rechazarlo e indicar que el contenido es obligatorio (`400`). | RF 1.5.1 |
| SPEC-MLS-11 | No deseado | **Si** el contenido del hito no es texto, **entonces el sistema deberá** rechazarlo e indicar que el contenido es inválido (`400`). | RF 1.5.1 |
| SPEC-MLS-05 | No deseado | **Si** se intenta registrar un hito en un ticket en `Closed`, **entonces el sistema deberá** rechazarlo e indicar que primero hay que reabrir el ticket (`409`). | RF 1.4.5, RF 1.5.1 |
| SPEC-MLS-06 | No deseado | **Si** quien intenta registrar el hito es un cliente que no es el dueño o un representante que no es el asignado, **entonces el sistema deberá** responder como si el ticket no existiera (`404`, SPEC-TKT-19, 20 y 30). | RNF 4 |
| SPEC-MLS-07 | Por evento | **Cuando** el cliente dueño o el representante asignado solicita los hitos de un ticket, **el sistema deberá** devolverlos en orden cronológico ascendente por fecha de creación, desempatando por orden de registro. | RF 1.5.2 |
| SPEC-MLS-08 | Por evento | **Cuando** el cliente dueño o el representante asignado solicita los hitos de un ticket, **el sistema deberá** incluir en cada uno el contenido, el autor, su rol y la fecha de creación. | RF 1.5.2 |
| SPEC-MLS-09 | No deseado | **Si** se intenta modificar un hito ya registrado, **entonces el sistema deberá** rechazar la operación sin alterar el hito. | RNF 5 |
| SPEC-MLS-10 | No deseado | **Si** se intenta eliminar un hito ya registrado, **entonces el sistema deberá** rechazar la operación sin alterar el historial. | RNF 5 |
| SPEC-MLS-12 | Por evento | **Cuando** un administrador solicita los hitos de un ticket (`GET /tickets/{id}/milestones`), **el sistema deberá** devolverlos con el mismo orden y contenido que SPEC-MLS-07 y SPEC-MLS-08, sin importar el cliente ni el representante del ticket. | RF 1.5.3 |

## Decisiones

Resueltas el 2026-11-09 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación):

1. Los hitos son solo texto, sin adjuntos.
2. Un ticket cerrado no acepta hitos: primero hay que reabrirlo (SPEC-MLS-05).

Aprobada el 2026-11-10 (revisión transversal de huecos):

3. Un contenido que no es texto se rechaza como inválido (SPEC-MLS-11), con el mismo criterio que SPEC-USR-25.

Aprobadas el 2026-11-11 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación) (huecos G-22, Q1 y Q2):

4. **Precedencia entre `400` y `404` (SPEC-MLS-04, 11 y 06, G-22)**: la decisión 19 de [04-tickets](../04-tickets/spec.md#decisiones) rige también para `POST /tickets/{id}/milestones`. El formato del cuerpo se valida antes de buscar el ticket: un cuerpo con formato inválido responde `400` aunque el ticket no exista o sea ajeno, y no revela si existe (RNF 4). Con un cuerpo de formato válido, un ticket inexistente o ajeno responde `404` (SPEC-MLS-06, SPEC-TKT-19, 20 y 30).
5. **`start_progress` sobre un ticket que no está en `New` (SPEC-TKT-09 y 13, Q1)**: si el representante asignado envía `start_progress: true` y el ticket ya está en `InProgress`, el indicador se ignora: el hito se guarda, el ticket no cambia de estado, no se registra un cambio de estado y la respuesta es `201`. Es una excepción explícita a SPEC-TKT-13: el indicador no es una solicitud de transición independiente sino un agregado del alta del hito, y el efecto buscado (ticket en curso) ya se cumple; rechazar un mensaje válido por un indicador redundante sería hostil. Se descartaron responder `409` sin guardar el hito y guardarlo informando el rechazo. Un ticket en `Closed` sigue rechazando el hito por SPEC-MLS-05, con o sin el indicador.
6. **`start_progress` enviado por el cliente dueño (SPEC-TKT-09, Q2)**: si el cliente dueño envía `start_progress: true`, el indicador se ignora: el hito se guarda y la respuesta es `201`. El indicador solo actúa si lo envía el representante asignado y el ticket está en `New`. Es coherente con la decisión 5 y no obliga a buscar el ticket ni a conocer el rol frente a él antes de validar el formato (decisión 4). Se descartaron `403` y `400`.

Aprobadas el 2026-11-11 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación) (huecos G-25, G-21, G-26 y G-27):

7. **Tipo de `start_progress` (SPEC-TKT-09)**: el campo es opcional; si falta, vale `false`. Un valor que no es booleano (incluidos `null`, `"yes"` y `1`) responde `400` indicando el campo como inválido, con el mismo criterio que SPEC-USR-25.
8. **Validación del contenido (SPEC-MLS-04 y 11)**: un `content` ausente, vacío o con solo espacios → `required`; un valor que no es texto → `invalid` (misma convención que la decisión 12 de 04-tickets para el primer mensaje). El contenido no tiene longitud máxima.
9. **Códigos de error**: SPEC-MLS-04 y 11 responden `400` con el código de validación y el campo marcado como `required` o `invalid`; SPEC-MLS-05 responde `409` con el código nuevo `ticket_closed`; SPEC-MLS-06 responde `404` con `ticket_not_found` (SPEC-TKT-30). Un `Admin` que registra o lista hitos recibe `403` con `forbidden` (SPEC-TKT-27). **Orden entre el 400 de formato y el 403 del Admin (G-21)**: en `POST /tickets/{id}/milestones` el formato del cuerpo se valida antes que el rol: un `Admin` que envía un cuerpo con formato inválido recibe `400`, y con un cuerpo de formato válido recibe `403` (SPEC-TKT-27). Es el mismo criterio que la decisión 4: el formato va primero para todos los roles. **Impacto en otra área**: esto invierte lo que 04-tickets implementa hoy para sus propias operaciones (`TicketService.add_products` rechaza al `Admin` antes de validar el formato). Se alinearon el 2026-11-11 (T-MLS-19 a 22): el reordenamiento de `add_products` y `create_ticket`, las decisiones 11 y 19 de 04 y el plan, los tests y los diagramas de 04.
10. **Modificar o eliminar un hito (SPEC-MLS-09 y 10)**: la API no expone `PATCH`, `PUT` ni `DELETE` sobre un hito, así que esos pedidos quedan cubiertos por SPEC-PLT-15 (`404` o `405` con cuerpo JSON). El modelo es inmutable en el dominio (RNF 5).
11. **Orden completo de validaciones al registrar un hito (G-26)**: `POST /tickets/{id}/milestones` evalúa en este orden y responde con el primer error que encuentra: (0) `401` si no hay sesión (SPEC-USR-16); (1) `400` si el cuerpo tiene formato inválido (SPEC-MLS-04 y 11, decisiones 7 y 8); (2) `403` con `forbidden` si quien llama es `Admin` (SPEC-TKT-27, decisión 9); (3) `404` con `ticket_not_found` si el ticket no existe o es ajeno (SPEC-MLS-06, SPEC-TKT-19, 20 y 30), sin revelar si existe (RNF 4); (4) `409` con `ticket_closed` si el ticket está cerrado (SPEC-MLS-05). Se descartó dejar el orden implícito.
12. **Orden de validaciones al listar los hitos (G-27)**: `GET /tickets/{id}/milestones` no tiene cuerpo, así que no hay paso de formato. Evalúa en este orden y responde con el primer error que encuentra: (0) `401` si no hay sesión (SPEC-USR-16); (1) `403` con `forbidden` si quien llama es `Admin` (SPEC-TKT-27), exista o no el ticket; (2) `404` con `ticket_not_found` si el ticket no existe o es ajeno (SPEC-MLS-06, SPEC-TKT-19, 20 y 30). Se descartó dejar el orden implícito.

Aprobada el 2026-11-12 (nueva área [07-ui](../07-ui/spec.md), reemplazo de SPEC-TKT-27):

13. **Lectura de hitos por el Administrador (SPEC-MLS-12)**: SPEC-TKT-27 está reemplazada ([04-tickets](../04-tickets/spec.md#decisiones), decisión 22). El `Admin` puede listar los hitos de cualquier ticket, solo lectura. Cambios sobre las decisiones previas: en la decisión 9, el `Admin` que **lista** hitos ya no recibe `403` (el `Admin` que **registra** uno sigue recibiendo `403`, ahora por SPEC-TKT-32); en la decisión 12, el paso (1) (`403` al `Admin`) desaparece y `GET /tickets/{id}/milestones` evalúa (0) `401` y (1) `404` con `ticket_not_found` si el ticket no existe o es ajeno (un `Admin` nunca lo recibe por ajeno). El orden de la decisión 11 (registrar) no cambia. Las menciones a SPEC-TKT-27 en las decisiones 9, 11 y 12 se leen como SPEC-TKT-32 para escrituras.
