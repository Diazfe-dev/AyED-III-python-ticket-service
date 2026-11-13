# 02 — Tipos de producto y rubros · Test plan

Cada test cita en su docstring la spec y el caso: `"""SPEC-PTY-05 · TC-PTY-05a"""`.

Fixtures existentes (`tests/conftest.py`): `app`, `client`, `runner`, `schema`, `db_session`, `make_user`, `login_as`, `admin` y `admin_client` (ver [00-platform](../00-platform/test-plan.md) y [01-users](../01-users/test-plan.md)).

Fixtures nuevas (`tests/conftest.py`):
- `make_category`: fábrica `make_category(name=...)` que persiste una `Category` con `db_session` y hace commit. Sin nombre, genera uno único (`"Category 1"`, `"Category 2"`, …).
- `make_product_type`: fábrica `make_product_type(category, name=...)` que persiste un `ProductType` de esa categoría y hace commit. Sin nombre, genera uno único.

Dobles para tests unitarios (sin Flask ni base):
- `tests/unit/fakes.py`: `CommitSpy`, movido desde `tests/unit/users/fakes.py` en T-PTY-01 y compartido por usuarios y catálogo.
- `tests/unit/catalog/fakes.py`:
  - `FakeCategoryRepository`: diccionario en memoria que asigna ids, busca por `name_key`, lista por `(name_key, id)`, responde `has_product_types` con `bool(category.product_types)` y borra del diccionario.
  - `FakeProductTypeRepository`: diccionario en memoria que asigna ids, busca por `(category.id, name_key)` y borra del diccionario (al borrar, quita el tipo de `category.product_types`).

Las colecciones `Category.product_types` se mantienen solas en objetos transitorios gracias a `back_populates`, así que los fakes no necesitan conocerse entre sí.

Para los tests que verifican "sin cambios", se relee la fila con `db_session.expire_all()` después del request, igual que en `01-users`.

