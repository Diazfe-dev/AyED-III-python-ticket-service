# 07 — Interfaz web

Origen: RF 1.7 · Relacionados: RNF 2, RNF 4, RNF 8, RNF 9 · Depende de: SPEC-PLT-10, SPEC-PLT-15, SPEC-PLT-17 a SPEC-PLT-23 ([00-platform](../00-platform/spec.md)) · SPEC-USR-14 a SPEC-USR-17, SPEC-USR-27 a SPEC-USR-48 ([01-users](../01-users/spec.md)) · SPEC-PTY-21 a SPEC-PTY-23 ([02-product-types](../02-product-types/spec.md)) · SPEC-PRD-22 a SPEC-PRD-29 ([03-products](../03-products/spec.md)) · SPEC-TKT-32 a SPEC-TKT-46 ([04-tickets](../04-tickets/spec.md)) · SPEC-MLS-12 ([05-milestones](../05-milestones/spec.md))

Panel web simple, en HTML, JavaScript y CSS planos, que consume la API JSON del mismo origen. Es una página única con rutas por hash. No contiene reglas de negocio: cada decisión (permisos, propiedad, transiciones) es de la API, y la interfaz traduce sus respuestas a mensajes en español.

Rutas por hash (`#/...`) y pantallas por rol:

| Ruta | Pantalla | Representante | Administrador | Cliente |
|------|----------|:-------------:|:-------------:|:-------:|
| `#/login` | Inicio de sesión | público | público | público |
| `#/tickets` | Listado de tickets (inicio de Representante y Cliente) | asignados | todos, solo lectura | propios |
| `#/tickets/new` | Nuevo ticket | ✅ | ❌ | ❌ |
| `#/tickets/{id}` | Detalle del ticket | ✅ | solo lectura | ✅ |
| `#/users` | Usuarios (inicio del Administrador) | ❌ | ✅ | ❌ |
| `#/categories` | Categorías | ❌ | ✅ | ❌ |
| `#/product-types` | Tipos de producto | ❌ | ✅ | ❌ |
| `#/products` | Productos | ❌ | ✅ | ❌ |
| `#/account` | Cambio de la contraseña propia | ✅ | ✅ | ✅ |

## Servido y rutas

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-01 | Por evento | **Cuando** se solicita `GET /`, **el sistema deberá** responder `200` con la página HTML de la interfaz (`text/html`), sin requerir autenticación. | RF 1.7.1, RNF 8 |
| SPEC-UI-02 | Por evento | **Cuando** se solicita `GET /static/<ruta>` de un archivo de la interfaz, **el sistema deberá** responder `200` con el archivo y su tipo de contenido, sin requerir autenticación. | RF 1.7.1, RNF 8 |
| SPEC-UI-03 | No deseado | **Si** se solicita un archivo inexistente bajo `/static/`, **entonces el sistema deberá** responder `404` con un cuerpo JSON de error (SPEC-PLT-15). | RF 1.7.1, RNF 7 |
| SPEC-UI-04 | Ubicuo | **El sistema deberá** ser una única página que cambia de pantalla según el hash de la URL (tabla de rutas), sin recargar la página ni requerir otra ruta del servidor. | RF 1.7.1, RNF 8 |
| SPEC-UI-05 | Ubicuo | **El sistema deberá** llamar a la API solo con rutas relativas del mismo origen. | RF 1.7.1, RNF 8 |
| SPEC-UI-06 | Ubicuo | **El sistema deberá** funcionar sin paso de compilación y sin cargar scripts, estilos ni fuentes de orígenes externos. | RNF 8 |

