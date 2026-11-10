# Secuencias — 03 Productos

Spec: [specs/03-products/spec.md](../../specs/03-products/spec.md)

En todos los flujos de escritura, si `current_user` no es `Admin`, `admin_required` responde 403 antes de llegar al controller (SPEC-PRD-09). Sin sesión, todas las rutas responden 401. El controller arma el service con `get_product_service()` de `app/wiring.py` y traduce cada `DomainError` con `ERROR_RESPONSES`.

## 1. Alta y modificación de producto

Specs: SPEC-PRD-01, 02, 03, 04, 09, 11, 12, 13, 14, 15, 17, 19

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
        PC-->>Admin: 403 forbidden (SPEC-PRD-09)
    else current_user es Admin
        PC->>PS: create_product(name, product_type_id)
        alt nombre o product_type_id inválidos, se informan juntos
            PS-->>PC: raise ValidationError(fields)
            PC-->>Admin: 400 validation_error (SPEC-PRD-03, 11, 15)
        else campos válidos
            PS->>TR: get(product_type_id)
            TR-->>PS: ProductType o None
            alt el tipo no existe o el id no entra en INTEGER
                PS-->>PC: raise ProductTypeNotFoundError
                PC-->>Admin: 404 product_type_not_found (SPEC-PRD-02)
            else el tipo existe
                PS->>PR: find_by_name_in_type(name, product_type_id)
                alt el nombre ya existe en el tipo, sin distinguir mayúsculas
                    PS-->>PC: raise DuplicateProductError
                    PC-->>Admin: 409 duplicate_product (SPEC-PRD-13)
                else nombre libre
                    PS->>PR: add(Product(name, product_type, is_active=True)) con flush
                    Note over PR: el nombre se guarda recortado (SPEC-PRD-14)<br/>y el UNIQUE (product_type_id, name_key) traduce una carrera a DuplicateProductError
                    PS->>PS: commit()
                    PC-->>Admin: 201 Product (SPEC-PRD-01)
                end
            end
        end
    end

    Admin->>PC: PATCH /products/{id} (name y product_type_id opcionales)
    PC->>PS: update_product(id, name, product_type_id)
    PS->>PR: get(id)
    alt no existe o el id no entra en INTEGER
        PS-->>PC: raise ProductNotFoundError
        PC-->>Admin: 404 product_not_found (SPEC-PRD-17)
    else existe
        Note over PS: valida los campos presentes (400), el tipo de destino (404)<br/>y el duplicado con el nombre y el tipo finales (409), todo antes de asignar
        PS->>PS: asigna nombre y tipo, is_active no cambia (SPEC-PRD-19)
        PS->>PS: commit()
        PC-->>Admin: 200 Product (SPEC-PRD-04)
    end
```

## 2. Baja lógica de producto

Specs: SPEC-PRD-05, 06, 09, 17, 18

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
    alt no existe o el id no entra en INTEGER
        PS-->>PC: raise ProductNotFoundError
        PC-->>Admin: 404 product_not_found (SPEC-PRD-17)
    else existe
        PS->>PS: product.deactivate() pone is_active en False (SPEC-PRD-05)
        Note over PS: si ya estaba inactivo queda igual, la baja es idempotente (SPEC-PRD-18)
        PS->>PS: commit()
        Note over PR: no se borra la fila y el repositorio no tiene métodos de borrado.<br/>Los tickets existentes lo siguen mostrando (SPEC-PRD-06, completa en 04-tickets)
        PC-->>Admin: 200 Product con is_active false
    end
```

## 3. Listados de productos

Specs: SPEC-PRD-07, 08, 10, 15, 16, 20, 21

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario autenticado
    participant PC as CatalogController
    participant PS as ProductService
    participant CR as CategoryRepository
    participant TR as ProductTypeRepository
    participant PR as ProductRepository

    alt listado del catálogo
        U->>PC: GET /products (category_id y product_type_id opcionales)
        PC->>PS: list_products(category_id, product_type_id)
        alt algún filtro no es un entero positivo, se informan juntos
            PS-->>PC: raise ValidationError(fields)
            PC-->>U: 400 validation_error (SPEC-PRD-15)
        else filtros válidos
            opt con category_id
                PS->>CR: get(category_id)
                Note over PS: si no existe lanza CategoryNotFoundError y responde 404 (SPEC-PRD-16)
            end
            opt con product_type_id
                PS->>TR: get(product_type_id)
                Note over PS: si no existe lanza ProductTypeNotFoundError y responde 404 (SPEC-PRD-16)
            end
            PS->>PR: list_matching(category_id, product_type_id)
            Note over PR: join con el tipo para la categoría, orden por name_key e id (SPEC-PRD-21)<br/>y selectinload de tipo y categoría, 3 consultas como máximo
            PR-->>PS: productos activos e inactivos que cumplen todos los filtros (SPEC-PRD-07, 08)
            Note over PS: un tipo que no pertenece a la categoría da una lista vacía (SPEC-PRD-20)
            PC-->>U: 200 lista de Product
        end
    else productos para asociar a un ticket
        U->>PC: GET /products/available
        PC->>PS: list_available_products()
        PS->>PR: list_matching(active_only=True)
        PR-->>PS: solo productos activos, ordenados por nombre (SPEC-PRD-10, 21)
        PC-->>U: 200 lista de Product
    end
```
