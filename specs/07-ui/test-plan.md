# 07 — Interfaz web · Test plan

Cada prueba cita sus specs con el formato de SPEC-UI-99 y el caso al final: en el título de las pruebas de `node --test` y de Playwright (`test('SPEC-UI-14 rejects a mismatched confirmation without calling the API (TC-UI-14b)', ...)`) y en el docstring de las de `pytest` (`"""SPEC-UI-01 serves the interface page at the root without a session (TC-UI-01a)"""`). Una prueba puede citar varias specs (`SPEC-UI-15, SPEC-UI-64 ...`). Los casos de otras áreas que se completan acá citan su propia spec (`"""SPEC-PLT-23 · TC-PLT-23d"""`).

Niveles de esta área (el mecanismo de cada spec sigue la tabla de verificación de la spec):

- `integration` (**pytest**): rutas del servidor con `app.test_client()` y la prueba de trazabilidad. Archivos en `tests/ui/`.
- `unit` (**node --test**): módulos puros y cliente de la API, sin DOM ni red. Archivos en `tests/ui/js/`.
- `e2e` (**Playwright**, Chromium): comportamiento observable en el DOM o en el navegador. Archivos en `tests/ui/e2e/`.

En las tablas, los archivos son relativos a `tests/ui/` salvo que se indique otra ruta.

## Fixtures y preparación

`pytest` (existentes en `tests/conftest.py`): `app`, `client`, `schema`, `make_user`, `login_as`. Sin fixtures nuevos.

`node --test`:

- Hash, rol y respuestas como datos literales en cada prueba. Zonas horarias explícitas para las fechas (`UTC`, `America/Argentina/Buenos_Aires` (UTC-3, sin horario de verano), `Asia/Kolkata` (UTC+5:30)).
- `fakeFetch(responses)`: función local que registra cada llamada (`url`, `init`) y devuelve `Response` construidas con la clase global `Response` de Node (o lanza `TypeError` para simular la falta de conexión).
- `poisonGlobals()`: define `globalThis.fetch`, `globalThis.document` y `globalThis.window` como getters que lanzan, y los restaura al terminar (TC-UI-73a y 75b).

Playwright (`tests/ui/e2e/support/`, completos en T-UI-15 y sin editar después):

- `installFakeApi(page)` → `api`: intercepta todo pedido que no sea `/` ni `/static/**`; `api.on(method, path, responder)`; `api.requests` (método, URL, cabeceras, cuerpo, instante); `api.defer(method, path)` devuelve una compuerta `{ release(status, body), abort() }` para liberar la respuesta cuando la prueba lo indica; un pedido sin manejador hace fallar la prueba.
- `loginAs(page, api, role)`: simula `GET /me` `200` con el usuario del rol y abre `/`.
- `fixtures.js`: `ENGLISH_WORDS` (Save, Cancel, Delete, Loading, Search, Login, Logout, Close, Reopen, Submit, Name, Password, Next, Previous), `contrastRatio(fg, bg)` (WCAG 2.x), `historyLength(page)`, usuarios de ejemplo (`ADMIN` «Marta Ruiz», `REP` «Raúl Pérez», `CLIENT` «Ana Gómez»), tickets de ejemplo (`New`, `InProgress`, `Closed`, con fechas UTC fijas como `2026-01-01T12:00:00+00:00`) y páginas (`page(items, n, total)`).
- `tests/ui/e2e/server.py`: Flask real con base temporal y datos sembrados (los mismos nombres, más 25 tickets de «Ana Gómez» con «Raúl Pérez» para tener dos páginas, y un ticket con dos hitos y un cambio de estado). Lo usa solo `live.spec.js`; el resto sirve de él solo `/` y `/static/**`.

Ningún dato de prueba contiene las palabras de la decisión 29 (TC-UI-55a mira todo el texto visible).

Casos deterministas de `POST /logout` y de `GET /me` (sin `sleep`): la prueba crea la compuerta con `api.defer`, dispara la acción, hace sus comprobaciones mientras la respuesta está retenida y recién después llama a `release(...)` o `abort()`. El orden «antes» y «después» de SPEC-UI-130 se fija liberando las compuertas en ese orden y esperando a que la pantalla refleje cada paso con `expect(...)`.

## Matriz spec → casos

### Servido y rutas

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-01 | TC-UI-01a | integration | Sin sesión, `GET /` | `200`, `mimetype == "text/html"`, el cuerpo contiene `<script type="module" src="/static/js/app.js">` | `test_ui_routes.py` |
| UI-01 | TC-UI-01b | integration | `GET /` sin sesión y con `login_as` | Los dos `200` con el mismo cuerpo, igual a los bytes de `app/static/index.html`; sin redirección | `test_ui_routes.py` |
| UI-02 | TC-UI-02a | integration | Sin sesión, `GET /static/css/app.css` | `200`, `text/css` | `test_ui_routes.py` |
| UI-02 | TC-UI-02b | integration | Sin sesión, `GET /static/js/app.js` | `200`, `text/javascript` | `test_ui_routes.py` |
| UI-02 | TC-UI-02c | integration | Sin sesión, `GET /static/js/core/routes.js` | `200`, `text/javascript` (los módulos importados también se sirven) | `test_ui_routes.py` |
| UI-03 | TC-UI-03a | integration | `GET /static/no-existe.js` | `404` `{"error": "not_found"}` en JSON | `test_ui_routes.py` |
| UI-03 | TC-UI-03b | integration | `GET /static/js/` (directorio) | `404` JSON; el cuerpo no lista archivos | `test_ui_routes.py` |
| UI-03 | TC-UI-03c | integration | `GET /static/../app/__init__.py` y `GET /static/%2e%2e/app/__init__.py` | `404` JSON; el cuerpo no contiene código | `test_ui_routes.py` |
| UI-04 | TC-UI-04a | unit | `classify(hash, role)` para cada fila de la tabla de rutas y cada rol | Cada ruta da su pantalla (o `forbidden` según la tabla); `#/tickets/new` da `ticket-new` | `js/routes.test.js` |
| UI-04 | TC-UI-04b | e2e | Representante; marca `window.__marca = 1`; recorre «Tickets» → «Nuevo ticket» → «Mi cuenta» con la navegación | Cambia la pantalla, la marca sigue, ningún pedido de documento (`resourceType() == "document"`) después del primero | `e2e/routing.spec.js` |
| UI-05 | TC-UI-05a | unit | Escaneo de `app/static/**` | Ningún `http://`, `https://` ni `//host` en `src`, `href`, `import`, `url()` ni literales de ruta | `js/static-scan.test.js` |
| UI-05 | TC-UI-05b | e2e | Recorrido de los tres roles con registro de `page.on("request")` | Todo pedido a la API tiene el origen de `baseURL` y la ruta del código es relativa | `e2e/security.spec.js` |
| UI-06 | TC-UI-06a | unit | Escaneo de `index.html` y `css/app.css` | Sin `<script>`, `<link>` ni `@import`/`@font-face` hacia otro origen; `index.html` referencia fuentes sin compilar (`/static/js/app.js` existe en el repo) | `js/static-scan.test.js` |
| UI-06 | TC-UI-06b | e2e | Carga de `/` y de cada pantalla | Ningún pedido de `script`, `stylesheet` ni `font` a otro origen | `e2e/security.spec.js` |

