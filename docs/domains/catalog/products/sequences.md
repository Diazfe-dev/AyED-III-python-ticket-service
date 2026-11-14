# Secuencias — 03 Productos

Spec: [specs/03-products/spec.md](../../specs/03-products/spec.md)

`POST /products` usa `login_required` y pasa `actor` al service: un `Admin` o un `Representative` lo ejecutan y un `Client` recibe 403 después del 400 de formato y antes del 404 y del 409 (SPEC-PRD-35, 37). `PATCH`, la baja y la reactivación usan `admin_required`: todo no-`Admin` recibe 403 antes de buscar el producto y de leer el cuerpo (SPEC-PRD-36, 37). Sin sesión, todas las rutas responden 401. El controller arma el service con `get_product_service()` de `app/wiring.py` y traduce cada `DomainError` con `ERROR_RESPONSES`.

## 1. Alta y modificación de producto

Specs: SPEC-PRD-01, 02, 03, 04, 11, 12, 13, 14, 17, 19, 33, 35, 36, 37

```mermaid
sequenceDiagram
    autonumber
    actor U as Admin, Representative o Client
    participant PC as CatalogController
    participant PS as ProductService
    participant TR as ProductTypeRepository
    participant PR as ProductRepository

    U->>PC: POST /products (name, product_type_id)
    alt sin sesión
        PC-->>U: 401 authentication_required
    else con sesión (login_required)
        PC->>PS: create_product(name, product_type_id, actor=current_user)
        alt nombre o product_type_id inválidos, se informan juntos
            PS-->>PC: raise ValidationError(fields)
            PC-->>U: 400 validation_error, antes del 403 (SPEC-PRD-03, 11, 33, 35, 37)
        else campos válidos
            alt actor.role no está en PRODUCT_CREATORS (Client)
                PS-->>PC: raise PermissionDeniedError
                PC-->>U: 403 forbidden, antes de buscar el tipo (SPEC-PRD-37)
            else Admin o Representative
                PS->>TR: get(product_type_id)
                TR-->>PS: ProductType o None
                alt el tipo no existe o el id no entra en INTEGER
                    PS-->>PC: raise ProductTypeNotFoundError
                    PC-->>U: 404 product_type_not_found (SPEC-PRD-02)
                else el tipo existe
                    PS->>PR: find_by_name_in_type(name, product_type_id)
                    alt el nombre ya existe en el tipo, sin distinguir mayúsculas
                        PS-->>PC: raise DuplicateProductError
                        PC-->>U: 409 duplicate_product (SPEC-PRD-13)
                    else nombre libre
                        PS->>PR: add(Product(name, product_type, is_active=True)) con flush
                        Note over PR: el nombre se guarda recortado (SPEC-PRD-14)<br/>y el UNIQUE (product_type_id, name_key) traduce una carrera a DuplicateProductError
                        PS->>PS: commit()
                        PC-->>U: 201 Product (SPEC-PRD-01, 35)
                    end
                end
            end
        end
    end

    Admin->>PC: PATCH /products/{id} (name y product_type_id opcionales)
    alt current_user no es Admin (admin_required)
        PC-->>Admin: 403 forbidden, antes del 404 y del 400 (SPEC-PRD-36, 37)
    end
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

Specs: SPEC-PRD-05, 06, 17, 18, 36, 37

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant PS as ProductService
    participant PR as ProductRepository

    Admin->>PC: POST /products/{id}/deactivate
    alt current_user no es Admin (admin_required)
        PC-->>Admin: 403 forbidden, antes del 404 (SPEC-PRD-36, 37)
    end
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

## 3. Reactivación de producto

Specs: SPEC-PRD-22, 23, 24, 25

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant PS as ProductService
    participant PR as ProductRepository

    Admin->>PC: POST /products/{id}/activate
    alt current_user no es Admin
        PC-->>Admin: 403 forbidden (SPEC-PRD-25)
    else current_user es Admin
        PC->>PS: activate_product(product_id)
        PS->>PR: get(product_id)
        alt no existe o el id no entra en INTEGER
            PS-->>PC: raise ProductNotFoundError
            PC-->>Admin: 404 product_not_found (SPEC-PRD-24)
        else existe
            PS->>PS: product.activate() pone is_active en True (SPEC-PRD-22)
            Note over PS: si ya estaba activo queda igual, la reactivación es idempotente (SPEC-PRD-23)
            PS->>PS: commit()
            PC-->>Admin: 200 Product con is_active true
        end
    end
```

## 4. Listados de productos

Specs: SPEC-PRD-10, 21, 26, 27, 28, 29, 30, 31, 32, 33, 34

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario autenticado
    participant PC as CatalogController
    participant PS as ProductService
    participant TR as ProductTypeRepository
    participant PR as ProductRepository

    alt listado del catálogo
        U->>PC: GET /products (product_type_id, q, is_active, page y page_size opcionales)
        PC->>PS: list_products(product_type_id, q, is_active, page, page_size)
        alt el product_type_id no es un entero positivo, is_active no es true ni false o la paginación es inválida, se informan juntos
            PS-->>PC: raise ValidationError(fields)
            PC-->>U: 400 validation_error (SPEC-PRD-28, 33)
        else filtros válidos
            opt con product_type_id
                PS->>TR: get(product_type_id)
                Note over PS: si no existe lanza ProductTypeNotFoundError y responde 404 (SPEC-PRD-34)
            end
            PS->>PR: list_matching(product_type_id, is_active, q, window)
            Note over PS: q se normaliza con search_text: vacío o solo espacios equivale a no enviarlo<br/>y window es None si no llegó page ni page_size
            Note over PR: filtra por product_type_id, is_active exacto y q como subcadena literal de name_key (SPEC-PRD-26, 27),<br/>orden por name_key e id (SPEC-PRD-21) y selectinload del tipo (WITH_TYPE), 2 consultas como máximo
            PR-->>PS: lista, o Page con total si hay window, de productos que cumplen todos los filtros (SPEC-PRD-31, 32, 29)
            PC-->>U: 200 lista de Product con su tipo {id, name}, o Page con items, page, page_size y total (SPEC-PRD-31)
        end
    else productos para asociar a un ticket
        U->>PC: GET /products/available (q, page y page_size opcionales)
        Note over PC: _listing_args toma solo q, page y page_size: cualquier otro parámetro se ignora (SPEC-PRD-30)
        PC->>PS: list_available_products(q, page, page_size)
        opt la paginación es inválida
            PS-->>PC: raise ValidationError(fields)
            PC-->>U: 400 validation_error (SPEC-PLT-17 a 22)
        end
        PS->>PR: list_matching(is_active=True, q, window)
        PR-->>PS: solo productos activos que contienen q, ordenados por nombre (SPEC-PRD-10, 21, 26, 29)
        PC-->>U: 200 lista de Product, o Page
    end
```
