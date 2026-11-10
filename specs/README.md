# Specs

Descomposición de los requerimientos funcionales de [REQUERIMIENTOS.md](../REQUERIMIENTOS.md) en especificaciones atómicas y verificables, escritas con **EARS** (*Easy Approach to Requirements Syntax*).

## Patrones EARS

Cada spec usa exactamente uno de estos patrones. Las palabras clave van en **negrita**.

| Patrón | Plantilla | Cuándo usarlo |
|--------|-----------|---------------|
| Ubicuo | **El sistema deberá** \<respuesta\>. | Comportamiento que se cumple siempre. |
| Por evento | **Cuando** \<disparador\>, **el sistema deberá** \<respuesta\>. | Reacción a una acción o evento. |
| Por estado | **Mientras** \<condición\>, **el sistema deberá** \<respuesta\>. | Comportamiento válido solo en cierto estado. |
| Comportamiento no deseado | **Si** \<condición no deseada\>, **entonces el sistema deberá** \<respuesta\>. | Errores, accesos indebidos, entradas inválidas. |
| Opcional | **Donde** \<característica presente\>, **el sistema deberá** \<respuesta\>. | Comportamiento que depende de una configuración o característica. |
| Complejo | **Mientras** \<condición\>, **cuando** \<disparador\>, **el sistema deberá** \<respuesta\>. | Combinación de estado y evento. |

## Convenciones

- **ID**: `SPEC-<ÁREA>-<NN>`. Áreas: `USR` (usuarios y accesos), `PTY` (tipos de producto), `PRD` (productos), `TKT` (ciclo de vida del ticket), `MLS` (hitos), `NTF` (notificaciones).
- **Atómica**: una spec, un comportamiento. Si hace falta "y" para describir dos respuestas independientes, son dos specs.
- **Verificable**: cada spec se puede probar con al menos un test. El test referencia el ID en su docstring.
- **Trazable**: cada spec indica el RF de origen y, si aplica, los RNF y el diagrama relacionados.
- **Inmutable una vez implementada**: si el comportamiento cambia, se marca la spec como `Reemplazada por SPEC-...` y se crea una nueva. No se reutilizan IDs.
- Las nuevas specs de un área toman el siguiente número libre y se ubican en la sección que corresponde, aunque el orden de IDs no quede correlativo.
- Cada `spec.md` termina con una sección **Decisiones** (ambigüedades ya resueltas) y, si hace falta, **Preguntas abiertas**. Una spec que depende de una pregunta abierta no se implementa hasta resolverla. La decisión se registra en [MEMORY.md](../MEMORY.md) y se pasa a la sección Decisiones.

## Estructura de un área

Cada área es una carpeta `NN-<área>/`. `spec.md` existe siempre. Los demás archivos se crean cuando se empieza a trabajar el área, en este orden y antes de escribir código (ver [AGENTS.md](../AGENTS.md)):

| Archivo | Responde |
|---------|----------|
| `spec.md` | **Qué** debe hacer el sistema (specs EARS, fuente de verdad) |
| `plan.md` | **Cómo** se implementa |
| `tasks.md` | **En qué orden** se hace |
| `test-plan.md` | **Cómo se verifica** |

## Índice

| Área | Descripción | RF | spec | plan | tasks | test-plan |
|------|-------------|----|------|------|-------|-----------|
| [01-users/](01-users/spec.md) | Gestión de usuarios y accesos | 1.1 | ✅ | ⬜ | ⬜ | ⬜ |
| [02-product-types/](02-product-types/spec.md) | Gestión de tipos de producto y rubros | 1.2 | ✅ | ⬜ | ⬜ | ⬜ |
| [03-products/](03-products/spec.md) | Gestión de productos | 1.3 | ✅ | ⬜ | ⬜ | ⬜ |
| [04-tickets/](04-tickets/spec.md) | Ciclo de vida del ticket | 1.4 | ✅ | ⬜ | ⬜ | ⬜ |
| [05-milestones/](05-milestones/spec.md) | Gestión de hitos | 1.5 | ✅ | ⬜ | ⬜ | ⬜ |
| [06-notifications/](06-notifications/spec.md) | Gestión de notificaciones | 1.6 | ✅ | ⬜ | ⬜ | ⬜ |

## Actores

- **Administrador** (rol `Admin`, RF 1.1.5): gestiona usuarios, categorías, tipos de producto y productos.
- **Representante**: crea y gestiona tickets de sus clientes.
- **Cliente**: consulta e interactúa solo con sus propios tickets.