### Sesión, identidad y contraseña

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-07 | TC-UI-07a | unit | `mePending{initial}` + `meAnswered(200, Admin, "")`, y lo mismo con `Representative` y `Client` | `open`; efectos `render(home)` y `replaceHash("#/users")` o `"#/tickets"` | `js/session.test.js` |
| UI-07 | TC-UI-07b | unit | Ídem con el hash `#/login` | Mismo resultado que con el hash vacío | `js/session.test.js` |
| UI-07 | TC-UI-07c | e2e | `GET /me` `200` para cada rol; abre `/` sin hash | `Admin` ve «Usuarios»; `Representative` y `Client` ven el listado de tickets | `e2e/boot.spec.js` |
| UI-07 | TC-UI-07d | e2e | `GET /me` `200` (`Client`); abre `/#/login` | Se muestra el inicio del rol, no el login | `e2e/boot.spec.js` |
| UI-08 | TC-UI-08a | unit | `mePending{initial}` + `meAnswered(401)` | `anonymous{notice: false}`; `render(login)` y `replaceHash("#/login")` | `js/session.test.js` |
| UI-08 | TC-UI-08b | unit | `mePending{login}` + `meAnswered(401)`; `meError` → `retryClicked` → `meAnswered(401)` | Login sin aviso en los dos | `js/session.test.js` |
| UI-08 | TC-UI-08c | e2e | `GET /me` `401`; abre `/#/tickets` | Formulario de inicio de sesión, sin «Tu sesión venció»; `location.hash == "#/login"` | `e2e/boot.spec.js` |
| UI-116 | TC-UI-116a | unit | `meAnswered(200)` con `#/account` (los tres roles), `#/products` (`Admin`), `#/tickets/new` (`Representative`) y `#/tickets/5` | `render` de esa pantalla, sin `replaceHash` | `js/session.test.js` |
| UI-116 | TC-UI-116b | e2e | `GET /me` `200` (`Client`); abre `/#/account` | Pantalla «Mi cuenta» | `e2e/boot.spec.js` |
| UI-117 | TC-UI-117a | unit | `meAnswered` con `500` JSON, `403` JSON `forbidden`, `404` sin cuerpo y sin conexión | `meError` con el error para 58, 56 y 59; nunca `render(login)` | `js/session.test.js` |
| UI-117 | TC-UI-117b | e2e | `GET /me` `500` `{"error": "internal_error"}` | «Ocurrió un error inesperado. Intente nuevamente.» y «Reintentar»; sin formulario de login | `e2e/boot.spec.js` |
| UI-117 | TC-UI-117c | e2e | `GET /me` abortado (`route.abort`) | «No se pudo conectar con el servidor. Intente nuevamente.» y «Reintentar» | `e2e/boot.spec.js` |
| UI-117 | TC-UI-117d | e2e | Login `200`; el `GET /me` posterior responde `503` sin cuerpo | Mensaje de sin conexión y «Reintentar»; no vuelve al login | `e2e/login.spec.js` |
| UI-118 | TC-UI-118a | unit | `meError{initial}` y `meError{login}` + `retryClicked` | `mePending` con el mismo `origin` y efecto `request(GET /me)`; luego `200` evalúa el hash (`initial`) o va al inicio (`login`) | `js/session.test.js` |
| UI-118 | TC-UI-118b | e2e | `GET /me` `500` y después `200` (`Client`) en `/#/account`; pulsa «Reintentar» | Hay dos `GET /me` y se muestra «Mi cuenta» | `e2e/boot.spec.js` |
| UI-118 | TC-UI-118c | e2e | Login `200`, `GET /me` `500`, «Reintentar», `GET /me` `200` (`Admin`) | Inicio del rol (`#/users`) | `e2e/login.spec.js` |
| UI-118 | TC-UI-118d | e2e | `GET /me` `500`, «Reintentar», `GET /me` `401` | Login sin aviso de sesión vencida | `e2e/boot.spec.js` |
| UI-09 | TC-UI-09a | unit | `anonymous` + `loginAnswered(200)`; luego `meAnswered(200, Client, "#/account")` | `mePending{login}` con `request(GET /me)`; después inicio del rol y `replaceHash("#/tickets")`, no `#/account` | `js/session.test.js` |
| UI-09 | TC-UI-09b | e2e | `GET /me` `401`; email y contraseña; `POST /login` `200`; `GET /me` `200` (`Client`) | El cuerpo de `POST /login` tiene `email` y `password`; se muestra el listado de tickets y `location.hash == "#/tickets"` | `e2e/login.spec.js` |
| UI-09 | TC-UI-09c | e2e | **Servidor sembrado**: login del `Admin` sembrado | Inicio `#/users` con las cuentas reales de la siembra | `e2e/live.spec.js` |
| UI-10 | TC-UI-10a | unit | `translateError(401 {"error": "invalid_credentials"})` | «Email o contraseña incorrectos.» | `js/messages.test.js` |
| UI-10 | TC-UI-10b | e2e | `POST /login` `401` `invalid_credentials` | Ese mensaje en la región de alertas; sigue en `#/login`; no hay otro texto sobre el motivo | `e2e/login.spec.js` |
| UI-11 | TC-UI-11a | unit | `open` + `logoutClicked` | `closing`; `currentUser(state) === null`; época + 1; efectos `request(POST /logout)` y `setInert(true)`, antes de cualquier respuesta | `js/session.test.js` |
| UI-11 | TC-UI-11b | e2e | Representante en el listado; `POST /logout` retenido; pulsa «Cerrar sesión» | Hay exactamente un `POST /logout` mientras sigue retenido; ningún otro pedido sale después del clic (proxy de la decisión 56) | `e2e/logout.spec.js` |
| UI-11 | TC-UI-11c | e2e | Un `GET /tickets?page=2...` retenido antes del clic; `POST /logout` retenido; se libera el listado con `200` y otras filas | Las filas nuevas no aparecen (proxy de la decisión 56); al liberar el logout, login | `e2e/logout.spec.js` |
| UI-12 | TC-UI-12a | unit | `open` + `apiAnswered(401, epoch vigente)` | `anonymous{notice: true}`; época + 1; `render(login)` con aviso y `replaceHash("#/login")` | `js/session.test.js` |
| UI-12 | TC-UI-12b | unit | `401` de `POST /login` (en `anonymous`), de `POST /logout` (en `closing`) y del `GET /me` de carga | Ninguno produce `notice: true` (los cubren 10, 129 y 08) | `js/session.test.js` |
| UI-12 | TC-UI-12c | e2e | Listado mostrado; «Siguiente» responde `401` | Login con «Tu sesión venció. Inicia sesión nuevamente.»; `location.hash == "#/login"`; las filas anteriores ya no se ven | `e2e/expiry.spec.js` |
| UI-13 | TC-UI-13a | e2e | `#/account`; actual, nueva y confirmación iguales | Un `POST /me/password` con `{"current_password", "new_password"}` (sin la confirmación) | `e2e/account.spec.js` |
| UI-122 | TC-UI-122a | e2e | `POST /me/password` `204` | «Contraseña actualizada.» en la región de estado | `e2e/account.spec.js` |
| UI-122 | TC-UI-122b | e2e | `POST /me/password` `400` `validation_error` | No aparece «Contraseña actualizada.» | `e2e/account.spec.js` |
| UI-124 | TC-UI-124a | unit | `classify("", role)` y `classify("#/login", role)` con sesión | `home` | `js/routes.test.js` |
| UI-124 | TC-UI-124b | e2e | Sesión abierta en `#/tickets/1`; cambia el hash a `#/login` y luego a vacío | Inicio del rol en los dos | `e2e/routing.spec.js` |
| UI-124 | TC-UI-124c | unit | `open` + `hashChanged("#/login")` y `hashChanged("")` | `render(home)` y `replaceHash(home)`; sin pedidos | `js/session.test.js` |
| UI-126 | TC-UI-126a | unit | `classify(hash, null)` para `""`, `#/users`, `#/tickets/007`, `#/tickets/new`, `#/desconocido` y `#/login` | `login` para todos; `#/login` es `login` sin cambio | `js/routes.test.js` |
| UI-126 | TC-UI-126b | unit | `anonymous` + `hashChanged` con esos hashes | `render(login)` (solo si no se mostraba), `replaceHash("#/login")`, `notice: false`, sin efectos `request` | `js/session.test.js` |
| UI-126 | TC-UI-126c | unit | `mePending`, `meError` y `closing` + `hashChanged("#/users")` | Estado sin cambios y sin efectos (no aplica 126) | `js/session.test.js` |
| UI-126 | TC-UI-126d | e2e | Sin sesión en el login; cambia el hash a `""`, `#/users`, `#/tickets/abc` y `#/desconocido` | Siempre el login, sin aviso, `api.requests` sin pedidos nuevos y `location.hash == "#/login"` | `e2e/login.spec.js` |
| UI-126 | TC-UI-126e | e2e | Email escrito y `POST /login` retenido; cambia el hash a `#/users`; luego libera `200` y `GET /me` `200` | Mientras está retenido: el login sigue con el email escrito; al liberar, inicio del rol (G-03, opción A) | `e2e/login.spec.js` |
| UI-127 | TC-UI-127a | unit | `mePending{initial}` + `hashChanged`; `meError` + `hashChanged`; `mePending{login}` + `hashChanged` | Sin efectos; tras `200`, `initial` evalúa el hash que trae el evento y `login` va al inicio | `js/session.test.js` |
| UI-127 | TC-UI-127b | e2e | `GET /me` inicial retenido; cambia el hash a `#/account`; libera `200` (`Client`) | Mientras está retenido, sigue el indicador de carga; después, «Mi cuenta» | `e2e/boot.spec.js` |
| UI-127 | TC-UI-127c | e2e | `GET /me` `500` (error con «Reintentar»); cambia el hash a `#/account`; «Reintentar» con `200` | El error sigue tras el cambio de hash; después del reintento, «Mi cuenta» | `e2e/boot.spec.js` |
| UI-127 | TC-UI-127d | e2e | Login `200`; `GET /me` posterior retenido; cambia el hash a `#/account`; libera `200` | Carga durante la espera; después, inicio del rol (`#/tickets`) | `e2e/login.spec.js` |
| UI-127 | TC-UI-127e | e2e | `GET /me` inicial retenido; cambia el hash a `#/users`; libera `401` | Login sin aviso, `location.hash == "#/login"` | `e2e/boot.spec.js` |
| UI-128 | TC-UI-128a | unit | Cada transición que muestra el login (126, 08, 129, 12) | Incluye `replaceHash("#/login")` (no un `pushHash`) | `js/session.test.js` |
| UI-128 | TC-UI-128b | e2e | Mide `history.length` antes y después del login mostrado por 126, 08, 129 y 12 | `location.hash == "#/login"` y `history.length` no crece | `e2e/expiry.spec.js` |
| UI-129 | TC-UI-129a | e2e | `POST /logout` retenido; se libera con `204` | Login sin aviso, `location.hash == "#/login"` | `e2e/logout.spec.js` |
| UI-129 | TC-UI-129b | e2e | Ídem con `500` JSON | Ídem | `e2e/logout.spec.js` |
| UI-129 | TC-UI-129c | e2e | Ídem con `401` | Ídem (sin «Tu sesión venció») | `e2e/logout.spec.js` |
| UI-129 | TC-UI-129d | e2e | Ídem con `abort()` | Ídem | `e2e/logout.spec.js` |
| UI-129 | TC-UI-129e | unit | `closing` + `logoutSettled` con `204`, `500`, `401` y sin conexión | `anonymous{notice: false}`, `render(login)`, `replaceHash("#/login")`, `setInert(false)` | `js/session.test.js` |
| UI-129 | TC-UI-129f | e2e | **Servidor sembrado**: logout real del representante | Login sin aviso; un `GET /` posterior con `GET /me` real responde `401` y sigue el login | `e2e/live.spec.js` |
| UI-130 | TC-UI-130a | unit | `apiAnswered` con una época vieja y estados `200` y `401`, en `closing`, `anonymous` y en un `open` nuevo | Estado sin cambios y sin efectos | `js/session.test.js` |
| UI-130 | TC-UI-130b | e2e | Un `GET /tickets` retenido (enviado antes); `POST /logout` retenido; se libera el listado con `401` **antes** del logout y luego el logout | Ningún aviso de sesión vencida; las filas no cambian; al final, login sin aviso | `e2e/logout.spec.js` |
| UI-130 | TC-UI-130c | e2e | Ídem, pero el listado se libera con `200` **después** de la respuesta del logout | Login sin aviso y sin filas dibujadas | `e2e/logout.spec.js` |
| UI-130 | TC-UI-130d | e2e | Dos pedidos retenidos; uno responde `401` (sesión cerrada por 12); luego el otro responde `200` con filas | Login con el aviso de 12 y sin filas; ningún aviso ni dato adicional por el `200` tardío | `e2e/expiry.spec.js` |
| UI-131 | TC-UI-131a | unit | `closing` + `hashChanged("#/account")` | Sin efectos; la ruta mostrada no cambia | `js/session.test.js` |
| UI-131 | TC-UI-131b | e2e | Listado mostrado; `POST /logout` retenido; cambia el hash a `#/account` | Sigue el encabezado del listado y no hay pedidos nuevos; al liberar, login (no se comprueba el hash durante la espera, decisión 56) | `e2e/logout.spec.js` |
| UI-132 | TC-UI-132a | unit | Transiciones que muestran el inicio (07, 09, 19, 124) | Incluyen `replaceHash(home)` con `#/users` o `#/tickets` según el rol | `js/session.test.js` |
| UI-132 | TC-UI-132b | e2e | Tras 07, 09, 19 y 124: `location.hash` y `history.length` | `#/users` o `#/tickets`; el historial no crece | `e2e/routing.spec.js` |
| UI-133 | TC-UI-133a | unit | `closing` + `controlActivated` (paginación, filtro, búsqueda, acción, «Cerrar sesión»); `canSend(closing)` | Sin efectos; `canSend` falso; un cliente con ese `canSend` no llama a `fetch` | `js/session.test.js` |
| UI-133 | TC-UI-133b | e2e | `POST /logout` retenido; «Siguiente» (`click({ force: true })`), filtro (`selectOption` con `force`), búsqueda (`dispatchEvent("submit")`), «Cerrar» de un ticket (`force`) y «Cerrar sesión» otra vez | Cero pedidos nuevos; el número de página, las filas y el filtro mostrado no cambian | `e2e/logout.spec.js` |
| UI-133 | TC-UI-133c | e2e | Ídem con `dispatchEvent("click")` sobre un enlace de la navegación (`aria-disabled`) y un botón deshabilitado | Cero pedidos y la pantalla no cambia | `e2e/logout.spec.js` |
| UI-134 | TC-UI-134a | e2e | `POST /logout` retenido | Todo `button`, `input`, `select` y `textarea` de la navegación y de la pantalla tiene `disabled`, y todo enlace `aria-disabled="true"` | `e2e/logout.spec.js` |
| UI-134 | TC-UI-134b | unit | `isInert` en cada estado | Verdadero solo en `closing` | `js/session.test.js` |
| UI-14 | TC-UI-14a | unit | `confirmationMismatch("clave-uno-1", "clave-dos-2")` y con valores iguales | `true` y `false` | `js/forms.test.js` |
| UI-14 | TC-UI-14b | e2e | Nueva y confirmación distintas | Marca en el formulario y cero `POST /me/password` | `e2e/account.spec.js` |
| UI-15 | TC-UI-15a | e2e | `POST /me/password` `400` `invalid_current_password` | «La contraseña actual no es correcta.» en el formulario; sigue la navegación y `#/account` | `e2e/account.spec.js` |

