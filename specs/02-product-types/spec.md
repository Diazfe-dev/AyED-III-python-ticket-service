# 02 — Gestión de tipos de producto y rubros

Origen: RF 1.2 · Diagramas: [secuencias](../../diagrams/sequences/02-product-types.md), [clases](../../diagrams/classes.md)

Jerarquía de clasificación: `Category` (rubro) → `ProductType` → `Product`.

## Categorías (rubros)

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PTY-01 | Por evento | **Cuando** un administrador crea una categoría con un nombre, **el sistema deberá** registrarla. | RF 1.2.3, Seq. tipos §1 |
| SPEC-PTY-02 | No deseado | **Si** ya existe una categoría con el mismo nombre (sin distinguir mayúsculas), **entonces el sistema deberá** rechazar la creación o la modificación. | RF 1.2.3 |
| SPEC-PTY-12 | Por evento | **Cuando** un administrador modifica el nombre de una categoría, **el sistema deberá** guardar el cambio. | RF 1.2.3 |
| SPEC-PTY-13 | Por evento | **Cuando** un administrador da de baja una categoría sin tipos de producto asociados, **el sistema deberá** eliminarla. | RF 1.2.3 |
| SPEC-PTY-14 | No deseado | **Si** un administrador intenta dar de baja una categoría que tiene tipos de producto asociados, **entonces el sistema deberá** rechazar la baja e informar el motivo. | RF 1.2.3 |

## Tipos de producto

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PTY-03 | Por evento | **Cuando** un administrador crea un tipo de producto con nombre y categoría, **el sistema deberá** registrarlo asociado a esa categoría. | RF 1.2.1 |
| SPEC-PTY-04 | No deseado | **Si** la categoría indicada no existe, **entonces el sistema deberá** rechazar la creación del tipo de producto. | RF 1.2.1 |
| SPEC-PTY-05 | No deseado | **Si** ya existe un tipo de producto con el mismo nombre en la misma categoría, **entonces el sistema deberá** rechazar la creación. | RF 1.2.1 |
| SPEC-PTY-06 | Por evento | **Cuando** un administrador modifica el nombre o la categoría de un tipo de producto, **el sistema deberá** guardar los cambios. | RF 1.2.1 |
| SPEC-PTY-07 | Por evento | **Cuando** un administrador da de baja un tipo de producto sin productos asociados (activos o inactivos), **el sistema deberá** eliminarlo. | RF 1.2.1 |
| SPEC-PTY-08 | No deseado | **Si** un administrador intenta dar de baja un tipo de producto que tiene productos asociados, **entonces el sistema deberá** rechazar la baja e informar el motivo. | RF 1.2.1 |

## Listados y permisos

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PTY-09 | Por evento | **Cuando** un usuario autenticado solicita el listado de tipos de producto, **el sistema deberá** devolverlos agrupados por categoría. | RF 1.2.2 |
| SPEC-PTY-10 | Por evento | **Cuando** un usuario autenticado solicita los tipos de producto de una categoría, **el sistema deberá** devolver solo los de esa categoría. | RF 1.2.2 |
| SPEC-PTY-11 | No deseado | **Si** un usuario sin rol `Admin` intenta crear, modificar o dar de baja categorías o tipos de producto, **entonces el sistema deberá** denegar la operación. | RF 1.1.5, RNF 2 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. Las categorías tienen ABM completo (RF 1.2.3). Su baja es física y se rechaza si tienen tipos asociados.
