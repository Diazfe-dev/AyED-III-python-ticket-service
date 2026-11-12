# 06 — Gestión de notificaciones

Origen: RF 1.6 · Diagramas: [secuencias](../../diagrams/sequences/06-notifications.md), [clases](../../diagrams/classes.md) (patrón Strategy)

Depende de: SPEC-USR-06, SPEC-USR-23 ([01-users](../01-users/spec.md)) · SPEC-TKT-01, SPEC-TKT-04, SPEC-TKT-07, SPEC-TKT-09, SPEC-TKT-10, SPEC-TKT-11, SPEC-TKT-12, SPEC-TKT-14, SPEC-TKT-15, SPEC-TKT-21 ([04-tickets](../04-tickets/spec.md)) · SPEC-MLS-01, SPEC-MLS-02, SPEC-MLS-03 ([05-milestones](../05-milestones/spec.md))

## Canal de envío

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-NTF-01 | Opcional | **Donde** el canal preferido del destinatario es `mail`, **el sistema deberá** enviar la notificación con la estrategia de mail. | RF 1.6.1, Diagrama de clases |
| SPEC-NTF-02 | Opcional | **Donde** el canal preferido del destinatario es `whatsapp`, **el sistema deberá** enviar la notificación con la estrategia de WhatsApp. | RF 1.6.1, Diagrama de clases |
| SPEC-NTF-12 | Ubicuo | **El sistema deberá** simular el envío de las notificaciones registrándolas, sin conectarse con servicios externos de mail ni de WhatsApp. | RF 1.6.1 |
| SPEC-NTF-03 | Ubicuo | **El sistema deberá** registrar cada notificación asociada al ticket que la originó, con destinatario, canal, mensaje, fecha (el instante actual en UTC) y estado (`sent` o `failed`). | RF 1.6.1, Diagrama de clases (`Ticket.notifications`) |
| SPEC-NTF-18 | Ubicuo | **El sistema deberá** redactar el mensaje de cada notificación de modo que identifique el ticket y el evento que la originó (creación, hito, cambio de estado con el nuevo estado, cierre o reapertura); el texto exacto no forma parte del contrato. | RF 1.6.2, Decisión 10 |
| SPEC-NTF-04 | No deseado | **Si** el envío de una notificación falla, **entonces el sistema deberá** registrarla con estado `failed` y el texto del error producido. | RF 1.6.1 |
| SPEC-NTF-14 | No deseado | **Si** el envío de una notificación falla, **entonces el sistema no deberá** revertir la operación del ticket que la originó (el cambio persiste). | RF 1.6.1 |
| SPEC-NTF-19 | No deseado | **Si** el envío de una notificación falla, **entonces el sistema deberá** devolver a quien solicitó la operación la misma respuesta exitosa que si el envío no hubiera fallado. | RF 1.6.1 |
| SPEC-NTF-15 | No deseado | **Si** una operación no termina con éxito (cualquier respuesta `4xx` o `5xx`, incluido el `401` y un `500` con rollback), **entonces el sistema no deberá** enviar ni registrar ninguna notificación. | RF 1.6 |

## Notificaciones al cliente

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-NTF-05 | Por evento | **Cuando** se crea un ticket, **el sistema deberá** enviar exactamente una notificación al cliente asociado. El hito inicial (SPEC-TKT-04) y el estado inicial `New` (SPEC-TKT-15) no disparan SPEC-NTF-06, 07 ni 08. | RF 1.6.1, Seq. tickets §1 |
| SPEC-NTF-06 | Por evento | **Cuando** el representante registra un nuevo hito en un ticket sin que cambie el estado, **el sistema deberá** notificar al cliente del ticket. | RF 1.6.2 |
| SPEC-NTF-07 | Por evento | **Cuando** el representante cambia el estado de un ticket sin registrar un hito, **el sistema deberá** notificar al cliente del ticket indicando el nuevo estado. | RF 1.6.2 |
| SPEC-NTF-08 | Por evento | **Cuando** el representante registra un hito que además cambia el estado, **el sistema deberá** enviar al cliente una única notificación que informe ambos eventos, en lugar de las de SPEC-NTF-06 y SPEC-NTF-07. | RF 1.6.2, Seq. hitos §1 |