### Navegación y pantallas por rol

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-16 | TC-UI-16a | e2e | Sesión de representante | La navegación tiene exactamente «Tickets», «Nuevo ticket», «Mi cuenta» y «Cerrar sesión» | `e2e/nav.spec.js` |
| UI-16 | TC-UI-16b | unit | `navItems("Representative")` | Esas cuatro entradas con sus rutas | `js/routes.test.js` |
| UI-17 | TC-UI-17a | e2e | Sesión de administrador | «Usuarios», «Categorías», «Tipos de producto», «Productos», «Tickets», «Mi cuenta», «Cerrar sesión» | `e2e/nav.spec.js` |
| UI-17 | TC-UI-17b | unit | `navItems("Admin")` | Esas siete entradas | `js/routes.test.js` |
| UI-18 | TC-UI-18a | e2e | Sesión de cliente | «Mis tickets», «Mi cuenta», «Cerrar sesión» | `e2e/nav.spec.js` |
| UI-18 | TC-UI-18b | unit | `navItems("Client")` | Esas tres entradas | `js/routes.test.js` |
| UI-19 | TC-UI-19a | unit | `classify`: `Representative` en `#/users` y `#/products`; `Client` en `#/tickets/new` y `#/categories`; `Admin` en `#/tickets/new` | `forbidden` (inicio del rol) | `js/routes.test.js` |
| UI-19 | TC-UI-19b | e2e | `Client` abre `#/users` | Listado de tickets y `location.hash == "#/tickets"` | `e2e/routing.spec.js` |
| UI-20 | TC-UI-20a | unit | `classify` con sesión: `#/desconocido`, `#/users/1`, `#/tickets/`, `#/` | `not_found`; `""` no (es `home`) | `js/routes.test.js` |
| UI-20 | TC-UI-20b | e2e | Sesión de `Admin` en `#/desconocido`; pulsa el enlace | «Página no encontrada»; el enlace lleva a «Usuarios» | `e2e/routing.spec.js` |
| UI-21 | TC-UI-21a | unit | `ticketActions(role, state)` para los tres roles y los tres estados; la función no recibe dueño ni representante | Solo cambian por rol y por las reglas 77 a 79 | `js/ticket-actions.test.js` |
| UI-21 | TC-UI-21b | e2e | Representante, ticket `InProgress`; «Cerrar» responde `409` `invalid_transition` | El botón se ofrece; se muestra «Esa acción no está permitida en el estado actual del ticket.» | `e2e/ticket-actions.spec.js` |
| UI-21 | TC-UI-21c | e2e | Cliente, ticket `New`; «Agregar hito» responde `403` `forbidden` | Se muestra «No tiene permiso para realizar esta acción.» | `e2e/ticket-actions.spec.js` |

