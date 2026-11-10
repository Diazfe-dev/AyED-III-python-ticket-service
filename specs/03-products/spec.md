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
| SPEC-PRD-10 | Por evento | **Cuando** un usuario autenticado solicita los productos disponibles para asociar a un ticket, **el sistema deberá** devolver solo los productos activos. | RF 1.3.1 |
| SPEC-PRD-11 | No deseado | **Si** el alta o la modificación de un producto tiene un nombre vacío o que no es texto, **entonces el sistema deberá** rechazarla e indicar que el nombre es inválido. | RF 1.3.1 |
| SPEC-PRD-12 | No deseado | **Si** la modificación de un producto indica un tipo de producto inexistente, **entonces el sistema deberá** rechazarla. | RF 1.3.2 |
| SPEC-PRD-13 | No deseado | **Si** ya existe un producto con el mismo nombre en el mismo tipo de producto (sin distinguir mayúsculas), **entonces el sistema deberá** rechazar el alta o la modificación. | RF 1.3.1 |
| SPEC-PRD-14 | Ubicuo | **El sistema deberá** guardar los nombres de los productos sin espacios al inicio ni al final. | RF 1.3.1 |
| SPEC-PRD-15 | No deseado | **Si** el identificador de tipo de producto de un alta o de una modificación, o el de categoría o tipo usado como filtro del listado, no es un entero positivo, **entonces el sistema deberá** rechazar la solicitud e indicar qué campo es inválido (`400`). | RF 1.3.2, RF 1.3.3 |
| SPEC-PRD-16 | No deseado | **Si** el listado se filtra por una categoría o un tipo de producto inexistente, **entonces el sistema deberá** responder que no existe (`404`). | RF 1.3.3 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. La baja de productos es lógica (`is_active`). Un producto inactivo no se puede asociar a tickets nuevos (SPEC-TKT-08), pero sigue apareciendo en los existentes.

Aprobadas el 2026-11-10 (revisión transversal de huecos, mismo criterio que `02-product-types`):

2. Se agregan SPEC-PRD-11 a 16: validación del nombre en alta y modificación, tipo inexistente en la modificación, unicidad por tipo sin distinguir mayúsculas, nombres sin espacios en los extremos, identificadores mal formados → `400` y filtro por categoría o tipo inexistente → `404`.
3. SPEC-PRD-10 aplica a cualquier usuario autenticado: SPEC-PRD-07 ya permite listar todos los productos, así que restringir los disponibles al representante no protegía nada.
4. SPEC-PTY-08 (no borrar un tipo con productos) se implementa en esta área, porque recién acá existe `Product`.
5. SPEC-PRD-06 depende de `04-tickets`: se verifica lo posible y el caso completo queda pendiente para esa área.
