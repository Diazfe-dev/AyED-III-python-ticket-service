# 02 — Tipos de producto y rubros · Tasks

Estados: `[ ]` pendiente · `[~]` en curso · `[x]` hecha. Cada task es un ciclo TDD con los casos de [test-plan.md](test-plan.md). La tabla está en orden de ejecución: dominio → repositorios → service → contrato y controllers → cierre.

T-PTY-01 es un refactor sin cambio de comportamiento: no tiene fase roja propia, y se considera terminado cuando toda la suite existente sigue en verde. Va en un commit `refactor(...)` aparte, sin mezclarlo con comportamiento nuevo.

T-PTY-30 a 33 se agregaron el 2026-11-10 al sincronizar el plan con SPEC-PTY-19 y 20 (los IDs no se renumeran): figuran en la tabla en su lugar de ejecución.

Las tasks de endpoints (T-PTY-21 a 28) agregan la operación a `docs/openapi.json` y la ruta en el mismo ciclo: en la fase roja fallan el test del endpoint y TC-PLT-14b, y en la verde pasan los dos (ver [plan.md](plan.md#decisiones-técnicas)). Cada una suma su endpoint a la lista parametrizada de TC-PTY-11a y 11b cuando es de escritura.

| Estado | ID | Task | Specs | Capa | Terminado cuando |
|--------|----|------|-------|------|------------------|
| [x] | T-PTY-01 | Refactor: extraer `REQUIRED`, `INVALID`, `text_error`, `raise_if_invalid` y `provided` de `user_service.py` a `app/services/validation.py`, y mover `CommitSpy` a `tests/unit/fakes.py` | — (USR-05, 22, 25 sin cambios) | Services / tests | `pytest` completo en verde sin cambiar ningún assert; `ruff` limpio |
| [x] | T-PTY-02 | `normalize_name` y `Category` mapeada con `name` recortado y `name_key` completada por `@validates("name")` | PTY-01, 02, 19 | Dominio | TC-PTY-02a, 02b y 19a en verde |
| [x] | T-PTY-03 | `ProductType` mapeado: FK `category_id` `ON DELETE RESTRICT`, `UNIQUE (category_id, name_key)`, relaciones `category` / `product_types` con `back_populates`, `order_by` y `passive_deletes="all"` | PTY-03, 05, 19 | Dominio | TC-PTY-03b y 19b en verde |
| [x] | T-PTY-04 | `SqlAlchemyCategoryRepository` con `add` y `get`. Fixtures `make_category` y `make_product_type` en `conftest.py` | PTY-01 | Repositories / tests | TC-PTY-01b en verde |
| [x] | T-PTY-05 | `UNIQUE` en `name_key`; `add` hace `flush()` y traduce `IntegrityError` a `DuplicateCategoryError` (nueva en `errors.py`); `find_by_name` por clave normalizada | PTY-02 | Repositories / Dominio | TC-PTY-02e, 02f y 02g en verde |
| [x] | T-PTY-06 | `CategoryRepository.list_all` ordenado por `name_key` e `id` | PTY-17 | Repositories | TC-PTY-17a en verde |
| [x] | T-PTY-07 | `CategoryRepository.has_product_types` y `delete` (`session.delete` + `flush`, `IntegrityError` → `CategoryInUseError`, nueva en `errors.py`) | PTY-13, 14 | Repositories / Dominio | TC-PTY-13c, 14b, 14c y 14d en verde |
| [x] | T-PTY-08 | `CategoryRepository.list_with_product_types` con `selectinload` y orden por nombre | PTY-09 | Repositories | TC-PTY-09b y 09c en verde |
| [x] | T-PTY-09 | `SqlAlchemyProductTypeRepository` con `add` (`flush` + `IntegrityError` → `DuplicateProductTypeError`, nueva en `errors.py`), `get` y `find_by_name_in_category` | PTY-03, 05 | Repositories / Dominio | TC-PTY-03c, 05c y 05d en verde |
| [x] | T-PTY-10 | `ProductTypeRepository.delete` (`session.delete` + `flush`) | PTY-07 | Repositories | TC-PTY-07c en verde |
| [x] | T-PTY-33 | `SQLITE_MAX_INTEGER` y `fits_integer_column` en `app/db.py`; los `get` de los dos repositorios devuelven `None` para un id fuera de rango | PTY-06, 18 | App / Repositories | TC-PTY-06g y 18d en verde |
| [x] | T-PTY-11 | `CatalogService.create_category`, caso feliz. Fakes en `tests/unit/catalog/fakes.py` | PTY-01 | Services / tests | TC-PTY-01a en verde |
| [x] | T-PTY-12 | Validación del nombre en `create_category` con `ValidationError(fields)` | PTY-15 | Services | TC-PTY-15a y 15b en verde |
| [x] | T-PTY-13 | Verificación de categoría duplicada antes de insertar (sin distinguir mayúsculas) | PTY-02 | Services | TC-PTY-02c en verde |
| [x] | T-PTY-14 | `CatalogService.update_category`: renombrar, propio nombre permitido, `CategoryNotFoundError` (nueva en `errors.py`), duplicado y validación del nombre, sin modificar ni hacer commit ante un rechazo | PTY-02, 12, 15 | Services / Dominio | TC-PTY-02d, 12a, 12b, 12c y 15c en verde |
| [x] | T-PTY-15 | `CatalogService.delete_category`: baja sin tipos y rechazo con tipos | PTY-13, 14 | Services | TC-PTY-13a, 13b y 14a en verde |
| [x] | T-PTY-16 | `CatalogService.list_categories` | PTY-17 | Services | TC-PTY-17b en verde |
| [x] | T-PTY-17 | `CatalogService.create_product_type`: caso feliz, validación del nombre, categoría inexistente y duplicado en la misma categoría | PTY-03, 04, 05, 15 | Services | TC-PTY-03a, 04a, 05a, 05b y 15d en verde |
| [x] | T-PTY-30 | `id_error` y `parse_id` en `app/services/validation.py`; `create_product_type` valida el `category_id` (ausente → `required`, mal formado → `invalid`) junto con el nombre | PTY-20 | Services | TC-PTY-20a, 20b y 20c en verde |
| [x] | T-PTY-18 | `CatalogService.update_product_type`: nombre y categoría, propio nombre permitido, `ProductTypeNotFoundError` (nueva en `errors.py`), categoría de destino inexistente, duplicado en la categoría de destino y validación del nombre, sin modificar ni hacer commit ante un rechazo | PTY-06, 15, 16 | Services / Dominio | TC-PTY-06a, 06b, 06c, 06d, 15e, 16a, 16b y 16c en verde |
| [x] | T-PTY-31 | `update_product_type` valida el formato del `category_id` presente | PTY-20 | Services | TC-PTY-20d en verde |
| [x] | T-PTY-19 | `CatalogService.delete_product_type` | PTY-07 | Services | TC-PTY-07a y 07b en verde |
| [x] | T-PTY-20 | `CatalogService.list_product_types` con y sin `category_id`, y `CategoryNotFoundError` para una categoría inexistente | PTY-09, 10, 18 | Services | TC-PTY-09a, 10a y 18a en verde |
| [x] | T-PTY-32 | `list_product_types` valida el formato del `category_id` | PTY-20 | Services | TC-PTY-20e en verde |
| [x] | T-PTY-21 | `app/wiring.py` (`get_catalog_service`), blueprint `catalog` registrado en `create_app`, serializador `category_json`, filas nuevas en `ERROR_RESPONSES`. Contrato (tag `catalog`, esquemas `Category` y `CategoryRequest`) + `POST /categories` | PTY-01, 02, 11, 15, 19 | App / Contrato / Controllers | TC-PTY-01c, 02h, 15f, 19c, TC-PTY-11a y 11b para `POST /categories`, TC-PLT-14a y 14b en verde |
| [x] | T-PTY-22 | Contrato + `GET /categories` | PTY-17 | Contrato / Controllers | TC-PTY-17c, TC-PLT-14a y 14b en verde |
| [x] | T-PTY-23 | Contrato + `PATCH /categories/{category_id}` | PTY-02, 11, 12, 15 | Contrato / Controllers | TC-PTY-02i, 12d, 12e, 15g, TC-PTY-11a y 11b para este endpoint, TC-PLT-14a y 14b en verde |
| [x] | T-PTY-24 | Contrato + `DELETE /categories/{category_id}` | PTY-11, 13, 14 | Contrato / Controllers | TC-PTY-13d, 13e, 14e, TC-PTY-11a y 11b para este endpoint, TC-PLT-14a y 14b en verde |
| [x] | T-PTY-25 | Contrato (esquemas `ProductType` y `CreateProductTypeRequest`) + `POST /product-types`; serializador `product_type_json` | PTY-03, 04, 05, 11, 15, 20 | Contrato / Controllers | TC-PTY-03d, 04c, 05e, 15h, 20f, TC-PTY-11a y 11b para este endpoint, TC-PLT-14a y 14b en verde |
| [x] | T-PTY-26 | Contrato (esquema `UpdateProductTypeRequest`) + `PATCH /product-types/{product_type_id}` | PTY-06, 11, 15, 16, 19, 20 | Contrato / Controllers | TC-PTY-06e, 06f, 15i, 16d, 16e, 19d, 20g, TC-PTY-11a y 11b para este endpoint, TC-PLT-14a y 14b en verde |
| [x] | T-PTY-27 | Contrato + `DELETE /product-types/{product_type_id}` | PTY-07, 11 | Contrato / Controllers | TC-PTY-07d, 07e, TC-PTY-11a y 11b (los 6 endpoints de escritura), TC-PLT-14a y 14b en verde |
| [x] | T-PTY-28 | Contrato (esquema `CategoryWithProductTypes`) + `GET /product-types` con y sin `category_id`; serializador `category_group_json` | PTY-09, 10, 18, 20 | Contrato / Controllers | TC-PTY-09d, 10b, 18c, 18e, 20h, TC-PLT-14a y 14b en verde |
| [x] | T-PTY-29 | Cierre del área: `ruff`, cobertura ≥ 90 %, test de guarda, diagramas sincronizados, README de specs y `MEMORY.md` actualizados | Todas | — | `ruff check`, `ruff format --check` y `pytest --cov=app --cov-fail-under=90` en verde; TC-USR-16d en verde con los 8 endpoints nuevos; `diagrams/classes.md` y `diagrams/sequences/02-product-types.md` coinciden con el código (ver discrepancias en el PR del plan) |

Notas de la implementación (2026-11-10):

- TC-PTY-07d verifica la baja con `GET /product-types`, que llega en T-PTY-28: quedó en rojo al terminar T-PTY-27 y pasó a verde con T-PTY-28. Las dos tasks se cerraron juntas.
- Las filas de `ERROR_RESPONSES` se agregaron en la task del primer endpoint que necesitaba cada una (T-PTY-21, 23, 24, 25 y 26), no todas en T-PTY-21, para que cada fila nazca con un test en rojo.
- TC-PTY-14d pasó sin fase roja propia: la FK `ON DELETE RESTRICT` ya existía desde T-PTY-03. TC-PTY-14c se reforzó para exigir que el rechazo venga de la FK (`FOREIGN KEY` en la causa) y no del `NOT NULL` que aparece sin `passive_deletes="all"`.

Pendiente fuera de esta área: SPEC-PTY-08 (TC-PTY-08a a 08c) se implementa en `03-products`, junto con `Product`, `ProductTypeRepository.has_products` y `ProductTypeInUseError`.