## Sesión, identidad y contraseña

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-07 | Por evento | **Cuando** se carga la interfaz, **el sistema deberá** consultar `GET /me` y, si responde `200`, mostrar el inicio del rol recibido (`#/users` para `Admin`, `#/tickets` para `Representative` y `Client`) o la pantalla pedida si su rol la permite. | RF 1.7.5, RF 1.1.8 |
| SPEC-UI-08 | No deseado | **Si** `GET /me` responde `401`, **entonces la interfaz deberá** mostrar la pantalla de inicio de sesión (`#/login`). | RF 1.7.5 |
| SPEC-UI-09 | Por evento | **Cuando** el usuario envía su email y su contraseña en `#/login` y `POST /login` responde `200`, **el sistema deberá** consultar `GET /me` y mostrar el inicio de su rol. | RF 1.7.5, SPEC-USR-14 |
| SPEC-UI-10 | No deseado | **Si** `POST /login` responde `401` (`invalid_credentials`), **entonces la interfaz deberá** mostrar el mensaje genérico de credenciales inválidas, sin indicar el motivo, y mantenerse en `#/login`. | RF 1.7.5, SPEC-USR-15 |
| SPEC-UI-11 | Por evento | **Cuando** el usuario pulsa «Cerrar sesión», **el sistema deberá** llamar a `POST /logout`, descartar todo dato en memoria de la sesión y mostrar `#/login`. | RF 1.7.5, SPEC-USR-17 |
| SPEC-UI-12 | No deseado | **Si** cualquier respuesta de la API, salvo la de `POST /login`, es `401`, **entonces la interfaz deberá** tratar la sesión como cerrada: descartar los datos en memoria y mostrar `#/login` con un aviso de sesión vencida. | RF 1.7.5, SPEC-USR-16 |
| SPEC-UI-13 | Por evento | **Cuando** el usuario envía en `#/account` su contraseña actual, la nueva y su confirmación, **el sistema deberá** llamar a la API para cambiarla y mostrar un mensaje de confirmación. | RF 1.7.5, RF 1.1.7 |
| SPEC-UI-14 | No deseado | **Si** la nueva contraseña y su confirmación no coinciden, **entonces la interfaz deberá** indicarlo en el formulario sin enviar el pedido a la API. | RF 1.7.5 |
| SPEC-UI-15 | No deseado | **Si** la API rechaza la contraseña actual (`invalid_current_password`), **entonces la interfaz deberá** mostrar ese error en el formulario sin cerrar la sesión. | RF 1.7.5, SPEC-USR-38 |

## Navegación y pantallas por rol

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-16 | Complejo | **Mientras** la sesión es de un representante, **cuando** se muestra la navegación, **el sistema deberá** ofrecer «Tickets», «Nuevo ticket», «Mi cuenta» y «Cerrar sesión». | RF 1.7.2 |
| SPEC-UI-17 | Complejo | **Mientras** la sesión es de un administrador, **cuando** se muestra la navegación, **el sistema deberá** ofrecer «Usuarios», «Categorías», «Tipos de producto», «Productos», «Tickets», «Mi cuenta» y «Cerrar sesión». | RF 1.7.3 |
| SPEC-UI-18 | Complejo | **Mientras** la sesión es de un cliente, **cuando** se muestra la navegación, **el sistema deberá** ofrecer «Mis tickets», «Mi cuenta» y «Cerrar sesión». | RF 1.7.4 |
| SPEC-UI-19 | No deseado | **Si** el hash pide una pantalla que no corresponde al rol de la sesión, **entonces la interfaz deberá** mostrar el inicio del rol. La API sigue denegando el acceso aunque se fuerce la ruta. | RF 1.7.1, RNF 2 |
| SPEC-UI-20 | No deseado | **Si** el hash no corresponde a ninguna ruta conocida, **entonces la interfaz deberá** mostrar una pantalla «Página no encontrada» con un enlace al inicio del rol. | RF 1.7.1 |
| SPEC-UI-21 | Ubicuo | **El sistema deberá** ofrecer cada acción según el rol de la pantalla y el estado del ticket que informa la API (por ejemplo, «Reabrir» solo en un ticket cerrado) únicamente como ayuda visual, y aceptar siempre la respuesta de la API como decisión final. | RF 1.7.1, RF 1.7.2, RF 1.7.4 |

