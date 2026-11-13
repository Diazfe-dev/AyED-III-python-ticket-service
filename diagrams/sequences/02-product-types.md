# Secuencias — 02 Tipos de producto y rubros

Spec: [specs/02-product-types/spec.md](../../specs/02-product-types/spec.md)

En todos los flujos de escritura, si `current_user` no es `Admin`, `admin_required` responde 403 (SPEC-PTY-11), y sin sesión `login_required` responde 401. Para no repetirlo, solo se muestra en el primer diagrama. El controller obtiene el service con `get_catalog_service()` (`app/wiring.py`), que lo arma con los repositorios y `commit = session.commit`. Las excepciones de dominio se traducen a HTTP con la tabla de `app/controllers/errors.py`.

## 1. Alta y modificación de categoría

Specs: SPEC-PTY-01, 02, 11, 12, 15, 19

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant CS as CatalogService
    participant CR as CategoryRepository

    Admin->>PC: POST /categories (name)
    alt current_user no es Admin
        PC-->>Admin: 403 forbidden (SPEC-PTY-11)
    else current_user es Admin
        PC->>CS: create_category(name)
        alt name ausente, vacío o que no es texto
            CS-->>PC: raise ValidationError
            PC-->>Admin: 400 validation_error con fields.name (SPEC-PTY-15)
        else name válido
            CS->>CR: find_by_name(name) por name_key
            CR-->>CS: Category o None
            alt ya existe sin distinguir mayúsculas
                CS-->>PC: raise DuplicateCategoryError
                PC-->>Admin: 409 duplicate_category (SPEC-PTY-02)
            else no existe
                CS->>CR: add(Category(name)) con flush
                Note over CS,CR: el dominio recorta el nombre y calcula name_key (SPEC-PTY-19)
                CS->>CS: commit()
                PC-->>Admin: 201 Category (SPEC-PTY-01)
            end
        end
    end

    Note over Admin,CR: PATCH /categories/{id} primero busca la categoría con get (404 category_not_found),<br/>después valida el nombre (400) y la unicidad ignorando a la propia categoría (409).<br/>Un name ausente o null no modifica nada (SPEC-PTY-12)
```

## 2. Alta y modificación de tipo de producto

Specs: SPEC-PTY-03, 04, 05, 06, 15, 16, 19, 20

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
    alt name o category_id inválidos
        CS-->>PC: raise ValidationError
        PC-->>Admin: 400 validation_error con fields.name y o fields.category_id (SPEC-PTY-15, 20)
    else campos válidos
        CS->>CR: get(parse_id(category_id))
        CR-->>CS: Category o None
        alt la categoría no existe
            CS-->>PC: raise CategoryNotFoundError
            PC-->>Admin: 404 category_not_found (SPEC-PTY-04)
        else la categoría existe
            CS->>TR: find_by_name_in_category(name, category.id)
            TR-->>CS: ProductType o None
            alt ya existe en esa categoría sin distinguir mayúsculas
                CS-->>PC: raise DuplicateProductTypeError
                PC-->>Admin: 409 duplicate_product_type (SPEC-PTY-05)
            else no existe
                CS->>TR: add(ProductType(name, category)) con flush
                CS->>CS: commit()
                PC-->>Admin: 201 ProductType (SPEC-PTY-03)
            end
        end
    end

    Note over Admin,TR: PATCH /product-types/{id} busca el tipo (404 product_type_not_found), valida los campos presentes (400),<br/>busca la categoría de destino si viene category_id (404 category_not_found) y verifica el nombre final<br/>en la categoría de destino (409). Recién entonces asigna y hace commit (SPEC-PTY-06, 16)
```

## 3. Baja de categoría o de tipo de producto

