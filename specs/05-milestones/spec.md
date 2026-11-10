# 05 — Gestión de hitos

Origen: RF 1.5 · Relacionados: RNF 4, RNF 5 · Diagramas: [secuencias](../../diagrams/sequences/05-milestones.md), [clases](../../diagrams/classes.md)

Un hito (`Milestone`) es un mensaje o evento registrado en un ticket, con contenido, autor y fecha de creación.

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-MLS-01 | Complejo | **Mientras** el ticket no está en `Closed`, **cuando** el representante asignado registra un hito con contenido, **el sistema deberá** agregarlo al ticket. | RF 1.5.1 |
| SPEC-MLS-02 | Complejo | **Mientras** el ticket no está en `Closed`, **cuando** el cliente dueño responde con un mensaje, **el sistema deberá** agregarlo al ticket como hito. | RF 1.5.1, RF 1.6.3 |
| SPEC-MLS-03 | Por evento | **Cuando** se registra un hito, **el sistema deberá** guardar como autor al usuario autenticado y como fecha de creación el instante actual en UTC. | RF 1.5.1, Diagrama de clases |
| SPEC-MLS-04 | No deseado | **Si** el contenido del hito está vacío o tiene solo espacios, **entonces el sistema deberá** rechazarlo. | RF 1.5.1 |
| SPEC-MLS-11 | No deseado | **Si** el contenido del hito no es texto, **entonces el sistema deberá** rechazarlo e indicar que el contenido es inválido. | RF 1.5.1 |
| SPEC-MLS-05 | No deseado | **Si** se intenta registrar un hito en un ticket en `Closed`, **entonces el sistema deberá** rechazarlo e indicar que primero hay que reabrir el ticket. | RF 1.4.5, RF 1.5.1 |
| SPEC-MLS-06 | No deseado | **Si** quien intenta registrar el hito no es el cliente dueño ni el representante asignado, **entonces el sistema deberá** rechazarlo. | RNF 4 |
| SPEC-MLS-07 | Por evento | **Cuando** se solicitan los hitos de un ticket, **el sistema deberá** devolverlos en orden cronológico ascendente por fecha de creación, desempatando por orden de registro. | RF 1.5.2 |
| SPEC-MLS-08 | Por evento | **Cuando** se solicitan los hitos de un ticket, **el sistema deberá** incluir en cada uno el autor, su rol y la fecha de creación. | RF 1.5.2 |
| SPEC-MLS-09 | No deseado | **Si** se intenta modificar un hito ya registrado, **entonces el sistema deberá** rechazar la operación sin alterar el hito. | RNF 5 |
| SPEC-MLS-10 | No deseado | **Si** se intenta eliminar un hito ya registrado, **entonces el sistema deberá** rechazar la operación sin alterar el historial. | RNF 5 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. Los hitos son solo texto, sin adjuntos.
2. Un ticket cerrado no acepta hitos: primero hay que reabrirlo (SPEC-MLS-05).

Aprobada el 2026-11-10 (revisión transversal de huecos):

3. Un contenido que no es texto se rechaza como inválido (SPEC-MLS-11), con el mismo criterio que SPEC-USR-25.