## Tickets

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-22 | Por evento | **Cuando** el usuario abre `#/tickets`, **el sistema deberá** pedir `GET /tickets` y mostrar cada ticket con su identificador, cliente, estado y fecha de creación, tal como los devuelve la API. | RF 1.7.2, RF 1.7.3, RF 1.7.4 |
| SPEC-UI-23 | Por evento | **Cuando** el usuario aplica un filtro de estado o de texto, o cambia el orden por fecha de creación, **el sistema deberá** pedir el listado con `state`, `q` u `order` y mostrar el resultado. | RF 1.7.2, RF 1.4.9 |
| SPEC-UI-24 | Por evento | **Cuando** un representante o un administrador elige un cliente en el filtro del listado, **el sistema deberá** pedir el listado con `client_id`. | RF 1.7.2, RF 1.7.3, RF 1.4.9 |
| SPEC-UI-25 | Por evento | **Cuando** un administrador elige un representante en el filtro del listado, **el sistema deberá** pedir el listado con `representative_id`. | RF 1.7.3, RF 1.4.9 |
| SPEC-UI-26 | Por evento | **Cuando** se muestra un listado paginable, **el sistema deberá** pedirlo con `page` y `page_size` y ofrecer páginas anterior y siguiente, el número de página y el total de resultados. | RF 1.7.1, RNF 10 |
| SPEC-UI-27 | Por evento | **Cuando** el usuario abre `#/tickets/{id}`, **el sistema deberá** pedir el ticket, sus hitos y su historial de estados, y mostrar el estado, el cliente, el representante, los productos, los hitos y los cambios de estado. | RF 1.7.2, RF 1.7.3, RF 1.7.4 |
| SPEC-UI-28 | Ubicuo | **El sistema deberá** mostrar los hitos y los cambios de estado en el orden en que los devuelve la API, con el contenido o estado nuevo, el autor y su rol, y la fecha. | RF 1.7.2, RF 1.7.4, RF 1.5.2 |
| SPEC-UI-29 | Ubicuo | **El sistema deberá** mostrar las fechas y horas recibidas en UTC en la zona horaria del navegador, en formato de fecha y hora en español. | RF 1.7.6 |
| SPEC-UI-30 | Por evento | **Cuando** un representante abre `#/tickets/new`, **el sistema deberá** mostrar un formulario con cliente, primer mensaje y productos opcionales. | RF 1.7.2 |
| SPEC-UI-31 | Por evento | **Cuando** un representante busca un cliente en el selector del formulario de alta, **el sistema deberá** pedir `GET /clients` con `q` y ofrecer solo los clientes que devuelve la API, mostrando su nombre. | RF 1.7.2, SPEC-USR-32, SPEC-USR-46 |
| SPEC-UI-32 | Por evento | **Cuando** un representante busca productos en el formulario de alta o al asociar productos a un ticket, **el sistema deberá** pedir `GET /products/available` con `q` y ofrecer solo los productos que devuelve la API. | RF 1.7.2, SPEC-PRD-26 |
| SPEC-UI-33 | Por evento | **Cuando** un representante envía el formulario de alta y la API crea el ticket, **el sistema deberá** mostrar el detalle del ticket creado. | RF 1.7.2 |
| SPEC-UI-34 | Por evento | **Cuando** el representante asignado o el cliente dueño envía un mensaje en el detalle, **el sistema deberá** registrarlo como hito en la API. | RF 1.7.2, RF 1.7.4 |
| SPEC-UI-35 | Opcional | **Donde** quien registra el hito es un representante, **el sistema deberá** ofrecer la opción opcional «Comenzar a trabajar» (`start_progress`) y enviarla con el hito; a un cliente no se la ofrece. | RF 1.7.2, SPEC-TKT-09 |
| SPEC-UI-36 | Por evento | **Cuando** el representante asignado o el cliente dueño pulsa «Cerrar», **el sistema deberá** pedir el cierre del ticket a la API. | RF 1.7.2, RF 1.7.4 |
| SPEC-UI-37 | Por evento | **Cuando** el representante asignado o el cliente dueño pulsa «Reabrir», **el sistema deberá** pedir la reapertura del ticket a la API. | RF 1.7.2, RF 1.7.4 |
| SPEC-UI-38 | Por evento | **Cuando** el representante asignado elige productos y confirma, **el sistema deberá** pedir a la API que los asocie al ticket. | RF 1.7.2 |
| SPEC-UI-39 | Por evento | **Cuando** el representante asignado pulsa «Quitar» junto a un producto del ticket, **el sistema deberá** pedir a la API que lo quite. | RF 1.7.2 |
| SPEC-UI-40 | Complejo | **Mientras** la sesión es de un cliente, **cuando** se muestra el detalle de un ticket, **el sistema deberá** ofrecer solo registrar mensajes, cerrar y reabrir, sin crear tickets ni asociar o quitar productos. | RF 1.7.4 |
| SPEC-UI-41 | Complejo | **Mientras** la sesión es de un administrador, **cuando** se muestran el listado o el detalle de un ticket, **el sistema deberá** presentarlos solo para consulta, sin formularios ni botones que modifiquen tickets. | RF 1.7.3, RF 1.4.8 |
| SPEC-UI-42 | Por evento | **Cuando** una acción sobre un ticket termina con éxito, **el sistema deberá** volver a pedir el ticket, sus hitos y su historial a la API y mostrar lo que devuelve, sin armar el resultado por su cuenta. | RF 1.7.1, RF 1.7.2 |
| SPEC-UI-43 | Por estado | **Mientras** una acción está en curso, **el sistema deberá** deshabilitar el botón que la dispara para evitar envíos repetidos. | RF 1.7.1 |

