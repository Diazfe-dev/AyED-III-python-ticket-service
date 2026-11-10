# 03 — Productos · Plan de implementación

Specs cubiertas: SPEC-PRD-01 a SPEC-PRD-21 ([spec.md](spec.md)) y SPEC-PTY-08 de [02-product-types](../02-product-types/spec.md) (decisión 4 de la spec). RNF: 2 (autenticación y permisos), 5 (conservación del historial, parcial) y 7 (API documentada). SPEC-PRD-06 se verifica completa en `04-tickets` (decisión 5 de la spec).

## Enfoque

Tercera área de negocio. Agrega la entidad `Product` (último nivel de la jerarquía `Category` → `ProductType` → `Product`), el caso de uso `ProductService` (alta, modificación, baja lógica y listados), un repositorio sobre SQLAlchemy y 5 endpoints JSON en el blueprint `catalog`. Además completa SPEC-PTY-08: la baja de un tipo con productos se rechaza en el service y en la base.

Se monta sobre lo que ya construyeron `01-users` y `02-product-types`, sin reinventar nada:

- Dominio: el mixin `CatalogName` (`name` recortado y `name_key = normalize_name(name)`), el patrón FK `ON DELETE RESTRICT` + `passive_deletes="all"` y el método `deactivate()` de `User` como modelo de la baja lógica.
- Services: `text_error`, `id_error`, `parse_id`, `provided` y `raise_if_invalid` de `app/services/validation.py`, el `commit` inyectado y el orden de validación de `CatalogService` (formato → existencia → duplicado, todo antes de asignar).
- Repositories: `flush` + traducción de `IntegrityError`, `fits_integer_column` en los `get`, `selectinload` en los listados y `SqlAlchemyProductTypeRepository.get` / `SqlAlchemyCategoryRepository.get` para validar referencias.
- App y controllers: `app/wiring.py`, `login_required` y `admin_required`, `ERROR_RESPONSES`, `json_body()`, `category_json` y `product_type_json`.
- Tests: los fixtures `make_category`, `make_product_type`, `admin_client` y `login_as`, los fakes de `tests/unit/catalog/fakes.py`, `CommitSpy`, el contador de sentencias de TC-PTY-09c, el test de guarda TC-USR-16d y el de sincronización con el contrato (SPEC-PLT-14).

## Componentes por capa

| Capa | Archivo | Responsabilidad | Specs |
|------|---------|-----------------|-------|
| Dominio | `app/domain/products.py` | `Product(CatalogName, Base)` mapeado: `name` y `name_key` del mixin, `product_type_id` (FK `RESTRICT`), `is_active` y `deactivate()`. `Product.product_type` y la nueva `ProductType.products` con `back_populates` | PRD-01, 05, 13, 14, 18, PTY-08 |
| Dominio | `app/domain/errors.py` | Nuevas subclases de `DomainError`: `ProductNotFoundError`, `DuplicateProductError` y `ProductTypeInUseError` | PRD-13, 17, PTY-08 |
| Services | `app/services/product_service.py` | `ProductService(products, product_types, categories, commit)`: `create_product`, `update_product`, `deactivate_product`, `list_products` y `list_available_products`. Protocolo `ProductRepository`; reutiliza los protocolos `ProductTypeRepository` y `CategoryRepository` de `catalog_service.py`. Valida el nombre y el formato de los ids, verifica referencias y duplicados antes de asignar, y llama a `commit` una vez por operación exitosa | PRD-01 a 05, 07, 08, 10 a 21 |
| Services | `app/services/catalog_service.py` | El protocolo `ProductTypeRepository` suma `has_products`; `delete_product_type` lanza `ProductTypeInUseError` si el tipo tiene productos | PTY-08 |
| Repositories | `app/repositories/product_repository.py` | `SqlAlchemyProductRepository(session)`: `add`, `get`, `find_by_name_in_type` y `list_matching`. `add` traduce `IntegrityError` a `DuplicateProductError`; `get` devuelve `None` para un id fuera del rango de `INTEGER`; `list_matching(category_id, product_type_id, active_only)` filtra, ordena por `name_key` e `id`, y carga tipo y categoría con `selectinload`. Sin métodos de borrado | PRD-01, 06, 07, 08, 10, 13, 17, 20, 21 |
| Repositories | `app/repositories/product_type_repository.py` | Suma `has_products(product_type_id)` (consulta `exists`, cuenta activos e inactivos); `delete` traduce `IntegrityError` a `ProductTypeInUseError` | PTY-08 |
| App | `app/wiring.py` | Suma `get_product_service()`: arma el service del request con `get_session()` y los tres repositorios | — |
| Controllers | `app/controllers/catalog.py` | Los 5 endpoints de productos en el blueprint `catalog` existente (el `CatalogController` del diagrama) | PRD-01 a 05, 07 a 21 |
| Controllers | `app/controllers/serializers.py` | Suma `product_json` (reutiliza `product_type_json` y `category_json`) | PRD-07 |
| Controllers | `app/controllers/errors.py` | Suma 3 filas a `ERROR_RESPONSES` (ver cuerpos de error) | PRD-13, 17, PTY-08 |
| Contrato | `docs/openapi.json` | Las 5 operaciones nuevas con el tag `catalog`, los esquemas `Product`, `CreateProductRequest` y `UpdateProductRequest`, las respuestas `ProductNotFound`, `DuplicateProduct` y `ProductTypeInUse`, y el `409` en `DELETE /product-types/{product_type_id}` | RNF 7 |

