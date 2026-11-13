# 07 — Interfaz web · Plan de implementación

Specs cubiertas: SPEC-UI-01 a SPEC-UI-136 ([spec.md](spec.md)), con las decisiones 1 a 65. RF 1.7.1 a 1.7.6. RNF: 2 (sesión por cookie, sin secretos ni identidad en el navegador, texto de la API como texto), 7 (las rutas de la UI quedan fuera del contrato, SPEC-PLT-23), 8 (front plano servido por Flask, mismo origen, sin build), 9 (pruebas de JavaScript con `node --test`, suite de Playwright y prueba de trazabilidad) y 10 (listados paginados con `page_size` 20).

> **Estado**: plan derivado el 2026-11-12 de la spec validada y re-sincronizado el mismo día con la octava ronda (SPEC-UI-135 y 136, decisiones 57 a 61) y con las decisiones 62 a 65 (definición de «reemplazó», falla de conexión, instancia de pantalla y sus pruebas). No hay código del front todavía. El desglose está en [tasks.md](tasks.md) (39 tasks, T-UI-01 a T-UI-39; T-UI-39 va después de T-UI-12 en el orden de lectura) y los casos en [test-plan.md](test-plan.md) (270 casos: 15 `pytest`, 85 `node --test`, 170 Playwright). Los huecos G-01 a G-06 están **resueltos** con las decisiones del usuario (ver [Huecos y preguntas](#huecos-y-preguntas-abiertas)); no queda ninguna decisión pendiente.

## Enfoque

Área sin dominio, services, repositorios ni tablas nuevas. Todo lo que la interfaz consume ya está especificado en 00 a 05 (re-sincronizados el 2026-11-12) y se implementa en sus tasks: esta área solo depende de ellas. Lo que agrega:

- **Controllers**: un blueprint `ui` con `GET /` que devuelve `app/static/index.html` (mismo patrón que `api_docs.py`: `Response(bytes, mimetype="text/html")`). `GET /static/<path:filename>` ya lo registra `Flask(__name__)` y sus `404` ya salen en JSON por `HTTP_ERROR_RESPONSES` (SPEC-PLT-15).
- **Front plano** en `app/static/`: un `index.html`, una hoja `css/app.css` y módulos ES en `js/`, separados en cuatro grupos: `core/` (puros: sin DOM ni red), `net/` (cliente de la API con `fetch` inyectado), `dom/` (ayudas de dibujo y controles) y `screens/` (una pantalla por archivo). `js/app.js` es el único punto que toca `window`, `document`, `location`, `history` y `fetch` globales para conectarlos.
- **Máquina de estados de la sesión** pura (`core/session.js`): concentra la carga inicial, el login, la sesión abierta, el cierre y la sesión vencida (SPEC-UI-07 a 12, 116 a 118, 124, 126 a 134), con la matriz de las decisiones 41 a 58. Se prueba entera con `node --test`.
- **Token de pedido y de pantalla** puro (`core/requests.js`, misma familia que la época de sesión): con la sesión abierta descarta la respuesta (o la falla de conexión) de una lectura reemplazada por otra más nueva de los mismos datos en la misma pantalla (SPEC-UI-135) o de un pedido de una instancia de pantalla que ya no es la vigente (SPEC-UI-136), sin descartar nunca un `401` y sin que las escrituras ni los pedidos de recursos distintos se reemplacen entre sí (decisiones 57, 62 a 64). Se prueba con `node --test` y con Playwright.
- **Herramientas de prueba**: `package.json` sin `dependencies` (solo `@playwright/test` en `devDependencies`), `playwright.config.js`, un servidor de Flask para Playwright (`tests/ui/e2e/server.py`), la prueba de trazabilidad (`tests/ui/test_traceability.py`) y el CI (`.github/workflows/ci.yml`, que no existe).

Lo que **no** hace esta área: reglas de negocio (permisos, propiedad y transiciones son de la API, decisión 1), métricas, tableros ni listado de notificaciones (decisión 3), y cambios en la API (decisión 4: están en 00 a 05).

## Arquitectura del front

```
app/
  controllers/ui.py            # blueprint "ui": GET / → index.html (text/html)
  static/
    index.html                 # lang="es", <title>, regiones fijas, <script type="module" src="/static/js/app.js">
    css/app.css                # diseño adaptable (360 px), foco visible, contraste ≥ 4,5:1, sin fuentes externas
    js/
      app.js                   # entrada: conecta window/document/location/history/fetch con la máquina y las pantallas
      core/                    # PUROS (SPEC-UI-73): sin fetch, document ni window; importables con node --test
        routes.js              # tabla de rutas, clasificación del hash con y sin sesión, inicio y navegación por rol
        session.js             # máquina de estados de sesión, carga, login, cierre y vencimiento (reductor puro)
        requests.js            # instancia de pantalla y clave de recurso por lectura: descarta respuestas reemplazadas o de otra instancia (135, 136)
        query.js               # armado de consultas de listado (filtros, q, order, page, page_size=20) y paginación
        messages.js            # traducción de errores de la API a mensajes (tabla de mensajes, 57, 58, 59, 119)
        labels.js              # etiquetas de estados, roles y estado de cuenta (96, 123)
        dates.js               # formato dd/mm/aaaa HH:mm en la zona del navegador (29)
        ticket-actions.js      # acciones de ticket por rol y por las tres reglas de estado (21, 35, 40, 41, 77 a 80)
        forms.js               # comparación de contraseña y confirmación (14, 100)
      net/
        api-client.js          # createApiClient(fetchFn, ...): rutas relativas, cookie, sin Authorization (60, 75)
      dom/
        render.js              # el(): solo textContent; regiones aria-live; indicador de carga; «No hay resultados»; título
        shell.js               # cabecera y navegación por rol, «Cerrar sesión»
        inert.js               # pantalla inerte mientras POST /logout está pendiente (133, 134)
        listing.js             # controlador de listados paginables: filtros, q, orden, página, recarga (120, 125)
        paginator.js           # controles «Anterior» / «Siguiente», número de página y total (101 a 106)
        confirm.js             # confirmación con <dialog> nativo para «Eliminar» (54)
      screens/
        index.js               # registro pantalla → módulo
        boot.js, login.js, not-found.js, account.js,
        tickets-list.js, ticket-detail.js, ticket-new.js,
        users.js, categories.js, product-types.js, products.js
```

Reglas de la estructura:

- **Puros contra impuros** (SPEC-UI-73 y 74): `core/` no nombra `fetch`, `document` ni `window` (ni como identificador suelto) y solo importa de `core/`. `net/api-client.js` no usa el `fetch` global: lo recibe por parámetro (SPEC-UI-75) y por eso también se importa desde `node --test`. `dom/` y `screens/` usan el DOM y reciben el cliente de la API por parámetro. Solo `app.js` liga `window.fetch` y los eventos globales.
- **Texto siempre como texto** (SPEC-UI-63): `dom/render.js` expone `el(tag, attrs, children)`, que crea nodos con `textContent` y atributos con `setAttribute` sobre una lista blanca. Ningún archivo del front usa `innerHTML`, `outerHTML`, `insertAdjacentHTML` ni `document.write` (lo controla el escaneo estático).
- **Sin estilos ni scripts en línea** (SPEC-UI-65): ni `<script>` sin `src`, ni atributos `on*=`, ni atributos `style`; la apariencia se cambia con clases. Así la página funciona con `default-src 'self'` sin `'unsafe-inline'`.
- **Sin orígenes externos** (SPEC-UI-05 y 06): rutas de la forma `/me`, `/static/...`; nada de `http://`, `https://` ni `//host`; fuentes del sistema (sin `@font-face` ni `@import` remotos).
- **Sin almacenamiento** (SPEC-UI-62): el rol y la identidad viven solo en el estado de la máquina (memoria). Ningún archivo nombra `localStorage`, `sessionStorage` ni `document.cookie`.
- **Fechas**: `core/dates.js` usa `Intl.DateTimeFormat` con `hourCycle: "h23"` y arma `dd/mm/aaaa HH:mm` con `formatToParts`; recibe la zona como parámetro opcional (por defecto, la del navegador) para probarla en Node con zonas fijas.

### Cómo sirve Flask la interfaz

| Ruta | Quién la sirve | Respuesta | Specs |
|------|----------------|-----------|-------|
| `GET /` | blueprint `ui` (`app/controllers/ui.py`, registrado en `create_app`) | `200` `text/html` con los bytes de `app/static/index.html` (ruta calculada con `current_app.static_folder`), sin `login_required` | UI-01, PLT-23, USR-49 |
| `GET /static/<path:filename>` | regla `static` que registra `Flask(__name__)` | `200` con el tipo según la extensión (`text/css`, `text/javascript`, `text/html`) | UI-02 |
| `GET /static/<inexistente>`, un directorio (`/static/js/`) o un intento de salir de la carpeta (`/static/../app/__init__.py`) | la misma regla (`send_from_directory` con `safe_join`) | `404` `{"error": "not_found"}` por `HTTP_ERROR_RESPONSES` | UI-03 |

- **Sin listado de directorios**: Flask nunca lista carpetas; `/static/js/` es `404` JSON (TC-UI-03b).
- **Cabeceras de caché**: no se agregan. Los archivos estáticos usan el comportamiento por defecto de Flask (`SEND_FILE_MAX_AGE_DEFAULT = None`: `Cache-Control: no-cache` con `ETag` y `Last-Modified`, el navegador revalida), que sirve para un front sin build ni versiones con hash. `GET /` no lleva validadores. Agregar una política de caché sería comportamiento sin spec.
- **Contrato y guardas**: SPEC-PLT-23 excluye `GET /` y `GET /static/<path:filename>` del contrato (la paridad la reescribe T-PLT-22) y SPEC-USR-49 las nombra públicas (T-USR-54). T-UI-02 agrega TC-PLT-23d y la parte `GET /` y `/static` de TC-USR-49b, que esas áreas dejaron pendientes de 07.

### Máquina de estados de la sesión (`core/session.js`)

Reductor puro: `transition(state, event) → { state, effects }`. No hace pedidos ni toca el DOM: devuelve **efectos** que `app.js` ejecuta (`render(screen, params)`, `replaceHash(hash)`, `request(kind, ...)`, `setInert(bool)`, `showNotice(kind)`). Cada estado lleva un contador `epoch` (época de la sesión) que sube cada vez que la sesión se cierra (SPEC-UI-11 o 12); todo pedido se envía etiquetado con la época vigente y su respuesta llega como evento con esa etiqueta.

Estados (las decisiones 41 y 46 los definen):

| Estado | Significado | Pantalla |
|--------|-------------|----------|
| `mePending{origin}` | `GET /me` pendiente; `origin` es `initial` (carga o su reintento) o `login` (posterior a un inicio de sesión) | indicador de carga (SPEC-UI-71) |
| `meError{origin, error}` | el `GET /me` respondió distinto de `200` y `401` o no hubo conexión | error de SPEC-UI-56, 58 o 59 con «Reintentar» (SPEC-UI-117) |
| `anonymous{notice, loginPending}` | sin sesión abierta; `notice` indica el aviso de SPEC-UI-12 | `#/login` |
| `open{user, route}` | sesión abierta (identidad recibida con `200`, decisión 41) | la pantalla de la ruta |
| `closing{route}` | `POST /logout` pendiente; la identidad ya se descartó (SPEC-UI-11) | la pantalla que se mostraba, inerte (SPEC-UI-131, 133 y 134) |

Matriz de transiciones (el resultado de cada par estado-evento es único, decisiones 41 a 58):

| Evento \ Estado | `mePending{initial}` | `mePending{login}` | `meError{origin}` | `anonymous` | `open` | `closing` |
|---|---|---|---|---|---|---|
| `meAnswered 200 (user, hash actual)` | → `open`; clasifica el hash con el rol: vacío o `#/login` → inicio + `replaceHash(inicio)` (07, 132); permitido → esa pantalla (116); no permitido → inicio + `replaceHash` (19, 132); desconocido o `{id}` inválido → «Página no encontrada» (20, 97) | → `open`; inicio del rol + `replaceHash(inicio)`, sin mirar el hash (09, 127, 132) | — | — | — | — |
| `meAnswered 401` | → `anonymous{notice: false}`; login + `replaceHash("#/login")` (08, 128) | igual (08, 128) | — | — | — | — |
| `meAnswered otro estado` o sin conexión | → `meError{initial}` (117) | → `meError{login}` (117) | — | — | — | — |
| `retryClicked` | — | — | → `mePending{origin}` + `GET /me` (118) | — | — | — |
| `hashChanged(hash)` | sin efectos: se evalúa al responder (127) | sin efectos (127) | sin efectos (127) | si el hash no es `#/login`: login (sin volver a dibujarlo si ya se muestra: conserva el formulario y el `POST /login` pendiente, decisión 58), sin aviso, `replaceHash("#/login")` y sin pedidos (126, 128) | clasifica: vacío o `#/login` → inicio + `replaceHash` (124, 132); no permitido → inicio + `replaceHash` (19, 132); desconocido o `{id}` inválido → «Página no encontrada» sin pedidos (20, 97); permitido → pantalla (04) | sin efectos (131) |
| `loginSubmitted` | — | — | — | `POST /login`; `loginPending` | — | — |
| `loginAnswered 200` | — | — | — | → `mePending{login}` + `GET /me` (09) | — | — |
| `loginAnswered` error | — | — | — | mensaje: `invalid_credentials` (10) o SPEC-UI-56, 58, 59 | — | — |
| `logoutClicked` | — | — | — | — | → `closing{route}`; `epoch + 1`; se descarta la identidad; `POST /logout`; `setInert(true)` (11, 133, 134) | sin efectos (133) |
| `logoutSettled` (cualquier estado o sin conexión) | — | — | — | — | — | → `anonymous{notice: false}`; login + `replaceHash("#/login")`; `setInert(false)` (129, 128) |
| `apiAnswered 401` con la época vigente (no `/login`, `/logout` ni el `GET /me` de carga) | — | — | — | — | → `anonymous{notice: true}`; `epoch + 1`; login con «Tu sesión venció. Inicia sesión nuevamente.» + `replaceHash("#/login")` (12, 128) | — |
| `apiAnswered` con una época vieja (cualquier estado HTTP) | ignorada (130) | ignorada | ignorada | ignorada (sin aviso ni datos) | ignorada | ignorada |
| `apiAnswered` con la época vigente y estado distinto de `401` (o sin conexión) | — | — | — | — | se consulta `core/requests.js`: lectura reemplazada por otra más nueva de los mismos datos en la misma instancia → ignorada (135); de una instancia de pantalla que ya no es la vigente (también si la misma ruta se volvió a mostrar) → ignorada, sin navegar (136); vigente → se entrega a la pantalla | — |
| `controlActivated` (cualquier control de la pantalla) | — | — | — | — | se entrega a la pantalla | sin efectos ni pedidos (133) |

Funciones auxiliares puras: `canSend(state)` (falso en `closing`: el cliente de la API no envía nada, defensa además de la pantalla inerte), `isInert(state)` y `currentUser(state)` (`null` fuera de `open`). La clasificación del hash la hace `core/routes.js` y la máquina solo la consume. `app.js` reemplaza el hash con `history.replaceState(null, "", hash)`, que **no** dispara `hashchange` (evita bucles) y no suma entradas al historial (SPEC-UI-128 y 132).

### Respuestas reemplazadas o de otra pantalla (`core/requests.js`)

Módulo puro de la misma familia que la época de sesión (contadores que solo suben, sin cancelar pedidos), separado de `core/session.js` para que cada spec tenga su archivo de prueba y para que su task corra en paralelo con la cadena de la máquina (SPEC-UI-135 y 136, decisiones 57 y 62 a 64):

- `initialRequests()` → `{ screen: 0, seq: 0, latest: {} }`.
- `openScreen(state)` → estado con `screen + 1` y `latest` vacío. **Instancia de pantalla** (decisión 64): `app.js` lo llama en cada efecto `render(screen, params)` con sesión abierta, es decir, cada vez que se **muestra** una pantalla: al cambiar de ruta (también de `#/tickets/7` a `#/tickets/8`), al mostrar el inicio del rol o «Página no encontrada», y al **volver a la misma ruta** (`#/tickets/new` → `#/account` → `#/tickets/new` son tres instancias). El módulo no conoce rutas: cada llamada abre una instancia nueva aunque la ruta sea la misma. No se llama al volver a pedir datos dentro de la pantalla que ya se muestra (cambio de filtro, `q` o página, recarga tras una acción, SPEC-UI-42, 120 y 125): eso sigue en la misma instancia.
- `issue(state, method, key?)` → `{ state, tag }`, con `tag = { screen, key, seq, write }`:
  - **Escritura** (`method` es `POST`, `PATCH` o `DELETE`): `write: true`; no lee ni escribe `latest`, aunque reciba una clave. Nunca queda reemplazada ni reemplaza a otro pedido (decisión 62); solo puede quedar de una instancia anterior (136).
  - **Lectura** (`GET`) con clave: `latest[key] = seq`. La **clave de recurso** nombra «los mismos datos en la misma pantalla» (decisión 62): un listado o consulta tiene una sola clave sin importar filtros, `q`, orden o página (listado: `list`; selectores y búsquedas: `clients`, `representatives`, `products`, `categories`, `product-types`), y un recurso recargado conserva su clave (detalle: `ticket`, `milestones`, `state-changes`). Claves distintas nunca se reemplazan: los tres `GET` en paralelo de SPEC-UI-27 y 42 llevan `ticket`, `milestones` y `state-changes` y se dibujan todos.
  - **Lectura sin clave**: recibe una clave única y nunca queda reemplazada (comportamiento seguro por defecto).
- `verdict(state, tag, status)` → `"deliver"` o `"ignore"`: `401` → siempre `"deliver"` (lo maneja SPEC-UI-12 en la máquina de sesión); otro estado o falla de conexión (`status: null`, decisión 63) → `"ignore"` si `tag.screen !== state.screen` (136, también para escrituras) o si `!tag.write && latest[tag.key] !== tag.seq` (135); si no, `"deliver"`.

Orden en `app.js` al llegar una respuesta o una falla de conexión: (1) época vieja → ignorada por la máquina (SPEC-UI-130); (2) `401` de la época vigente → sesión vencida con «Tu sesión venció» (SPEC-UI-12), aunque el pedido haya quedado reemplazado o sea de otra instancia; (3) `verdict` → ignorada (135, 136) o entregada a la pantalla. Así una sesión realmente cerrada nunca queda oculta por un pedido viejo, y SPEC-UI-130 no cambia. «Ignorada» significa sin datos, sin mensaje de error (ni el genérico ni el de falta de conexión), sin quitar el indicador de carga del pedido vigente y sin navegar (el salto de SPEC-UI-33 después de salir de `#/tickets/new` no ocurre, tampoco si el usuario ya volvió a `#/tickets/new`).

### Pantallas por rol

| Pantalla (ruta) | Archivo | Roles | Pedidos | Componentes y comportamiento | Specs |
|---|---|---|---|---|---|
| Carga | `screens/boot.js` | todos | `GET /me` | indicador «Cargando…»; error con «Reintentar» | 07, 08, 71, 116 a 118, 127 |
| Inicio de sesión (`#/login`) | `screens/login.js` | sin sesión | `POST /login` | formulario email y contraseña (etiquetados), «Ingresar», mensaje genérico, aviso de sesión vencida; vacía la contraseña tras enviar | 09, 10, 12, 64, 126, 128 |
| Navegación | `dom/shell.js` | con sesión | — | Representante: «Tickets», «Nuevo ticket», «Mi cuenta», «Cerrar sesión»; Administrador: «Usuarios», «Categorías», «Tipos de producto», «Productos», «Tickets», «Mi cuenta», «Cerrar sesión»; Cliente: «Mis tickets», «Mi cuenta», «Cerrar sesión». Enlaces `<a href="#/...">` y un `<button>` para cerrar sesión | 16, 17, 18, 11 |
| Página no encontrada | `screens/not-found.js` | con sesión | ninguno | «Página no encontrada» y un enlace al inicio del rol | 20, 97 |
| Tickets (`#/tickets`) | `screens/tickets-list.js` | los tres | `GET /tickets`; selectores `GET /clients` (Representante y Administrador) y `GET /representatives` (Administrador), sin `page` | tabla id, cliente, estado (etiqueta), fecha; filtro de estado, búsqueda (`q`, al enviar), orden por fecha; paginador; el Administrador sin «Nuevo ticket» ni acciones; una respuesta de listado reemplazada por otra más nueva (otro filtro, `q` o página) se ignora (clave `list`) | 22 a 26, 41, 71, 101 a 108, 115, 119, 135 |
| Detalle (`#/tickets/{id}`) | `screens/ticket-detail.js` | los tres (Administrador solo lectura) | `GET /tickets/{id}`, `/milestones`, `/state-changes`; acciones `POST .../milestones`, `.../close`, `.../reopen`, `.../products`, `DELETE .../products/{pid}`; `GET /products/available?q=` | estado, cliente, representante, productos, hitos y cambios de estado en el orden de la API; formulario de hito con «Comenzar a trabajar» (solo Representante); «Cerrar», «Reabrir», asociar y «Quitar» según `ticket-actions.js`; tras éxito vuelve a pedir las tres lecturas; botón deshabilitado mientras dura su acción; las tres lecturas llevan claves distintas (`ticket`, `milestones`, `state-changes`): en paralelo se dibujan todas y una recarga reemplaza solo a la lectura anterior de su misma clave | 21, 27, 28, 29, 32, 34 a 43, 77 a 81, 135 |
| Nuevo ticket (`#/tickets/new`) | `screens/ticket-new.js` | Representante | `GET /clients?q=`, `GET /products/available?q=`, `POST /tickets` | cliente (búsqueda y selector), primer mensaje, productos opcionales; con `201` va a `#/tickets/{id}`, salvo que el usuario ya haya salido de esa instancia de la pantalla, aunque haya vuelto a `#/tickets/new` (la respuesta se ignora sin navegar) | 30 a 33, 136 |
| Usuarios (`#/users`) | `screens/users.js` | Administrador | `GET /users`, `POST /users`, `PATCH /users/{id}`, `POST /users/{id}/deactivate`, `/activate`, `/password` | tabla nombre, email, rol, estado; búsqueda y filtro activo/inactivo; alta con los tres roles y canal opcional; edición; «Dar de baja»/«Reactivar» según `is_active`; restablecimiento con confirmación; recarga de la página actual | 26, 44 a 48, 57, 64, 82 a 85, 100, 110, 120, 125 |
| Categorías (`#/categories`) | `screens/categories.js` | Administrador | `GET /categories`, `POST`, `PATCH`, `DELETE /categories/{id}` | lista, búsqueda, alta, edición, «Eliminar» con confirmación; recarga completa con el mismo `q` | 49, 54, 86 a 88, 120 |
| Tipos de producto (`#/product-types`) | `screens/product-types.js` | Administrador | `GET /product-types`, `GET /categories`, `POST`, `PATCH`, `DELETE /product-types/{id}` | agrupados por categoría, búsqueda, alta y edición con selector de categoría, «Eliminar» con confirmación | 50, 54, 89 a 91, 120 |
| Productos (`#/products`) | `screens/products.js` | Administrador | `GET /products`, `GET /categories`, `GET /product-types`, `POST`, `PATCH /products/{id}`, `/deactivate`, `/activate` | tabla nombre, tipo, categoría, estado; búsqueda y filtros (estado, categoría, tipo); alta y edición; «Dar de baja»/«Reactivar»; recarga | 26, 51 a 53, 92 a 95, 109, 111, 120, 125 |
| Mi cuenta (`#/account`) | `screens/account.js` | los tres | `POST /me/password` | contraseña actual, nueva y confirmación; compara antes de enviar; «Contraseña actualizada.» solo con éxito; vacía los campos | 13 a 15, 64, 122 |

Comunes a todas las pantallas: título de página por pantalla (`«<pantalla> · Mesa de ayuda»`, SPEC-UI-112), mensajes de error en una región `role="alert"` y confirmaciones en `role="status"` (SPEC-UI-69), indicador de carga mientras hay un pedido pendiente (SPEC-UI-71), «No hay resultados» en listados vacíos (SPEC-UI-115), solo controles nativos (`button`, `a[href]`, `input`, `select`, `textarea`, `dialog`; SPEC-UI-113), cada campo con `<label for>` visible (SPEC-UI-67), foco visible con `:focus-visible` (SPEC-UI-114), tablas dentro de un contenedor con `overflow-x: auto` (SPEC-UI-70). Las búsquedas se piden al **enviar** el formulario de búsqueda (Enter o «Buscar»), no al tipear; los filtros `<select>` piden al cambiar. En todas las pantallas, con la sesión abierta, la respuesta (o la falla de conexión) de una lectura reemplazada o de una instancia de pantalla que ya no es la vigente se ignora (SPEC-UI-135 y 136, `core/requests.js`); las pruebas de Playwright de la spec cubren el listado de tickets, el alta de ticket y los tres `GET` en paralelo del detalle.

### Herramientas de prueba y CI

| Pieza | Archivo | Contenido |
|-------|---------|-----------|
| Paquete de desarrollo | `package.json` (+ `package-lock.json`) | `"private": true`, `"type": "module"` (los `.js` de `app/static/js` y de las pruebas son ES modules para Node), **sin** `dependencies`; `devDependencies`: solo `@playwright/test` con versión exacta (sin `^`); `engines.node` `>=22`; scripts `test:js` = `node --test "tests/ui/js/**/*.test.js"`, `test:e2e` = `playwright test`, `test` = los dos |
| Pruebas unitarias de JS | `tests/ui/js/*.test.js` | `node:test` y `node:assert/strict`; importan `app/static/js/core/*.js` y `net/api-client.js` sin DOM ni red (con `fetch` simulado) |
| Configuración de Playwright | `playwright.config.js` | `testDir: "tests/ui/e2e"`, `testMatch: "**/*.spec.js"`, un proyecto Chromium, `baseURL` `http://127.0.0.1:5051`, `webServer` con `python tests/ui/e2e/server.py` (env `PYTHONPATH=.`), `url` de espera `/health`, `reuseExistingServer: !process.env.CI`, `retries: 0`, `forbidOnly: !!process.env.CI` |
| Servidor para Playwright | `tests/ui/e2e/server.py` | `create_app({"SECRET_KEY": secrets.token_hex(32), "DATABASE_URL": "sqlite:///<tmp>/e2e.db"})`, `create_schema` y datos sembrados con los services (un `Admin`, dos representantes, dos clientes, categorías, tipos, productos y tickets con hitos y cambios de estado); `app.run(host="127.0.0.1", port=5051)`. No es un `test_*.py`, así que `pytest` no lo colecta; `ruff` sí lo revisa |
| API simulada para Playwright | `tests/ui/e2e/support/fake-api.js` | `installFakeApi(page)`: intercepta con `page.route` todo pedido que no sea `/` ni `/static/**` (estos los sirve el Flask real); registra cada pedido (método, URL, cabeceras, cuerpo); responde con manejadores por método y ruta; `defer()` para liberar una respuesta cuando la prueba lo indica (retrasos deterministas, sin `sleep`); `abort` para la falta de conexión; un pedido sin manejador hace fallar la prueba |
| Datos y utilidades | `tests/ui/e2e/support/fixtures.js` | lista de palabras en inglés de la decisión 29, credenciales del servidor sembrado, ayudas para la relación de contraste (fórmula WCAG) y para contar entradas del historial |
| Pruebas de pytest | `tests/ui/test_ui_routes.py`, `tests/ui/test_traceability.py` | rutas del servidor (UI-01 a 03) y trazabilidad (UI-76, 98, 99 y 121) |
| CI | `.github/workflows/ci.yml` (nuevo) | ver abajo |

Dos modos de prueba en Playwright:

- **Con API simulada** (casi todas): el Flask real sirve `/` y `/static/**`; la API se simula por prueba. Es lo que permite los casos deterministas (respuestas retrasadas y liberadas en un orden fijo, `route.abort`, estados `5xx`, `204`, cuerpos sin JSON) sin tocar la base, y las pruebas corren en paralelo.
- **Contra el servidor sembrado** (`live.spec.js`, 4 casos): un recorrido corto con la API real (login de cada rol, listado, detalle, logout) que protege la integración con los contratos de 00 a 05. Solo leen datos sembrados, así que no dependen del orden ni se pisan.

Los datos de prueba (sembrados y simulados) evitan las 14 palabras en inglés de la decisión 29 (por ejemplo, nombres «Ana Gómez», «Raúl Pérez», categoría «Computación», producto «Notebook Lenovo»), para que SPEC-UI-55 se pueda comprobar con el texto visible completo.

**Prueba de trazabilidad** (`tests/ui/test_traceability.py`, un módulo con cuatro pruebas, una por spec):

1. SPEC-UI-121: lee los IDs con la expresión `^\| SPEC-UI-(\d+) \|` de `specs/07-ui/spec.md` (solo las filas de las tablas, no las decisiones); junta los docstrings de toda prueba de Python del repo (`ast`: funciones `test_*`, también dentro de clases) y los títulos de prueba de todo `.js` bajo `tests/` (llamadas `test(...)` e `it(...)` cuyo primer argumento es un literal de texto; no `describe` ni `test.describe`); falla con la lista de las specs sin cita.
2. SPEC-UI-99: para las pruebas de esta área (las que citan algún `SPEC-UI-` y todas las de `tests/ui/`, `tests/ui/js/` y `tests/ui/e2e/`), exige `^SPEC-UI-\d+(, SPEC-UI-\d+)* [\x20-\x7E]+$` (descripción en ASCII imprimible, como aproximación verificable de «en inglés») y que el título sea un literal de comillas simples o dobles (no una plantilla con `${}`), para que la extracción no se pierda ninguno.
3. SPEC-UI-98: existe `playwright.config.js`, su `testDir` es `tests/ui/e2e` y hay al menos un `*.spec.js` ahí.
4. SPEC-UI-76: `package.json` no tiene la clave `dependencies` y su script `test:js` corre `node --test`.

Convención de títulos y docstrings de esta área: `SPEC-UI-NN <english description> (TC-UI-NNx)`, por ejemplo `SPEC-UI-14 rejects a mismatched confirmation without calling the API (TC-UI-14b)` o, en pytest, `"""SPEC-UI-01 serves the interface page at the root without a session (TC-UI-01a)"""`. El caso del test-plan va al final, entre paréntesis, para que el formato de SPEC-UI-99 se cumpla.

**CI** (`.github/workflows/ci.yml`), en cada `push` y `pull_request` (sin filtro de rama, así cubre `main`, que pide AGENTS.md, y la rama `dev` de los PR pendientes):

| Job | Pasos | Cuándo corre |
|-----|-------|--------------|
| `python` | `actions/setup-python` 3.12 → `pip install -r requirements.txt -r requirements-dev.txt` → `ruff check .` → `ruff format --check .` → `pytest --cov=app --cov-fail-under=90` (incluye `tests/ui/test_ui_routes.py` y la trazabilidad) | siempre |
| `js` | `actions/setup-node` 22 (con caché de npm) → `npm ci` → `npm run test:js` | siempre, en paralelo con `python` |
| `e2e` | `setup-python` + `pip install` (el servidor es Flask) → `setup-node` 22 → `npm ci` → `npx playwright install --with-deps chromium` → `npm run test:e2e`; si falla, sube `playwright-report/` como artefacto | siempre, en paralelo; no depende de los otros jobs |

Si algún job falla, el PR no se mergea (constitución, principio 4).

## Componentes por capa

| Capa | Archivo | Responsabilidad | Specs |
|------|---------|-----------------|-------|
| Dominio | — | Sin cambios | — |
| Services | — | Sin cambios | — |
| Repositories | — | Sin cambios | — |
| Controllers | `app/controllers/ui.py` (nuevo) | Blueprint `ui`: `GET /` → `Response(index.read_bytes(), mimetype="text/html")`, sin `login_required` | UI-01 |
| App | `app/__init__.py` | Registra el blueprint `ui` | UI-01 |
| Front (puro) | `app/static/js/core/*.js` | Rutas, sesión, token de pedido y de pantalla, consultas y paginación, mensajes, etiquetas, fechas, acciones de ticket, formularios | ver la tabla de arquitectura |
| Front (red) | `app/static/js/net/api-client.js` | Pedidos con `fetch` inyectado, `credentials: "same-origin"`, JSON, sin `Authorization`, clasificación de la respuesta (`ok`, `status`, `body`, `networkError`) y etiqueta de época | UI-05, 59, 60, 75, 130 |
| Front (DOM) | `app/static/js/dom/*.js`, `screens/*.js`, `app.js`, `index.html`, `css/app.css` | Dibujo, navegación, pantallas, pantalla inerte, accesibilidad y diseño adaptable | el resto |

## Modelo de datos

Sin tablas, columnas ni migraciones. El front no guarda nada fuera de la memoria (SPEC-UI-62).

## Patrones aplicados

- **Máquina de estados como reductor puro** (equivalente del patrón State para el front): un solo lugar decide qué hace cada evento en cada estado de la sesión, con una tabla por estado en lugar de condicionales repartidos en las pantallas; los efectos se ejecutan afuera.
- **Inyección de dependencias por parámetro**: el cliente de la API recibe `fetch` (SPEC-UI-75), las pantallas reciben el cliente y las funciones de navegación, `dates.js` recibe la zona. Permite probar sin navegador.
- **Núcleo funcional, cáscara imperativa**: `core/` decide; `app.js`, `dom/` y `screens/` ejecutan.
- **Tablas en lugar de condicionales**: rutas y permisos por rol (`routes.js`), mensajes por código (`messages.js`), etiquetas por código (`labels.js`), acciones por rol y estado (`ticket-actions.js`).
- **Epoch (token de sesión)** para descartar respuestas de una sesión cerrada (SPEC-UI-130) sin cancelar pedidos en curso.
- **Token de pantalla y de pedido** (misma idea que la época, en `core/requests.js`) para descartar, con la sesión abierta, respuestas reemplazadas o de otra instancia de pantalla (SPEC-UI-135 y 136), sin tocar el `401`: instancia por pantalla mostrada, clave de recurso por lectura, escrituras fuera del reemplazo.
- **Controles nativos**: sin componentes propios que imiten botones o diálogos.

## Decisiones técnicas

| Decisión | Motivo y alternativas descartadas |
|----------|-----------------------------------|
| Archivos en `app/static/` (carpeta por defecto de `Flask(__name__)`) | Flask ya la sirve en `/static/` (SPEC-UI-02) con `404` JSON (SPEC-UI-03) y TC-PLT-23c ya la nombra. Se descartó una carpeta propia con `static_folder` (más configuración por nada). |
| `GET /` con un blueprint que devuelve los bytes de `index.html` con `mimetype="text/html"` | Mismo patrón que `/docs` en `api_docs.py`. Se descartaron `send_static_file` (agrega validadores condicionales que nadie pidió) y un `redirect` a `/static/index.html` (SPEC-UI-01 pide `200`). |
| Sin cabeceras de caché propias | Ninguna spec las pide; el valor por defecto de Flask revalida los estáticos, que es lo que necesita un front sin build. |
| Módulos ES sin bundler, cargados con `<script type="module" src="/static/js/app.js">` | SPEC-UI-06 y 74. Los navegadores resuelven los `import` relativos. |
| Puros en `core/` y cliente de la API en `net/` | SPEC-UI-73 exige que los puros no nombren `fetch`; el cliente lo recibe por parámetro y queda fuera de `core/` para que el escaneo sea simple (sin `fetch` en ningún archivo de `core/`). |
| Máquina de sesión pura con efectos | Las specs 07 a 12, 116 a 118 y 124 a 134 son una matriz estado × evento; como reductor se prueba entera con `node --test` (incluido el descarte inmediato de la identidad de SPEC-UI-11, que Playwright solo ve de forma indirecta, decisión 56). Se descartó repartir la lógica en listeners del DOM (no se puede probar sin navegador). |
| `history.replaceState` para fijar `#/login` y el inicio del rol | No dispara `hashchange` ni suma entradas (SPEC-UI-128 y 132). Se descartó `location.replace("#/...")`, que dispara `hashchange` y obliga a filtrar el evento propio. |
| Tras crear un ticket se navega a `#/tickets/{id}` con `location.hash` (suma una entrada) | Es una navegación del usuario, como el enlace de SPEC-UI-20; SPEC-UI-132 solo pide reemplazar al mostrar el inicio del rol. |
| Época de sesión para SPEC-UI-130 | Cada pedido lleva la época con la que salió; si al responder la época cambió, se ignora con cualquier estado. Se descartó `AbortController` (un pedido abortado igual pudo llegar al servidor y la spec pide ignorar la respuesta, no cancelar). |
| Token de pantalla y de pedido en un módulo puro aparte (`core/requests.js`) para SPEC-UI-135 y 136 | Misma técnica que la época (contadores, sin cancelar) y misma razón para descartar `AbortController`. Va aparte de `core/session.js` porque es otra responsabilidad (qué respuesta sigue vigente dentro de una sesión abierta, no el estado de la sesión), tiene su propio archivo de prueba y su task corre en paralelo con la cadena de la máquina. Se descartaron: meterlo en la máquina de sesión (agranda la matriz con un estado por pantalla) y resolverlo en cada pantalla (repetido y sin prueba pura). El `401` nunca se descarta (decisión 57): lo decide la máquina antes de consultar el módulo. |
| `issue` recibe el método y decide por él si el pedido es escritura (decisión 62) | Que el módulo clasifique por método garantiza que una escritura nunca se descarta por reemplazo aunque una pantalla le pase una clave por error. Se descartó dejar la distinción solo en «las acciones no pasan clave» (una convención que nada comprueba). |
| La clave de recurso no incluye filtros, `q`, orden ni página | «Los mismos datos» de la decisión 62 son el listado o la consulta, no cada combinación de parámetros: si la clave incluyera los parámetros, dos filtros distintos no se reemplazarían y volvería el problema de SPEC-UI-135. Se descartó derivar la clave de la URL. |
| Instancia nueva en cada pantalla mostrada, también en la misma ruta, y no en las recargas dentro de la pantalla | Es la decisión 64: el `201` de un alta anterior no navega aunque el usuario haya vuelto a `#/tickets/new`. Se descartó identificar la instancia por la ruta (no distinguiría la vuelta a la misma ruta). Las recargas (cambio de filtro, recarga tras una acción) no son una pantalla nueva: si abrieran instancia, una escritura en curso de la pantalla quedaría descartada. |
| La conexión del módulo con `app.js` se hace en dos pasos: la clave por pedido en T-UI-22 (SPEC-UI-135) y el token de pantalla en T-UI-25 (SPEC-UI-136); el `401` obsoleto se prueba en T-UI-31 | Cada paso entra con la prueba de Playwright que lo ve fallar primero (TDD). El aviso de sesión vencida lo conecta T-UI-31 en `app.js`, por eso los casos del `401` obsoleto (TC-UI-135g y 136g) van ahí. Las pantallas hechas antes no pasan clave: sus lecturas quedan con clave única (nunca reemplazadas) hasta que la pantalla la pase; T-UI-24 pasa las claves del detalle. |
| Pantalla inerte (SPEC-UI-133 y 134) en dos capas: `dom/inert.js` pone `disabled` en `button`, `input`, `select` y `textarea` y `aria-disabled="true"` con `tabindex="-1"` en los enlaces, y un listener en fase de captura sobre el documento cancela `click`, `submit`, `change`, `input` y `keydown` de activación; además `canSend()` es falso en `closing` y el cliente no envía | Un control deshabilitado no recibe clics, pero un `submit` o un `dispatchEvent` sí llegarían; la captura y `canSend` lo cierran. Las pruebas usan `force: true` y `dispatchEvent` porque `click` de Playwright espera controles habilitados. |
| Confirmación de «Eliminar» con `<dialog>` nativo («Confirmar» / «Cancelar») | `window.confirm` muestra botones que traduce el navegador (en el Chromium del CI, «Cancel» y «OK»), lo que rompería SPEC-UI-55; `<dialog>` es nativo (SPEC-UI-113) y accesible con teclado. |
| Búsqueda al enviar, no al tipear | Un pedido por búsqueda, determinista en las pruebas, y menos respuestas cruzadas; las que igual se crucen las descarta SPEC-UI-135. |
| Representante: filtro por cliente; Administrador: por cliente y por representante; Cliente: sin esos filtros | Es el alcance de SPEC-UI-24 y 25; la API respondería `403` a un filtro prohibido (SPEC-TKT-46). No es una regla de ticket (SPEC-UI-21 restringe solo las acciones). |
| «Comenzar a trabajar» sin marcar → el cuerpo no lleva `start_progress` | SPEC-UI-81 solo pide enviar `true` si está marcado; ausente vale `false` en la API (decisión 7 de 05). |
| Canal opcional sin elegir → el alta no envía `preferred_channel`; la edición envía nombre, email y canal del formulario | SPEC-UI-45 y 46; la API toma su valor por defecto. |
| Texto de confirmación del alta de usuario: «Usuario creado.», en la tabla de mensajes propios de `core/messages.js` junto a «Contraseña actualizada.» | SPEC-UI-85 lo nombra y la spec lo suma a la tabla «Mensajes propios de la interfaz» (decisión 59, G-04 resuelto). |
| `node --test` con un patrón de archivos y Node 22 | Desde Node 21 `--test` acepta patrones; con 22 (LTS) se fija en `engines` y en el CI. |
| Un solo navegador (Chromium) en Playwright | RNF 9 pide un navegador real; uno alcanza y el CI queda corto. |
| Casi todas las pruebas de Playwright con API simulada y 4 contra el servidor sembrado | Determinismo y velocidad, sin rutas de reinicio en la app (romperían SPEC-PLT-23 y SPEC-USR-49); el recorrido real cubre la integración. |
| Relación de contraste calculada en la prueba (fórmula WCAG sobre `getComputedStyle`), sin librerías | No se agregan dependencias (`axe-core` sería una). El CSS evita fondos con imagen o degradado para que el cálculo sea exacto. |
| Prueba de trazabilidad: un módulo (`tests/ui/test_traceability.py`) con una prueba por spec (76, 98, 99 y 121) | Cada falla dice qué spec rompe (G-06 resuelto con este criterio). El formato de SPEC-UI-99 exige descripción literal en ASCII imprimible, como lo dice ahora la spec (decisión 60, G-05 resuelto). |
| La prueba de cobertura de la trazabilidad (SPEC-UI-121) se escribe al final (T-UI-36) | Escrita antes, dejaría el CI en rojo hasta la última task. Se prueba quitando una cita (sin fase roja propia). El formato (SPEC-UI-99) va temprano (T-UI-16) para que toda prueba nueva lo cumpla. |
| Pruebas extra en `node --test` para specs que la tabla asigna a Playwright (sesión, acciones de ticket, formularios) | La tabla fija el mecanismo mínimo; las pruebas puras suman precisión sin reemplazar a Playwright, que sigue teniendo su caso para cada spec de su fila. |

## Dependencias con otras áreas

Cada pantalla depende de las tasks de API que implementan lo que consume (las tasks de 07 las listan en `Depende de`):

| Pantalla o pieza de 07 | Tasks de otras áreas |
|------------------------|----------------------|
| `GET /` y estáticos (T-UI-02) | T-PLT-22 (paridad con las rutas de la UI), T-USR-54 (rutas públicas por par método-ruta) |
| Carga y sesión (T-UI-18) | T-USR-48 (`GET /me`); `POST /login` y `POST /logout` ya existen |
| Mi cuenta (T-UI-21) | T-USR-52 (`POST /me/password`) |
| Tickets, listado (T-UI-22) | T-TKT-47 (filtros, orden y paginación; el `Admin` lista todo desde T-TKT-46), T-USR-50 (`GET /clients` del representante), T-USR-49 (parámetros de `GET /representatives`) |
| Detalle (T-UI-23) | T-TKT-45 (el `Admin` lee el detalle), T-MLS-23 (el `Admin` lee los hitos), T-TKT-50 (`GET .../state-changes`) |
| Acciones del detalle (T-UI-24, que además espera a T-UI-22 por la clave de pedido en `app.js`) y nuevo ticket (T-UI-25) | T-PRD-38 (`GET /products/available?q=`), T-USR-50 (`GET /clients?q=`) |
| Usuarios (T-UI-26) | T-USR-49 (`GET /users`), T-USR-51 (reactivar), T-USR-53 (restablecer contraseña) |
| Categorías y tipos (T-UI-27 y 28) | T-PTY-39 (`q` en `GET /categories` y `GET /product-types`) |
| Productos (T-UI-29) | T-PRD-36 (reactivar), T-PRD-37 (filtros y paginación), T-PTY-39 |
| Recorrido real (T-UI-35) | Las anteriores |
| Diagramas (T-UI-37) | T-TKT-51 (último que edita `diagrams/classes.md` en la cadena T-PLT-23 → T-USR-55 → T-PTY-40 → T-PRD-39 → T-TKT-51) |
| Cierre (T-UI-38) | T-PLT-24 (también edita `AGENTS.md`), T-TKT-52 y T-MLS-26 (últimos cierres de la re-sincronización) |

Casos de otras áreas que esta área completa: TC-PLT-23d (`GET /` existe y no está en el contrato) y la parte `GET /` y `GET /static/<archivo>` de TC-USR-49b, los dos en T-UI-02 y con su propia cita (`SPEC-PLT-23 · TC-PLT-23d`, `SPEC-USR-49 · TC-USR-49b`).

## Diagramas

- `diagrams/sequences/07-ui.md` (nuevo): §0 servido (`GET /`, `/static`, `404`); §1 carga inicial (`GET /me` `200`/`401`/otro, «Reintentar», hash retenido); §2 inicio de sesión (`POST /login` → `GET /me` → inicio del rol); §3 navegación con sesión (clasificación del hash, `replaceState`, instancia de pantalla nueva en cada pantalla mostrada, también al volver a la misma ruta, y respuesta o falla de conexión de la instancia anterior ignorada sin navegar, SPEC-UI-136); §4 cierre de sesión (`POST /logout` retrasado, pantalla inerte, hash retenido, respuestas viejas ignoradas por época); §5 sesión vencida (`401` → login con aviso); §6 listado paginable con filtros (dos consultas respondidas al revés: la reemplazada se ignora, SPEC-UI-135; un `401` no se ignora); §7 acción sobre un ticket y recarga (los tres `GET` con claves distintas se dibujan todos; la escritura no se reemplaza); §8 acción de administración y recarga (incluido SPEC-UI-125); §9 cambio de contraseña. Cada sección con su línea `Specs:`; una línea final «Specs transversales» lista las que no son secuencias (55, 61 a 63, 65 a 76, 96, 98, 99, 112 a 115, 121, 123).
- `diagrams/classes.md`: el blueprint `ui` en la capa de controllers y un paquete «Front (`app/static/js`)» con los módulos de `core/`, `net/`, `dom/` y `screens/` (incluido `core/requests.js`) y la dirección de sus dependencias (`screens` → `dom`, `core`; `app.js` → todos; `core` → `core`).

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Respuestas fuera de orden con la sesión abierta (dos filtros respondidos al revés; una creación de ticket que responde después de que el usuario cambió de pantalla y salta al detalle) | Cubierto por SPEC-UI-135 y 136: `core/requests.js` (T-UI-39) con TC-UI-135a, 135b, 135d, 135e, 136a, 136b y 136d, y Playwright determinista en T-UI-22 (TC-UI-135c, 135f), T-UI-24 (TC-UI-135h), T-UI-25 (TC-UI-136c, 136e, 136f) y T-UI-31 (TC-UI-135g, 136g: el `401` obsoleto, cuando `app.js` ya muestra el aviso de sesión vencida). |
| Un pedido reemplazado que responde `401` queda descartado y oculta una sesión vencida | El `401` se resuelve en la máquina de sesión antes de consultar el módulo, y `verdict` nunca devuelve `"ignore"` para `401` (TC-UI-135b y 136b; en el navegador, TC-UI-135g y 136g). |
| Una escritura queda descartada por una lectura posterior o por otra escritura | `issue` clasifica por método: las escrituras no tocan `latest` y `verdict` no les aplica el reemplazo (TC-UI-135d). |
| Una recarga del detalle descarta otra lectura del mismo detalle (los tres `GET` en paralelo) | Claves distintas por recurso; TC-UI-135e (módulo) y TC-UI-135h (navegador, liberadas en orden inverso). |
| Una pantalla olvida pasar la clave y dos lecturas suyas se pisan | Sin clave la lectura no se reemplaza nunca (comportamiento previo, sin datos falsos); las claves de cada pantalla se listan en la regla de tasks.md y el token de pantalla sigue protegiendo el cambio de pantalla. |
| `app.js` abre una instancia nueva en una recarga dentro de la misma pantalla y descarta una escritura en curso | `openScreen` solo se llama en el efecto `render` de la máquina (pantalla mostrada), nunca desde `dom/listing.js` ni desde una pantalla; TC-UI-135c y 135h ven que la pantalla sigue entregando respuestas tras recargar. |
| Pruebas de Playwright inestables por tiempos | Sin `sleep`: retrasos con `defer()` liberados por la prueba, aserciones con `expect(...)`/`expect.poll`, `retries: 0` para que una inestabilidad se vea. |
| `click` de Playwright espera controles habilitados y con `aria-disabled` no actúa, así que las pruebas de SPEC-UI-133 pasarían sin probar nada | Usan `force: true` y `dispatchEvent("click")`/`dispatchEvent("submit")`, y comprueban cero pedidos con el registro de `fake-api.js`. |
| Un texto en inglés que agrega el navegador (`window.confirm`, mensajes de validación nativa de formularios como `required`) | `<dialog>` propio para confirmar; los formularios usan `novalidate` y la validación la hace la API (SPEC-UI-57) o el módulo puro (14 y 100). |
| La política de contenido estricta bloquea algo que en desarrollo funciona | Sin estilos ni scripts en línea (escaneo estático, TC-UI-65a) y la prueba con la política real (TC-UI-65b). |
| Fechas que cambian según la zona de la máquina del CI | `dates.js` recibe la zona; `node --test` usa zonas fijas y Playwright fija `timezoneId`. |
| `node --test` no encuentra archivos con otra versión de Node | `engines.node >= 22` y `setup-node` 22 en el CI. |
| El servidor de Playwright no encuentra el paquete `app` | `PYTHONPATH=.` en `webServer.env`; el directorio de trabajo es la raíz del repo. |
| Puerto 5051 ocupado en una máquina local | `reuseExistingServer` fuera del CI; el puerto se puede cambiar con la variable `E2E_PORT` en el config y en `server.py`. |
| La extracción de títulos de la trazabilidad no ve un título armado con plantilla | SPEC-UI-99 (TC-UI-99a) exige títulos literales en ASCII imprimible (decisión 60); un título con `${...}` falla. |
| Muchas pruebas de navegador alargan el CI | Un solo navegador, API simulada y ejecución en paralelo; el job `e2e` corre en paralelo con `python` y `js`. |
| La regla de ruta `static` existe aunque falte la carpeta, y `index.html` todavía no existe al registrar `GET /` | T-UI-02 crea `index.html` y `css/app.css` en el mismo ciclo que la ruta. |
| Romper TC-PLT-23a o TC-USR-49a al agregar `GET /` | T-UI-02 depende de T-PLT-22 y T-USR-54, que ya nombran `("GET", "/")`. |
| Contraste de controles deshabilitados por debajo de 4,5:1 (SPEC-UI-72 no los exceptúa) | El CSS de `:disabled` y `[aria-disabled="true"]` mantiene el contraste; TC-UI-72a mide también la pantalla inerte. |

## Notas del validador resueltas en este plan

- (a) **Respuestas fuera de orden con sesión abierta** (WARNING): resuelto con SPEC-UI-135 y 136 (decisión 57, G-01 opción A) y precisado con las decisiones 62 a 65 (qué es «reemplazó», falla de conexión, instancia de pantalla, pruebas); T-UI-39 y los casos TC-UI-135a a 135h y 136a a 136g.
- (b) **Redacción de SPEC-UI-133** (NOTE): la spec ya dice «no deberá enviar» (decisión 61, G-02). Sin cambio de comportamiento, tasks ni casos.
- (c) **`#/login` vuelto a mostrar por SPEC-UI-126 con `POST /login` pendiente** (NOTE): la decisión 58 confirma el comportamiento del plan (G-03): no se vuelve a dibujar el login, se conservan el formulario y el pedido pendiente y SPEC-UI-09 maneja su respuesta (TC-UI-126e).
- (d) **SPEC-UI-11 probada solo de forma indirecta en Playwright** (NOTE): se mantiene la prueba indirecta de la decisión 56 (TC-UI-11b y 11c) y se suma una prueba directa sobre la máquina pura (TC-UI-11a: tras `logoutClicked`, `currentUser` es `null` y la época sube antes de que responda `POST /logout`).

## Huecos y preguntas abiertas

Todos los huecos están **resueltos** (2026-11-12, decisiones del usuario). No queda ninguna pregunta abierta.

| ID | Specs | Pregunta | Resolución | Impacto en el plan | Estado |
|----|-------|----------|------------|--------------------|--------|
| G-01 | 135, 136 (nuevas); 22, 33 | ¿Qué hace la interfaz con la respuesta de un pedido hecho con la sesión abierta cuando ya se reemplazó por uno más nuevo de la misma pantalla o el usuario ya cambió de pantalla? | **Opción A**, dos specs nuevas: SPEC-UI-135 (reemplazado) y SPEC-UI-136 (otra pantalla, sin navegar), ambas sin descartar el `401` (decisión 57) | T-UI-39 nueva (`core/requests.js`, TC-UI-135a, 135b, 136a, 136b); T-UI-22 suma TC-UI-135c y la clave por pedido en `app.js`; T-UI-25 suma TC-UI-136c y el token de pantalla en `app.js`; T-UI-30, 36 y 38 ajustan dependencias | Resuelto |
| G-02 | 133 | Redacción EARS «deberá no enviar» frente a «no deberá» | La spec pasó a «**el sistema no deberá** enviar …» (decisión 61) | Ninguno | Resuelto |
| G-03 | 126, 09 | Con `POST /login` pendiente, ¿SPEC-UI-126 conserva el formulario y el pedido pendiente? | Se mantiene el comportamiento por defecto: sí (decisión 58) | TC-UI-126e sin cambios; T-UI-19 cita la decisión 58 | Resuelto |
| G-04 | 85, 55 | Texto de la confirmación del alta de usuario | «Usuario creado.», en la tabla «Mensajes propios de la interfaz» (decisión 59) | T-UI-05 suma el texto a `messages.js`; TC-UI-85a lo comprueba | Resuelto |
| G-05 | 99 | «Descripción en inglés» no es verificable al pie de la letra | Título literal (sin `${...}`) en ASCII imprimible `0x20` a `0x7E`, ya escrito en SPEC-UI-99 (decisión 60) | TC-UI-99a sin cambios | Resuelto |
| G-06 | 76, 98, 99, 121 | «Una prueba de `pytest`» de trazabilidad | Un módulo `tests/ui/test_traceability.py` con una prueba por spec (cuatro) | Ninguno | Resuelto |