## Administración

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-44 | Por evento | **Cuando** un administrador abre `#/users`, **el sistema deberá** pedir `GET /users` y mostrar nombre, email, rol y estado de cada cuenta, con búsqueda `q`, filtro `is_active` y paginación. | RF 1.7.3, RF 1.1.2 |
| SPEC-UI-45 | Por evento | **Cuando** un administrador envía el formulario de alta de usuario, con nombre, email, rol (incluido `Admin`), contraseña y canal opcional, **el sistema deberá** pedir el alta a la API y mostrar el usuario en el listado. | RF 1.7.3, RF 1.1.1 |
| SPEC-UI-46 | Por evento | **Cuando** un administrador edita el nombre, el email o el canal de un usuario, **el sistema deberá** pedir la modificación a la API. | RF 1.7.3, RF 1.1.1 |
| SPEC-UI-47 | Por evento | **Cuando** un administrador pulsa «Dar de baja» en un usuario activo o «Reactivar» en uno inactivo, **el sistema deberá** pedir a la API la baja o la reactivación. | RF 1.7.3, RF 1.1.6 |
| SPEC-UI-48 | Por evento | **Cuando** un administrador ingresa una contraseña nueva para un usuario y confirma, **el sistema deberá** pedir a la API el restablecimiento, sin pedir la contraseña anterior. | RF 1.7.3, RF 1.1.7 |
| SPEC-UI-49 | Por evento | **Cuando** un administrador abre `#/categories`, **el sistema deberá** pedir `GET /categories` con `q` opcional y ofrecer crear, renombrar y eliminar categorías. | RF 1.7.3, RF 1.2.3 |
| SPEC-UI-50 | Por evento | **Cuando** un administrador abre `#/product-types`, **el sistema deberá** pedir `GET /product-types` con `q` opcional, mostrarlos agrupados por categoría y ofrecer crear, modificar (nombre y categoría) y eliminar tipos. | RF 1.7.3, RF 1.2.1 |
| SPEC-UI-51 | Por evento | **Cuando** un administrador abre `#/products`, **el sistema deberá** pedir `GET /products` y mostrar nombre, tipo, categoría y estado, con búsqueda `q`, filtros `is_active`, `category_id` y `product_type_id`, y paginación. | RF 1.7.3, RF 1.3.3, RF 1.3.5 |
| SPEC-UI-52 | Por evento | **Cuando** un administrador crea o modifica un producto, **el sistema deberá** pedir el alta o la modificación (nombre y tipo) a la API. | RF 1.7.3, RF 1.3.1 |
| SPEC-UI-53 | Por evento | **Cuando** un administrador pulsa «Dar de baja» en un producto activo o «Reactivar» en uno inactivo, **el sistema deberá** pedir a la API la baja o la reactivación. | RF 1.7.3, RF 1.3.4 |
| SPEC-UI-54 | Por evento | **Cuando** un administrador pulsa «Eliminar» en una categoría o un tipo de producto, **el sistema deberá** pedir confirmación y enviar la baja solo si la persona confirma. | RF 1.7.3, RF 1.2.1, RF 1.2.3 |