## Modelo de datos

Tabla `products`:

| Columna | Tipo | Restricciones | Notas |
|---------|------|---------------|-------|
| `id` | `Integer` | PK | |
| `name` | `String(120)` | `NOT NULL` | Del mixin `CatalogName`: sin espacios en los extremos (SPEC-PRD-14) |
| `name_key` | `String(120)` | `NOT NULL` | Del mixin: `strip().casefold()`. La completa el `@validates("name")` |
| `product_type_id` | `Integer` | `NOT NULL`, FK `product_types.id` `ON DELETE RESTRICT`, índice | Red de seguridad de SPEC-PTY-08 en la base |
| `is_active` | `Boolean` | `NOT NULL`, `default=True` | Baja lógica (SPEC-PRD-05) |
| — | — | `UNIQUE (product_type_id, name_key)` (`uq_products_type_name`) | SPEC-PRD-13 en la base |

Relaciones:

- `Product.product_type`: `relationship(back_populates="products")`, muchos a uno.
- `ProductType.products`: `relationship(back_populates="product_type", passive_deletes="all")`. Sin `cascade="delete"` ni `delete-orphan`: borrar un tipo nunca borra sus productos. `passive_deletes="all"` evita que el ORM ponga `product_type_id` en `NULL` antes del `DELETE`, así el rechazo lo decide la FK `RESTRICT` y no un `NOT NULL` (mismo riesgo que TC-PTY-14c).

La categoría de un producto no se guarda en `products`: se obtiene por `product.product_type.category`. La tabla de asociación con tickets (`ticket_products`) llega en `04-tickets`.

## Interfaz HTTP

Todas las respuestas son JSON. Representación:

- `Product`: `{"id", "name", "is_active", "product_type": ProductType, "category": Category}`, donde `ProductType` es `{"id", "name", "category_id"}` y `Category` es `{"id", "name"}` (los esquemas de `02-product-types`).

| Método y ruta | Acceso | Éxito | Errores | Specs |
|---------------|--------|-------|---------|-------|
| `GET /products` | sesión | `200` lista de `Product` (activos e inactivos) ordenada por nombre | `401` | PRD-07, 21 |
| `GET /products?category_id={id}&product_type_id={id}` | sesión | `200` lista de `Product` que cumplen todos los filtros presentes | `400` (`category_id` o `product_type_id` mal formado), `401`, `404` `category_not_found` o `product_type_not_found` | PRD-08, 15, 16, 20, 21 |
| `GET /products/available` | sesión | `200` lista de `Product` activos ordenada por nombre | `401` | PRD-10, 21 |
| `POST /products` | admin | `201` `Product` | `400`, `401`, `403`, `404` `product_type_not_found`, `409` `duplicate_product` | PRD-01, 02, 03, 09, 11, 13, 14, 15 |
| `PATCH /products/{product_id}` | admin | `200` `Product` | `400`, `401`, `403`, `404` `product_not_found` o `product_type_not_found`, `409` `duplicate_product` | PRD-04, 09, 11, 12, 13, 14, 15, 17, 19 |
| `POST /products/{product_id}/deactivate` | admin | `200` `Product` con `is_active: false` | `401`, `403`, `404` `product_not_found` | PRD-05, 06, 09, 17, 18 |
| `DELETE /product-types/{product_type_id}` (existente) | admin | `204` | suma `409` `product_type_in_use` | PTY-08 |

