# 03 — Productos · Test plan

Cada test cita en su docstring la spec y el caso: `"""SPEC-PRD-13 · TC-PRD-13a"""`.

Fixtures existentes (`tests/conftest.py`): `app`, `client`, `schema`, `db_session`, `make_user`, `login_as`, `admin`, `admin_client`, `make_category` y `make_product_type` (ver [01-users](../01-users/test-plan.md) y [02-product-types](../02-product-types/test-plan.md)).

Fixture nueva (`tests/conftest.py`):
- `make_product`: fábrica `make_product(product_type, name=..., is_active=True)` que persiste un `Product` de ese tipo y hace commit. Sin nombre, genera uno único (`"Product 1"`, `"Product 2"`, …).

Helper compartido (T-PRD-01): `count_statements(session)` en `tests/integration/catalog/queries.py`, movido desde `test_category_repository.py`. Cuenta las sentencias SQL con un listener `before_cursor_execute` del engine.

Dobles para tests unitarios (sin Flask ni base), en `tests/unit/catalog/fakes.py`:
- `FakeProductRepository` (nuevo): diccionario en memoria que asigna ids, busca por `(product_type.id, name_key)` y lista con los filtros de `list_matching` (categoría por `product.product_type.category.id`, tipo por `product.product_type.id`, `active_only` por `is_active`), ordenado por `(name_key, id)`.
- `FakeProductTypeRepository` (existente): suma `has_products(product_type_id)`, que responde `bool(product_type.products)`.
- `FakeCategoryRepository` (existente) y `CommitSpy` (`tests/unit/fakes.py`) sin cambios.

Las colecciones `ProductType.products` se mantienen solas en objetos transitorios gracias a `back_populates`, así que los fakes no necesitan conocerse entre sí.

Datos de referencia de los casos: la categoría `"Hardware"` con los tipos `"Notebook"` y `"Desktop"`, y la categoría `"Oficina"` con el tipo `"Impresora"`. Para los tests que verifican "sin cambios", se relee la fila con `db_session.expire_all()` después del request.