### Tickets

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-22 | TC-UI-22a | e2e | Representante; `GET /tickets` devuelve una página con 3 tickets | Pedido `GET /tickets?page=1&page_size=20`; cada fila muestra id, nombre del cliente, etiqueta del estado y fecha `dd/mm/aaaa HH:mm` | `e2e/tickets-list.spec.js` |
| UI-22 | TC-UI-22b | e2e | **Servidor sembrado**: login del representante | Se ven sus tickets reales (20 filas y el total 25) | `e2e/live.spec.js` |
| UI-23 | TC-UI-23a | unit | `listQuery("/tickets", {state: "InProgress"}, 1)` | `/tickets?state=InProgress&page=1&page_size=20` | `js/query.test.js` |
| UI-23 | TC-UI-23b | e2e | Elige «En curso» en el filtro de estado | Pedido con `state=InProgress` y se muestran sus filas | `e2e/tickets-list.spec.js` |
| UI-107 | TC-UI-107a | unit | `q: "  impresora "` y `q: ""` | `q=impresora`; con vacío, sin `q` | `js/query.test.js` |
| UI-107 | TC-UI-107b | e2e | Escribe «impresora» y envía la búsqueda | Pedido con `q=impresora` y se muestra el resultado | `e2e/tickets-list.spec.js` |
| UI-108 | TC-UI-108a | unit | `order: "asc"` y `"desc"` | `order=asc` / `order=desc` | `js/query.test.js` |
| UI-108 | TC-UI-108b | e2e | Elige «Más antiguos primero» | Pedido con `order=asc` | `e2e/tickets-list.spec.js` |
| UI-24 | TC-UI-24a | unit | `client_id: 7` | `client_id=7` | `js/query.test.js` |
| UI-24 | TC-UI-24b | e2e | Representante; `GET /clients` devuelve `[{id: 7, name: "Ana Gómez"}]`; elige «Ana Gómez» | `GET /clients` sin `page`; luego `GET /tickets?client_id=7&page=1&page_size=20` | `e2e/tickets-list.spec.js` |
| UI-24 | TC-UI-24c | e2e | `Admin`; ídem | Ídem | `e2e/tickets-list.spec.js` |
| UI-25 | TC-UI-25a | unit | `representative_id: 3` | `representative_id=3` | `js/query.test.js` |
| UI-25 | TC-UI-25b | e2e | `Admin`; `GET /representatives` devuelve «Raúl Pérez»; lo elige | `GET /representatives` sin `page`; luego el listado con `representative_id=3` | `e2e/tickets-list.spec.js` |
| UI-26 | TC-UI-26a | unit | `listQuery` de `/users`, `/products` y `/tickets` | Siempre `page` y `page_size=20` | `js/query.test.js` |
| UI-26 | TC-UI-26b | e2e | Abre `#/tickets` | El pedido lleva `page=1&page_size=20` | `e2e/tickets-list.spec.js` |
| UI-26 | TC-UI-26c | e2e | Abre `#/users` | Ídem para `GET /users` | `e2e/users.spec.js` |
| UI-26 | TC-UI-26d | e2e | Abre `#/products` | Ídem para `GET /products` | `e2e/products.spec.js` |
| UI-101 | TC-UI-101a | unit | `pageInfo({page: 2, page_size: 20, total: 45})` | Página 2, total 45 | `js/query.test.js` |
| UI-101 | TC-UI-101b | e2e | Página 1 con `total` 45 | Se ven «Anterior», «Siguiente», el número de página y «45 resultados» | `e2e/tickets-list.spec.js` |
| UI-102 | TC-UI-102a | unit | `nextPage` con filtros `{state, q}` | Página + 1 con los mismos filtros y `page_size` | `js/query.test.js` |
| UI-102 | TC-UI-102b | e2e | Con filtro de estado, pulsa «Siguiente» | Pedido con `page=2`, `page_size=20` y el mismo `state` | `e2e/tickets-list.spec.js` |
| UI-103 | TC-UI-103a | unit | `previousPage` en la página 3 | Página 2, mismos filtros | `js/query.test.js` |
| UI-103 | TC-UI-103b | e2e | En la página 2, pulsa «Anterior» | Pedido con `page=1` y los mismos filtros | `e2e/tickets-list.spec.js` |
| UI-104 | TC-UI-104a | unit | Página 3 + `applyFilter` (filtro, `q` y orden) | Página 1 en los tres | `js/query.test.js` |
| UI-104 | TC-UI-104b | e2e | En la página 2, cambia el filtro de estado | Pedido con `page=1` | `e2e/tickets-list.spec.js` |
| UI-105 | TC-UI-105a | unit | `hasPrevious` en la página 1 y en la 2 | `false` y `true` | `js/query.test.js` |
| UI-105 | TC-UI-105b | e2e | Página 1 | «Anterior» deshabilitado | `e2e/tickets-list.spec.js` |
| UI-106 | TC-UI-106a | unit | `hasNext` con `total` 0, 20, 21 y 40 en las páginas 1 y 2 | Falso cuando `page * 20 >= total` | `js/query.test.js` |
| UI-106 | TC-UI-106b | e2e | Última página (`page` 3, `total` 45) | «Siguiente» deshabilitado | `e2e/tickets-list.spec.js` |
| UI-27 | TC-UI-27a | e2e | Abre `#/tickets/7` | Pide `GET /tickets/7`, `/tickets/7/milestones` y `/tickets/7/state-changes`; muestra estado, cliente, representante, productos, hitos y cambios de estado | `e2e/ticket-detail.spec.js` |
| UI-27 | TC-UI-27b | e2e | **Servidor sembrado**: detalle del ticket con dos hitos y un cambio de estado | Se ven los dos hitos y el cambio de estado reales | `e2e/live.spec.js` |
| UI-97 | TC-UI-97a | unit | `isValidTicketId` y `classify` con `0`, `007`, `-1`, `1.5`, `abc`, `9223372036854775808` (inválidos) y `1`, `9223372036854775807` (válidos); `#/tickets/new` | Inválidos → `not_found`; válidos → detalle; `new` → nuevo ticket | `js/routes.test.js` |
| UI-97 | TC-UI-97b | e2e | Con sesión, abre `#/tickets/007` | «Página no encontrada» y cero pedidos a la API después del `GET /me` | `e2e/routing.spec.js` |
| UI-28 | TC-UI-28a | e2e | Hitos e historial devueltos en un orden no cronológico a propósito | Se muestran en el orden recibido, con contenido o estado (etiqueta), autor, rol (etiqueta) y fecha | `e2e/ticket-detail.spec.js` |
| UI-29 | TC-UI-29a | unit | `2026-01-01T12:00:00+00:00` en `America/Argentina/Buenos_Aires`, `Asia/Kolkata` y `UTC`; `2026-01-01T01:30:00Z` en Buenos Aires (cambia el día) | `01/01/2026 09:00`, `01/01/2026 17:30`, `01/01/2026 12:00`, `31/12/2025 22:30` | `js/dates.test.js` |
| UI-29 | TC-UI-29b | e2e | Contexto con `timezoneId: "America/Argentina/Buenos_Aires"` | El detalle muestra `01/01/2026 09:00` para `12:00 UTC` | `e2e/ticket-detail.spec.js` |
| UI-30 | TC-UI-30a | e2e | Representante abre `#/tickets/new` | Campos etiquetados «Cliente», «Primer mensaje» y «Productos» (opcional) y el botón de envío | `e2e/ticket-new.spec.js` |
| UI-31 | TC-UI-31a | e2e | Busca «ana»; `GET /clients?q=ana` devuelve dos clientes | Pedido sin `page`; el selector ofrece solo esos dos, por nombre | `e2e/ticket-new.spec.js` |
| UI-32 | TC-UI-32a | e2e | En el alta, busca «note» | `GET /products/available?q=note`; se ofrecen solo los devueltos | `e2e/ticket-new.spec.js` |
| UI-32 | TC-UI-32b | e2e | En el detalle (representante), busca productos para asociar | Ídem | `e2e/ticket-actions.spec.js` |
| UI-33 | TC-UI-33a | e2e | `POST /tickets` `201` `{"id": 15, ...}` | `location.hash == "#/tickets/15"` y se pide `GET /tickets/15` | `e2e/ticket-new.spec.js` |
| UI-34 | TC-UI-34a | e2e | Representante envía «Revisando» | `POST /tickets/7/milestones` con `{"content": "Revisando"}` | `e2e/ticket-actions.spec.js` |
| UI-34 | TC-UI-34b | e2e | Cliente envía «Gracias» | Ídem con su contenido | `e2e/ticket-actions.spec.js` |
| UI-35 | TC-UI-35a | e2e | Representante, ticket `New` | El formulario de hito ofrece «Comenzar a trabajar» | `e2e/ticket-actions.spec.js` |
| UI-35 | TC-UI-35b | unit | `ticketActions("Representative", "New")` | Incluye `startProgress` | `js/ticket-actions.test.js` |
| UI-36 | TC-UI-36a | e2e | Representante y cliente pulsan «Cerrar» | `POST /tickets/7/close` | `e2e/ticket-actions.spec.js` |
| UI-37 | TC-UI-37a | e2e | Ticket `Closed`; pulsa «Reabrir» | `POST /tickets/7/reopen` | `e2e/ticket-actions.spec.js` |
| UI-38 | TC-UI-38a | e2e | Representante elige dos productos y confirma | `POST /tickets/7/products` con `{"product_ids": [3, 4]}` | `e2e/ticket-actions.spec.js` |
| UI-39 | TC-UI-39a | e2e | «Quitar» junto al producto 3 | `DELETE /tickets/7/products/3` | `e2e/ticket-actions.spec.js` |
| UI-77 | TC-UI-77a | unit | `ticketActions(role, "Closed")` para representante y cliente | Sin `close` | `js/ticket-actions.test.js` |
| UI-77 | TC-UI-77b | e2e | Ticket `Closed` | No hay «Cerrar» | `e2e/ticket-actions.spec.js` |
| UI-78 | TC-UI-78a | unit | Ídem | Sin `milestone` | `js/ticket-actions.test.js` |
| UI-78 | TC-UI-78b | e2e | Ticket `Closed` | No hay formulario «Agregar hito» | `e2e/ticket-actions.spec.js` |
| UI-79 | TC-UI-79a | unit | `New` e `InProgress` | Sin `reopen` | `js/ticket-actions.test.js` |
| UI-79 | TC-UI-79b | e2e | Tickets `New` e `InProgress` | No hay «Reabrir» | `e2e/ticket-actions.spec.js` |
| UI-80 | TC-UI-80a | unit | `ticketActions("Client", "New")` | Sin `startProgress` | `js/ticket-actions.test.js` |
| UI-80 | TC-UI-80b | e2e | Cliente, ticket `New` | El formulario de hito no ofrece «Comenzar a trabajar» | `e2e/ticket-actions.spec.js` |
| UI-81 | TC-UI-81a | e2e | Representante marca «Comenzar a trabajar» y envía | Cuerpo `{"content": ..., "start_progress": true}` | `e2e/ticket-actions.spec.js` |
| UI-81 | TC-UI-81b | e2e | Sin marcar | El cuerpo no tiene `start_progress` | `e2e/ticket-actions.spec.js` |
| UI-40 | TC-UI-40a | e2e | Cliente, ticket `New` y otro `Closed` | Solo «Agregar hito» y «Cerrar» (en `New`) o «Reabrir» (en `Closed`); sin asociar ni «Quitar» | `e2e/ticket-actions.spec.js` |
| UI-40 | TC-UI-40b | unit | `ticketActions("Client", state)` | Subconjunto de `{milestone, close, reopen}` | `js/ticket-actions.test.js` |
| UI-41 | TC-UI-41a | e2e | `Admin` en `#/tickets` | Sin «Nuevo ticket» ni botones que modifiquen tickets (los filtros sí) | `e2e/tickets-list.spec.js` |
| UI-41 | TC-UI-41b | e2e | `Admin` en `#/tickets/7` | Ningún formulario ni botón de acción en el detalle | `e2e/ticket-detail.spec.js` |
| UI-41 | TC-UI-41c | unit | `ticketActions("Admin", state)` | Vacío para los tres estados | `js/ticket-actions.test.js` |
| UI-42 | TC-UI-42a | e2e | «Cerrar» `200`; las lecturas siguientes devuelven `Closed` y un cambio de estado nuevo | Después del `POST` se piden otra vez las tres lecturas y se muestra lo que devuelven (no lo arma la interfaz) | `e2e/ticket-actions.spec.js` |
| UI-43 | TC-UI-43a | e2e | `POST .../close` retenido | «Cerrar» deshabilitado; un clic con `force` no envía otro pedido | `e2e/ticket-actions.spec.js` |