Re-sincronización del 2026-11-12: SPEC-PTY-09 está reemplazada por SPEC-PTY-22; sus casos se re-trazan como TC-PTY-22a a 22d (T-PTY-34) sin cambiar datos ni resultados. Casos nuevos para SPEC-PTY-21, 22 (`q` vacío), 23 y 24 en la sección [Búsqueda por nombre](#búsqueda-por-nombre-re-sincronización-del-2026-11-12).

## Matriz spec → casos

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| PTY-01 | TC-PTY-01a | unit | `create_category("Hardware")` con fakes | Devuelve una `Category` con `name == "Hardware"`, guardada en el repositorio, y `commit` se llamó una vez | `tests/unit/catalog/test_catalog_service.py` |
| PTY-01 | TC-PTY-01b | integration | `add(Category(name="Hardware"))`, commit y `get(id)` en una sesión nueva | Devuelve la categoría con el mismo nombre | `tests/integration/catalog/test_category_repository.py` |
| PTY-01 | TC-PTY-01c | integration | `admin_client` hace `POST /categories` con `{"name": "Hardware"}` | `201` `{"id": <int>, "name": "Hardware"}` y la fila existe | `tests/integration/catalog/test_categories_api.py` |
| PTY-02 | TC-PTY-02a | unit | `normalize_name("  Hardware ")` y `normalize_name("ÁUDIO")` | `"hardware"` y `"áudio"` | `tests/unit/catalog/test_products.py` |
| PTY-02 | TC-PTY-02b | unit | `Category(name="  Hardware ")` | `name == "Hardware"` y `name_key == "hardware"` | `tests/unit/catalog/test_products.py` |
| PTY-02 | TC-PTY-02c | unit | Existe `"Hardware"`; `create_category(" HARDWARE ")` | Lanza `DuplicateCategoryError`; no se agrega nada y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-02 | TC-PTY-02d | unit | Existen `"Hardware"` y `"Redes"`; `update_category(redes.id, name="hardware")` | Lanza `DuplicateCategoryError`; `"Redes"` no cambia y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-02 | TC-PTY-02e | integration | Existe `"áudio"`; `add(Category(name="ÁUDIO"))` y `find_by_name("ÁUDIO")` | `add` lanza `DuplicateCategoryError` y `find_by_name` devuelve `"áudio"` (la base compara con `casefold`, no con el `lower()` ASCII de SQLite) | `tests/integration/catalog/test_category_repository.py` |
| PTY-02 | TC-PTY-02f | integration | Dos `add` con `"Audio"` y `"AUDIO"`, sin pasar por el service | El segundo lanza `DuplicateCategoryError` (no `IntegrityError`) | `tests/integration/catalog/test_category_repository.py` |
| PTY-02 | TC-PTY-02g | integration | Existe `"Hardware"`; `find_by_name(" hardware ")` y `find_by_name("Redes")` | Devuelve `"Hardware"` y `None` | `tests/integration/catalog/test_category_repository.py` |
| PTY-02 | TC-PTY-02h | integration | `POST /categories` con `"HARDWARE"` cuando existe `"Hardware"` | `409` `{"error": "duplicate_category"}` y sigue habiendo una sola categoría | `tests/integration/catalog/test_categories_api.py` |
| PTY-02 | TC-PTY-02i | integration | Existen A y B; `PATCH /categories/{B}` con el nombre de A en minúsculas | `409` `{"error": "duplicate_category"}` y B no cambia | `tests/integration/catalog/test_categories_api.py` |
| PTY-03 | TC-PTY-03a | unit | Existe `"Hardware"`; `create_product_type("Notebook", hardware.id)` | Devuelve un `ProductType` con esa categoría, guardado en el repositorio, y `commit` se llamó una vez | `tests/unit/catalog/test_catalog_service.py` |
| PTY-03 | TC-PTY-03b | unit | `ProductType(name=" Notebook ", category=hardware)` | `name == "Notebook"`, `name_key == "notebook"` y el tipo está en `hardware.product_types` | `tests/unit/catalog/test_products.py` |
| PTY-03 | TC-PTY-03c | integration | `add(ProductType(...))`, commit y `get(id)` en una sesión nueva | Devuelve el tipo con su `category_id` y `category.name` correctos | `tests/integration/catalog/test_product_type_repository.py` |
| PTY-03 | TC-PTY-03d | integration | `admin_client` hace `POST /product-types` con `{"name": "Notebook", "category_id": <hardware>}` | `201` `{"id": <int>, "name": "Notebook", "category_id": <hardware>}` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-04 | TC-PTY-04a | unit | `create_product_type("Notebook", 9999)` | Lanza `CategoryNotFoundError`; no se agrega nada y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-04 | TC-PTY-04b | unit | **Reemplazado por TC-PTY-20a, 20b y 20c** (SPEC-PTY-20, 2026-11-10): un `category_id` mal formado ya no es `CategoryNotFoundError` sino `ValidationError` | — | — |
| PTY-04 | TC-PTY-04c | integration | `POST /product-types` con `category_id: 9999` (el caso sin `category_id` pasó a TC-PTY-20f el 2026-11-10) | `404` `{"error": "category_not_found"}` y sin tipo creado | `tests/integration/catalog/test_product_types_api.py` |
| PTY-05 | TC-PTY-05a | unit | Existe `"Notebook"` en `"Hardware"`; `create_product_type("NOTEBOOK", hardware.id)` | Lanza `DuplicateProductTypeError`; no se agrega nada y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-05 | TC-PTY-05b | unit | Existe `"Notebook"` en `"Hardware"`; `create_product_type("Notebook", oficina.id)` | Se crea: el nombre se repite en otra categoría | `tests/unit/catalog/test_catalog_service.py` |
| PTY-05 | TC-PTY-05c | integration | Dos `add` con `"Notebook"` y `"notebook"` en la misma categoría, sin pasar por el service | El segundo lanza `DuplicateProductTypeError` (no `IntegrityError`) | `tests/integration/catalog/test_product_type_repository.py` |
| PTY-05 | TC-PTY-05d | integration | `"Notebook"` en dos categorías distintas; `find_by_name_in_category(" NOTEBOOK ", hardware.id)` | Las dos filas conviven; la búsqueda devuelve solo la de `"Hardware"` | `tests/integration/catalog/test_product_type_repository.py` |
| PTY-05 | TC-PTY-05e | integration | `POST /product-types` con un nombre que ya existe en esa categoría (otra combinación de mayúsculas) | `409` `{"error": "duplicate_product_type"}` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-06 | TC-PTY-06a | unit | `update_product_type(id, name="Ultrabook")` | El nombre cambia, la categoría se conserva y hay un commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-06 | TC-PTY-06b | unit | `update_product_type(id, category_id=oficina.id)` | El tipo pasa a `"Oficina"`: está en `oficina.product_types` y ya no en `hardware.product_types`; hay un commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-06 | TC-PTY-06c | unit | `update_product_type(id, name="NOTEBOOK")` sobre `"Notebook"` | No lanza y el nombre queda `"NOTEBOOK"` | `tests/unit/catalog/test_catalog_service.py` |
| PTY-06 | TC-PTY-06d | unit | `update_product_type(9999, name="X")` | Lanza `ProductTypeNotFoundError` y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-06 | TC-PTY-06e | integration | `PATCH /product-types/{id}` con `name` y `category_id` nuevos, y además una clave ajena (`"id": 99`) | `200` con los datos nuevos; el `id` no cambia y la fila quedó modificada | `tests/integration/catalog/test_product_types_api.py` |
| PTY-06 | TC-PTY-06f | integration | `PATCH /product-types/9999` | `404` `{"error": "product_type_not_found"}` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-06 | TC-PTY-06g | integration | `SqlAlchemyProductTypeRepository.get(2**63)` (fuera del rango de `INTEGER` de SQLite) | Devuelve `None` sin lanzar `OverflowError` | `tests/integration/catalog/test_product_type_repository.py` |
| PTY-07 | TC-PTY-07a | unit | `delete_product_type(id)` | El tipo ya no está en el repositorio y hay un commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-07 | TC-PTY-07b | unit | `delete_product_type(9999)` | Lanza `ProductTypeNotFoundError` y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-07 | TC-PTY-07c | integration | `delete(product_type)`, commit y `get(id)` en una sesión nueva | Devuelve `None`; la categoría sigue existiendo | `tests/integration/catalog/test_product_type_repository.py` |
| PTY-07 | TC-PTY-07d | integration | `DELETE /product-types/{id}` | `204` sin cuerpo; el tipo ya no aparece en `GET /product-types` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-07 | TC-PTY-07e | integration | `DELETE /product-types/9999` | `404` `{"error": "product_type_not_found"}` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-08 | TC-PTY-08a | unit | Implementado en `03-products` (T-PRD-21): tipo con un producto inactivo; `delete_product_type(id)` | Lanza `ProductTypeInUseError`; el tipo sigue en el repositorio y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-08 | TC-PTY-08b | integration | Implementado en `03-products` (T-PRD-10): `ProductTypeRepository.delete` de un tipo con productos, sin pasar por el service | Lanza `ProductTypeInUseError` (FK `RESTRICT` de `products.product_type_id`) y la fila sigue | `tests/integration/catalog/test_product_type_repository.py` |
| PTY-08 | TC-PTY-08c | integration | Implementado en `03-products` (T-PRD-27): `DELETE /product-types/{id}` de un tipo con un producto activo | `409` `{"error": "product_type_in_use"}` y el tipo sigue existiendo | `tests/integration/catalog/test_product_types_api.py` |
| PTY-09 | — | — | **SPEC-PTY-09 reemplazada por SPEC-PTY-22 (2026-11-12)**: TC-PTY-09a a 09d pasan a TC-PTY-22a a 22d (mismos datos y resultados, ver la sección nueva); las filas siguientes quedan como registro | — | — |
| PTY-09 | TC-PTY-09a | unit | Categorías `"Redes"` (con `"Router"` y `"Access point"`), `"audio"` (sin tipos) y `"Hardware"` (con `"Notebook"`); `list_product_types()` | Devuelve las tres categorías en el orden `"audio"`, `"Hardware"`, `"Redes"`, cada una con sus tipos ordenados por nombre (`"Access point"`, `"Router"`) y `"audio"` con la lista vacía | `tests/unit/catalog/test_catalog_service.py` |
| PTY-09 | TC-PTY-09b | integration | Mismos datos que 09a; `list_with_product_types()` | Mismo orden de categorías y de tipos que 09a | `tests/integration/catalog/test_category_repository.py` |
| PTY-09 | TC-PTY-09c | integration | 3 categorías con 2 tipos cada una; se cuentan las sentencias SQL con un listener `before_cursor_execute` mientras se llama a `list_with_product_types()` y se recorren todos los tipos | Como máximo 2 sentencias (sin N+1) | `tests/integration/catalog/test_category_repository.py` |
| PTY-09 | TC-PTY-09d | integration | Sesión de un `Client`; `GET /product-types` | `200` con la lista de `{"id", "name", "product_types": [{"id", "name", "category_id"}]}` en el orden de 09a | `tests/integration/catalog/test_product_types_api.py` |
| PTY-10 | TC-PTY-10a | unit | `list_product_types(category_id=hardware.id)` con tipos en dos categorías | Devuelve un solo grupo, `"Hardware"`, con solo sus tipos | `tests/unit/catalog/test_catalog_service.py` |
| PTY-10 | TC-PTY-10b | integration | Sesión de un `Representative`; `GET /product-types?category_id=<hardware>` | `200` con un solo grupo, el de `"Hardware"`, y solo sus tipos | `tests/integration/catalog/test_product_types_api.py` |
| PTY-11 | TC-PTY-11a | integration | Parametrizado por endpoint de escritura (`POST /categories`, `PATCH` y `DELETE /categories/{id}`, `POST /product-types`, `PATCH` y `DELETE /product-types/{id}`) sobre datos existentes, con la sesión de un `Representative` | `403` `{"error": "forbidden"}` en todos y la base no cambia | `tests/integration/catalog/test_catalog_permissions.py` |
| PTY-11 | TC-PTY-11b | integration | Igual que 11a con la sesión de un `Client` | `403` en todos y la base no cambia | `tests/integration/catalog/test_catalog_permissions.py` |
| PTY-12 | TC-PTY-12a | unit | `update_category(id, name="Redes")` | El nombre cambia y hay un commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-12 | TC-PTY-12b | unit | `update_category(id, name="HARDWARE")` sobre `"Hardware"` | No lanza y el nombre queda `"HARDWARE"` | `tests/unit/catalog/test_catalog_service.py` |
| PTY-12 | TC-PTY-12c | unit | `update_category(9999, name="Redes")` | Lanza `CategoryNotFoundError` y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-12 | TC-PTY-12d | integration | `PATCH /categories/{id}` con `{"name": "Redes"}` | `200` `{"id": <id>, "name": "Redes"}` y la fila quedó modificada | `tests/integration/catalog/test_categories_api.py` |
| PTY-12 | TC-PTY-12e | integration | `PATCH /categories/9999` | `404` `{"error": "category_not_found"}` | `tests/integration/catalog/test_categories_api.py` |
| PTY-13 | TC-PTY-13a | unit | `delete_category(id)` de una categoría sin tipos | Ya no está en el repositorio y hay un commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-13 | TC-PTY-13b | unit | `delete_category(9999)` | Lanza `CategoryNotFoundError` y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-13 | TC-PTY-13c | integration | `delete(category)` de una categoría sin tipos, commit y `get(id)` en una sesión nueva | Devuelve `None` | `tests/integration/catalog/test_category_repository.py` |
| PTY-13 | TC-PTY-13d | integration | `DELETE /categories/{id}` de una categoría sin tipos | `204` sin cuerpo; la categoría ya no aparece en `GET /categories` | `tests/integration/catalog/test_categories_api.py` |
| PTY-13 | TC-PTY-13e | integration | `DELETE /categories/9999` | `404` `{"error": "category_not_found"}` | `tests/integration/catalog/test_categories_api.py` |
| PTY-14 | TC-PTY-14a | unit | Categoría con un tipo; `delete_category(id)` | Lanza `CategoryInUseError`; la categoría sigue en el repositorio y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-14 | TC-PTY-14b | integration | Una categoría con un tipo y otra sin tipos; `has_product_types` de cada una | `True` y `False` | `tests/integration/catalog/test_category_repository.py` |
| PTY-14 | TC-PTY-14c | integration | `CategoryRepository.delete` de una categoría con un tipo, sin pasar por el service | Lanza `CategoryInUseError` (no `IntegrityError`); en una sesión nueva la categoría y el tipo siguen, con el mismo `category_id` | `tests/integration/catalog/test_category_repository.py` |
| PTY-14 | TC-PTY-14d | integration | Categoría con un tipo; `DELETE FROM categories WHERE id = :id` con parámetro enlazado, sobre la conexión | Lanza `IntegrityError` (la FK `RESTRICT` protege también ante SQL directo) | `tests/integration/catalog/test_category_repository.py` |
| PTY-14 | TC-PTY-14e | integration | `DELETE /categories/{id}` de una categoría con un tipo | `409` `{"error": "category_in_use"}`; la categoría y el tipo siguen existiendo | `tests/integration/catalog/test_categories_api.py` |
| PTY-15 | TC-PTY-15a | unit | Parametrizado: `create_category` con `None`, `""` y `"   "` | `ValidationError` con `fields == {"name": "required"}`; no se agrega nada y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-15 | TC-PTY-15b | unit | Parametrizado: `create_category` con `123`, `["Hardware"]` y `{"name": "x"}` | `ValidationError` con `fields == {"name": "invalid"}`; no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-15 | TC-PTY-15c | unit | `update_category(id, name="   ")` y `update_category(id, name=5)` | `fields == {"name": "required"}` y `{"name": "invalid"}`; el nombre no cambia y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-15 | TC-PTY-15d | unit | `create_product_type("", hardware.id)` y `create_product_type(7, hardware.id)` | `fields == {"name": "required"}` y `{"name": "invalid"}`; no se agrega nada y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-15 | TC-PTY-15e | unit | `update_product_type(id, name="   ")` y `update_product_type(id, name=["x"])` | `fields == {"name": "required"}` y `{"name": "invalid"}`; el tipo no cambia y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-15 | TC-PTY-15f | integration | `POST /categories` con `{"name": ""}`, con `{"name": 123}` y con el cuerpo vacío | `400` con `fields.name` en `"required"`, `"invalid"` y `"required"`; sin categoría creada | `tests/integration/catalog/test_categories_api.py` |
| PTY-15 | TC-PTY-15g | integration | `PATCH /categories/{id}` con `{"name": "  "}` | `400` `{"error": "validation_error", "fields": {"name": "required"}}` y la fila no cambia | `tests/integration/catalog/test_categories_api.py` |
| PTY-15 | TC-PTY-15h | integration | `POST /product-types` con `{"name": 123, "category_id": <hardware>}` | `400` con `fields == {"name": "invalid"}` y sin tipo creado | `tests/integration/catalog/test_product_types_api.py` |
| PTY-15 | TC-PTY-15i | integration | `PATCH /product-types/{id}` con `{"name": ""}` | `400` con `fields == {"name": "required"}` y la fila no cambia | `tests/integration/catalog/test_product_types_api.py` |
| PTY-16 | TC-PTY-16a | unit | `update_product_type(id, category_id=9999)` | Lanza `CategoryNotFoundError`; el tipo sigue en su categoría y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-16 | TC-PTY-16b | unit | `"Notebook"` en `"Hardware"` y `"notebook"` en `"Oficina"`; `update_product_type(hardware_notebook.id, category_id=oficina.id)` | Lanza `DuplicateProductTypeError`; el tipo sigue en `"Hardware"` y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-16 | TC-PTY-16c | unit | `"Notebook"` y `"Desktop"` en `"Hardware"`; `update_product_type(desktop.id, name="NOTEBOOK")` | Lanza `DuplicateProductTypeError`; el nombre no cambia y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-16 | TC-PTY-16d | integration | `PATCH /product-types/{id}` con `category_id: 9999` | `404` `{"error": "category_not_found"}` y la fila no cambia | `tests/integration/catalog/test_product_types_api.py` |
| PTY-16 | TC-PTY-16e | integration | Mismos datos que 16b; `PATCH /product-types/{id}` con `category_id` de `"Oficina"` | `409` `{"error": "duplicate_product_type"}` y la fila no cambia | `tests/integration/catalog/test_product_types_api.py` |
| PTY-17 | TC-PTY-17a | integration | Categorías `"redes"`, `"Audio"` y `"hardware"` insertadas en ese orden; `list_all()` | Devuelve `"Audio"`, `"hardware"`, `"redes"` (orden alfabético sin distinguir mayúsculas) | `tests/integration/catalog/test_category_repository.py` |
| PTY-17 | TC-PTY-17b | unit | `list_categories()` con fakes con varias categorías | Devuelve todas las categorías ordenadas por nombre sin distinguir mayúsculas | `tests/unit/catalog/test_catalog_service.py` |
| PTY-17 | TC-PTY-17c | integration | Sesión de un `Client`; `GET /categories` con los datos de 17a | `200` `[{"id", "name"}, ...]` en el orden de 17a | `tests/integration/catalog/test_categories_api.py` |
| PTY-18 | TC-PTY-18a | unit | `list_product_types(category_id=9999)` | Lanza `CategoryNotFoundError` | `tests/unit/catalog/test_catalog_service.py` |
| PTY-18 | TC-PTY-18b | unit | **Reemplazado por TC-PTY-20e** (SPEC-PTY-20, 2026-11-10) | — | — |
| PTY-18 | TC-PTY-18c | integration | `GET /product-types?category_id=9999` (el caso `abc` pasó a TC-PTY-20h el 2026-11-10) | `404` `{"error": "category_not_found"}` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-18 | TC-PTY-18d | integration | `SqlAlchemyCategoryRepository.get(2**63)` | Devuelve `None` sin lanzar `OverflowError` | `tests/integration/catalog/test_category_repository.py` |
| PTY-18 | TC-PTY-18e | integration | `GET /product-types?category_id=99999999999999999999` | `404` `{"error": "category_not_found"}` (no `500`) | `tests/integration/catalog/test_product_types_api.py` |
| PTY-19 | TC-PTY-19a | unit | `Category(name="  Mesa de  ayuda ")` | `name == "Mesa de  ayuda"`: sin espacios en los extremos y con los internos intactos | `tests/unit/catalog/test_products.py` |
| PTY-19 | TC-PTY-19b | unit | `ProductType(name=" Notebook ", category=...)` y después `product_type.name = "  Ultrabook "` | `name == "Notebook"` y luego `"Ultrabook"`, con `name_key` acompañando | `tests/unit/catalog/test_products.py` |
| PTY-19 | TC-PTY-19c | integration | `POST /categories` con `{"name": "  Hardware "}` | `201` con `name == "Hardware"` y la fila guardada con `"Hardware"` | `tests/integration/catalog/test_categories_api.py` |
| PTY-19 | TC-PTY-19d | integration | `PATCH /product-types/{id}` con `{"name": "  Ultrabook "}` | `200` con `name == "Ultrabook"` y la fila guardada con `"Ultrabook"` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-20 | TC-PTY-20a | unit | Parametrizado: `create_product_type("Notebook", v)` con `v` en `True`, `False`, `1.5`, `0`, `-3`, `"abc"`, `"-1"`, `"0"`, `"1.5"`, `""` y `[1]` (existe la categoría `1`) | `ValidationError` con `fields == {"category_id": "invalid"}`; no se agrega nada y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-20 | TC-PTY-20b | unit | `create_product_type("Notebook", None)` y `create_product_type("", None)` | `fields == {"category_id": "required"}` y `{"name": "required", "category_id": "required"}` (los campos se validan juntos); no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-20 | TC-PTY-20c | unit | Existe la categoría `1`; `create_product_type("Notebook", "1")` | Se crea el tipo en esa categoría: un texto de dígitos es un id válido (el query string llega como texto) | `tests/unit/catalog/test_catalog_service.py` |
| PTY-20 | TC-PTY-20d | unit | Parametrizado: `update_product_type(id, category_id=v)` con `v` en `0`, `"abc"` y `True` | `fields == {"category_id": "invalid"}`; el tipo sigue en su categoría y no hay commit | `tests/unit/catalog/test_catalog_service.py` |
| PTY-20 | TC-PTY-20e | unit | Parametrizado: `list_product_types(category_id=v)` con `v` en `"abc"`, `""`, `"-1"`, `"0"`, `"1.5"` y un texto de 5000 dígitos (más de lo que Python convierte a `int`) | `ValidationError` con `fields == {"category_id": "invalid"}` (sin `ValueError`) | `tests/unit/catalog/test_catalog_service.py` |
| PTY-20 | TC-PTY-20f | integration | `POST /product-types` con `category_id` en `"abc"` y `true`, y sin `category_id` | `400` `validation_error` con `fields.category_id` en `"invalid"`, `"invalid"` y `"required"`; sin tipo creado | `tests/integration/catalog/test_product_types_api.py` |
| PTY-20 | TC-PTY-20g | integration | `PATCH /product-types/{id}` con `{"category_id": 0}` | `400` con `fields == {"category_id": "invalid"}` y la fila no cambia | `tests/integration/catalog/test_product_types_api.py` |
| PTY-20 | TC-PTY-20h | integration | `GET /product-types?category_id=abc` y `GET /product-types?category_id=` | `400` `{"error": "validation_error", "fields": {"category_id": "invalid"}}` en los dos casos | `tests/integration/catalog/test_product_types_api.py` |

Además, cada task de endpoint deja en verde TC-PLT-14a y 14b (sincronización entre las rutas y el contrato), y TC-USR-16d cubre los 8 endpoints nuevos sin sesión (`401`) sin modificar el test.

### Búsqueda por nombre (re-sincronización del 2026-11-12)

Datos de referencia: las categorías `"Redes"` (tipos `"Router"` y `"Access point"`), `"audio"` (sin tipos), `"Hardware"` (tipos `"Notebook"` y `"Ruteador USB"`) y `"Electrónica"` (tipo `"Cámara"`), más la categoría `"50% off"` (sin tipos) para el `autoescape`. Los fakes suman `FakeCategoryRepository.list_all(q)` (filtra por `q.casefold() in name_key`) y `FakeProductTypeRepository.search(q, category_id)` (mismo filtro sobre los tipos, ordenados por `(category.name_key, category.id, name_key, id)`).

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| PTY-21 | TC-PTY-21a | unit | Datos de referencia con fakes; `list_categories(q="RED")` y `list_categories(q="zzz")` | `["Redes"]` y `[]` | `tests/unit/catalog/test_catalog_service.py` |
| PTY-21 | TC-PTY-21b | integration | Datos de referencia; `list_all(q="ÓNICA")`, `list_all(q="e")` y `list_all(q="%")` | `["Electrónica"]` (mayúsculas fuera de ASCII); `"Electrónica"`, `"Redes"` en orden por nombre; `["50% off"]` (`%` literal) | `tests/integration/catalog/test_category_repository.py` |
| PTY-21 | TC-PTY-21c | integration | Sesión de un `Client`; `GET /categories?q=re` | `200` con `[{"id", "name": "Redes"}]` | `tests/integration/catalog/test_categories_api.py` |
| PTY-21 | TC-PTY-21d | integration | `GET /categories?q=` y `GET /categories?q=%20` (SPEC-PLT-27) | `200` con todas las categorías, igual que sin `q` | `tests/integration/catalog/test_categories_api.py` |
| PTY-22 | TC-PTY-22a | unit | Igual que TC-PTY-09a (antes 09a; desde T-PTY-37 el resultado es una lista de `CategoryGroup`) | Igual que TC-PTY-09a | `tests/unit/catalog/test_catalog_service.py` |
| PTY-22 | TC-PTY-22b | integration | Igual que TC-PTY-09b (antes 09b) | Igual que TC-PTY-09b | `tests/integration/catalog/test_category_repository.py` |
| PTY-22 | TC-PTY-22c | integration | Igual que TC-PTY-09c (antes 09c) | Como máximo 2 sentencias (sin N+1) | `tests/integration/catalog/test_category_repository.py` |
| PTY-22 | TC-PTY-22d | integration | Igual que TC-PTY-09d (antes 09d) | Igual que TC-PTY-09d | `tests/integration/catalog/test_product_types_api.py` |
| PTY-22 | TC-PTY-22e | unit | Datos de referencia; `list_product_types(q="")` y `list_product_types(q="   ")` (SPEC-PLT-27) | Los mismos grupos que `list_product_types()`, incluida `"audio"` sin tipos | `tests/unit/catalog/test_catalog_service.py` |
| PTY-23 | TC-PTY-23a | unit | Datos de referencia con fakes, salvo que la fixture unitaria crea `"Electrónica"` sin tipos (sin `"Cámara"`, que también contiene `r`); `list_product_types(q="R")` (mayúscula: prueba que no distingue mayúsculas; coincide solo con `"Router"` y `"Ruteador USB"`) | Dos grupos en orden: `"Hardware"` con `["Ruteador USB"]` y `"Redes"` con `["Router"]`; sin `"audio"` ni `"Electrónica"` (sin coincidencias) y sin `"Notebook"` ni `"Access point"` | `tests/unit/catalog/test_catalog_service.py` |
| PTY-23 | TC-PTY-23b | integration | Datos propios del caso: categorías `"Hardware"`, `"Redes"` y `"audio"`; tipos `"Router"` (Redes), `"Router USB"` (Hardware), `"Cámara"` (audio) y `"Notebook"` (Hardware); `search("CÁM")`, `search("rout")`, `search("rout", category_id=redes.id)` y `search("%")` | `["Cámara"]` (mayúsculas fuera de ASCII); `["Router USB", "Router"]` (orden por categoría y nombre: `"Hardware"` antes que `"Redes"`); `["Router"]`; `[]` (`%` literal) | `tests/integration/catalog/test_product_type_repository.py` |
| PTY-23 | TC-PTY-23c | integration | 3 categorías con 2 tipos cada una; `count_statements` mientras se llama a `search("o")` y se recorre la categoría de cada tipo | Como máximo 2 sentencias (sin N+1) | `tests/integration/catalog/test_product_type_repository.py` |
| PTY-23 | TC-PTY-23d | unit | `list_product_types(category_id=hardware.id, q="note")`, `list_product_types(category_id=hardware.id, q="zzz")`, `list_product_types(category_id=9999, q="a")` y `list_product_types(category_id="abc", q="a")` | `[Hardware: ["Notebook"]]`; `[]` (la categoría sin coincidencias se omite); `CategoryNotFoundError`; `ValidationError` `{"category_id": "invalid"}` | `tests/unit/catalog/test_catalog_service.py` |
| PTY-23 | TC-PTY-23e | unit | Datos de referencia; `list_product_types(q="redes")` (coincide con el nombre de la categoría `"Redes"`, no con el de ningún tipo) | `[]`: `q` busca en el nombre del tipo, no en el de la categoría | `tests/unit/catalog/test_catalog_service.py` |
| PTY-23 | TC-PTY-23f | integration | Sesión de un `Representative`; datos de referencia completos (con `"Cámara"` en `"Electrónica"`); `GET /product-types?q=UTE` y `GET /product-types?category_id=<redes>&q=UTE` (`ute` está en `"Router"` y en `"Ruteador USB"`, y en ningún otro tipo) | `200` con dos grupos en orden: `"Hardware"` con solo `"Ruteador USB"` y `"Redes"` con solo `"Router"` (sin `"audio"` ni `"Electrónica"`, sin `"Notebook"` ni `"Access point"`); `200` con solo `"Redes"` con `"Router"` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-23 | TC-PTY-23g | integration | `GET /product-types?q=` y `GET /product-types?category_id=abc&q=UTE` | `200` igual que sin `q` (incluida `"audio"`); `400` `{"error": "validation_error", "fields": {"category_id": "invalid"}}` | `tests/integration/catalog/test_product_types_api.py` |
| PTY-24 | TC-PTY-24a | integration | `GET /categories?page=0&page_size=abc` y `GET /categories?page=1&page_size=1` | `200` con el arreglo plano de todas las categorías en los dos (ni `400` ni objeto `{items, ...}`) | `tests/integration/catalog/test_categories_api.py` |
| PTY-24 | TC-PTY-24b | integration | `GET /product-types?page=abc`, `GET /product-types?page=1&page_size=1` y `GET /product-types?q=UTE&page=2` | `200` con el arreglo plano de grupos en los tres; el último, filtrado por `q` como TC-PTY-23f (`"Hardware"` con `"Ruteador USB"` y `"Redes"` con `"Router"`, no una página vacía) | `tests/integration/catalog/test_product_types_api.py` |

## Casos borde

- Nombre duplicado con otra combinación de mayúsculas y espacios alrededor: TC-PTY-02c, 02f, 02h y 05a.
- Mayúsculas no ASCII (`"ÁUDIO"` / `"áudio"`), que el `lower()` de SQLite no resuelve: TC-PTY-02a y 02e.
- Renombrar una categoría o un tipo a su propio nombre con otras mayúsculas: TC-PTY-12b y 06c.
- Mismo nombre de tipo en categorías distintas (permitido): TC-PTY-05b y 05d.
- Mover un tipo a una categoría que ya tiene uno con ese nombre: TC-PTY-16b y 16e.
- Renombrar un tipo al nombre de un hermano: TC-PTY-16c.
- Ids inexistentes en la modificación y en la baja: TC-PTY-06d, 06f, 07b, 07e, 12c, 12e, 13b y 13e.
- `category_id` que no es un entero positivo (`true`, decimal, texto, negativo, `0`, vacío) o ausente en el alta: TC-PTY-20a a 20h. Un texto de dígitos se acepta: TC-PTY-20c.
- Id entero fuera del rango de `INTEGER` de SQLite: TC-PTY-06g, 18d y 18e.
- Nombres con espacios en los extremos y espacios internos: TC-PTY-19a a 19d.
- Nombre ausente, vacío, solo espacios o que no es texto, en alta y modificación: TC-PTY-15a a 15i.
- Nombre y `category_id` inválidos a la vez (se informan los dos): TC-PTY-20b.
- Categoría sin tipos en el listado agrupado: TC-PTY-09a.
- Orden alfabético sin distinguir mayúsculas: TC-PTY-09a, 09b y 17a.
- Baja de una categoría con tipos por un camino que no pasa por el service (repositorio o SQL directo): TC-PTY-14c y 14d.
- Claves que `PATCH` no admite (`id`): TC-PTY-06e.
- Consultas N+1 en el listado agrupado: TC-PTY-09c (hoy TC-PTY-22c) y en la búsqueda de tipos: TC-PTY-23c.
- `q` con mayúsculas fuera de ASCII, con `%`, vacío o solo espacios: TC-PTY-21b, 21d, 22e, 23b y 23g.
- `q` que solo coincide con el nombre de una categoría (no con sus tipos): TC-PTY-23e.
- `q` con filtro de categoría: categoría sin coincidencias, inexistente o mal formada: TC-PTY-23d y 23g.
- `page` y `page_size` inválidos o válidos se ignoran en los dos listados: TC-PTY-24a y 24b.

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 2 (autenticación y permisos) | TC-PTY-11a y 11b (`403` para no admins en los 6 endpoints de escritura), TC-USR-16d (`401` sin sesión en los 8 endpoints; hoy TC-USR-49a), y TC-PTY-09d (hoy 22d), 10b, 17c, 21c y 23f (las lecturas solo piden sesión) |
| RNF 7 (documentación de la API) | TC-PLT-14a y 14b en cada task de endpoint (T-PTY-21 a 28); TC-PLT-23a y 23b en T-PTY-39 |
| RNF 10 (listados; estos no se paginan por decisión del usuario) | TC-PTY-24a y 24b |