## Errores y mensajes en español

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-55 | Ubicuo | **El sistema deberá** mostrar todos sus textos (etiquetas, botones, mensajes y títulos) en español neutro, con identificadores de código en inglés. | RF 1.7.6 |
| SPEC-UI-56 | Por evento | **Cuando** la API responde un error con un código de la tabla de mensajes, **el sistema deberá** mostrar el mensaje en español de esa tabla. | RF 1.7.6 |
| SPEC-UI-57 | Por evento | **Cuando** la API responde `validation_error` con `fields`, **el sistema deberá** marcar cada campo indicado con «Este campo es obligatorio» (`required`) o «El valor ingresado no es válido» (`invalid`). | RF 1.7.6 |
| SPEC-UI-58 | No deseado | **Si** la API responde un código que no figura en la tabla, o un error `5xx`, **entonces la interfaz deberá** mostrar «Ocurrió un error inesperado. Intente nuevamente.» sin detalles internos. | RF 1.7.6, SPEC-PLT-16 |
| SPEC-UI-59 | No deseado | **Si** no se puede conectar con el servidor o la respuesta no es JSON, **entonces la interfaz deberá** mostrar «No se pudo conectar con el servidor. Intente nuevamente.». | RF 1.7.6 |

Tabla de mensajes (código de la API → texto):

| Código | Mensaje |
|--------|---------|
| `invalid_credentials` | Email o contraseña incorrectos. |
| `invalid_current_password` | La contraseña actual no es correcta. |
| `forbidden` | No tiene permiso para realizar esta acción. |
| `duplicate_email` | Ya existe un usuario con ese email. |
| `self_deactivation` | No puede darse de baja a sí mismo. |
| `user_not_found` | El usuario no existe. |
| `duplicate_category` | Ya existe una categoría con ese nombre. |
| `category_in_use` | La categoría tiene tipos de producto asociados y no se puede eliminar. |
| `category_not_found` | La categoría no existe. |
| `duplicate_product_type` | Ya existe un tipo de producto con ese nombre en la categoría. |
| `product_type_in_use` | El tipo de producto tiene productos asociados y no se puede eliminar. |
| `product_type_not_found` | El tipo de producto no existe. |
| `duplicate_product` | Ya existe un producto con ese nombre en el tipo de producto. |
| `product_not_found` | El producto no existe. |
| `ticket_not_found` | El ticket no existe. |
| `ticket_closed` | El ticket está cerrado. Reábralo para agregar mensajes. |
| `invalid_transition` | Esa acción no está permitida en el estado actual del ticket. |
| `invalid_client` | El cliente indicado no existe o está inactivo. |
| `invalid_product` | Alguno de los productos no existe o está inactivo. |
| `product_not_in_ticket` | El producto no está asociado al ticket. |

