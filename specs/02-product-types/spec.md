# 02 — Gestión de tipos de producto y rubros

Origen: RF 1.2 (RF 1.2.4 para la búsqueda) · Diagramas: [secuencias](../../diagrams/sequences/02-product-types.md), [clases](../../diagrams/classes.md)

Jerarquía de clasificación: `Category` (rubro) → `ProductType` → `Product`.

## Categorías (rubros)

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PTY-01 | Por evento | **Cuando** un administrador crea una categoría con un nombre, **el sistema deberá** registrarla. | RF 1.2.3, Seq. tipos §1 |
| SPEC-PTY-02 | No deseado | **Si** ya existe una categoría con el mismo nombre (sin distinguir mayúsculas), **entonces el sistema deberá** rechazar la creación o la modificación. | RF 1.2.3 |
| SPEC-PTY-12 | Por evento | **Cuando** un administrador modifica el nombre de una categoría, **el sistema deberá** guardar el cambio. | RF 1.2.3 |
| SPEC-PTY-13 | Por evento | **Cuando** un administrador da de baja una categoría sin tipos de producto asociados, **el sistema deberá** eliminarla. | RF 1.2.3 |
| SPEC-PTY-14 | No deseado | **Si** un administrador intenta dar de baja una categoría que tiene tipos de producto asociados, **entonces el sistema deberá** rechazar la baja e informar el motivo. | RF 1.2.3 |
| SPEC-PTY-15 | No deseado | **Si** el alta o la modificación de una categoría o de un tipo de producto tiene un nombre vacío o que no es texto, **entonces el sistema deberá** rechazarla e indicar que el nombre es inválido. | RF 1.2.1, RF 1.2.3 |
| SPEC-PTY-19 | Ubicuo | **El sistema deberá** guardar los nombres de categorías y tipos de producto sin espacios al inicio ni al final. | RF 1.2.1, RF 1.2.3 |
| SPEC-PTY-20 | No deseado | **Si** el identificador de categoría de un alta, de una modificación o de un listado de tipos no es un entero positivo, **entonces el sistema deberá** rechazar la solicitud e indicar que la categoría es inválida (`400`). | RF 1.2.1, RF 1.2.2 |

## Tipos de producto

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PTY-03 | Por evento | **Cuando** un administrador crea un tipo de producto con nombre y categoría, **el sistema deberá** registrarlo asociado a esa categoría. | RF 1.2.1 |
| SPEC-PTY-04 | No deseado | **Si** la categoría indicada no existe, **entonces el sistema deberá** rechazar la creación del tipo de producto. | RF 1.2.1 |
| SPEC-PTY-05 | No deseado | **Si** ya existe un tipo de producto con el mismo nombre en la misma categoría (sin distinguir mayúsculas), **entonces el sistema deberá** rechazar la creación. | RF 1.2.1 |
| SPEC-PTY-06 | Por evento | **Cuando** un administrador modifica el nombre o la categoría de un tipo de producto, **el sistema deberá** guardar los cambios. | RF 1.2.1 |
| SPEC-PTY-07 | Por evento | **Cuando** un administrador da de baja un tipo de producto sin productos asociados (activos o inactivos), **el sistema deberá** eliminarlo. | RF 1.2.1 |
| SPEC-PTY-08 | No deseado | **Si** un administrador intenta dar de baja un tipo de producto que tiene productos asociados, **entonces el sistema deberá** rechazar la baja e informar el motivo. | RF 1.2.1 |
| SPEC-PTY-16 | No deseado | **Si** la modificación de un tipo de producto indica una categoría inexistente o un nombre que ya existe en la categoría de destino (sin distinguir mayúsculas), **entonces el sistema deberá** rechazarla. | RF 1.2.1 |

## Listados y permisos

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PTY-09 | Por evento | **Reemplazada por SPEC-PTY-22.** **Cuando** un usuario autenticado solicita el listado de tipos de producto, **el sistema deberá** devolverlos agrupados por categoría, incluidas las categorías sin tipos. | RF 1.2.2 |
| SPEC-PTY-10 | Por evento | **Cuando** un usuario autenticado solicita los tipos de producto de una categoría, **el sistema deberá** devolver solo los de esa categoría. | RF 1.2.2 |
| SPEC-PTY-17 | Por evento | **Cuando** un usuario autenticado solicita el listado de categorías, **el sistema deberá** devolver todas las categorías ordenadas por nombre. | RF 1.2.3 |
| SPEC-PTY-18 | No deseado | **Si** se solicitan los tipos de producto de una categoría inexistente, **entonces el sistema deberá** responder que la categoría no existe (`404`). | RF 1.2.2 |
| SPEC-PTY-11 | No deseado | **Si** un usuario sin rol `Admin` intenta crear, modificar o dar de baja categorías o tipos de producto, **entonces el sistema deberá** denegar la operación. | RF 1.1.5, RNF 2 |

## Búsqueda por nombre

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PTY-21 | Por evento | **Cuando** un usuario autenticado envía `q` en el listado de categorías, **el sistema deberá** devolver solo las categorías cuyo nombre contiene ese texto, sin distinguir mayúsculas y ordenadas por nombre. | RF 1.2.4, RF 1.2.3 |
| SPEC-PTY-22 | Por evento | **Cuando** un usuario autenticado solicita el listado de tipos de producto sin `q`, **el sistema deberá** devolverlos agrupados por categoría, incluidas las categorías sin tipos. | RF 1.2.2 |
| SPEC-PTY-23 | Por evento | **Cuando** un usuario autenticado envía `q` en el listado de tipos de producto, con o sin filtro de categoría, **el sistema deberá** devolver solo los tipos cuyo nombre contiene ese texto, sin distinguir mayúsculas, agrupados por categoría y sin las categorías que no tienen coincidencias. | RF 1.2.4, RF 1.2.2 |

## Decisiones

Resueltas el 2026-11-09 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación):

1. Las categorías tienen ABM completo (RF 1.2.3). Su baja es física y se rechaza si tienen tipos asociados.

Resueltas el 2026-11-10, al planificar el área:

2. Se agregan SPEC-PTY-15 a 18 para cubrir huecos: validación del nombre, validaciones de la modificación de tipos, listado de categorías y categoría inexistente en el listado de tipos.
3. SPEC-PTY-07 y 08 dependen de `Product` (área `03-products`): en esta área se verifica lo posible y el caso completo queda pendiente para `03-products`, como TC-USR-10d. La clave foránea con `ON DELETE RESTRICT` funciona como red de seguridad en la base.
4. Al aprobar el plan (2026-11-10): los nombres de tipo tampoco distinguen mayúsculas (PTY-05 y 16), el listado agrupado incluye categorías vacías (PTY-09), los nombres se guardan sin espacios en los extremos (PTY-19) y un `category_id` mal formado es un error de validación `400`, no un `404` (PTY-20). Las specs editadas todavía no estaban implementadas.

Aprobadas el 2026-11-12 (nueva área [07-ui](../07-ui/spec.md)):

5. **Búsqueda `q` en categorías y tipos (SPEC-PTY-21 y 23)**: coincidencia por texto contenido en el nombre, sin distinguir mayúsculas. Son listados cortos, así que **no** se paginan (la convención de [00-platform](../00-platform/spec.md#paginación-opcional-de-listados) no aplica y `page` y `page_size` se ignoran). SPEC-PTY-09 se reemplaza por SPEC-PTY-22 (mismo comportamiento, ahora acotado a "sin `q`") porque con `q` las categorías sin coincidencias se omiten (SPEC-PTY-23). Sin `q`, ambos listados se comportan como hasta ahora.