### Administración

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-44 | TC-UI-44a | e2e | `GET /users` devuelve una página con un `Admin` activo y un `Client` inactivo | Nombre, email, «Administrador»/«Cliente» y «Activo»/«Inactivo» | `e2e/users.spec.js` |
| UI-82 | TC-UI-82a | e2e | Busca «gómez» | Pedido con `q=gómez` (codificado) y se muestra el resultado | `e2e/users.spec.js` |
| UI-83 | TC-UI-83a | e2e | Elige «Inactivo» y luego «Activo» | Pedidos con `is_active=false` y `is_active=true` | `e2e/users.spec.js` |
| UI-45 | TC-UI-45a | e2e | Alta con nombre, email, rol, contraseña y canal «WhatsApp» | `POST /users` con `name`, `email`, `role`, `password` y `preferred_channel` | `e2e/users.spec.js` |
| UI-45 | TC-UI-45b | e2e | Alta sin elegir canal | El cuerpo no tiene `preferred_channel` | `e2e/users.spec.js` |
| UI-84 | TC-UI-84a | e2e | Formulario de alta | El selector de rol ofrece «Administrador» (`Admin`), «Representante» y «Cliente» | `e2e/users.spec.js` |
| UI-85 | TC-UI-85a | e2e | `POST /users` `201` | «Usuario creado.» en la región de estado (G-04) | `e2e/users.spec.js` |
| UI-46 | TC-UI-46a | e2e | Edita el nombre de la cuenta 5 | `PATCH /users/5` con nombre, email y canal del formulario | `e2e/users.spec.js` |
| UI-47 | TC-UI-47a | e2e | Cuenta activa; «Dar de baja» | `POST /users/5/deactivate` | `e2e/users.spec.js` |
| UI-110 | TC-UI-110a | e2e | Cuenta inactiva; «Reactivar» | `POST /users/5/activate` | `e2e/users.spec.js` |
| UI-48 | TC-UI-48a | e2e | Restablecimiento con nueva y confirmación iguales | `POST /users/5/password` con solo `new_password`; el formulario no pide la anterior | `e2e/users.spec.js` |
| UI-100 | TC-UI-100a | e2e | Nueva y confirmación distintas | Marca en el formulario y cero pedidos | `e2e/users.spec.js` |
| UI-100 | TC-UI-100b | unit | `confirmationMismatch` con espacios al final (`"clave-uno-1 "` y `"clave-uno-1"`) | `true` (se comparan tal cual) | `js/forms.test.js` |
| UI-49 | TC-UI-49a | e2e | `GET /categories` devuelve dos | Se muestran las dos | `e2e/categories.spec.js` |
| UI-86 | TC-UI-86a | e2e | Alta «Impresión» | `POST /categories` con `{"name": "Impresión"}` | `e2e/categories.spec.js` |
| UI-87 | TC-UI-87a | e2e | Edita la categoría 3 | `PATCH /categories/3` con el nombre | `e2e/categories.spec.js` |
| UI-88 | TC-UI-88a | e2e | Busca «comp» | `GET /categories?q=comp` (sin `page`) | `e2e/categories.spec.js` |
| UI-50 | TC-UI-50a | e2e | `GET /product-types` con dos categorías | Un grupo por categoría con sus tipos | `e2e/product-types.spec.js` |
| UI-89 | TC-UI-89a | e2e | Busca «note» | `GET /product-types?q=note` | `e2e/product-types.spec.js` |
| UI-90 | TC-UI-90a | e2e | Alta con categoría elegida del selector | El selector se llena con `GET /categories`; `POST /product-types` con `name` y `category_id` | `e2e/product-types.spec.js` |
| UI-91 | TC-UI-91a | e2e | Cambia nombre y categoría del tipo 4 | `PATCH /product-types/4` con `name` y `category_id` | `e2e/product-types.spec.js` |
| UI-51 | TC-UI-51a | e2e | `GET /products` con uno activo y uno inactivo | Nombre, tipo, categoría y «Activo»/«Inactivo» | `e2e/products.spec.js` |
| UI-92 | TC-UI-92a | e2e | Busca «lenovo» | Pedido con `q=lenovo` | `e2e/products.spec.js` |
| UI-93 | TC-UI-93a | e2e | Elige «Inactivo» | Pedido con `is_active=false` | `e2e/products.spec.js` |
| UI-94 | TC-UI-94a | e2e | Elige una categoría (selector con `GET /categories`) | Pedido con `category_id` | `e2e/products.spec.js` |
| UI-95 | TC-UI-95a | e2e | Elige un tipo (selector con `GET /product-types`) | Pedido con `product_type_id` | `e2e/products.spec.js` |
| UI-52 | TC-UI-52a | e2e | Alta con tipo elegido (selector con `GET /product-types`) | `POST /products` con `name` y `product_type_id` | `e2e/products.spec.js` |
| UI-109 | TC-UI-109a | e2e | Cambia nombre y tipo del producto 9 | `PATCH /products/9` con `name` y `product_type_id` | `e2e/products.spec.js` |
| UI-53 | TC-UI-53a | e2e | Producto activo; «Dar de baja» | `POST /products/9/deactivate` | `e2e/products.spec.js` |
| UI-111 | TC-UI-111a | e2e | Producto inactivo; «Reactivar» | `POST /products/9/activate` | `e2e/products.spec.js` |
| UI-54 | TC-UI-54a | e2e | «Eliminar» en una categoría: primero «Cancelar», después «Confirmar» | Se abre el `<dialog>`; con «Cancelar», cero `DELETE`; con «Confirmar», un `DELETE /categories/3` | `e2e/categories.spec.js` |
| UI-54 | TC-UI-54b | e2e | Ídem en un tipo de producto | Ídem con `DELETE /product-types/4` | `e2e/product-types.spec.js` |
| UI-120 | TC-UI-120a | e2e | Usuarios en la página 2 con `q` e `is_active`; «Dar de baja» `200` | Se pide `GET /users` con la misma `q`, el mismo `is_active`, `page=2` y `page_size=20`, y se muestra lo devuelto | `e2e/users.spec.js` |
| UI-120 | TC-UI-120b | e2e | Productos con filtros; alta `201` | Se pide la página actual con los mismos filtros y `q` | `e2e/products.spec.js` |
| UI-120 | TC-UI-120c | e2e | Categorías con `q`; alta `201` | Se pide otra vez `GET /categories?q=...` (listado completo, sin `page`) | `e2e/categories.spec.js` |
| UI-120 | TC-UI-120d | e2e | Tipos con `q`; eliminación `204` | Se pide otra vez `GET /product-types?q=...` | `e2e/product-types.spec.js` |
| UI-120 | TC-UI-120e | unit | `reloadQuery` con filtros, `q` y página 3 | La misma URL de la página actual | `js/query.test.js` |
| UI-125 | TC-UI-125a | unit | `lastValidPage(41)`, `(40)`, `(1)` | 3, 2, 1 | `js/query.test.js` |
| UI-125 | TC-UI-125b | e2e | Usuarios en la página 3; tras «Dar de baja», la recarga devuelve `items: []` y `total: 40` | Se pide `page=2` con los mismos filtros y se muestra | `e2e/users.spec.js` |
| UI-125 | TC-UI-125c | e2e | Ídem en productos | Ídem | `e2e/products.spec.js` |