Cuerpos de error (`{"error": "<código>"}`); los de `401`, `403`, `category_not_found` y `product_type_not_found` ya existen:

| Excepción u origen | Status | Cuerpo |
|--------------------|--------|--------|
| `ValidationError` | `400` | `{"error": "validation_error", "fields": {"name": "required" \| "invalid", "product_type_id": "required" \| "invalid", "category_id": "invalid"}}` (solo los campos con error) |
| `ProductNotFoundError` | `404` | `{"error": "product_not_found"}` |
| `DuplicateProductError` | `409` | `{"error": "duplicate_product"}` |
| `ProductTypeInUseError` | `409` | `{"error": "product_type_in_use"}` (el código es el motivo que pide SPEC-PTY-08) |

## Patrones aplicados

- **Capas Controller → Service → Repository**: el controller lee el JSON o el query string, llama al service y serializa. Las reglas (nombre válido, ids bien formados, tipo existente, unicidad por tipo, filtros existentes) están en el service.
- **Baja lógica en el dominio**: `Product.deactivate()` pone `is_active = False`, igual que `User.deactivate()`. No hay camino de borrado físico (SPEC-PRD-05 y 06).
- **Registro en lugar de condicionales**: las 3 excepciones nuevas se suman a `ERROR_RESPONSES`; no hay `if` por tipo de error.
- **Inyección de dependencias por constructor**: `ProductService` recibe sus tres repositorios y la función `commit`. Los tests unitarios usan fakes en memoria.
- **Repository**: el service nunca toca la `Session`. El repositorio hace `flush` y traduce las violaciones de la base a errores de dominio.

## Decisiones técnicas