Specs: SPEC-PTY-07, 08, 13, 14 (SPEC-PTY-08 se implementó en `03-products`)

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant PC as CatalogController
    participant CS as CatalogService
    participant CR as CategoryRepository
    participant TR as ProductTypeRepository

    Admin->>PC: DELETE /categories/{id}
    PC->>CS: delete_category(id)
    CS->>CR: get(id)
    alt no existe
        CS-->>PC: raise CategoryNotFoundError
        PC-->>Admin: 404 category_not_found
    else existe
        CS->>CR: has_product_types(id) con una consulta exists
        alt tiene tipos
            CS-->>PC: raise CategoryInUseError
            PC-->>Admin: 409 category_in_use con el motivo (SPEC-PTY-14)
        else no tiene tipos
            CS->>CR: delete(category) con flush
            Note over CR: la FK ON DELETE RESTRICT rechaza la baja si apareció un tipo<br/>y el repositorio traduce el IntegrityError a CategoryInUseError
            CS->>CS: commit()
            PC-->>Admin: 204 No Content (SPEC-PTY-13)
        end
    end

    Admin->>PC: DELETE /product-types/{id}
    PC->>CS: delete_product_type(id)
    CS->>TR: get(id)
    alt no existe
        CS-->>PC: raise ProductTypeNotFoundError
        PC-->>Admin: 404 product_type_not_found
    else existe
        CS->>TR: has_products(id) con una consulta exists, activos e inactivos
        alt tiene productos
            CS-->>PC: raise ProductTypeInUseError
            PC-->>Admin: 409 product_type_in_use con el motivo (SPEC-PTY-08)
        else no tiene productos
            CS->>TR: delete(product_type) con flush
            Note over TR: la FK ON DELETE RESTRICT de products rechaza la baja si apareció un producto<br/>y el repositorio traduce el IntegrityError a ProductTypeInUseError
            CS->>CS: commit()
            PC-->>Admin: 204 No Content (SPEC-PTY-07)
        end
    end
```

## 4. Listados de categorías y de tipos por categoría, con búsqueda `q`

Specs: SPEC-PTY-10, 17, 18, 20, 21, 22, 23, 24 (SPEC-PTY-09 la reemplaza SPEC-PTY-22)

Ninguno de los dos listados se pagina: `page` y `page_size` se ignoran (SPEC-PTY-24). `search_text(q)` devuelve `None` si `q` falta o es solo espacios, y entonces el listado se comporta como sin `q`.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario autenticado
    participant PC as CatalogController
    participant CS as CatalogService
    participant CR as CategoryRepository
    participant TR as ProductTypeRepository

    U->>PC: GET /categories con q opcional
    PC->>CS: list_categories(q)
    CS->>CR: list_all(search_text(q))
    Note over CR: con q filtra por name_key que contiene q.casefold(),<br/>sin q devuelve todas; ordena por name_key e id
    CR-->>CS: categorías
    PC-->>U: 200 lista de Category (SPEC-PTY-17, 21)

    U->>PC: GET /product-types con category_id y q opcionales
    PC->>CS: list_product_types(category_id, q)
    alt category_id que no es un entero positivo
        CS-->>PC: raise ValidationError
        PC-->>U: 400 validation_error con fields.category_id (SPEC-PTY-20)
    else category_id ausente o válido
        opt category_id presente
            CS->>CR: get(parse_id(category_id))
            alt la categoría no existe
                CS-->>PC: raise CategoryNotFoundError
                PC-->>U: 404 category_not_found (SPEC-PTY-18)
            end
        end
        alt q presente
            CS->>TR: search(q, category_id)
            Note over TR: join con la categoría, filtra por name_key y ordena por categoría y tipo;<br/>CS agrupa con _group y omite las categorías sin coincidencias
            TR-->>CS: tipos coincidentes
            PC-->>U: 200 lista de CategoryGroup con coincidencias (SPEC-PTY-23)
        else sin q y sin category_id
            CS->>CR: list_with_product_types()
            Note over CR: select de categories con selectinload de product_types:<br/>2 consultas, incluye las categorías sin tipos
            CR-->>CS: categorías con sus tipos ordenados por nombre
            PC-->>U: 200 lista de CategoryGroup (SPEC-PTY-22)
        else sin q y con category_id
            PC-->>U: 200 lista con un solo grupo (SPEC-PTY-10)
        end
    end
```
