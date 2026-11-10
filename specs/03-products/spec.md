# 03 — Gestión de productos

Origen: RF 1.3 · Diagramas: [secuencias](../../diagrams/sequences/03-products.md), [clases](../../diagrams/classes.md)

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PRD-01 | Por evento | **Cuando** un administrador crea un producto con nombre y tipo de producto, **el sistema deberá** registrarlo activo y asociado a ese tipo. | RF 1.3.1, RF 1.3.2 |
| SPEC-PRD-02 | No deseado | **Si** el tipo de producto indicado no existe, **entonces el sistema deberá** rechazar la creación del producto. | RF 1.3.2 |
| SPEC-PRD-03 | No deseado | **Si** el producto no tiene nombre, **entonces el sistema deberá** rechazar la creación. | RF 1.3.1 |
| SPEC-PRD-04 | Por evento | **Cuando** un administrador modifica el nombre o el tipo de un producto, **el sistema deberá** guardar los cambios. | RF 1.3.1, RF 1.3.2 |
| SPEC-PRD-05 | Por evento | **Cuando** un administrador da de baja un producto, **el sistema deberá** marcarlo como inactivo sin eliminarlo. | RF 1.3.1 |
| SPEC-PRD-06 | Ubicuo | **El sistema deberá** conservar la asociación de un producto inactivo con los tickets a los que ya estaba asociado. | RF 1.3.1, RNF 5 |
| SPEC-PRD-07 | Por evento | **Cuando** un usuario autenticado solicita el listado de productos, **el sistema deberá** devolver cada producto con su tipo, su categoría y su estado. | RF 1.3.3 |
| SPEC-PRD-08 | Por evento | **Cuando** un usuario autenticado filtra el listado por categoría o por tipo de producto, **el sistema deberá** devolver solo los productos que coinciden. | RF 1.3.3, Diagrama de clases (`getProductsByCategory`) |
| SPEC-PRD-09 | No deseado | **Si** un usuario sin rol `Admin` intenta crear, modificar o dar de baja productos, **entonces el sistema deberá** denegar la operación. | RF 1.1.5, RNF 2 |
| SPEC-PRD-10 | Por evento | **Cuando** un representante solicita los productos disponibles para asociar a un ticket, **el sistema deberá** devolver solo los productos activos. | RF 1.3.1 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. La baja de productos es lógica (`is_active`). Un producto inactivo no se puede asociar a tickets nuevos (SPEC-TKT-08), pero sigue apareciendo en los existentes.
