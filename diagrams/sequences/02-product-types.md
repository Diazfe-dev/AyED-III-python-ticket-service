# Secuencias — 02 Tipos de producto y rubros

Spec: [specs/02-product-types/spec.md](../../specs/02-product-types/spec.md)

En todos los flujos de escritura, si `current_user` no es `Admin`, el controller responde 403 (SPEC-PTY-11). Para no repetirlo, solo se muestra en el primer diagrama.

## 1. Alta y modificación de categoría

Specs: SPEC-PTY-01, 02, 11, 12

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant CS as CatalogService
    participant CR as CategoryRepository

    Admin->>PC: POST /categories (name)
    alt current_user no es Admin
        PC-->>Admin: 403 Forbidden (SPEC-PTY-11)
    else current_user es Admin
        PC->>CS: create_category(name)
        CS->>CR: find_by_name(name) sin distinguir mayúsculas
        CR-->>CS: Category o None
        alt ya existe
            CS-->>PC: raise DuplicateCategoryError
            PC-->>Admin: 409 Conflict (SPEC-PTY-02)
        else no existe
            CS->>CR: add(Category(name)) y commit()
            PC-->>Admin: 201 Created (SPEC-PTY-01)
        end
    end

    Note over Admin,CR: La modificación (PUT /categories/{id}) sigue el mismo flujo:<br/>valida unicidad y guarda el nuevo nombre (SPEC-PTY-12)
```

## 2. Alta de tipo de producto

Specs: SPEC-PTY-03, 04, 05, 06

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant CS as CatalogService
    participant CR as CategoryRepository
    participant TR as ProductTypeRepository

    Admin->>PC: POST /product-types (name, category_id)
    PC->>CS: create_product_type(name, category_id)
    CS->>CR: get(category_id)
    CR-->>CS: Category o None
    alt la categoría no existe
        CS-->>PC: raise CategoryNotFoundError
        PC-->>Admin: 404 Not Found (SPEC-PTY-04)
    else la categoría existe
        CS->>TR: find_by_name_in_category(name, category_id)
        TR-->>CS: ProductType o None
        alt ya existe en esa categoría
            CS-->>PC: raise DuplicateProductTypeError
            PC-->>Admin: 409 Conflict (SPEC-PTY-05)
        else no existe
            CS->>TR: add(ProductType(name, category)) y commit()
            PC-->>Admin: 201 Created (SPEC-PTY-03)
        end
    end

    Note over Admin,TR: La modificación (nombre o categoría) aplica las mismas validaciones (SPEC-PTY-06)
```

## 3. Baja de categoría o de tipo de producto

Specs: SPEC-PTY-07, 08, 13, 14

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant CS as CatalogService
    participant R as Repository (Category / ProductType)

    Admin->>PC: DELETE /categories/{id} o /product-types/{id}
    PC->>CS: delete_category(id) o delete_product_type(id)
    CS->>R: count_children(id)
    Note over CS,R: Categoría → cuenta sus tipos de producto.<br/>Tipo → cuenta sus productos, activos o inactivos.
    R-->>CS: n
    alt n mayor que 0
        CS-->>PC: raise EntityInUseError
        PC-->>Admin: 409 Conflict con el motivo (SPEC-PTY-08, 14)
    else n igual a 0
        CS->>R: delete(entity) y commit()
        PC-->>Admin: 204 No Content (SPEC-PTY-07, 13)
    end
```

## 4. Listado de tipos por categoría

Specs: SPEC-PTY-09, 10

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario autenticado
    participant PC as CatalogController
    participant CS as CatalogService
    participant TR as ProductTypeRepository

    U->>PC: GET /product-types?category_id=opcional
    PC->>CS: list_product_types(category_id)
    alt con category_id
        CS->>TR: list_by_category(category_id)
        TR-->>CS: tipos de esa categoría (SPEC-PTY-10)
    else sin filtro
        CS->>TR: list_all() con selectinload(category)
        TR-->>CS: todos los tipos
        CS->>CS: agrupar por categoría (SPEC-PTY-09)
    end
    PC-->>U: 200 OK
```