### Errores y mensajes en español

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-55 | TC-UI-55a | e2e | Para cada rol, cada pantalla (login, carga con error, no encontrada, tickets, detalle, nuevo, usuarios, categorías, tipos, productos, mi cuenta, pantalla inerte) | El `innerText` del `body` y el `document.title` no contienen ninguna palabra de `ENGLISH_WORDS` (palabra completa, sensible a mayúsculas) | `e2e/spanish.spec.js` |
| UI-55 | TC-UI-55b | unit | Valores de las tablas de `messages.js` y `labels.js` | Ninguna palabra de la lista | `js/messages.test.js` |
| UI-56 | TC-UI-56a | unit | Los 20 códigos de la tabla de mensajes | Cada uno da su texto exacto | `js/messages.test.js` |
| UI-56 | TC-UI-56b | e2e | Alta de categoría `409` `duplicate_category` | «Ya existe una categoría con ese nombre.» | `e2e/errors.spec.js` |
| UI-57 | TC-UI-57a | unit | `translateError(400 {"error": "validation_error", "fields": {"email": "invalid", "name": "required"}}, "form")` | `{email: "El valor ingresado no es válido", name: "Este campo es obligatorio"}` | `js/messages.test.js` |
| UI-57 | TC-UI-57b | e2e | Alta de usuario con esa respuesta | Cada campo muestra su marca junto a él | `e2e/users.spec.js` |
| UI-58 | TC-UI-58a | unit | Código desconocido `{"error": "algo_raro"}` y `500` `{"error": "internal_error"}` | «Ocurrió un error inesperado. Intente nuevamente.» | `js/messages.test.js` |
| UI-58 | TC-UI-58b | e2e | Acción con `500` JSON que incluye un `detail` interno | Mensaje genérico; el `detail` no aparece | `e2e/errors.spec.js` |
| UI-59 | TC-UI-59a | unit | Sin conexión; `502` con HTML; `400` con JSON sin `error` de texto; `204` | Los tres primeros dan «No se pudo conectar con el servidor. Intente nuevamente.»; `204` es éxito | `js/messages.test.js` |
| UI-59 | TC-UI-59b | e2e | Listado con `route.abort` | Mensaje de sin conexión | `e2e/errors.spec.js` |
| UI-59 | TC-UI-59c | unit | Cliente con `fakeFetch` que lanza `TypeError`, que devuelve `204` y que devuelve `text/html` | `{networkError: true}`, `{ok: true, body: null}`, `{ok: false, body: null}` | `js/api-client.test.js` |
| UI-119 | TC-UI-119a | unit | `translateError(400 validation_error {fields: {page: "invalid"}}, "list")` | Mensaje genérico, sin marcas | `js/messages.test.js` |
| UI-119 | TC-UI-119b | e2e | `GET /tickets` `400` `validation_error` con `fields.state` | Mensaje genérico y ningún campo marcado | `e2e/tickets-list.spec.js` |
| UI-96 | TC-UI-96a | unit | `stateLabel`, `roleLabel`, `activeLabel` con los códigos de la tabla | Nuevo, En curso, Cerrado, Cliente, Representante, Administrador, Activo, Inactivo | `js/labels.test.js` |
| UI-96 | TC-UI-96b | e2e | Listado, detalle y usuarios | Se ven las etiquetas, nunca `InProgress`, `Representative` ni `true` | `e2e/errors.spec.js` |
| UI-123 | TC-UI-123a | unit | `stateLabel("Escalado")`, `roleLabel("Auditor")` | Devuelven el código tal cual | `js/labels.test.js` |
| UI-123 | TC-UI-123b | e2e | Ticket con estado `Escalado` | La fila y el detalle muestran «Escalado» | `e2e/errors.spec.js` |

### Seguridad

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-60 | TC-UI-60a | unit | `request` con `fakeFetch` | `init.headers` sin `Authorization`; `init.credentials == "same-origin"`; URL sin `token` | `js/api-client.test.js` |
| UI-60 | TC-UI-60b | e2e | Recorrido con registro de pedidos | Ningún pedido lleva `Authorization` ni `token`, `api_key` o `secret` en la URL | `e2e/security.spec.js` |
| UI-61 | TC-UI-61a | unit | Escaneo de `app/static/**` | Sin `-----BEGIN ... PRIVATE KEY-----`, `AKIA[0-9A-Z]{16}`, `(api_key\|secret\|token)\s*[:=]\s*["'][^"']+["']` ni `Bearer\s+[A-Za-z0-9._-]+` | `js/static-scan.test.js` |
| UI-62 | TC-UI-62a | e2e | Tras iniciar sesión y navegar | `localStorage.length == 0`, `sessionStorage.length == 0`, `document.cookie` sin rol, email ni nombre y `location.hash` sin ellos | `e2e/security.spec.js` |
| UI-62 | TC-UI-62b | unit | Escaneo de `app/static/js/**` | Sin `localStorage`, `sessionStorage` ni `document.cookie` | `js/static-scan.test.js` |
| UI-63 | TC-UI-63a | e2e | Nombre del cliente `<img src=x onerror="window.__xss=1">` y un hito `<b>hola</b>` | Se ven como texto literal; no hay `img` ni `b` creados y `window.__xss` no existe | `e2e/errors.spec.js` |
| UI-63 | TC-UI-63b | unit | Escaneo de `app/static/js/**` | Sin `innerHTML`, `outerHTML`, `insertAdjacentHTML` ni `document.write` | `js/static-scan.test.js` |
| UI-64 | TC-UI-64a | e2e | Cambio de contraseña con `204` y con `400` | Los tres campos de contraseña quedan vacíos en los dos casos | `e2e/account.spec.js` |
| UI-64 | TC-UI-64b | e2e | Login con `401` | El campo de contraseña queda vacío (el email se conserva) | `e2e/login.spec.js` |
| UI-64 | TC-UI-64c | e2e | Alta de usuario y restablecimiento, con éxito y con error | Los campos de contraseña quedan vacíos | `e2e/users.spec.js` |
| UI-65 | TC-UI-65a | unit | Escaneo de `index.html` y de `app/static/js/**` | Sin atributos `on*=`, `style=`, URLs `javascript:` ni `<script>` sin `src` | `js/static-scan.test.js` |
| UI-65 | TC-UI-65b | e2e | `/` servido con `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'` (con `route.fetch` + `route.fulfill`); login y recorrido de pantallas | Cero eventos `securitypolicyviolation` y ningún mensaje de consola de CSP | `e2e/security.spec.js` |

### Accesibilidad y diseño adaptable

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-66 | TC-UI-66a | e2e | Abre `/` | `document.documentElement.lang == "es"` | `e2e/a11y.spec.js` |
| UI-112 | TC-UI-112a | e2e | Recorre cada pantalla | `document.title` cambia y nombra la pantalla («Usuarios · Mesa de ayuda», etc.) | `e2e/titles.spec.js` |
| UI-67 | TC-UI-67a | e2e | Cada formulario de cada pantalla | Todo `input`, `select` y `textarea` tiene un `label` asociado y visible | `e2e/a11y.spec.js` |
| UI-68 | TC-UI-68a | e2e | Solo teclado (`Tab`, `Enter`, `Space`, flechas en `select`): login, ir a «Nuevo ticket», crear, abrir el detalle, cerrar el ticket, cerrar sesión | El recorrido termina sin usar el ratón | `e2e/a11y.spec.js` |
| UI-113 | TC-UI-113a | e2e | Cada pantalla | No hay `[role=button]`, `[onclick]` ni `div`/`span` con `tabindex`; las acciones son `button`, `a[href]`, campos o `dialog` | `e2e/a11y.spec.js` |
| UI-114 | TC-UI-114a | e2e | Enfoca con `Tab` cada control de una pantalla | `outline-style` distinto de `none` (o `box-shadow` distinto del estado sin foco) | `e2e/a11y.spec.js` |
| UI-69 | TC-UI-69a | e2e | Un error y una confirmación | El error está dentro de `role="alert"` y la confirmación dentro de `role="status"` (`aria-live`) | `e2e/a11y.spec.js` |
| UI-70 | TC-UI-70a | e2e | Viewport de 360 × 740 en cada pantalla, con tablas de 8 columnas | `scrollWidth <= clientWidth` del documento; la tabla se desplaza dentro de su contenedor | `e2e/a11y.spec.js` |
| UI-71 | TC-UI-71a | e2e | `GET /tickets` retenido | Indicador «Cargando…» visible mientras está retenido y oculto después | `e2e/tickets-list.spec.js` |
| UI-71 | TC-UI-71b | e2e | `GET /me` retenido | Indicador visible durante la carga | `e2e/boot.spec.js` |
| UI-115 | TC-UI-115a | e2e | `GET /tickets` con `items: []`, `total: 0` | «No hay resultados» | `e2e/tickets-list.spec.js` |
| UI-115 | TC-UI-115b | e2e | Usuarios, productos, categorías y tipos vacíos | «No hay resultados» en cada uno | `e2e/a11y.spec.js` |
| UI-72 | TC-UI-72a | e2e | Cada pantalla, incluida la inerte, en reposo y con un mensaje de error | Todo nodo de texto visible tiene `contrastRatio >= 4.5` con su fondo efectivo | `e2e/a11y.spec.js` |

