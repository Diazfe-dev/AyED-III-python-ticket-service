# 02 — Tipos de producto y rubros · Plan de implementación

Specs cubiertas: SPEC-PTY-01 a SPEC-PTY-24 ([spec.md](spec.md)). SPEC-PTY-09 está reemplazada por SPEC-PTY-22 (2026-11-12, mismo comportamiento sin `q`). RNF: 2 (autenticación y permisos), 7 (API documentada) y 10 (estos listados **no** se paginan, SPEC-PTY-24). SPEC-PTY-08 se verifica completa en `03-products` (decisión 3 de la spec).

> **Re-sincronización del 2026-11-12** (nueva área [07-ui](../07-ui/spec.md)): búsqueda `q` en `GET /categories` y `GET /product-types`, sin paginación. Ver [Búsqueda por nombre](#búsqueda-por-nombre-2026-11-12) y las tasks T-PTY-34 a 41. Las secciones anteriores describen el diseño original; donde algo cambió, manda la sección nueva.

## Enfoque

Segunda área de negocio. Agrega las entidades `Category` (rubro) y `ProductType`, el caso de uso `CatalogService` (ABM de categorías y de tipos, y sus listados), dos repositorios sobre SQLAlchemy y el blueprint `catalog` con 8 endpoints JSON. Se monta sobre lo que ya construyó `01-users`: `login_required` y `admin_required`, la tabla excepción → HTTP de `app/controllers/errors.py`, `json_body()` de `app/controllers/serializers.py`, `ValidationError(fields)`, el `commit` inyectado, el patrón `flush` + traducción de `IntegrityError` en el repositorio, los fixtures de `tests/conftest.py`, el test de guarda de rutas (TC-USR-16d) y el test de sincronización con el contrato (SPEC-PLT-14).

La entidad `Product` **no** se crea en esta área: es de `03-products`. Ver la decisión sobre SPEC-PTY-07 y 08.

## Componentes por capa

| Capa | Archivo | Responsabilidad | Specs |
|------|---------|-----------------|-------|
| Dominio | `app/domain/products.py` | `normalize_name(name)` (`strip().casefold()`). `Category` y `ProductType` mapeadas, cada una con `name` (recortado por un `@validates("name")`) y la columna de búsqueda `name_key`, que completa el mismo validador. `Category.product_types` y `ProductType.category` con `back_populates`. `Product` se agrega a este archivo en `03-products` | PTY-01, 02, 03, 05, 19 |
| Dominio | `app/domain/errors.py` | Nuevas subclases de `DomainError`: `CategoryNotFoundError`, `ProductTypeNotFoundError`, `DuplicateCategoryError`, `DuplicateProductTypeError` y `CategoryInUseError` | PTY-02, 04, 05, 06, 12, 13, 14, 16, 18 |
| Services | `app/services/validation.py` | Helpers de validación extraídos de `user_service.py` sin cambiar su comportamiento: `REQUIRED`, `INVALID`, `text_error(value)`, `raise_if_invalid(errors)` y `provided(**values)`. Los usan `UserService` y `CatalogService`. Suma `id_error(value)` y `parse_id(value)` para identificadores que llegan del JSON o del query string (SPEC-PTY-20); `03-products` los reutiliza para `product_type_id` | PTY-15, 20 (y USR-05, 22, 25 sin cambios) |
| Services | `app/services/catalog_service.py` | `CatalogService(category_repository, product_type_repository, commit)`: `create_category`, `update_category`, `delete_category`, `list_categories`, `create_product_type`, `update_product_type`, `delete_product_type` y `list_product_types`. Protocolos `CategoryRepository` y `ProductTypeRepository`. Valida el nombre y el formato del `category_id`, verifica duplicados y categorías antes de asignar, y llama a `commit` una vez por operación exitosa | PTY-01 a 07, 09, 10, 12 a 20 |
| Repositories | `app/repositories/category_repository.py` | `SqlAlchemyCategoryRepository(session)`: `add`, `get`, `find_by_name`, `list_all`, `list_with_product_types`, `has_product_types` y `delete`. `add` traduce `IntegrityError` a `DuplicateCategoryError`; `delete` traduce `IntegrityError` a `CategoryInUseError`; `get` devuelve `None` para un id fuera del rango de `INTEGER` de SQLite | PTY-01, 02, 09, 12, 13, 14, 17, 18 |
| Repositories | `app/repositories/product_type_repository.py` | `SqlAlchemyProductTypeRepository(session)`: `add`, `get`, `find_by_name_in_category` y `delete`. `add` traduce `IntegrityError` a `DuplicateProductTypeError`; `get` con el mismo rango que `categories`. `03-products` le agrega `has_products` | PTY-03, 05, 06, 07, 16 |
| App | `app/wiring.py` | `get_catalog_service()`: arma el service del request con `get_session()` y los dos repositorios | — |
| App | `app/db.py` | Suma `SQLITE_MAX_INTEGER` y `fits_integer_column(value)`, que usan los `get` de los repositorios del catálogo | PTY-06, 18 |
| Controllers | `app/controllers/catalog.py` | Blueprint `catalog` (el `CatalogController` del diagrama): los 8 endpoints de la interfaz HTTP | PTY-01 a 07, 09 a 20 |
| Controllers | `app/controllers/serializers.py` | Suma `category_json`, `product_type_json` y `category_group_json` | PTY-09, 10, 17 |
| Controllers | `app/controllers/errors.py` | Suma 5 filas a `ERROR_RESPONSES` (ver cuerpos de error) | PTY-02, 04, 05, 12, 13, 14, 16, 18 |
| App | `app/__init__.py` | Registra el blueprint `catalog` | — |
| Contrato | `docs/openapi.json` | Las 8 operaciones nuevas con el tag `catalog` y los esquemas `Category`, `CategoryRequest`, `ProductType`, `CreateProductTypeRequest`, `UpdateProductTypeRequest` y `CategoryWithProductTypes` | RNF 7 |

## Modelo de datos

Tabla `categories`:

| Columna | Tipo | Restricciones | Notas |
|---------|------|---------------|-------|
| `id` | `Integer` | PK | |
| `name` | `String(120)` | `NOT NULL` | Nombre para mostrar, sin espacios alrededor (`strip()`), con las mayúsculas que eligió el admin |
| `name_key` | `String(120)` | `NOT NULL`, `UNIQUE` | `normalize_name(name)`: `strip().casefold()`. La completa el `@validates("name")`; nadie la asigna a mano |

Tabla `product_types`:

| Columna | Tipo | Restricciones | Notas |
|---------|------|---------------|-------|
| `id` | `Integer` | PK | |
| `name` | `String(120)` | `NOT NULL` | Igual que en `categories` |
| `name_key` | `String(120)` | `NOT NULL` | Igual que en `categories` |
| `category_id` | `Integer` | `NOT NULL`, FK `categories.id` `ON DELETE RESTRICT`, índice | Red de seguridad de SPEC-PTY-14 en la base |
| — | — | `UNIQUE (category_id, name_key)` (`uq_product_types_category_name`) | SPEC-PTY-05 y 16 en la base |

Relaciones:

- `ProductType.category`: `relationship(back_populates="product_types")`, muchos a uno.
- `Category.product_types`: `relationship(back_populates="category", order_by=(ProductType.name_key, ProductType.id), passive_deletes="all")`. Sin `cascade="delete"` ni `delete-orphan`: borrar una categoría nunca borra sus tipos. `passive_deletes="all"` evita que el ORM intente poner `category_id` en `NULL` al borrar la categoría, así el rechazo lo decide la FK `RESTRICT` y no un `NOT NULL`.

`03-products` agrega la tabla `products` con `product_type_id` FK `product_types.id` `ON DELETE RESTRICT` y la relación `ProductType.products`.

## Interfaz HTTP

Todas las respuestas son JSON. Representaciones:

- `Category`: `{"id", "name"}`.
- `ProductType`: `{"id", "name", "category_id"}`.
- `CategoryWithProductTypes`: `{"id", "name", "product_types": [ProductType, ...]}`.

| Método y ruta | Acceso | Éxito | Errores | Specs |
|---------------|--------|-------|---------|-------|
| `GET /categories` | sesión | `200` lista de `Category` ordenada por nombre | `401` | PTY-17 |
| `POST /categories` | admin | `201` `Category` | `400`, `401`, `403`, `409` `duplicate_category` | PTY-01, 02, 11, 15, 19 |
| `PATCH /categories/{category_id}` | admin | `200` `Category` | `400`, `401`, `403`, `404` `category_not_found`, `409` `duplicate_category` | PTY-02, 11, 12, 15 |
| `DELETE /categories/{category_id}` | admin | `204` sin cuerpo | `401`, `403`, `404` `category_not_found`, `409` `category_in_use` | PTY-11, 13, 14 |
| `GET /product-types` | sesión | `200` lista de `CategoryWithProductTypes`: todas las categorías (también las que no tienen tipos), ordenadas por nombre, con sus tipos ordenados por nombre | `401` | PTY-09 |
| `GET /product-types?category_id={id}` | sesión | `200` lista con un solo `CategoryWithProductTypes`: el de esa categoría | `400` (`category_id` mal formado), `401`, `404` `category_not_found` | PTY-10, 18, 20 |
| `POST /product-types` | admin | `201` `ProductType` | `400`, `401`, `403`, `404` `category_not_found`, `409` `duplicate_product_type` | PTY-03, 04, 05, 11, 15, 19, 20 |
| `PATCH /product-types/{product_type_id}` | admin | `200` `ProductType` | `400`, `401`, `403`, `404` `product_type_not_found` o `category_not_found`, `409` `duplicate_product_type` | PTY-06, 11, 15, 16, 19, 20 |
| `DELETE /product-types/{product_type_id}` | admin | `204` sin cuerpo | `401`, `403`, `404` `product_type_not_found` (`409` `product_type_in_use` en `03-products`) | PTY-07, 08, 11 |

Cuerpos de error (`{"error": "<código>"}`); los de `401` y `403` ya existen:

| Excepción u origen | Status | Cuerpo |
|--------------------|--------|--------|
| `ValidationError` | `400` | `{"error": "validation_error", "fields": {"name": "required" \| "invalid", "category_id": "required" \| "invalid"}}` (solo los campos con error) |
| `login_required` sin sesión | `401` | `{"error": "authentication_required"}` |
| `admin_required` sin rol `Admin` | `403` | `{"error": "forbidden"}` |
| `CategoryNotFoundError` | `404` | `{"error": "category_not_found"}` |
| `ProductTypeNotFoundError` | `404` | `{"error": "product_type_not_found"}` |
| `DuplicateCategoryError` | `409` | `{"error": "duplicate_category"}` |
| `DuplicateProductTypeError` | `409` | `{"error": "duplicate_product_type"}` |
| `CategoryInUseError` | `409` | `{"error": "category_in_use"}` (el código es el motivo que pide SPEC-PTY-14) |

## Patrones aplicados

- **Capas Controller → Service → Repository**: el controller lee el JSON o el query string, llama al service y serializa. Las reglas (nombre válido, unicidad, categoría existente, categoría en uso) están en el service.
- **Agregado con colección ordenada**: `Category.product_types` ya viene ordenada, así que el listado agrupado (SPEC-PTY-09) es "categorías con sus tipos" y no hace falta agrupar a mano.
- **Registro en lugar de condicionales**: las 5 excepciones nuevas se suman a la tabla `ERROR_RESPONSES`; no hay `if` por tipo de error.
- **Inyección de dependencias por constructor**: `CatalogService` recibe los dos repositorios y la función `commit`. Los tests unitarios usan fakes en memoria.
- **Repository**: el service nunca toca la `Session`. Los repositorios hacen `flush` y traducen las violaciones de la base a errores de dominio, igual que `SqlAlchemyUserRepository`.

## Decisiones técnicas

| Decisión | Motivo |
|----------|--------|
| Unicidad sin distinguir mayúsculas con una columna `name_key = name.strip().casefold()` y `UNIQUE` sobre ella (o sobre `(category_id, name_key)`). El `@validates("name")` del dominio la completa | SQLite solo pasa a minúsculas los caracteres ASCII, tanto en `lower()` como en `COLLATE NOCASE`: `"ÁUDIO"` y `"áudio"` serían distintos para un índice `func.lower(name)` y el chequeo del service (en Python) diría otra cosa que la base. `casefold()` resuelve acentos y la `ñ`, y el service y la base comparan exactamente el mismo valor. Es el mismo criterio que el email normalizado de `01-users`, pero en una columna aparte para conservar el nombre como lo escribió el admin. Se descartaron un índice único sobre `func.lower(name)` y `COLLATE NOCASE` (solo ASCII), y guardar el nombre ya en minúsculas (se pierde el nombre para mostrar). **A revisar por el equipo.** |
| Los nombres de tipos de producto también se comparan sin distinguir mayúsculas, dentro de su categoría | SPEC-PTY-05 dice "mismo nombre" sin aclarar; tener dos criterios distintos en el mismo catálogo confunde ("Notebook" y "notebook" en el mismo rubro). Se descartó la comparación exacta. **Aprobada el 2026-11-10**: SPEC-PTY-05 y 16 ya lo dicen. |
| El nombre se guarda sin espacios alrededor (`strip()`); los espacios internos no se tocan. Lo recorta el `@validates("name")` del dominio, así vale para cualquier camino que asigne el nombre | `" Hardware "` y `"Hardware"` cuentan como el mismo nombre para la unicidad, así que guardar la versión recortada evita nombres que parecen iguales en los listados. Se descartó guardar el valor tal como llega (lo que hace `UserService` con el nombre de usuario), porque en el catálogo el nombre es la clave de negocio. **Aprobada el 2026-11-10 como SPEC-PTY-19.** |
| Renombrar una categoría o un tipo a su propio nombre (con otras mayúsculas) está permitido | El duplicado se busca por `name_key` y se ignora si quien lo tiene es la misma entidad, igual que el propio email en `update_user`. Sirve para corregir mayúsculas (`"hardware"` → `"Hardware"`). |
| Validación del nombre con los mismos códigos de `01-users`: ausente, `null`, vacío o solo espacios → `required`; un valor que no es texto → `invalid` | SPEC-PTY-15 pide indicar que el nombre es inválido; los dos códigos ya existen en la API y en `ValidationError(fields)`. Se extraen `text_error`, `raise_if_invalid` y `provided` a `app/services/validation.py` en un refactor previo (T-PTY-01), sin cambiar el comportamiento de usuarios. Se descartaron duplicar las funciones privadas de `user_service.py` y un código nuevo `invalid` para todo (rompería la coherencia con `01-users`). |
| `PATCH` con semántica parcial: un campo ausente o `null` no se modifica (`name`, y `category_id` en tipos) | Misma regla que `PATCH /users/{id}` (decisión del 2026-11-10). El controller solo pasa las claves admitidas e ignora las demás. |
| ~~Un `category_id` que no es un entero (ausente, `null`, `true`, `1.5`, `"abc"`, `"-1"`) se trata como una categoría inexistente: `404` `category_not_found` en `POST /product-types` (SPEC-PTY-04), en `PATCH /product-types/{id}` con `category_id` presente (SPEC-PTY-16) y en `GET /product-types?category_id=` (SPEC-PTY-18). Un entero JSON o un texto de dígitos ASCII se acepta. `bool` se rechaza aunque en Python sea `int` | Ninguna spec define un `400` para el id de la categoría, y un id que no es entero no identifica a ninguna categoría existente, así que el comportamiento queda trazado a specs ya aprobadas. El service convierte el valor con un helper `_parse_id` (el query string llega como texto). Se descartó un `400` con `fields.category_id` porque sería comportamiento sin spec. **A revisar por el equipo** (ver huecos de la spec).~~ **Reemplazada el 2026-11-10** por la fila siguiente (SPEC-PTY-20). |
| Un `category_id` que no es un entero positivo es un error de validación: `400` con `fields.category_id: "invalid"` en `POST /product-types`, en `PATCH /product-types/{id}` con `category_id` presente y en `GET /product-types?category_id=` (SPEC-PTY-20). Se acepta un entero JSON mayor que 0 o un texto de dígitos ASCII que represente un número mayor que 0; se rechazan `true`/`false` (aunque en Python sean `int`), decimales, negativos, `0`, texto vacío y cualquier otro tipo. Un texto de más dígitos de los que Python convierte a `int` (4300 por defecto) también es `invalid`: sin esa regla, `int()` lanza `ValueError` y la respuesta es un `500`. En `POST /product-types` un `category_id` ausente o `null` es `required` (`400`), igual que el nombre, y los dos campos se validan juntos. En `PATCH` ausente o `null` no modifica (decisión de `PATCH` parcial). Un `?category_id=` vacío es `invalid`; sin el parámetro, el listado es completo. Un id bien formado que no existe sigue siendo `404` `category_not_found` (SPEC-PTY-04, 16 y 18) | Un id mal formado no identifica nada: es un error del cliente igual que un nombre que no es texto (SPEC-PTY-15, USR-25), y `400` con el campo le dice qué corregir. Los helpers `id_error` y `parse_id` viven en `services/validation.py` para que `03-products` los use con `product_type_id`. El texto de dígitos se acepta porque el query string llega siempre como texto; se descartó que el service distinga el origen del valor (JSON o query string), que solo agregaría un parámetro. Se descartó el `404` de la fila anterior (decisión 4 de la spec). |
| Un id entero que no entra en el `INTEGER` de SQLite (mayor que `2**63 - 1`) cuenta como inexistente: los `get` de los repositorios del catálogo devuelven `None` sin consultar la base | Sin esta guarda, `sqlite3` lanza `OverflowError` al enlazar el parámetro y la respuesta es un `500`, tanto con `?category_id=` como con un id en la ruta (`<int:...>` de Flask no tiene límite). Es una restricción del motor, así que vive en la capa de persistencia (`fits_integer_column` en `app/db.py`) y no en el service. Para el cliente el id es válido y no existe: `404` (SPEC-PTY-06, 12, 13 y 18). `01-users` tiene el mismo problema en `PATCH /users/{id}` y queda fuera de esta área (ver Engram `tp-final/pitfall/sqlite-overflow-id-grande`). |
| En `POST /product-types` primero se validan el nombre y el formato del `category_id` (`400`), después la existencia de la categoría (`404`) y por último el duplicado (`409`). En `PATCH` primero se busca el tipo (`404`), después se validan los campos presentes, después la categoría de destino y por último el duplicado | Mismo orden que `01-users`: `_get_existing` y la validación de formato antes de cualquier regla que consulte la base. Todo se verifica antes de asignar, así un rechazo no deja la entidad modificada ni dispara un `autoflush` con datos inválidos. |
| Al mover un tipo de categoría, el duplicado se busca en la categoría de destino con el nombre final (el nuevo si viene, o el actual) | Cubre los dos casos de SPEC-PTY-16: mover un tipo a una categoría que ya tiene uno con ese nombre y renombrarlo al nombre de un hermano. |
| Endpoints: `GET`/`POST /categories`, `PATCH`/`DELETE /categories/{category_id}`, `GET`/`POST /product-types` y `PATCH`/`DELETE /product-types/{product_type_id}` | Siguen los métodos de `CatalogController` del diagrama de capas más `list_categories` (SPEC-PTY-17). La baja usa `DELETE` y responde `204` porque es física (decisión 1 de la spec): categorías y tipos no tienen historial. La modificación usa `PATCH` (el diagrama de secuencia 1 dice `PUT`) por coherencia con `PATCH /users/{id}` y porque los campos son opcionales. |
| `GET /product-types` responde siempre una lista de grupos `CategoryWithProductTypes`. Sin filtro trae todas las categorías, también las vacías; con `category_id` trae solo el grupo de esa categoría | Una sola forma de respuesta para el endpoint: un solo esquema en el contrato y un solo serializador. Se descartó devolver una lista plana de tipos cuando hay filtro (el contrato necesitaría un `oneOf` y el cliente dos parsers). Las categorías vacías aparecen porque el listado sirve para clasificar (RF 1.2.2) y una categoría recién creada tiene que verse. **Aprobada el 2026-11-10**: SPEC-PTY-09 lo dice. |
| Orden de los listados: categorías por `name_key` y después por `id`; tipos dentro de cada grupo por `name_key` y después por `id` | SPEC-PTY-17 pide "ordenadas por nombre"; ordenar por la clave normalizada evita que `"Zeta"` quede antes que `"audio"` por el orden de bytes. El `id` como desempate hace que los tests sean determinísticos. |
| Listado agrupado sin N+1: `CategoryRepository.list_with_product_types()` hace `select(Category).options(selectinload(Category.product_types)).order_by(...)`: 2 consultas sin importar cuántas categorías haya | Lo pide AGENTS.md para los listados. Se descartó el enfoque del diagrama de secuencia 4 (`ProductTypeRepository.list_all()` con `selectinload(category)` y agrupar en el service), porque deja afuera a las categorías vacías y obliga a escribir el agrupamiento a mano. Un test cuenta las sentencias SQL con un listener `before_cursor_execute` del engine. |
| La baja de una categoría con tipos se rechaza dos veces: en el service con `has_product_types(category_id)` (una consulta `exists`) y en la base con la FK `ON DELETE RESTRICT`. `CategoryRepository.delete` hace `session.delete` + `flush` y traduce el `IntegrityError` a `CategoryInUseError` | El chequeo del service es la regla de negocio (SPEC-PTY-14) y produce el error con su motivo. La FK protege contra una carrera o contra un camino que no pase por el service (decisión 3 de la spec). El diagrama de secuencia 3 usa `count_children` y devuelve un número; alcanza con saber si hay alguno. |
| Errores con una clase por caso (`CategoryInUseError`, y `ProductTypeInUseError` en `03-products`) en lugar del `EntityInUseError` genérico del diagrama de secuencia 3 | La tabla de `errors.py` resuelve el código a partir de la clase; con una sola clase haría falta llevar el código en `details`. |
| SPEC-PTY-07 se verifica ahora; SPEC-PTY-08 queda pendiente completa para `03-products` | Sin la entidad `Product`, todo tipo de producto cumple "sin productos asociados", así que SPEC-PTY-07 se prueba entera en esta área. SPEC-PTY-08 no tiene nada verificable sin productos: escribir hoy un `has_products` que devuelva siempre `False`, o un `ProductTypeInUseError` que nadie lanza, sería código sin comportamiento real. En `03-products` se agregan `ProductTypeRepository.has_products(product_type_id)` (consulta `exists` sobre `products`, que cuenta activos e inactivos), el chequeo en `delete_product_type`, `ProductTypeInUseError` → `409` `product_type_in_use`, la FK `products.product_type_id` `ON DELETE RESTRICT` con su traducción en `ProductTypeRepository.delete`, y los casos TC-PTY-08a a 08c, que ya figuran en el [test-plan](test-plan.md) como pendientes. Mismo criterio que TC-USR-10d. Se descartó planificar en `02` un protocolo `ProductCounter` inyectado en `CatalogService`: el diagrama de capas no lo tiene y no habría una implementación real que inyectar. |
| `get_catalog_service()` vive en un módulo nuevo `app/wiring.py` | Los controllers no pueden usar la `Session` (prohibición de AGENTS.md), así que alguien fuera de `controllers/` tiene que armar el service con `get_session()`. `app/auth.py` arma `UserService` porque lo necesita para `current_user()`; sumarle el catálogo mezclaría responsabilidades. Se descartaron armar el service dentro de `controllers/catalog.py` (usaría `get_session()`) y ponerlo en `app/auth.py`. `get_user_service()` se queda donde está para no tocar `01-users`. |
| Cada task de endpoint agrega la operación a `docs/openapi.json` **y** la ruta en el mismo ciclo TDD | Igual que en `01-users`: el test de SPEC-PLT-14 falla si el contrato y `app.url_map` difieren en cualquiera de los dos sentidos. En la fase roja fallan el test del endpoint y TC-PLT-14b; en la verde pasan los dos. El JSON se edita cargándolo y reescribiéndolo, nunca pegando texto (errores a evitar en Engram, `tp-final/pitfall/*`). |
| Sin reloj inyectable en esta área | Ninguna spec del catálogo registra fechas. |

## Búsqueda por nombre (2026-11-12)

### Componentes por capa (cambios)

| Capa | Archivo | Cambio | Specs |
|------|---------|--------|-------|
| Repositories | `app/repositories/category_repository.py` | `list_all(q=None)`: con `q`, filtra `name_key` que contiene `q.casefold()` (`autoescape`); mismo orden `name_key`, `id` | PTY-21 |
| Repositories | `app/repositories/product_type_repository.py` | `search(q, category_id=None) -> list[ProductType]`: tipos cuyo `name_key` contiene `q.casefold()`, opcionalmente de una categoría, con `selectinload(ProductType.category)` y orden `Category.name_key`, `Category.id`, `ProductType.name_key`, `ProductType.id` | PTY-23 |
| Services | `app/services/catalog_service.py` | `CategoryGroup(category, product_types)` (dataclass congelada). `list_categories(q=None)`; `list_product_types(category_id=None, q=None) -> list[CategoryGroup]`: sin `q`, los grupos salen de `list_with_product_types()` o de la categoría pedida (como hoy); con `q`, de agrupar `search(...)` por categoría. Los protocolos suman `q` y `search` | PTY-10, 21, 22, 23 |
| Controllers | `app/controllers/catalog.py` | `GET /categories` y `GET /product-types` pasan `request.args.get("q")`; no leen `page` ni `page_size` | PTY-21, 23, 24 |
| Controllers | `app/controllers/serializers.py` | `category_group_json(group)` recibe el `CategoryGroup` (mismo JSON que hoy) | PTY-22, 23 |
| Contrato | `docs/openapi.json` | Parámetro `Q` (de 00) en las dos operaciones; la descripción aclara que no se paginan | RNF 7, PTY-24 |

Sin cambios en el modelo de datos: `name_key` ya guarda `casefold()` del nombre.

### Decisiones técnicas

| Decisión | Motivo y alternativas descartadas |
|----------|-----------------------------------|
| `q` se compara contra `name_key` con `q.casefold()` | La columna ya existe para la unicidad sin distinguir mayúsculas (incluidas las no ASCII, TC-PTY-02a); no hace falta la función SQL `casefold` de 01. `contains(..., autoescape=True)` busca `%` y `_` literales. |
| Con `q`, el listado de tipos se arma desde `ProductTypeRepository.search` y el service agrupa por categoría en un `CategoryGroup`, en lugar de cargar `Category.product_types` con criterio (`selectinload(Category.product_types.and_(...))`) | Una colección cargada con criterio deja objetos `Category` con `product_types` parcial en el identity map de la sesión: otro acceso en el mismo request vería datos falsos, y los fakes no pueden imitarlo sin mutar las colecciones. Agrupar en el service es explícito y los fakes lo reproducen con una lista. Costo: un refactor previo (T-PTY-37) para que el service devuelva siempre grupos y el serializador los reciba. |
| El refactor T-PTY-37 va separado y antes del comportamiento nuevo | Cambia el tipo que devuelve `list_product_types` sin cambiar el JSON; aislarlo deja ver que la suite sigue en verde antes de agregar `q` (mismo criterio que T-PTY-01 y T-PRD-01). |
| Con `category_id` y `q`, primero el formato (`400`) y la existencia de la categoría (`404`), después la búsqueda; una categoría sin coincidencias da `[]` | SPEC-PTY-23 omite las categorías sin coincidencias "con o sin filtro de categoría"; SPEC-PTY-18 y 20 siguen rigiendo para el `category_id`. Mismo orden que hoy. |
| `q` busca solo en el nombre del tipo, no en el de la categoría | SPEC-PTY-23: "tipos cuyo nombre contiene ese texto". TC-PTY-23e. |
| `page` y `page_size` no se leen en estos endpoints | SPEC-PTY-24 y la decisión 6 (del usuario): se ignoran, sin `400` ni objeto paginado. |
| SPEC-PTY-09 → 22 se resuelve re-trazando los docstrings (T-PTY-34), sin código | Es el mismo comportamiento acotado a "sin `q`". Los IDs TC-PTY-09a a 09d quedan en el test-plan como registro y sus tests pasan a citar TC-PTY-22a a 22d. |

### Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Un N+1 al recorrer la categoría de cada tipo buscado | `selectinload(ProductType.category)`; TC-PTY-23c cuenta como máximo 2 sentencias. |
| El refactor de `CategoryGroup` cambia el JSON de `GET /product-types` sin que se note | TC-PTY-22d (antes 09d) y 10b comparan el cuerpo completo y siguen en verde sin cambios. |
| Un `page_size` inválido termina en `400` por reutilizar el helper de paginación por error | TC-PTY-24a y 24b. |

## Dependencias con otras áreas

- Usa de `00-platform`: `create_app`, `get_session()`, `Base`, `create_schema`, el contrato `docs/openapi.json` y su test de sincronización (SPEC-PLT-14).
- Usa de `01-users`: `login_required`, `admin_required`, `ERROR_RESPONSES` y `register_error_handlers`, `json_body()`, `ValidationError(fields)`, los helpers de validación (extraídos a `services/validation.py`), los fixtures `schema`, `db_session`, `make_user`, `login_as` y `admin_client`, `CommitSpy` (movido a `tests/unit/fakes.py`) y el test de guarda TC-USR-16d, que cubre los 8 endpoints nuevos sin cambios.
- `03-products` agrega `Product` a `app/domain/products.py`, la relación `ProductType.products`, `ProductTypeRepository.has_products`, el chequeo en `delete_product_type`, `ProductTypeInUseError` y los casos TC-PTY-08a a 08c. Usa `ProductTypeRepository.get` para validar el tipo de un producto (SPEC-PRD-02).

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Sin `passive_deletes="all"` en `Category.product_types`, el ORM pone `category_id` en `NULL` antes del `DELETE` y el error sería un `NOT NULL` (o, peor, con la columna nullable, dejaría tipos huérfanos) | `passive_deletes="all"` en la relación y TC-PTY-14c, que borra por el repositorio sin pasar por el service y espera `CategoryInUseError` con la categoría y el tipo intactos. |
| El `autoflush` puede mandar a la base un nombre duplicado antes del chequeo del service (por ejemplo, si se asigna el nombre y después se consulta `find_by_name`) | El service valida y busca duplicados **antes** de asignar cualquier atributo, igual que `update_user`. |
| `add` de un tipo traduce cualquier `IntegrityError` a `DuplicateProductTypeError`, también una FK a una categoría borrada en paralelo | El service ya verificó la categoría en la misma transacción; la carrera es muy improbable en el alcance del TP. Se documenta y no se agrega una segunda traducción. |
| `casefold()` y `lower()` difieren en algunos caracteres (`"ß"` → `"ss"`) | Es el comportamiento buscado: dos nombres que solo difieren en eso se consideran iguales. El test con `"ÁUDIO"`/`"áudio"` (TC-PTY-02e) protege que la base y el service usen la misma clave. |
| Una consulta N+1 en el listado agrupado pasa desapercibida con pocos datos | TC-PTY-09c cuenta las sentencias SQL con 3 categorías de 2 tipos cada una y exige como máximo 2. |
| SPEC-PTY-08 queda sin test en verde al cerrar el área | Está documentado en la decisión 3 de la spec, en este plan y en el test-plan como pendiente de `03-products`. El cierre del área (T-PTY-29) lo registra en `MEMORY.md`. |
| Un `category_id` enorme (`?category_id=99999999999999999999`) produce un `OverflowError` de `sqlite3` y un `500` | `fits_integer_column` en los `get` de los repositorios, TC-PTY-06g, 18d y 18e. |
| Olvidar `admin_required` en un endpoint de escritura o `login_required` en uno de lectura | TC-USR-16d recorre `app.url_map` y TC-PTY-11a y 11b parametrizan los 6 endpoints de escritura con un `Representative` y un `Client`. |
