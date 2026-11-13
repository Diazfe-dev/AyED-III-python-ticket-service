# 03 — Gestión de productos

Origen: RF 1.3 · Relacionados: RNF 10 · Diagramas: [secuencias](../../diagrams/sequences/03-products.md), [clases](../../diagrams/classes.md)

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
| SPEC-PRD-17 | No deseado | **Si** se intenta modificar o dar de baja un producto inexistente, incluido un identificador fuera del rango que admite la base, **entonces el sistema deberá** responder que el producto no existe (`404`). | RF 1.3.1 |
| SPEC-PRD-18 | Por evento | **Cuando** un administrador da de baja un producto que ya está inactivo, **el sistema deberá** responder con éxito sin modificarlo. | RF 1.3.1 |
| SPEC-PRD-19 | Complejo | **Mientras** un producto está inactivo, **cuando** un administrador modifica su nombre o su tipo, **el sistema deberá** guardar los cambios y mantenerlo inactivo. | RF 1.3.1 |
| SPEC-PRD-20 | Por evento | **Cuando** el listado se filtra a la vez por una categoría y por un tipo de producto que no pertenece a esa categoría, **el sistema deberá** devolver una lista vacía. | RF 1.3.3 |
| SPEC-PRD-21 | Ubicuo | **El sistema deberá** devolver los listados de productos ordenados alfabéticamente por nombre. | RF 1.3.3 |

## Reactivación, búsqueda y paginación

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PRD-22 | Por evento | **Cuando** un administrador reactiva un producto inactivo (`POST /products/{id}/activate`), **el sistema deberá** marcarlo como activo, de modo que pueda asociarse a tickets nuevos. | RF 1.3.4 |
| SPEC-PRD-23 | Por evento | **Cuando** un administrador reactiva un producto que ya está activo, **el sistema deberá** responder con éxito sin modificarlo. | RF 1.3.4 |
| SPEC-PRD-24 | No deseado | **Si** se intenta reactivar un producto inexistente, incluido un identificador fuera del rango que admite la base, **entonces el sistema deberá** responder que el producto no existe (`404`). | RF 1.3.4 |
| SPEC-PRD-25 | No deseado | **Si** un usuario sin rol `Admin` intenta reactivar un producto, **entonces el sistema deberá** denegar la operación (`403`). | RF 1.1.5, RNF 2 |
| SPEC-PRD-26 | Por evento | **Cuando** un usuario autenticado envía `q` en el listado de productos o en el de productos disponibles, **el sistema deberá** devolver solo los productos cuyo nombre contiene ese texto, sin distinguir mayúsculas. | RF 1.3.5 |
| SPEC-PRD-27 | Por evento | **Cuando** un usuario autenticado envía `is_active` (`true` o `false`) en el listado de productos, **el sistema deberá** devolver solo los productos con ese estado. | RF 1.3.5 |
| SPEC-PRD-28 | No deseado | **Si** `is_active` no es `true` ni `false`, **entonces el sistema deberá** rechazar el listado con `400` y el código `validation_error`, indicando ese parámetro como inválido. | RF 1.3.5 |
| SPEC-PRD-29 | Opcional | **Donde** se solicita el listado de productos o el de productos disponibles con `page` o `page_size`, **el sistema deberá** paginarlo según SPEC-PLT-17 a SPEC-PLT-22. | RNF 10 |
| SPEC-PRD-30 | Ubicuo | **El sistema deberá** ignorar en `GET /products/available` todo parámetro de consulta que no sea `q`, `page` ni `page_size`, sin rechazarlo. | RF 1.3.5 |

## Decisiones

Resueltas el 2026-11-09 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación):

1. La baja de productos es lógica (`is_active`). Un producto inactivo no se puede asociar a tickets nuevos (SPEC-TKT-08), pero sigue apareciendo en los existentes.

Aprobadas el 2026-11-10 (revisión transversal de huecos, mismo criterio que `02-product-types`):

2. Se agregan SPEC-PRD-11 a 16: validación del nombre en alta y modificación, tipo inexistente en la modificación, unicidad por tipo sin distinguir mayúsculas, nombres sin espacios en los extremos, identificadores mal formados → `400` y filtro por categoría o tipo inexistente → `404`.
3. SPEC-PRD-10 aplica a cualquier usuario autenticado: SPEC-PRD-07 ya permite listar todos los productos, así que restringir los disponibles al representante no protegía nada.
4. SPEC-PTY-08 (no borrar un tipo con productos) se implementa en esta área, porque recién acá existe `Product`.
5. SPEC-PRD-06 depende de `04-tickets`: se verifica lo posible y el caso completo queda pendiente para esa área.
6. Al aprobar el plan (2026-11-10): producto inexistente o id fuera de rango → `404` (SPEC-PRD-17), la baja de un producto inactivo es idempotente (SPEC-PRD-18), un producto inactivo se puede modificar y sigue inactivo (SPEC-PRD-19), filtros incompatibles → lista vacía (SPEC-PRD-20) y orden alfabético (SPEC-PRD-21). La reactivación de productos o usuarios queda fuera: ningún RF la pide.

Aprobadas el 2026-11-12 (nueva área [07-ui](../07-ui/spec.md)):

7. **Reactivación (SPEC-PRD-22 a 25)**: levanta la exclusión de la decisión 6. Es idempotente y `Admin` únicamente, con el mismo criterio que SPEC-PRD-18 y SPEC-PRD-09; SPEC-PRD-09 no se edita porque no menciona la reactivación.
8. **Filtros del listado (SPEC-PRD-26 a 29)**: `q` (texto contenido en el nombre) rige para `GET /products` y `GET /products/available` (para el selector de productos del ticket). `is_active` solo rige para `GET /products`: los disponibles son siempre activos (SPEC-PRD-10). Se combinan con `category_id` y `product_type_id` (SPEC-PRD-08 y 20) con AND. El orden alfabético de SPEC-PRD-21 se mantiene y es el orden de la paginación.

Aprobadas el 2026-11-12 (validación de requerimientos de [07-ui](../07-ui/spec.md)):

9. **Parámetros no admitidos en los disponibles (SPEC-PRD-30)**: `GET /products/available` solo admite `q`, `page` y `page_size`; cualquier otro (por ejemplo `is_active`, `category_id`) se ignora, como hoy. No es un error, porque los disponibles son siempre activos (SPEC-PRD-10).
10. **`q` vacío**: en SPEC-PRD-26, un `q` vacío o con solo espacios equivale a no enviar `q` (SPEC-PLT-27).