### Estructura verificable

| Spec | Caso | Nivel | Datos / preparación | Resultado esperado | Archivo |
|------|------|-------|---------------------|--------------------|---------|
| UI-73 | TC-UI-73a | unit | `poisonGlobals()`; importa cada archivo de `core/` y ejecuta una función de cada uno | No lanza | `js/purity.test.js` |
| UI-73 | TC-UI-73b | unit | Escaneo de `core/*.js` | Ningún `\bfetch\b`, `\bdocument\b` ni `\bwindow\b`; solo importa de `core/` | `js/purity.test.js` |
| UI-74 | TC-UI-74a | unit | Lee `index.html`; importa los módulos de `core/` con `import()` | `<script type="module" src="/static/js/app.js">`; los módulos exponen `export` (la importación funciona) | `js/purity.test.js` |
| UI-75 | TC-UI-75a | unit | `createApiClient(fakeFetch)`; `request("POST", "/login", {...})` | `fakeFetch` recibe `/login`, método `POST` y el cuerpo JSON; la respuesta se clasifica | `js/api-client.test.js` |
| UI-75 | TC-UI-75b | unit | Ídem con `poisonGlobals()` | Funciona igual: solo usa el `fetch` inyectado | `js/api-client.test.js` |
| UI-76 | TC-UI-76a | integration | Lee `package.json` | No tiene la clave `dependencies` | `test_traceability.py` |
| UI-76 | TC-UI-76b | integration | Ídem | `scripts["test:js"]` contiene `node --test` | `test_traceability.py` |
| UI-98 | TC-UI-98a | integration | Lee `playwright.config.js` y `tests/ui/e2e/` | El archivo existe, nombra `tests/ui/e2e` como `testDir` y hay al menos un `*.spec.js` | `test_traceability.py` |
| UI-99 | TC-UI-99a | integration | Todas las pruebas de esta área (títulos y docstrings) | Cumplen `^SPEC-UI-\d+(, SPEC-UI-\d+)* [\x20-\x7E]+$` y los títulos son literales | `test_traceability.py` |
| UI-99 | TC-UI-99b | integration | Textos de muestra con `test(...)`, `it(...)`, `describe(...)`, `test.describe(...)` y una plantilla con `${}` | El extractor toma solo los de prueba e informa la plantilla | `test_traceability.py` |
| UI-121 | TC-UI-121a | integration | IDs de `spec.md` y citas de todo el repo | Cada uno de los 134 IDs tiene al menos una cita | `test_traceability.py` |
| UI-121 | TC-UI-121b | integration | Lectura de `spec.md` | Lee 134 IDs, solo de las filas de las tablas (no de las decisiones) | `test_traceability.py` |

### Casos de otras áreas que esta área completa

| Spec | Caso | Nivel | Resultado esperado | Archivo | Task |
|------|------|-------|--------------------|---------|------|
| PLT-23 | TC-PLT-23d | integration | Existe la regla `GET /` y no figura en los `paths` del contrato | `tests/integration/platform/test_api_docs.py` | T-UI-02 |
| USR-49 | TC-USR-49b (parte `GET /` y `GET /static/css/app.css`) | integration | Sin sesión, ninguno responde `authentication_required` (los dos `200`) | `tests/integration/users/test_route_guard.py` | T-UI-02 |

## Casos borde

- Hash vacío con y sin sesión (TC-UI-07a, 124a, 124c, 126a); `#/login` con sesión (07b, 07d, 124b); `#/tickets/new` antes que `#/tickets/{id}` (97a).
- Validez de `{id}`: `0`, `007`, `-1`, `1.5`, `abc`, `9223372036854775808` inválidos y `9223372036854775807` válido (97a); `{id}` inválido sin pedidos (97b).
- `GET /me` con `200`, `401`, `5xx` JSON, `403` JSON, `404` sin cuerpo y sin conexión, en la carga, tras el login y en el reintento (07a a 08c, 117a a 118d).
- Cambios de hash con `GET /me` pendiente, con error y con `POST /logout` pendiente (127a a 127e, 131a, 131b); con `POST /login` pendiente (126e).
- `POST /logout` con `204`, `500`, `401` y abortado (129a a 129e); respuestas previas `401` y `200` liberadas antes y después (130b, 130c) y tras una sesión vencida (130d).
- Controles activados con la pantalla inerte por clic forzado, `selectOption` forzado y `dispatchEvent` (133b, 133c).
- Paginación con `total` 0, exacto (20, 40) y con resto (21, 45); última página vaciada por una baja (106a, 125a a 125c).
- `q` con espacios y vacío (107a); texto con acentos codificado (82a).
- Fechas que cruzan el día por la zona (29a).
- `204` sin cuerpo como éxito; `502` HTML y JSON sin `error` como sin conexión (59a, 59c).
- Códigos de estado y de rol desconocidos (123a, 123b); texto de la API con HTML (63a).
- Confirmación con espacios al final (100b).
- Historial que no crece al fijar `#/login` y el inicio del rol (128b, 132b).

## RNF cubiertos

| RNF | Casos |
|-----|-------|
| RNF 1 (TDD) | Cada task escribe primero su prueba de `pytest`, `node --test` o Playwright y la ve fallar (o registra por qué no tiene fase roja propia) |
| RNF 2 (autenticación robusta) | TC-UI-60a, 60b (solo la cookie), 61a (sin secretos), 62a, 62b (sin identidad en el navegador), 63a, 63b (texto como texto), 64a a 64c (contraseñas vaciadas), 65a, 65b (CSP estricta), 12c (sesión vencida), 19b (rol sin permiso), 10b (mensaje genérico) |
| RNF 7 (API documentada) | TC-PLT-23a a 23d: las rutas de la UI existen y quedan fuera del contrato |
| RNF 8 (interfaz servida por la API) | TC-UI-01a a 03c, 05a, 05b, 06a, 06b, 74a, 65b |
| RNF 9 (pruebas de la interfaz) | TC-UI-73a, 73b, 74a, 75a, 75b, 76a, 76b, 98a, 99a, 99b, 121a, 121b y el CI de T-UI-17 |
| RNF 10 (paginación) | TC-UI-26a a 26d, 101a a 106b, 120a, 120b, 120e, 125a a 125c |

## Trazabilidad spec → casos

Mecanismos: **P** = `pytest`, **N** = `node --test`, **W** = Playwright (con API simulada; **W\*** contra el servidor sembrado).

