# Secuencias — 03 Productos

Spec: [specs/03-products/spec.md](../../specs/03-products/spec.md)

En todos los flujos de escritura, si `current_user` no es `Admin`, el controller responde 403 (SPEC-PRD-09).

## 1. Alta y modificación de producto

Specs: SPEC-PRD-01, 02, 03, 04, 09

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant PS as ProductService
    participant TR as ProductTypeRepository
    participant PR as ProductRepository

    Admin->>PC: POST /products (name, product_type_id)
    alt current_user no es Admin
        PC-->>Admin: 403 Forbidden (SPEC-PRD-09)
    else current_user es Admin
        PC->>PS: create_product(name, product_type_id)
        alt el nombre está vacío
            PS-->>PC: raise ValidationError
            PC-->>Admin: 400 Bad Request (SPEC-PRD-03)
        else nombre válido
            PS->>TR: get(product_type_id)
            TR-->>PS: ProductType o None
            alt el tipo no existe
                PS-->>PC: raise ProductTypeNotFoundError
                PC-->>Admin: 404 Not Found (SPEC-PRD-02)
            else el tipo existe
                PS->>PR: add(Product(name, product_type, is_active=True)) y commit()
                PC-->>Admin: 201 Created (SPEC-PRD-01)
            end
        end
    end

    Note over Admin,PR: La modificación (nombre o tipo) aplica las mismas validaciones (SPEC-PRD-04)
```

## 2. Baja lógica de producto

Specs: SPEC-PRD-05, 06

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant PS as ProductService
    participant PR as ProductRepository

    Admin->>PC: POST /products/{id}/deactivate
    PC->>PS: deactivate_product(product_id)
    PS->>PR: get(product_id)
    PR-->>PS: product
    PS->>PS: product.deactivate() → is_active = False (SPEC-PRD-05)
    PS->>PR: commit()
    Note over PR: No se borra la fila ni la asociación ticket_products:<br/>los tickets existentes lo siguen mostrando (SPEC-PRD-06)
    PC-->>Admin: 200 OK
```

## 3. Listados de productos

Specs: SPEC-PRD-07, 08, 10

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario autenticado
    participant PC as CatalogController
    participant PS as ProductService
    participant PR as ProductRepository

    alt listado del catálogo
        U->>PC: GET /products (filtros opcionales: category_id, product_type_id)
        PC->>PS: list_products(filters)
        PS->>PR: list(filters) con selectinload(product_type, category)
        PR-->>PS: productos con tipo, categoría y estado (SPEC-PRD-07, 08)
    else productos para asociar a un ticket (Representante)
        U->>PC: GET /products/available
        PC->>PS: list_available_products()
        PS->>PR: list(is_active=True)
        PR-->>PS: solo productos activos (SPEC-PRD-10)
    end
    PC-->>U: 200 OK
```