| Decisión | Motivo |
|----------|--------|
| Un `ProductService` propio, separado de `CatalogService` | Lo pide el diagrama de capas (`ProductService` con `ProductRepository` y `ProductTypeRepository`). `CatalogService` ya tiene 8 casos de uso de categorías y tipos; sumarle 5 de productos lo convertiría en un service con dos responsabilidades. Se descartó extender `CatalogService`. El controller sigue siendo uno solo (`catalog.py`), como en el diagrama. |
| `ProductService` recibe también un `CategoryRepository` | SPEC-PRD-16 pide `404` para un filtro por categoría inexistente, y solo el repositorio de categorías sabe si existe. Se descartaron devolver una lista vacía (viola PRD-16) y agregar a `ProductTypeRepository` una consulta sobre categorías (mezcla responsabilidades). **Discrepancia con el diagrama de capas**, que no tiene esa flecha. |
| `Product` usa el mixin `CatalogName` | SPEC-PRD-13 y 14 son las mismas reglas que PTY-05 y 19: nombre recortado y unicidad sin distinguir mayúsculas por `casefold()` (el `lower()` de SQLite solo convierte ASCII). Reutilizar el mixin evita duplicar el `@validates`. Se descartó un índice sobre `func.lower(name)` por el mismo motivo que en `02-product-types`. |
| La unicidad es por tipo: `UNIQUE (product_type_id, name_key)`, y el service busca el duplicado con `find_by_name_in_type(name, product_type_id)` antes de insertar | Es lo que dice SPEC-PRD-13 ("en el mismo tipo de producto"). El mismo nombre en otro tipo está permitido. El chequeo del service da el error con su motivo; el `UNIQUE` protege ante una carrera, y `add` traduce su `IntegrityError` a `DuplicateProductError`. |
| La unicidad cuenta productos activos e inactivos | Un producto inactivo sigue existiendo y apareciendo en los tickets (decisión 1 de la spec); dos productos con el mismo nombre en el mismo tipo serían indistinguibles en un ticket. Es el mismo criterio que el email de un usuario inactivo (SPEC-USR-04). Se descartó liberar el nombre al dar de baja. |
| El service crea el producto con `is_active=True` explícito, y la columna además tiene `default=True` | El `default` de columna solo se aplica al insertar: en un objeto transitorio vale `None` (errores a evitar de `MEMORY.md`), y el test unitario con fakes verifica el estado antes de cualquier flush. Así lo muestra también el diagrama de secuencia 1. El `default` cubre a quien cree un `Product` sin pasar por el service (fixtures). |
| Validación con los códigos de `01-users` y `02-product-types`: nombre ausente, `null`, vacío o solo espacios → `required`; nombre que no es texto → `invalid`; `product_type_id` ausente o `null` en el alta → `required`; `product_type_id` que no es un entero positivo → `invalid` (`id_error`) | SPEC-PRD-03, 11 y 15. Es la regla de SPEC-PTY-20 y de la decisión (a) del 2026-11-10 de `MEMORY.md`: se acepta un entero JSON mayor que 0 o un texto de dígitos ASCII; se rechazan `true`/`false`, decimales, negativos, `0`, texto vacío, textos de más de 4300 dígitos y cualquier otro tipo. En el alta, nombre y `product_type_id` se validan juntos y se informan los dos. Se descartó tratar un `product_type_id` ausente como tipo inexistente (`404`): no identifica nada, igual que con `category_id`. |
| Orden en `create_product`: formato del nombre y del `product_type_id` (`400`) → existencia del tipo (`404`) → duplicado (`409`). En `update_product`: existencia del producto (`404`) → formato de los campos presentes (`400`) → tipo de destino (`404`) → duplicado con el nombre final en el tipo final (`409`) → asignar | Mismo orden que `CatalogService`. Todo se verifica antes de asignar, así un rechazo no deja el producto modificado ni dispara un `autoflush` con datos inválidos. El duplicado con nombre y tipo finales cubre los dos casos de PRD-13 en la modificación: renombrar al nombre de un hermano y mover a un tipo que ya tiene ese nombre. Renombrar a su propio nombre con otras mayúsculas está permitido (el dueño del nombre se ignora). |
| `PATCH` con semántica parcial: un campo ausente o `null` no se modifica; el controller solo pasa `name` y `product_type_id` e ignora las demás claves (incluida `is_active`) | Misma regla que `PATCH /users/{id}` y `PATCH /product-types/{id}`. `is_active` solo cambia con la baja; ninguna spec define una reactivación. |
| Un producto inactivo se puede modificar (`PATCH`) y sigue inactivo | SPEC-PRD-19. Corregir el nombre de un producto que figura en tickets viejos es razonable. Se descartó rechazarlo con un `409`. |
| Dar de baja un producto que ya está inactivo responde `200` y lo deja inactivo (idempotente), con un `commit` sin cambios | SPEC-PRD-18. Es lo que hace hoy `deactivate_user` con un usuario inactivo. Se descartó un `409` `product_already_inactive`. |
| `deactivate_product` devuelve el `Product` y el endpoint responde `200` con su representación | Igual que `POST /users/{id}/deactivate` (`200` con `is_active: false`). El diagrama de capas dice que devuelve `None`; con el producto el controller no necesita una segunda consulta. **Discrepancia menor con el diagrama de capas.** |
| La baja es `POST /products/{product_id}/deactivate`, no `DELETE` | Lo indica el diagrama de secuencia 2. `DELETE` sugiere un borrado físico (mismo criterio que usuarios). |
| Un id de producto inexistente responde `404` `product_not_found` en `PATCH` y en la baja, incluido uno mayor que `2**63 - 1` (`fits_integer_column` en `SqlAlchemyProductRepository.get`) | SPEC-PRD-17 (antes trazado a PRD-04 y 05, como hizo `02-product-types` con PTY-06 y 07). La guarda de rango es obligatoria en todo `get` por id (errores a evitar de `MEMORY.md`): sin ella `sqlite3` lanza `OverflowError` y la respuesta es un `500`. |
| `list_products(category_id=None, product_type_id=None)`: valida el formato de los dos filtros presentes (`400`, se informan juntos), después la existencia de la categoría (`404` `category_not_found`) y la del tipo (`404` `product_type_not_found`), y recién entonces consulta | SPEC-PRD-08, 15 y 16. Un `?category_id=` vacío es `invalid`; sin el parámetro no se filtra (decisión (a) de `02-product-types`). Los parámetros desconocidos se ignoran. |
| Con los dos filtros a la vez se devuelven los productos que cumplen ambos (intersección). Si el tipo existe pero no pertenece a la categoría, la respuesta es `200` con una lista vacía | SPEC-PRD-08 y PRD-20. No necesita un error nuevo. Se descartaron un `400` (el pedido es válido) y un `404` (las dos entidades existen). |
| El filtro por categoría se resuelve con un `join` sobre `Product.product_type` (`ProductType.category_id == :id`); `products` no guarda `category_id` | Un `category_id` copiado en `products` podría desincronizarse al mover un tipo de categoría (SPEC-PTY-06). Con el `join`, mover un tipo mueve también sus productos en los listados. Se descartó desnormalizar. |
| `ProductRepository.list_matching(category_id=None, product_type_id=None, active_only=False)` en lugar de `list(filters)` del diagrama | Un método llamado `list` dentro de la clase tapa al tipo `list` en las anotaciones de los métodos siguientes del cuerpo de la clase (Python 3.12 evalúa las anotaciones al definir la función): `-> list[Product]` fallaría al importar. Los parámetros con nombre son más claros que un diccionario `filters`. Mismo estilo que `list_all` y `list_with_product_types`. **Discrepancia con el diagrama de capas.** |
| Listados sin N+1: `select(Product).options(selectinload(Product.product_type).selectinload(ProductType.category))`, como máximo 3 consultas sin importar cuántos productos haya | Lo pide AGENTS.md. Cada `Product` se serializa con su tipo y su categoría (SPEC-PRD-07), así que sin la carga anticipada habría una consulta por producto. Un test cuenta las sentencias con el mismo listener que TC-PTY-09c. Se descartó `joinedload` para seguir la convención de AGENTS.md. |
| Orden de los listados: por `name_key` y después por `id` | SPEC-PRD-21 (orden alfabético). Ordenar por la clave normalizada es lo que hacen los listados del catálogo (SPEC-PTY-17) y el `id` como desempate hace que los tests sean determinísticos (dos productos de tipos distintos pueden llamarse igual). |
| `GET /products` incluye los productos inactivos; `GET /products/available` devuelve solo los activos y no acepta filtros | SPEC-PRD-07 pide el estado de cada producto, lo que solo tiene sentido si aparecen los inactivos (mismo criterio que los listados de usuarios). SPEC-PRD-10 no pide filtros para los disponibles; sus parámetros se ignoran. Las dos rutas solo piden sesión (decisión 3 de la spec). |
| `GET /products/available` no choca con `/products/{product_id}` | Las rutas con id usan el conversor `<int:product_id>`, que no acepta `available`, y no existe un `GET /products/{product_id}` (ninguna spec lo pide). |
| La baja de un tipo con productos se rechaza dos veces: en `CatalogService.delete_product_type` con `has_products(product_type_id)` (una consulta `exists` que cuenta activos e inactivos) y en la base con la FK `products.product_type_id` `ON DELETE RESTRICT`. `ProductTypeRepository.delete` hace `flush` y traduce el `IntegrityError` a `ProductTypeInUseError` | Es el diseño que dejó planificado `02-product-types` (decisión 3 de su spec y `MEMORY.md`), espejo de SPEC-PTY-14. El chequeo del service es la regla de negocio y da el motivo; la FK protege ante una carrera o un camino que no pase por el service. `CatalogService` no necesita una dependencia nueva: `has_products` vive en el repositorio de tipos que ya recibe. |
| Los casos de SPEC-PTY-08 conservan sus IDs (TC-PTY-08a a 08c, en el [test-plan de 02](../02-product-types/test-plan.md)) y se implementan con tasks `T-PRD-*`. Se suma TC-PTY-08d para `has_products`, documentado en el [test-plan](test-plan.md) de esta área | Los IDs de casos no se reutilizan ni se renumeran. TC-PTY-08c no distingue si el `409` lo dio el service o la FK, así que `has_products` necesita un caso propio en el repositorio (como TC-PTY-14b). |
| `get_product_service()` en `app/wiring.py` | Mismo motivo que `get_catalog_service()`: los controllers no pueden usar la `Session`. |
| Cada task de endpoint agrega la operación a `docs/openapi.json` **y** la ruta en el mismo ciclo TDD, y las filas de `ERROR_RESPONSES` nacen en la task del primer endpoint que las necesita | En la fase roja fallan el test del endpoint y TC-PLT-14b; en la verde pasan los dos. Cada fila de la tabla de errores nace con un test en rojo (decisión (d) de `02-product-types`). El JSON se edita cargándolo y reescribiéndolo, nunca pegando texto. |
| `count_statements` pasa de `test_category_repository.py` a un módulo compartido `tests/integration/catalog/queries.py` (refactor sin cambio de comportamiento, T-PRD-01) | TC-PRD-07c necesita el mismo contador que TC-PTY-09c; importar desde otro módulo de tests acopla los archivos de test. |
| Sin reloj inyectable en esta área | Ninguna spec de productos registra fechas. |