| Spec | Casos | Mecanismo | Task |
|------|-------|-----------|------|
| UI-01 | 01a, 01b | P | T-UI-02 |
| UI-02 | 02a, 02b, 02c | P | T-UI-02, 18 |
| UI-03 | 03a, 03b, 03c | P | T-UI-02 |
| UI-04 | 04a, 04b | N, W | T-UI-03, 20 |
| UI-05 | 05a, 05b | N, W | T-UI-14, 33 |
| UI-06 | 06a, 06b | N, W | T-UI-14, 33 |
| UI-07 | 07a, 07b, 07c, 07d | N, W | T-UI-11, 18 |
| UI-08 | 08a, 08b, 08c | N, W | T-UI-11, 18 |
| UI-09 | 09a, 09b, 09c | N, W, W\* | T-UI-11, 19, 35 |
| UI-10 | 10a, 10b | N, W | T-UI-05, 19 |
| UI-11 | 11a, 11b, 11c | N, W | T-UI-12, 30 |
| UI-12 | 12a, 12b, 12c | N, W | T-UI-12, 31 |
| UI-13 | 13a | W | T-UI-21 |
| UI-14 | 14a, 14b | N, W | T-UI-09, 21 |
| UI-15 | 15a | W | T-UI-21 |
| UI-16 | 16a, 16b | W, N | T-UI-20, 03 |
| UI-17 | 17a, 17b | W, N | T-UI-20, 03 |
| UI-18 | 18a, 18b | W, N | T-UI-20, 03 |
| UI-19 | 19a, 19b | N, W | T-UI-03, 20 |
| UI-20 | 20a, 20b | N, W | T-UI-03, 20 |
| UI-21 | 21a, 21b, 21c | N, W | T-UI-08, 24 |
| UI-22 | 22a, 22b | W, W\* | T-UI-22, 35 |
| UI-23 | 23a, 23b | N, W | T-UI-04, 22 |
| UI-24 | 24a, 24b, 24c | N, W | T-UI-04, 22 |
| UI-25 | 25a, 25b | N, W | T-UI-04, 22 |
| UI-26 | 26a, 26b, 26c, 26d | N, W | T-UI-04, 22, 26, 29 |
| UI-27 | 27a, 27b | W, W\* | T-UI-23, 35 |
| UI-28 | 28a | W | T-UI-23 |
| UI-29 | 29a, 29b | N, W | T-UI-07, 23 |
| UI-30 | 30a | W | T-UI-25 |
| UI-31 | 31a | W | T-UI-25 |
| UI-32 | 32a, 32b | W | T-UI-25, 24 |
| UI-33 | 33a | W | T-UI-25 |
| UI-34 | 34a, 34b | W | T-UI-24 |
| UI-35 | 35a, 35b | W, N | T-UI-24, 08 |
| UI-36 | 36a | W | T-UI-24 |
| UI-37 | 37a | W | T-UI-24 |
| UI-38 | 38a | W | T-UI-24 |
| UI-39 | 39a | W | T-UI-24 |
| UI-40 | 40a, 40b | W, N | T-UI-24, 08 |
| UI-41 | 41a, 41b, 41c | W, N | T-UI-22, 23, 08 |
| UI-42 | 42a | W | T-UI-24 |
| UI-43 | 43a | W | T-UI-24 |
| UI-44 | 44a | W | T-UI-26 |
| UI-45 | 45a, 45b | W | T-UI-26 |
| UI-46 | 46a | W | T-UI-26 |
| UI-47 | 47a | W | T-UI-26 |
| UI-48 | 48a | W | T-UI-26 |
| UI-49 | 49a | W | T-UI-27 |
| UI-50 | 50a | W | T-UI-28 |
| UI-51 | 51a | W | T-UI-29 |
| UI-52 | 52a | W | T-UI-29 |
| UI-53 | 53a | W | T-UI-29 |
| UI-54 | 54a, 54b | W | T-UI-27, 28 |
| UI-55 | 55a, 55b | W, N | T-UI-32, 05 |
| UI-56 | 56a, 56b | N, W | T-UI-05, 32 |
| UI-57 | 57a, 57b | N, W | T-UI-05, 26 |
| UI-58 | 58a, 58b | N, W | T-UI-05, 32 |
| UI-59 | 59a, 59b, 59c | N, W, N | T-UI-05, 32, 10 |
| UI-60 | 60a, 60b | N, W | T-UI-10, 33 |
| UI-61 | 61a | N | T-UI-14 |
| UI-62 | 62a, 62b | W, N | T-UI-33, 14 |
| UI-63 | 63a, 63b | W, N | T-UI-32, 14 |
| UI-64 | 64a, 64b, 64c | W | T-UI-21, 19, 26 |
| UI-65 | 65a, 65b | N, W | T-UI-14, 33 |
| UI-66 | 66a | W | T-UI-15 |
| UI-67 | 67a | W | T-UI-34 |
| UI-68 | 68a | W | T-UI-34 |
| UI-69 | 69a | W | T-UI-34 |
| UI-70 | 70a | W | T-UI-34 |
| UI-71 | 71a, 71b | W | T-UI-22, 18 |
| UI-72 | 72a | W | T-UI-34 |
| UI-73 | 73a, 73b | N | T-UI-13 |
| UI-74 | 74a | N | T-UI-13 |
| UI-75 | 75a, 75b | N | T-UI-10 |
| UI-76 | 76a, 76b | P | T-UI-01 |
| UI-77 | 77a, 77b | N, W | T-UI-08, 24 |
| UI-78 | 78a, 78b | N, W | T-UI-08, 24 |
| UI-79 | 79a, 79b | N, W | T-UI-08, 24 |
| UI-80 | 80a, 80b | N, W | T-UI-08, 24 |
| UI-81 | 81a, 81b | W | T-UI-24 |
| UI-82 | 82a | W | T-UI-26 |
| UI-83 | 83a | W | T-UI-26 |
| UI-84 | 84a | W | T-UI-26 |
| UI-85 | 85a | W | T-UI-26 |
| UI-86 | 86a | W | T-UI-27 |
| UI-87 | 87a | W | T-UI-27 |
| UI-88 | 88a | W | T-UI-27 |
| UI-89 | 89a | W | T-UI-28 |
| UI-90 | 90a | W | T-UI-28 |
| UI-91 | 91a | W | T-UI-28 |
| UI-92 | 92a | W | T-UI-29 |
| UI-93 | 93a | W | T-UI-29 |
| UI-94 | 94a | W | T-UI-29 |
| UI-95 | 95a | W | T-UI-29 |
| UI-96 | 96a, 96b | N, W | T-UI-06, 32 |
| UI-97 | 97a, 97b | N, W | T-UI-03, 20 |
| UI-98 | 98a | P | T-UI-15 |
| UI-99 | 99a, 99b | P | T-UI-16 |
| UI-100 | 100a, 100b | W, N | T-UI-26, 09 |
| UI-101 | 101a, 101b | N, W | T-UI-04, 22 |
| UI-102 | 102a, 102b | N, W | T-UI-04, 22 |
| UI-103 | 103a, 103b | N, W | T-UI-04, 22 |
| UI-104 | 104a, 104b | N, W | T-UI-04, 22 |
| UI-105 | 105a, 105b | N, W | T-UI-04, 22 |
| UI-106 | 106a, 106b | N, W | T-UI-04, 22 |
| UI-107 | 107a, 107b | N, W | T-UI-04, 22 |
| UI-108 | 108a, 108b | N, W | T-UI-04, 22 |
| UI-109 | 109a | W | T-UI-29 |
| UI-110 | 110a | W | T-UI-26 |
| UI-111 | 111a | W | T-UI-29 |
| UI-112 | 112a | W | T-UI-18 |
| UI-113 | 113a | W | T-UI-34 |
| UI-114 | 114a | W | T-UI-34 |
| UI-115 | 115a, 115b | W | T-UI-22, 34 |
| UI-116 | 116a, 116b | N, W | T-UI-11, 18 |
| UI-117 | 117a, 117b, 117c, 117d | N, W | T-UI-11, 18, 19 |
| UI-118 | 118a, 118b, 118c, 118d | N, W | T-UI-11, 18, 19 |
| UI-119 | 119a, 119b | N, W | T-UI-05, 22 |
| UI-120 | 120a, 120b, 120c, 120d, 120e | W, N | T-UI-26, 29, 27, 28, 04 |
| UI-121 | 121a, 121b | P | T-UI-36 |
| UI-122 | 122a, 122b | W | T-UI-21 |
| UI-123 | 123a, 123b | N, W | T-UI-06, 32 |
| UI-124 | 124a, 124b, 124c | N, W | T-UI-03, 20, 12 |
| UI-125 | 125a, 125b, 125c | N, W | T-UI-04, 26, 29 |
| UI-126 | 126a, 126b, 126c, 126d, 126e | N, W | T-UI-03, 11, 19 |
| UI-127 | 127a, 127b, 127c, 127d, 127e | N, W | T-UI-11, 18, 19 |
| UI-128 | 128a, 128b | N, W | T-UI-11, 31 |
| UI-129 | 129a, 129b, 129c, 129d, 129e, 129f | W, N, W\* | T-UI-30, 12, 35 |
| UI-130 | 130a, 130b, 130c, 130d | N, W | T-UI-12, 30, 31 |
| UI-131 | 131a, 131b | N, W | T-UI-12, 30 |
| UI-132 | 132a, 132b | N, W | T-UI-11, 20 |
| UI-133 | 133a, 133b, 133c | N, W | T-UI-12, 30 |
| UI-134 | 134a, 134b | W, N | T-UI-30, 12 |

## Resumen

255 casos sobre 134 specs (todas con al menos un caso; las de la fila de Playwright de la tabla de verificación tienen al menos uno de Playwright, y las de la fila de `node --test`, al menos uno de `node --test`): **15** `pytest` (integration), **78** `node --test` (unit) y **162** Playwright (e2e: 158 con API simulada y 4 contra el servidor sembrado). Más 2 casos de otras áreas que se completan acá (TC-PLT-23d y TC-USR-49b). Si G-01 se resuelve con la opción A, se suman 2 casos `node --test` y 2 de Playwright con IDs de la spec nueva.