## Notificaciones al representante

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-NTF-09 | Por evento | **Cuando** el cliente responde en un ticket, **el sistema deberá** notificar al representante asignado. | RF 1.6.3 |
| SPEC-NTF-10 | Por evento | **Cuando** el cliente reabre un ticket, **el sistema deberá** notificar al representante asignado. | RF 1.6.3 |
| SPEC-NTF-13 | Por evento | **Cuando** el cliente cierra un ticket, **el sistema deberá** notificar al representante asignado. | RF 1.6.3 |

## Exclusiones

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-NTF-11 | No deseado | **Si** el destinatario de una notificación es el mismo usuario que realizó la acción, **entonces el sistema deberá** omitir el envío y no registrar la notificación. | Regla defensiva (RF 1.6) |
| SPEC-NTF-16 | Por evento | **Cuando** el destinatario de una notificación está inactivo, **el sistema deberá** notificarlo igual. | Decisión 9, Decisión 8 de [04-tickets](../04-tickets/spec.md#decisiones) |
| SPEC-NTF-17 | No deseado | **Cuando** se agregan productos a un ticket (SPEC-TKT-07) o se quitan (SPEC-TKT-21), **el sistema no deberá** enviar ninguna notificación. | Decisión 12, SPEC-TKT-07, SPEC-TKT-21 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. Cuando el cliente cierra un ticket, se notifica al representante (RF 1.6.3 ampliado).
2. Las notificaciones se simulan: las estrategias `MailNotification` y `WhatsappNotification` solo registran el envío. El patrón Strategy permite conectar envíos reales más adelante sin cambiar los services.

Confirmada el 2026-11-10 (revisión transversal de huecos):

3. Las notificaciones son internas: no tienen endpoint propio (no hay `NotificationController`). Se verifican con tests y consultando la base.

Aprobadas el 2026-11-11:

4. **Una sola notificación al crear un ticket (SPEC-NTF-05)**: crear un ticket envía exactamente una notificación al cliente. El hito inicial (SPEC-TKT-04) y el estado inicial `New` (SPEC-TKT-15) forman parte del alta y no disparan SPEC-NTF-06, 07 ni 08.
5. **SPEC-NTF-08 excluye a SPEC-NTF-06 y 07**: cuando un hito provoca un cambio de estado, el cliente recibe una única notificación combinada y nunca las separadas además. Un `start_progress` redundante (sin cambio de estado, decisión 5 de [05-milestones](../05-milestones/spec.md#decisiones)) genera solo la de SPEC-NTF-06.
6. **Fallo de envío dividido en tres specs (SPEC-NTF-04, 14 y 19)**: SPEC-NTF-04 cubre el registro del fallo (`Notification` con estado `failed` y el texto del error); SPEC-NTF-14 cubre que el fallo no revierte la operación del ticket (el cambio persiste); SPEC-NTF-19 cubre que quien llama recibe la misma respuesta exitosa. Se agregaron al final para no renumerar los IDs existentes.
7. **Datos registrados (SPEC-NTF-03)**: destinatario, canal, mensaje, fecha (el instante actual en UTC, mismo criterio que SPEC-TKT-14 y SPEC-MLS-03) y estado `sent` o `failed`. El texto del error se especifica solo en SPEC-NTF-04.
8. **Una operación que no termina con éxito no notifica (SPEC-NTF-15)**: cualquier respuesta `4xx` o `5xx` (incluido el `401` y un `500` con rollback) no envía ni registra ninguna notificación.
9. **Destinatarios inactivos (SPEC-NTF-16)**: un destinatario inactivo igual es notificado, coherente con la decisión 8 de [04-tickets](../04-tickets/spec.md#decisiones).
10. **Contenido del mensaje (SPEC-NTF-18)**: el mensaje debe identificar el ticket y el evento (creación, hito, cambio de estado con el nuevo estado, cierre, reapertura). El texto exacto no es parte del contrato: los tests verifican esos datos, no la frase.
11. **SPEC-NTF-11 es una regla defensiva**: en los flujos normales el destinatario nunca es quien realiza la acción; solo se alcanza llamando al service directamente. Por eso su origen la declara como regla defensiva y no cita solo RF 1.6. Cuando ocurre, se omite el envío y no se registra la notificación (mismo criterio que SPEC-NTF-15).
12. **Agregar o quitar productos no notifica (SPEC-NTF-17)**: agregar productos a un ticket (SPEC-TKT-07) o quitarlos (SPEC-TKT-21) no envía ninguna notificación.