## Matriz spec → casos

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| PRD-01 | TC-PRD-01a | unit | `Product(name="XPS 13", product_type=notebook, is_active=True)` | `product.product_type is notebook` y el producto está en `notebook.products` | `tests/unit/catalog/test_products.py` |
| PRD-01 | TC-PRD-01b | integration | `add(Product(name="XPS 13", product_type=notebook))` sin `is_active`, commit y `get(id)` en una sesión nueva | Devuelve el producto con el mismo nombre, su `product_type_id`, `product_type.category.name == "Hardware"` e `is_active is True` (default de la columna) | `tests/integration/catalog/test_product_repository.py` |
| PRD-01 | TC-PRD-01c | unit | `create_product("XPS 13", notebook.id)` con fakes | Devuelve un `Product` con ese nombre, `product_type is notebook` e `is_active is True`, guardado en el repositorio, y `commit` se llamó una vez | `tests/unit/catalog/test_product_service.py` |
| PRD-01 | TC-PRD-01d | integration | `admin_client` hace `POST /products` con `{"name": "XPS 13", "product_type_id": <notebook>}` | `201` `{"id": <int>, "name": "XPS 13", "is_active": true, "product_type": {"id": <notebook>, "name": "Notebook", "category_id": <hardware>}, "category": {"id": <hardware>, "name": "Hardware"}}` y la fila existe | `tests/integration/catalog/test_products_api.py` |
| PRD-02 | TC-PRD-02a | unit | `create_product("XPS 13", 9999)` | Lanza `ProductTypeNotFoundError`; no se agrega nada y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-02 | TC-PRD-02b | integration | `POST /products` con `product_type_id: 9999` | `404` `{"error": "product_type_not_found"}` y sin producto creado | `tests/integration/catalog/test_products_api.py` |
| PRD-02 | TC-PRD-02c | integration | `POST /products` con `product_type_id: 9223372036854775808` (`2**63`) | `404` `{"error": "product_type_not_found"}` (no `500`) | `tests/integration/catalog/test_products_api.py` |
| PRD-03 | TC-PRD-03a | unit | Parametrizado: `create_product(v, notebook.id)` con `v` en `None`, `""` y `"   "` | `ValidationError` con `fields == {"name": "required"}`; no se agrega nada y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-03 | TC-PRD-03b | integration | `POST /products` con `{"product_type_id": <notebook>}` (sin nombre) | `400` `{"error": "validation_error", "fields": {"name": "required"}}` y sin producto creado | `tests/integration/catalog/test_products_api.py` |
| PRD-04 | TC-PRD-04a | unit | `update_product(id, name="XPS 15")` | El nombre cambia, el tipo se conserva y hay un commit | `tests/unit/catalog/test_product_service.py` |
| PRD-04 | TC-PRD-04b | unit | `update_product(id, product_type_id=desktop.id)` | El producto pasa a `"Desktop"`: está en `desktop.products` y ya no en `notebook.products`; hay un commit | `tests/unit/catalog/test_product_service.py` |
| PRD-04 | TC-PRD-04c | unit | `update_product(id, name="xps 13")` sobre `"XPS 13"` | No lanza y el nombre queda `"xps 13"` | `tests/unit/catalog/test_product_service.py` |
| PRD-04 | TC-PRD-04g | integration | `PATCH /products/{id}` con `name` y `product_type_id` nuevos, y además claves ajenas (`"id": 99`, `"is_active": false`) | `200` con los datos nuevos; el `id` no cambia, `is_active` sigue en `true` y la fila quedó modificada | `tests/integration/catalog/test_products_api.py` |
| PRD-05 | TC-PRD-05a | unit | `product.deactivate()` | `is_active is False` | `tests/unit/catalog/test_products.py` |
| PRD-05 | TC-PRD-05b | unit | `deactivate_product(id)` de un producto activo | Devuelve el producto con `is_active is False`, sigue en el repositorio y hay un commit | `tests/unit/catalog/test_product_service.py` |
| PRD-05 | TC-PRD-05e | integration | `POST /products/{id}/deactivate` | `200` con la representación del producto e `is_active: false` | `tests/integration/catalog/test_products_api.py` |
| PRD-06 | TC-PRD-06a | integration | Baja por API y lectura con `db_session` después de `expire_all()` | La fila existe con el mismo nombre y `product_type_id`, e `is_active` en `False` | `tests/integration/catalog/test_products_api.py` |
| PRD-06 | TC-PRD-06b | integration | Atributos públicos de `SqlAlchemyProductRepository` | No existe ningún método `delete` ni `remove` | `tests/integration/catalog/test_product_repository.py` |
| PRD-06 | TC-PRD-06c | integration | Reglas de `app.url_map` que empiezan con `/products` | Ninguna acepta `DELETE` | `tests/integration/catalog/test_products_api.py` |
| PRD-06 | TC-PRD-06d | integration | Ticket con un producto que después se da de baja (cubierto en `04-tickets`, T-TKT-37) | El ticket sigue mostrando el producto, con `is_active: false`, y el producto ya no se puede asociar (`invalid_product`) | `tests/integration/tickets/test_cross_area.py` |
| PRD-07 | TC-PRD-07a | unit | Productos `"xps 13"` (Notebook), `"Optiplex"` (Desktop, inactivo) y `"LaserJet"` (Impresora); `list_products()` | Devuelve los tres, incluido el inactivo (el orden lo verifica TC-PRD-21a) | `tests/unit/catalog/test_product_service.py` |
| PRD-07 | TC-PRD-07b | integration | Mismos datos que 07a; `list_matching()` | Devuelve los tres; cada producto expone su tipo, su categoría y su `is_active` (el orden lo verifica TC-PRD-21b) | `tests/integration/catalog/test_product_repository.py` |
| PRD-07 | TC-PRD-07c | integration | 2 categorías, 3 tipos y 2 productos por tipo; se cuentan las sentencias con `count_statements` mientras se llama a `list_matching()` y se recorren el tipo y la categoría de cada producto | Como máximo 3 sentencias (sin N+1) | `tests/integration/catalog/test_product_repository.py` |
| PRD-07 | TC-PRD-07d | integration | Sesión de un `Client`; `GET /products` con los datos de 07a | `200` con la lista de `Product` en el orden de 07a; `"Optiplex"` con `is_active: false` | `tests/integration/catalog/test_products_api.py` |
| PRD-08 | TC-PRD-08a | unit | Datos de 07a; `list_products(category_id=hardware.id)` | Solo `"Optiplex"` y `"xps 13"` | `tests/unit/catalog/test_product_service.py` |
| PRD-08 | TC-PRD-08b | unit | Datos de 07a; `list_products(product_type_id=notebook.id)` | Solo `"xps 13"` | `tests/unit/catalog/test_product_service.py` |
| PRD-08 | TC-PRD-08c | unit | Datos de 07a; `list_products(category_id=hardware.id, product_type_id=notebook.id)` | `["xps 13"]` (intersección; el caso sin coincidencias es TC-PRD-20a) | `tests/unit/catalog/test_product_service.py` |
| PRD-08 | TC-PRD-08d | integration | Datos de 07a; `list_matching(category_id=hardware.id)` | Solo los productos de tipos de `"Hardware"` | `tests/integration/catalog/test_product_repository.py` |
| PRD-08 | TC-PRD-08e | integration | Datos de 07a; `list_matching(product_type_id=notebook.id)` | Solo los productos de `"Notebook"` | `tests/integration/catalog/test_product_repository.py` |
| PRD-08 | TC-PRD-08f | integration | Datos de 07a; `list_matching(category_id=hardware.id, product_type_id=notebook.id)` | `["xps 13"]` (el caso sin coincidencias es TC-PRD-20b) | `tests/integration/catalog/test_product_repository.py` |
| PRD-08 | TC-PRD-08g | integration | Sesión de un `Representative`; `GET /products?category_id=<hardware>` y `?product_type_id=<notebook>` | `200` con `"Optiplex"` y `"xps 13"`, y con `"xps 13"` (el caso sin coincidencias es TC-PRD-20c) | `tests/integration/catalog/test_products_api.py` |
| PRD-09 | TC-PRD-09a | integration | Parametrizado por endpoint de escritura (`POST /products`, `PATCH /products/{id}`, `POST /products/{id}/deactivate`) sobre un producto existente, con la sesión de un `Representative` | `403` `{"error": "forbidden"}` en todos y la tabla `products` no cambia | `tests/integration/catalog/test_catalog_permissions.py` |
| PRD-09 | TC-PRD-09b | integration | Igual que 09a con la sesión de un `Client` | `403` en todos y la tabla `products` no cambia | `tests/integration/catalog/test_catalog_permissions.py` |
| PRD-10 | TC-PRD-10a | unit | Datos de 07a; `list_available_products()` | Solo `"LaserJet"` y `"xps 13"`, en ese orden | `tests/unit/catalog/test_product_service.py` |
| PRD-10 | TC-PRD-10b | integration | Datos de 07a; `list_matching(active_only=True)` | Solo los activos, en el mismo orden | `tests/integration/catalog/test_product_repository.py` |
| PRD-10 | TC-PRD-10c | integration | Parametrizado por rol (`Client`, `Representative`); `GET /products/available` con los datos de 07a | `200` con solo los productos activos | `tests/integration/catalog/test_products_api.py` |
| PRD-11 | TC-PRD-11a | unit | Parametrizado: `create_product(v, notebook.id)` con `v` en `123`, `["XPS"]` y `{"name": "x"}` | `ValidationError` con `fields == {"name": "invalid"}`; no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-11 | TC-PRD-11b | unit | `update_product(id, name="   ")` y `update_product(id, name=5)` | `fields == {"name": "required"}` y `{"name": "invalid"}`; el nombre no cambia y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-11 | TC-PRD-11c | integration | `POST /products` con `{"name": 123, "product_type_id": <notebook>}` | `400` con `fields == {"name": "invalid"}` y sin producto creado | `tests/integration/catalog/test_products_api.py` |
| PRD-11 | TC-PRD-11d | integration | `PATCH /products/{id}` con `{"name": ""}` | `400` con `fields == {"name": "required"}` y la fila no cambia | `tests/integration/catalog/test_products_api.py` |
| PRD-12 | TC-PRD-12a | unit | `update_product(id, product_type_id=9999)` | Lanza `ProductTypeNotFoundError`; el producto sigue en su tipo y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-12 | TC-PRD-12b | integration | `PATCH /products/{id}` con `product_type_id: 9999` | `404` `{"error": "product_type_not_found"}` y la fila no cambia | `tests/integration/catalog/test_products_api.py` |
| PRD-13 | TC-PRD-13a | unit | Existe `"XPS 13"` en `"Notebook"`; `create_product(" xps 13 ", notebook.id)` | Lanza `DuplicateProductError`; no se agrega nada y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-13 | TC-PRD-13b | unit | Existe `"XPS 13"` en `"Notebook"`; `create_product("XPS 13", desktop.id)` | Se crea: el nombre se repite en otro tipo | `tests/unit/catalog/test_product_service.py` |
| PRD-13 | TC-PRD-13c | unit | `"XPS 13"` en `"Notebook"` y `"xps 13"` en `"Desktop"`; `update_product(desktop_xps.id, product_type_id=notebook.id)` | Lanza `DuplicateProductError`; el producto sigue en `"Desktop"` y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-13 | TC-PRD-13d | unit | `"XPS 13"` y `"XPS 15"` en `"Notebook"` (el primero inactivo); `update_product(xps15.id, name="XPS 13")` | Lanza `DuplicateProductError` (un inactivo también reserva el nombre); el nombre no cambia y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-13 | TC-PRD-13e | integration | Dos `add` con `"XPS 13"` y `"xps 13"` en el mismo tipo, sin pasar por el service | El segundo lanza `DuplicateProductError` (no `IntegrityError`) | `tests/integration/catalog/test_product_repository.py` |
| PRD-13 | TC-PRD-13f | integration | `"XPS 13"` en `"Notebook"` y en `"Desktop"`; `find_by_name_in_type(" xps 13 ", notebook.id)` y `find_by_name_in_type("Otro", notebook.id)` | Las dos filas conviven; la búsqueda devuelve solo la de `"Notebook"`, y `None` | `tests/integration/catalog/test_product_repository.py` |
| PRD-13 | TC-PRD-13g | integration | `POST /products` con un nombre que ya existe en ese tipo (otra combinación de mayúsculas) | `409` `{"error": "duplicate_product"}` y sigue habiendo un solo producto | `tests/integration/catalog/test_products_api.py` |
| PRD-13 | TC-PRD-13h | integration | `"XPS 13"` y `"XPS 15"` en `"Notebook"`; `PATCH /products/{xps15}` con `{"name": "xps 13"}` | `409` `{"error": "duplicate_product"}` y la fila no cambia | `tests/integration/catalog/test_products_api.py` |
| PRD-14 | TC-PRD-14a | unit | `Product(name="  XPS  13 ", product_type=notebook)` y después `product.name = " XPS 15 "` | `name == "XPS  13"` y `name_key == "xps  13"`; luego `"XPS 15"` con `name_key` acompañando | `tests/unit/catalog/test_products.py` |
| PRD-14 | TC-PRD-14b | integration | `POST /products` con `{"name": "  XPS 13 ", ...}` | `201` con `name == "XPS 13"` y la fila guardada con `"XPS 13"` | `tests/integration/catalog/test_products_api.py` |
| PRD-14 | TC-PRD-14c | integration | `PATCH /products/{id}` con `{"name": "  XPS 15 "}` | `200` con `name == "XPS 15"` y la fila guardada con `"XPS 15"` | `tests/integration/catalog/test_products_api.py` |
| PRD-15 | TC-PRD-15a | unit | Parametrizado: `create_product("XPS 13", v)` con `v` en `True`, `False`, `1.5`, `0`, `-3`, `"abc"`, `"-1"`, `"0"`, `"1.5"`, `""` y `[1]` (existe el tipo `1`) | `ValidationError` con `fields == {"product_type_id": "invalid"}`; no se agrega nada y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-15 | TC-PRD-15b | unit | `create_product("XPS 13", None)` y `create_product("", None)` | `fields == {"product_type_id": "required"}` y `{"name": "required", "product_type_id": "required"}` (los campos se validan juntos); no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-15 | TC-PRD-15c | unit | Existe el tipo `1`; `create_product("XPS 13", "1")` | Se crea el producto en ese tipo: un texto de dígitos es un id válido | `tests/unit/catalog/test_product_service.py` |
| PRD-15 | TC-PRD-15d | unit | Parametrizado: `update_product(id, product_type_id=v)` con `v` en `0`, `"abc"` y `True` | `fields == {"product_type_id": "invalid"}`; el producto sigue en su tipo y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-15 | TC-PRD-15e | unit | Parametrizado: `list_products(category_id=v)` y `list_products(product_type_id=v)` con `v` en `"abc"`, `""`, `"-1"`, `"0"`, `"1.5"` y un texto de 5000 dígitos; además `list_products(category_id="abc", product_type_id="0")` | `ValidationError` con el campo correspondiente en `"invalid"` (sin `ValueError`); con los dos mal formados, `fields == {"category_id": "invalid", "product_type_id": "invalid"}` | `tests/unit/catalog/test_product_service.py` |
| PRD-15 | TC-PRD-15f | integration | `POST /products` con `product_type_id` en `"abc"` y `true`, y sin `product_type_id` | `400` `validation_error` con `fields.product_type_id` en `"invalid"`, `"invalid"` y `"required"`; sin producto creado | `tests/integration/catalog/test_products_api.py` |
| PRD-15 | TC-PRD-15g | integration | `PATCH /products/{id}` con `{"product_type_id": 0}` | `400` con `fields == {"product_type_id": "invalid"}` y la fila no cambia | `tests/integration/catalog/test_products_api.py` |
| PRD-15 | TC-PRD-15h | integration | `GET /products?category_id=abc`, `GET /products?product_type_id=` y `GET /products?category_id=x&product_type_id=0` | `400` `validation_error` con `fields` `{"category_id": "invalid"}`, `{"product_type_id": "invalid"}` y los dos campos | `tests/integration/catalog/test_products_api.py` |
| PRD-16 | TC-PRD-16a | unit | `list_products(category_id=9999)` | Lanza `CategoryNotFoundError` | `tests/unit/catalog/test_product_service.py` |
| PRD-16 | TC-PRD-16b | unit | `list_products(product_type_id=9999)` | Lanza `ProductTypeNotFoundError` | `tests/unit/catalog/test_product_service.py` |
| PRD-16 | TC-PRD-16c | integration | `GET /products?category_id=9999` y `GET /products?product_type_id=9999` | `404` `{"error": "category_not_found"}` y `404` `{"error": "product_type_not_found"}` | `tests/integration/catalog/test_products_api.py` |
| PRD-16 | TC-PRD-16d | integration | `GET /products?category_id=99999999999999999999` y `GET /products?product_type_id=99999999999999999999` | `404` con `category_not_found` y `product_type_not_found` (no `500`) | `tests/integration/catalog/test_products_api.py` |
| PRD-17 | TC-PRD-17a | unit | `update_product(9999, name="X")` (antes TC-PRD-04d) | Lanza `ProductNotFoundError` y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-17 | TC-PRD-17b | unit | `deactivate_product(9999)` (antes TC-PRD-05c) | Lanza `ProductNotFoundError` y no hay commit | `tests/unit/catalog/test_product_service.py` |
| PRD-17 | TC-PRD-17c | integration | `SqlAlchemyProductRepository.get(2**63)` (antes TC-PRD-04f) | Devuelve `None` sin lanzar `OverflowError` | `tests/integration/catalog/test_product_repository.py` |
| PRD-17 | TC-PRD-17d | integration | `PATCH /products/9999` (antes TC-PRD-04h) | `404` `{"error": "product_not_found"}` | `tests/integration/catalog/test_products_api.py` |
| PRD-17 | TC-PRD-17e | integration | `PATCH /products/9223372036854775808` (`2**63`) (antes TC-PRD-04i) | `404` `{"error": "product_not_found"}` (no `500`) | `tests/integration/catalog/test_products_api.py` |
| PRD-17 | TC-PRD-17f | integration | Parametrizado: `POST /products/9999/deactivate` y `POST /products/9223372036854775808/deactivate` (antes TC-PRD-05f) | `404` `{"error": "product_not_found"}` en los dos | `tests/integration/catalog/test_products_api.py` |
| PRD-18 | TC-PRD-18a | unit | `deactivate_product(id)` de un producto ya inactivo (antes TC-PRD-05d) | No lanza; el producto sigue inactivo (idempotente) | `tests/unit/catalog/test_product_service.py` |
| PRD-18 | TC-PRD-18b | integration | `POST /products/{id}/deactivate` de un producto creado con `is_active=False` (antes TC-PRD-05g) | `200` con `is_active: false` | `tests/integration/catalog/test_products_api.py` |
| PRD-19 | TC-PRD-19a | unit | Producto inactivo; `update_product(id, name="XPS 15")` (antes TC-PRD-04e) | El nombre cambia, `is_active` sigue en `False` y hay un commit | `tests/unit/catalog/test_product_service.py` |
| PRD-19 | TC-PRD-19b | integration | Producto creado con `is_active=False`; `PATCH /products/{id}` con `{"name": "XPS 15", "product_type_id": <desktop>}` | `200` con los datos nuevos e `is_active: false`; la fila sigue inactiva | `tests/integration/catalog/test_products_api.py` |
| PRD-20 | TC-PRD-20a | unit | Datos de 07a; `list_products(category_id=oficina.id, product_type_id=notebook.id)` (antes parte de TC-PRD-08c) | `[]` (un tipo de otra categoría no es error) | `tests/unit/catalog/test_product_service.py` |
| PRD-20 | TC-PRD-20b | integration | Datos de 07a; `list_matching(category_id=oficina.id, product_type_id=notebook.id)` (antes parte de TC-PRD-08f) | `[]` | `tests/integration/catalog/test_product_repository.py` |
| PRD-20 | TC-PRD-20c | integration | Sesión de un `Representative`; `GET /products?category_id=<oficina>&product_type_id=<notebook>` (antes parte de TC-PRD-08g) | `200` con `[]` | `tests/integration/catalog/test_products_api.py` |
| PRD-21 | TC-PRD-21a | unit | Datos de 07a; `list_products()` y `list_available_products()` (antes el orden de TC-PRD-07a) | `"LaserJet"`, `"Optiplex"`, `"xps 13"` y `"LaserJet"`, `"xps 13"`: alfabético sin distinguir mayúsculas | `tests/unit/catalog/test_product_service.py` |
| PRD-21 | TC-PRD-21b | integration | Datos de 07a más `"XPS 13"` en `"Desktop"` (creado después); `list_matching()` (antes el orden de TC-PRD-07b) | `"LaserJet"`, `"Optiplex"`, `"xps 13"` (Notebook), `"XPS 13"` (Desktop): por nombre sin distinguir mayúsculas y, a igual nombre, por `id` | `tests/integration/catalog/test_product_repository.py` |

