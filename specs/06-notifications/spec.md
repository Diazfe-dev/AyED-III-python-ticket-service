# 06 — Gestión de notificaciones

Origen: RF 1.6 · Diagramas: [secuencias](../../diagrams/sequences/06-notifications.md), [clases](../../diagrams/classes.md) (patrón Strategy)

## Canal de envío

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-NTF-01 | Opcional | **Donde** el canal preferido del destinatario es `mail`, **el sistema deberá** enviar la notificación con la estrategia de mail. | RF 1.6.1, Diagrama de clases |
| SPEC-NTF-02 | Opcional | **Donde** el canal preferido del destinatario es `whatsapp`, **el sistema deberá** enviar la notificación con la estrategia de WhatsApp. | RF 1.6.1, Diagrama de clases |
| SPEC-NTF-12 | Ubicuo | **El sistema deberá** simular el envío de las notificaciones registrándolas, sin conectarse con servicios externos de mail ni de WhatsApp. | RF 1.6.1 |
| SPEC-NTF-03 | Ubicuo | **El sistema deberá** registrar cada notificación enviada asociada al ticket que la originó, con destinatario, canal, mensaje y fecha. | RF 1.6.1, Diagrama de clases (`Ticket.notifications`) |
| SPEC-NTF-04 | No deseado | **Si** el envío de una notificación falla, **entonces el sistema deberá** registrar el fallo sin revertir la operación del ticket que la originó. | RF 1.6.1 |

## Notificaciones al cliente

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-NTF-05 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** notificar al cliente asociado. | RF 1.6.1, Seq. tickets §1 |
| SPEC-NTF-06 | Por evento | **Cuando** el representante registra un nuevo hito en un ticket, **el sistema deberá** notificar al cliente del ticket. | RF 1.6.2 |
| SPEC-NTF-07 | Por evento | **Cuando** el representante cambia el estado de un ticket, **el sistema deberá** notificar al cliente del ticket indicando el nuevo estado. | RF 1.6.2 |
| SPEC-NTF-08 | Por evento | **Cuando** el representante registra un hito que además cambia el estado, **el sistema deberá** enviar al cliente una única notificación que informe ambos eventos. | RF 1.6.2, Seq. hitos §1 |

## Notificaciones al representante

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-NTF-09 | Por evento | **Cuando** el cliente responde en un ticket, **el sistema deberá** notificar al representante asignado. | RF 1.6.3 |
| SPEC-NTF-10 | Por evento | **Cuando** el cliente reabre un ticket, **el sistema deberá** notificar al representante asignado. | RF 1.6.3 |
| SPEC-NTF-13 | Por evento | **Cuando** el cliente cierra un ticket, **el sistema deberá** notificar al representante asignado. | RF 1.6.3 |

## Exclusiones

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-NTF-11 | No deseado | **Si** el destinatario de una notificación es el mismo usuario que realizó la acción, **entonces el sistema deberá** omitir el envío. | RF 1.6 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. Cuando el cliente cierra un ticket, se notifica al representante (RF 1.6.3 ampliado).
2. Las notificaciones se simulan: las estrategias `MailNotification` y `WhatsappNotification` solo registran el envío. El patrón Strategy permite conectar envíos reales más adelante sin cambiar los services.
