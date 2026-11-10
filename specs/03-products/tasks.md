# 03 — Productos · Tasks

Estados: `[ ]` pendiente · `[~]` en curso · `[x]` hecha. Cada task es un ciclo TDD con los casos de [test-plan.md](test-plan.md). La tabla está en orden de ejecución: dominio → repositorios → services → contrato y controllers → cierre. Las tasks de SPEC-PTY-08 (T-PRD-09, 10, 21 y 27) van en la capa que les corresponde; sus casos TC-PTY-08a a 08c están en el [test-plan de 02](../02-product-types/test-plan.md) y TC-PTY-08d en el de esta área.

T-PRD-01 es un refactor sin cambio de comportamiento: no tiene fase roja propia y se considera terminado cuando toda la suite existente sigue en verde. Va en un commit `refactor(...)` aparte.

Las tasks de endpoints (T-PRD-22 a 27) agregan la operación a `docs/openapi.json` y la ruta en el mismo ciclo: en la fase roja fallan el test del endpoint y TC-PLT-14b, y en la verde pasan los dos (ver [plan.md](plan.md#decisiones-técnicas)). Cada fila nueva de `ERROR_RESPONSES` se agrega en la task del primer endpoint que la necesita. Las tasks de escritura suman su endpoint a la lista parametrizada de TC-PRD-09a y 09b.

Sincronizado el 2026-11-10 con SPEC-PRD-17 a 21 (aprobadas con el plan): los casos que antes se trazaban a PRD-04, 05, 07 y 08 como bordes (producto inexistente, baja idempotente, producto inactivo modificado, filtros incompatibles y orden) pasaron a sus specs con IDs nuevos (ver [test-plan.md](test-plan.md)). No hicieron falta tasks nuevas: cada caso quedó en la task que ya lo cubría.

| Estado | ID | Task | Specs | Capa | Terminado cuando |
|--------|----|------|-------|------|------------------|
| [x] | T-PRD-01 | Refactor: mover `count_statements` de `tests/integration/catalog/test_category_repository.py` a `tests/integration/catalog/queries.py` | — (PTY-09 sin cambios) | Tests | `pytest` completo en verde sin cambiar ningún assert; `ruff` limpio |
| [x] | T-PRD-02 | `Product(CatalogName, Base)` mapeado: FK `product_type_id` `ON DELETE RESTRICT` con índice, `is_active` con `default=True`, `deactivate()`, relaciones `product_type` / `ProductType.products` con `back_populates` y `passive_deletes="all"` | PRD-01, 05, 14 | Dominio | TC-PRD-01a, 05a y 14a en verde |
| [x] | T-PRD-03 | `SqlAlchemyProductRepository` con `add` y `get`. Fixture `make_product(product_type, name=..., is_active=...)` en `conftest.py` | PRD-01, 06 | Repositories / tests | TC-PRD-01b y 06b en verde |
| [x] | T-PRD-04 | `UNIQUE (product_type_id, name_key)`; `add` hace `flush()` y traduce `IntegrityError` a `DuplicateProductError` (nueva en `errors.py`); `find_by_name_in_type` por clave normalizada | PRD-13 | Repositories / Dominio | TC-PRD-13e y 13f en verde |
| [x] | T-PRD-05 | `ProductRepository.get` devuelve `None` para un id fuera de rango (`fits_integer_column`) | PRD-17 | Repositories | TC-PRD-17c en verde |
| [x] | T-PRD-06 | `ProductRepository.list_matching()` sin filtros: todos los productos, ordenados por `name_key` e `id`, con `selectinload` de tipo y categoría | PRD-07, 21 | Repositories | TC-PRD-07b, 07c y 21b en verde |
| [x] | T-PRD-07 | `list_matching` con `category_id` (`join` sobre el tipo), con `product_type_id` y con los dos | PRD-08, 20 | Repositories | TC-PRD-08d, 08e, 08f y 20b en verde |
| [x] | T-PRD-08 | `list_matching(active_only=True)` | PRD-10 | Repositories | TC-PRD-10b en verde |
| [x] | T-PRD-09 | `ProductTypeRepository.has_products` (consulta `exists`, cuenta activos e inactivos) | PTY-08 | Repositories | TC-PTY-08d en verde |
| [x] | T-PRD-10 | `ProductTypeRepository.delete` traduce `IntegrityError` a `ProductTypeInUseError` (nueva en `errors.py`) | PTY-08 | Repositories / Dominio | TC-PTY-08b en verde, con `FOREIGN KEY` en la causa |
| [x] | T-PRD-11 | `ProductService.create_product`, caso feliz. Protocolo `ProductRepository` y `FakeProductRepository` en `tests/unit/catalog/fakes.py` | PRD-01 | Services / tests | TC-PRD-01c en verde |
| [x] | T-PRD-12 | `create_product` valida el nombre y el `product_type_id` juntos con `ValidationError(fields)` (`text_error`, `id_error`, `parse_id`) | PRD-03, 11, 15 | Services | TC-PRD-03a, 11a, 15a, 15b y 15c en verde |
| [x] | T-PRD-13 | `create_product` con un tipo inexistente lanza `ProductTypeNotFoundError` | PRD-02 | Services | TC-PRD-02a en verde |
| [x] | T-PRD-14 | `create_product` rechaza un nombre repetido en el mismo tipo (sin distinguir mayúsculas) y lo permite en otro tipo | PRD-13 | Services | TC-PRD-13a y 13b en verde |
| [x] | T-PRD-15 | `ProductService.update_product`: nombre y tipo, propio nombre permitido, `ProductNotFoundError` (nueva en `errors.py`) y un producto inactivo que sigue inactivo | PRD-04, 17, 19 | Services / Dominio | TC-PRD-04a, 04b, 04c, 17a y 19a en verde |
| [x] | T-PRD-16 | `update_product` rechaza nombre inválido, `product_type_id` mal formado, tipo de destino inexistente y duplicado en el tipo de destino, sin modificar ni hacer commit | PRD-11, 12, 13, 15 | Services | TC-PRD-11b, 12a, 13c, 13d y 15d en verde |
| [x] | T-PRD-17 | `ProductService.deactivate_product`: baja lógica, producto inexistente y producto ya inactivo (idempotente) | PRD-05, 17, 18 | Services | TC-PRD-05b, 17b y 18a en verde |
| [x] | T-PRD-18 | `ProductService.list_products` sin filtros, por categoría, por tipo y con los dos | PRD-07, 08, 20, 21 | Services | TC-PRD-07a, 08a, 08b, 08c, 20a y 21a en verde |
| [x] | T-PRD-19 | `list_products` valida el formato de los filtros (`400`) y la existencia de la categoría y del tipo (`404`) | PRD-15, 16 | Services | TC-PRD-15e, 16a y 16b en verde |
| [x] | T-PRD-20 | `ProductService.list_available_products` | PRD-10 | Services | TC-PRD-10a en verde |
| [x] | T-PRD-21 | `has_products` en el protocolo `ProductTypeRepository` y en `FakeProductTypeRepository`; `CatalogService.delete_product_type` lanza `ProductTypeInUseError` | PTY-08 | Services / tests | TC-PTY-08a en verde y TC-PTY-07a y 07b siguen en verde |
| [x] | T-PRD-22 | `get_product_service` en `app/wiring.py`, serializador `product_json`, fila `DuplicateProductError` en `ERROR_RESPONSES`. Contrato (esquemas `Product` y `CreateProductRequest`, respuesta `DuplicateProduct`) + `POST /products` | PRD-01, 02, 03, 09, 11, 13, 14, 15 | App / Contrato / Controllers | TC-PRD-01d, 02b, 02c, 03b, 11c, 13g, 14b, 15f, TC-PRD-09a y 09b para `POST /products`, TC-PLT-14a y 14b en verde |
| [x] | T-PRD-23 | Contrato (parámetros `category_id` y `product_type_id`) + `GET /products` con y sin filtros | PRD-07, 08, 15, 16, 20, 21 | Contrato / Controllers | TC-PRD-07d, 08g, 15h, 16c, 16d, 20c, TC-PLT-14a y 14b en verde |
| [x] | T-PRD-24 | Contrato + `GET /products/available` | PRD-10 | Contrato / Controllers | TC-PRD-10c, TC-PLT-14a y 14b en verde |
| [x] | T-PRD-25 | Fila `ProductNotFoundError` en `ERROR_RESPONSES`. Contrato (esquema `UpdateProductRequest`, respuesta `ProductNotFound`) + `PATCH /products/{product_id}` | PRD-04, 09, 11, 12, 13, 14, 15, 17, 19 | Contrato / Controllers | TC-PRD-04g, 11d, 12b, 13h, 14c, 15g, 17d, 17e, 19b, TC-PRD-09a y 09b para este endpoint, TC-PLT-14a y 14b en verde |
| [x] | T-PRD-26 | Contrato + `POST /products/{product_id}/deactivate` | PRD-05, 06, 09, 17, 18 | Contrato / Controllers | TC-PRD-05e, 06a, 06c, 17f, 18b, TC-PRD-09a y 09b (los 3 endpoints de escritura), TC-PLT-14a y 14b en verde |
| [x] | T-PRD-27 | Fila `ProductTypeInUseError` en `ERROR_RESPONSES`; respuesta `ProductTypeInUse` y `409` en `DELETE /product-types/{product_type_id}` del contrato | PTY-08 | Contrato / Controllers | TC-PTY-08c en verde y TC-PTY-07d y 07e siguen en verde |
| [x] | T-PRD-28 | Cierre del área: `ruff`, cobertura ≥ 90 %, test de guarda, diagramas sincronizados (`classes.md`, `sequences/03-products.md` y la baja de tipos de `sequences/02-product-types.md`), estructura de `AGENTS.md`, README de specs, `tasks.md` y `test-plan.md` de `02-product-types` (TC-PTY-08a a 08c hechos) y `MEMORY.md` | Todas | — | `ruff check`, `ruff format --check` y `pytest --cov=app --cov-fail-under=90` en verde; TC-USR-16d en verde con los 5 endpoints nuevos; los diagramas coinciden con el código (ver discrepancias en el PR del plan); TC-PRD-06d registrado como pendiente de `04-tickets` |

Notas para la implementación:

- TC-PRD-06b (el repositorio no tiene métodos de borrado) y TC-PRD-06c (ninguna ruta de `/products` acepta `DELETE`) pasan sin fase roja propia: son tests de protección contra un borrado físico futuro, igual que TC-USR-10b y 10c. Se escriben en su task igual.
- TC-PTY-08b tiene que fallar si se quita `passive_deletes="all"` de `ProductType.products` (la causa deja de ser `FOREIGN KEY`). Probarlo quitando la línea antes de cerrar T-PRD-10.
- T-PRD-21 cambia el protocolo `ProductTypeRepository`: `FakeProductTypeRepository.has_products` responde con `bool(product_type.products)`, que `back_populates` mantiene en objetos transitorios.

Notas de la implementación (2026-11-10):

- Pasaron sin fase roja propia, como se esperaba: TC-PRD-06b y 06c (protección), TC-PRD-13b (el caso permitido) y TC-PRD-21a y 21b (el orden ya lo daba T-PRD-06 y el fake ordena igual). TC-PRD-12a también pasó en verde de entrada: la versión mínima de `update_product` ya buscaba el tipo antes de asignar.
- TC-PTY-08b falla si se quita `passive_deletes="all"` de `ProductType.products` (la causa pasa a ser `NOT NULL`), y TC-PRD-07c falla sin el `selectinload`: los dos se probaron quitando la línea.
- La fila `ProductNotFoundError` de `ERROR_RESPONSES` se agregó después de la ruta de `PATCH`, para verla fallar sola (TC-PRD-17d y 17e respondían con la excepción sin traducir).
- TC-PRD-02b y 02c son dos tests y no uno parametrizado, para que cada docstring cite un solo caso.

Pendiente fuera de esta área: SPEC-PRD-06 (TC-PRD-06d) se completa en `04-tickets`, cuando existan los tickets y la asociación con productos.