## Seguridad

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-60 | Ubicuo | **El sistema deberá** autenticarse únicamente con la cookie de sesión de SPEC-PLT-10, sin tokens ni credenciales en cabeceras, en la URL ni en el código servido. | RNF 2, RNF 8 |
| SPEC-UI-61 | Ubicuo | **El sistema no deberá** incluir en los archivos de la interfaz claves, contraseñas ni otros secretos. | RNF 2 |
| SPEC-UI-62 | Ubicuo | **El sistema no deberá** guardar el rol, la identidad ni las credenciales del usuario en `localStorage`, `sessionStorage`, cookies ni la URL: el rol vive solo en memoria y se obtiene de `GET /me`. | RNF 2, RF 1.7.5 |
| SPEC-UI-63 | Ubicuo | **El sistema deberá** insertar todo texto que proviene de la API (nombres, emails, mensajes de hitos) en la página como texto, nunca como HTML. | RNF 2 |
| SPEC-UI-64 | Ubicuo | **El sistema deberá** capturar las contraseñas en campos de tipo contraseña y vaciarlos tras enviar el formulario, sin conservarlas en memoria más allá del envío. | RNF 2 |
| SPEC-UI-65 | Ubicuo | **El sistema no deberá** usar en la página scripts ni manejadores de eventos en línea, de modo que pueda aplicarse una política de contenido estricta. | RNF 2, RNF 8 |

## Accesibilidad y diseño adaptable

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-66 | Ubicuo | **El sistema deberá** declarar en la página el idioma español (`lang="es"`) y un título que identifique la pantalla actual. | RF 1.7.6 |
| SPEC-UI-67 | Ubicuo | **El sistema deberá** asociar una etiqueta visible a cada campo de formulario. | RF 1.7.1 |
| SPEC-UI-68 | Ubicuo | **El sistema deberá** poder usarse solo con el teclado, con controles nativos (botones, enlaces y campos) y foco visible. | RF 1.7.1 |
| SPEC-UI-69 | Por evento | **Cuando** se muestra un mensaje de error o de confirmación, **el sistema deberá** hacerlo en una región que los lectores de pantalla anuncien. | RF 1.7.1, RF 1.7.6 |
| SPEC-UI-70 | Ubicuo | **El sistema deberá** mostrarse utilizable, sin desplazamiento horizontal de la página, desde 360 px de ancho, con tablas que se adapten o se desplacen dentro de su contenedor. | RF 1.7.1 |
| SPEC-UI-71 | Ubicuo | **El sistema deberá** mostrar un indicador de carga mientras espera a la API y un mensaje «No hay resultados» cuando un listado está vacío. | RF 1.7.1 |
| SPEC-UI-72 | Ubicuo | **El sistema deberá** mantener una relación de contraste de al menos 4,5:1 en el texto. | RF 1.7.1 |

## Estructura verificable

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-73 | Ubicuo | **El sistema deberá** separar, en el código JavaScript de la interfaz, los módulos puros (rutas por hash, armado de consultas y filtros, traducción de errores, formato de fechas, paginación), que no usan el DOM ni la red, de los módulos que usan el DOM o llaman a la API. | RNF 9, RNF 8 |
| SPEC-UI-74 | Ubicuo | **El sistema deberá** escribir los módulos puros como módulos ES (`import` y `export`) cargados con `<script type="module">`, para que puedan importarse desde las pruebas sin navegador ni compilación. | RNF 9, RNF 8 |
| SPEC-UI-75 | Ubicuo | **El sistema deberá** hacer que el cliente de la API reciba la función de red (`fetch`) como parámetro, para poder probarlo con una versión simulada. | RNF 9 |
| SPEC-UI-76 | Ubicuo | **El sistema deberá** ejecutar las pruebas unitarias de JavaScript con Node, sin dependencias de ejecución ni compilación, dentro del CI. | RNF 9, constitución (principio 4) |

## Decisiones

Aprobadas el 2026-11-12 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación):