## Huecos de la spec

Los huecos detectados al planificar se resolvieron al aprobar el plan (decisión 6 de la spec, 2026-11-10):

1. **Baja de un producto ya inactivo**: SPEC-PRD-18 (`200` idempotente).
2. **Modificación de un producto inactivo**: SPEC-PRD-19 (se permite y sigue inactivo).
3. **Reactivación**: fuera de alcance, ningún RF la pide. `PATCH` ignora `is_active`.
4. **Los dos filtros a la vez con un tipo que no pertenece a la categoría**: SPEC-PRD-20 (`200` con lista vacía).
5. **Producto inexistente**: SPEC-PRD-17 (`404` `product_not_found`, también para un id fuera de rango).
6. **Orden de los listados de productos**: SPEC-PRD-21 (alfabético, por `name_key` e `id`).

## Dependencias con otras áreas

- Usa de `00-platform`: `create_app`, `get_session()`, `Base`, `create_schema`, `fits_integer_column`, el contrato `docs/openapi.json` y su test de sincronización (SPEC-PLT-14).
- Usa de `01-users`: `login_required`, `admin_required`, `ERROR_RESPONSES`, `json_body()`, `ValidationError(fields)`, los fixtures `schema`, `db_session`, `make_user`, `login_as` y `admin_client`, `CommitSpy` y el test de guarda TC-USR-16d, que cubre los 5 endpoints nuevos sin cambios.
- Usa de `02-product-types`: `CatalogName`, `normalize_name`, `ProductType`, `Category`, `SqlAlchemyProductTypeRepository.get`, `SqlAlchemyCategoryRepository.get`, los protocolos de `catalog_service.py`, `id_error` y `parse_id`, `product_type_json`, `category_json`, los fixtures `make_category` y `make_product_type`, los fakes de `tests/unit/catalog/fakes.py` y el contador de sentencias de TC-PTY-09c. Completa SPEC-PTY-08 (TC-PTY-08a a 08c).
- `04-tickets` usa `Product`, la regla "un producto inactivo no se asocia a tickets nuevos" (SPEC-TKT-08) y suma `ProductRepository.get_many(product_ids)` (está en el diagrama de capas, pero ninguna spec de esta área lo necesita). Ahí se completa TC-PRD-06d.

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Sin `passive_deletes="all"` en `ProductType.products`, el ORM pone `product_type_id` en `NULL` antes del `DELETE`; el `IntegrityError` de `NOT NULL` también se traduciría a `ProductTypeInUseError` y el test pasaría sin que la FK funcione | `passive_deletes="all"` en la relación y TC-PTY-08b exige `FOREIGN KEY` en la causa del error, igual que TC-PTY-14c. Probarlo quitando la línea que protege. |
| Un `has_products` roto que siempre devuelve `False` pasa desapercibido, porque la FK igual produce el `409` | TC-PTY-08d prueba `has_products` directo sobre el repositorio, con un producto inactivo. |
| El `autoflush` manda a la base un nombre duplicado antes del chequeo del service | El service valida y busca duplicados **antes** de asignar, igual que `update_product_type`. |
| `add` traduce cualquier `IntegrityError` a `DuplicateProductError`, también una FK a un tipo borrado en paralelo | El service ya verificó el tipo en la misma transacción; mismo riesgo aceptado en `02-product-types`. |
| Una consulta N+1 en el listado pasa desapercibida con pocos datos | TC-PRD-07c cuenta las sentencias con 2 categorías, 3 tipos y 2 productos por tipo, recorre tipo y categoría de cada producto y exige como máximo 3. |
| Un id enorme en la ruta, en el cuerpo o en el query string produce un `OverflowError` y un `500` | `fits_integer_column` en `SqlAlchemyProductRepository.get` (TC-PRD-17c) y las guardas existentes de los repositorios de tipos y categorías; TC-PRD-02c, 16d, 17e y 17f lo prueban por HTTP. |
| Olvidar `admin_required` en un endpoint de escritura o `login_required` en uno de lectura | TC-USR-16d recorre `app.url_map` (`401`), y TC-PRD-09a y 09b parametrizan los 3 endpoints de escritura con un `Representative` y un `Client`. |
| SPEC-PRD-06 queda sin el caso completo al cerrar el área | Documentado en la decisión 5 de la spec, en este plan y en el test-plan como pendiente de `04-tickets` (TC-PRD-06d), igual que TC-USR-10d. El cierre del área (T-PRD-28) lo registra en `MEMORY.md`. |