Además, cada task de endpoint deja en verde TC-PLT-14a y 14b (sincronización entre las rutas y el contrato), y TC-USR-16d cubre los 5 endpoints nuevos sin sesión (`401`) sin modificar el test.

## SPEC-PTY-08 (de `02-product-types`, implementada en esta área)

TC-PTY-08a, 08b y 08c están definidos en el [test-plan de 02](../02-product-types/test-plan.md#matriz-spec--casos) y se implementan con T-PRD-21, T-PRD-10 y T-PRD-27. TC-PTY-08b tiene que exigir `FOREIGN KEY` en `__cause__`, igual que TC-PTY-14c, para que el test falle si falta `passive_deletes="all"`. Esta área suma un caso:

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| PTY-08 | TC-PTY-08d | integration | Un tipo con un producto inactivo y otro tipo sin productos; `has_products` de cada uno | `True` y `False` (los inactivos cuentan) | `tests/integration/catalog/test_product_type_repository.py` |

## Casos borde

- Nombre repetido con otra combinación de mayúsculas y espacios alrededor: TC-PRD-13a, 13e y 13g.
- Mismo nombre en tipos distintos (permitido): TC-PRD-13b y 13f.
- Mover un producto a un tipo que ya tiene uno con ese nombre: TC-PRD-13c.
- Renombrar un producto al nombre de un hermano inactivo: TC-PRD-13d y 13h.
- Renombrar un producto a su propio nombre con otras mayúsculas: TC-PRD-04c.
- Modificar un producto inactivo: TC-PRD-19a y 19b.
- Baja de un producto ya inactivo (idempotente): TC-PRD-18a y 18b.
- Ids inexistentes en la modificación, la baja, el alta y los filtros: TC-PRD-02a, 02b, 12a, 12b, 16a a 16c y 17a a 17f.
- Id entero fuera del rango de `INTEGER` de SQLite, en la ruta, en el cuerpo y en el query string: TC-PRD-02c, 16d, 17c, 17e y 17f.
- `product_type_id`, `category_id` o filtro que no es un entero positivo (`true`, decimal, texto, negativo, `0`, vacío, más de 4300 dígitos) o ausente en el alta: TC-PRD-15a a 15h. Un texto de dígitos se acepta: TC-PRD-15c.
- Nombre y `product_type_id` inválidos a la vez, y los dos filtros inválidos a la vez (se informan los dos): TC-PRD-15b, 15e y 15h.
- Nombre ausente, vacío, solo espacios o que no es texto, en alta y modificación: TC-PRD-03a, 03b y 11a a 11d.
- Nombres con espacios en los extremos y espacios internos: TC-PRD-14a a 14c.
- Los dos filtros con un tipo que no pertenece a la categoría: TC-PRD-20a a 20c.
- Orden alfabético sin distinguir mayúsculas y desempate por `id`: TC-PRD-21a y 21b.
- Productos inactivos en el listado completo y fuera de los disponibles: TC-PRD-07a, 07d y 10a a 10c.
- Claves que `PATCH` no admite (`id`, `is_active`): TC-PRD-04g.
- Consultas N+1 en el listado: TC-PRD-07c.
- Baja de un tipo con productos (solo inactivos) y por un camino que no pasa por el service: TC-PTY-08a, 08b y 08d.

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 2 (autenticación y permisos) | TC-PRD-09a y 09b (`403` para no admins en los 3 endpoints de escritura), TC-USR-16d (`401` sin sesión en los 5 endpoints), y TC-PRD-07d, 08g y 10c (las lecturas solo piden sesión) |
| RNF 5 (conservación del historial, parcial) | TC-PRD-06a, 06b y 06c (TC-PRD-06d en `tests/integration/tickets/test_cross_area.py`, hecho en `04-tickets`) |
| RNF 7 (documentación de la API) | TC-PLT-14a y 14b en cada task de endpoint (T-PRD-22 a 27) |