1. **Interfaz plana servida por Flask (SPEC-UI-01 a 06)**: un panel en HTML, JavaScript y CSS sin build ni dependencias, de una sola página con rutas por hash, textos en español neutro e identificadores en inglés. Flask lo sirve desde la raíz `/`, con los archivos en `/static/`. Es el mismo origen que la API: no hace falta CORS ni tokens, y la autenticación es la cookie de sesión `HttpOnly` y `SameSite=Lax` (SPEC-PLT-10). Todo `401` significa sesión cerrada (SPEC-UI-12). Las reglas de negocio quedan en la API: la interfaz no decide transiciones ni propiedad y traduce los códigos de error a español (SPEC-UI-56).
2. **Tres experiencias**: (a) Representante: CRM de los tickets que tiene asignados (listar con filtros, detalle con hitos e historial, crear con selector de cliente y productos activos, registrar hito con `start_progress` opcional, cerrar, reabrir, asociar y quitar productos). (b) Administrador: administra usuarios (incluidas cuentas `Admin`), categorías, tipos de producto y productos, y ve **todos** los tickets en solo lectura. (c) Cliente: lista y detalle de sus tickets (hitos y estados), con registrar mensajes, cerrar y reabrir.
3. **Fuera de la v1**: métricas o tableros de resumen y listado de notificaciones.
4. **Cambios de la API que esta área requiere** (cada uno tiene specs en su área): `GET /me` (SPEC-USR-27); reactivar usuarios y productos (SPEC-USR-28 a 30, SPEC-PRD-22 a 25); listado de cuentas de cualquier rol (SPEC-USR-31); `GET /clients` para el representante, solo activos con `id` y `name` (SPEC-USR-32 a 34, reemplaza a SPEC-USR-11); cambio y restablecimiento de contraseña (SPEC-USR-37 a 42); historial de estados (SPEC-TKT-35 a 37); lectura del `Admin` sobre tickets e hitos (SPEC-TKT-33, 34 y SPEC-MLS-12, reemplaza a SPEC-TKT-27); filtros del lado del servidor (`q`, `is_active`, `state`, `client_id`, `representative_id`, `order`); y paginación opcional y compatible hacia atrás (SPEC-PLT-17 a 22). Como esos listados sin parámetros no cambian, la API existente no se rompe.
5. **Rutas de la UI y el contrato (SPEC-PLT-14 reemplazada por SPEC-PLT-23)**: `GET /` y `GET /static/<ruta>` no se documentan en `openapi.json`; la spec de rutas expuestas las excluye de forma explícita. Son públicas, como `/health` y `/docs`.
6. **Ayuda visual y no autoridad (SPEC-UI-21)**: la interfaz puede ocultar o deshabilitar botones según el rol y el estado que informa la API, solo para no ofrecer acciones evidentemente inútiles (por ejemplo «Reabrir» en un ticket abierto). Nunca replica la tabla de transiciones ni la propiedad del ticket: el permiso real y la validación son de la API, y su error siempre se muestra.
7. **Un `Admin` ve tickets en la misma ruta `#/tickets`** que los demás roles, con el contenido que su rol permite (todos, solo lectura). El inicio del `Admin` es `#/users`. Se descartó una ruta separada por rol para no duplicar pantallas.
8. **Node solo para desarrollo y CI (SPEC-UI-73 a 76)**: los módulos puros se prueban con el ejecutor de pruebas de Node, sin dependencias de ejecución, sin build y sin el DOM. La constitución se enmienda para permitirlo (principios 1, 3 y 4); **la enmienda requiere la aprobación explícita del equipo**.
9. **Eliminar es irreversible** para categorías y tipos (baja física, SPEC-PTY-13 y 07): la interfaz pide confirmación (SPEC-UI-54). Las bajas lógicas (usuarios y productos) son reversibles con la reactivación y no la piden.
10. **Fechas**: la API devuelve UTC y la interfaz las muestra en la zona horaria del navegador (SPEC-UI-29).
