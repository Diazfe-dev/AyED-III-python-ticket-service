# 07 — Interfaz web

Origen: RF 1.7 · Relacionados: RNF 2, RNF 4, RNF 8, RNF 9, RNF 10, SPEC-PLT-16 ([00-platform](../00-platform/spec.md)), SPEC-TKT-09 ([04-tickets](../04-tickets/spec.md)) · Depende de: SPEC-PLT-10, SPEC-PLT-15, SPEC-PLT-17 a SPEC-PLT-27 ([00-platform](../00-platform/spec.md)) · SPEC-USR-14, SPEC-USR-15, SPEC-USR-17, SPEC-USR-27 a SPEC-USR-50 ([01-users](../01-users/spec.md)) · SPEC-PTY-21 a SPEC-PTY-24 ([02-product-types](../02-product-types/spec.md)) · SPEC-PRD-22 a SPEC-PRD-30 ([03-products](../03-products/spec.md)) · SPEC-TKT-32 a SPEC-TKT-48 ([04-tickets](../04-tickets/spec.md)) · SPEC-MLS-12, SPEC-MLS-13 ([05-milestones](../05-milestones/spec.md))

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

Etiquetas en español de los códigos que devuelve la API (se usan en todas las pantallas):

| Código | Etiqueta | | Código | Etiqueta |
|--------|----------|-|--------|----------|
| Estado `New` | Nuevo | | Rol `Client` | Cliente |
| Estado `InProgress` | En curso | | Rol `Representative` | Representante |
| Estado `Closed` | Cerrado | | Rol `Admin` | Administrador |
| `is_active` verdadero | Activo | | `is_active` falso | Inactivo |

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
| SPEC-UI-11 | Por evento | **Cuando** el usuario pulsa «Cerrar sesión», **el sistema deberá** llamar a `POST /logout` y, responda con éxito o con error, descartar todo dato en memoria de la sesión y mostrar `#/login`. | RF 1.7.5, SPEC-USR-17 |
| SPEC-UI-12 | No deseado | **Si** una respuesta de la API es `401`, salvo la de `POST /login` y la del `GET /me` inicial de SPEC-UI-07 (que cubre SPEC-UI-08), **entonces la interfaz deberá** tratar la sesión como cerrada: descartar los datos en memoria y mostrar `#/login` con el aviso «Tu sesión venció. Inicia sesión nuevamente.». | RF 1.7.5, SPEC-USR-49 |
| SPEC-UI-13 | Por evento | **Cuando** el usuario envía en `#/account` su contraseña actual, la nueva y su confirmación, **el sistema deberá** llamar a la API para cambiarla y mostrar un mensaje de confirmación. | RF 1.7.5, RF 1.1.7 |
| SPEC-UI-14 | No deseado | **Si** la nueva contraseña y su confirmación no coinciden, **entonces la interfaz deberá** indicarlo en el formulario sin enviar el pedido a la API. | RF 1.7.5 |
| SPEC-UI-15 | No deseado | **Si** la API rechaza la contraseña actual (`invalid_current_password`), **entonces la interfaz deberá** mostrar ese error en el formulario sin cerrar la sesión. | RF 1.7.5, SPEC-USR-38 |

## Navegación y pantallas por rol

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-16 | Complejo | **Mientras** la sesión es de un representante, **cuando** se muestra la navegación, **el sistema deberá** ofrecer «Tickets», «Nuevo ticket», «Mi cuenta» y «Cerrar sesión». | RF 1.7.2 |
| SPEC-UI-17 | Complejo | **Mientras** la sesión es de un administrador, **cuando** se muestra la navegación, **el sistema deberá** ofrecer «Usuarios», «Categorías», «Tipos de producto», «Productos», «Tickets», «Mi cuenta» y «Cerrar sesión». | RF 1.7.3 |
| SPEC-UI-18 | Complejo | **Mientras** la sesión es de un cliente, **cuando** se muestra la navegación, **el sistema deberá** ofrecer «Mis tickets», «Mi cuenta» y «Cerrar sesión». | RF 1.7.4 |
| SPEC-UI-19 | No deseado | **Si** el hash pide una pantalla que no corresponde al rol de la sesión, **entonces la interfaz deberá** mostrar el inicio del rol. | RF 1.7.1, RNF 2 |
| SPEC-UI-20 | No deseado | **Si** el hash no corresponde a ninguna ruta conocida, **entonces la interfaz deberá** mostrar una pantalla «Página no encontrada» con un enlace al inicio del rol. | RF 1.7.1 |
| SPEC-UI-21 | Ubicuo | **El sistema deberá** ocultar acciones únicamente por el rol de la sesión y por las reglas de estado de SPEC-UI-77, SPEC-UI-78 y SPEC-UI-79; cualquier otro caso lo decide la API (`409` o `403`) y la interfaz muestra su error. | RF 1.7.1, RF 1.7.2, RF 1.7.4 |

## Tickets

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-22 | Por evento | **Cuando** el usuario abre `#/tickets`, **el sistema deberá** pedir `GET /tickets` y mostrar cada ticket con su identificador, cliente, estado (con la etiqueta de la tabla de etiquetas) y fecha de creación, tal como los devuelve la API. | RF 1.7.2, RF 1.7.3, RF 1.7.4 |
| SPEC-UI-23 | Por evento | **Cuando** el usuario aplica un filtro de estado o de texto, o cambia el orden por fecha de creación, **el sistema deberá** pedir el listado con `state`, `q` u `order` y mostrar el resultado. | RF 1.7.2, RF 1.4.9 |
| SPEC-UI-24 | Por evento | **Cuando** un representante o un administrador elige un cliente en el filtro del listado, **el sistema deberá** pedir el listado con `client_id`. | RF 1.7.2, RF 1.7.3, RF 1.4.9 |
| SPEC-UI-25 | Por evento | **Cuando** un administrador elige un representante en el filtro del listado, **el sistema deberá** pedir el listado con `representative_id`. | RF 1.7.3, RF 1.4.9 |
| SPEC-UI-26 | Por evento | **Cuando** se muestra un listado paginable (usuarios, productos o tickets), **el sistema deberá** pedirlo con `page` y con `page_size` igual a 20, y ofrecer páginas anterior y siguiente, el número de página y el total de resultados. | RF 1.7.1, RNF 10 |
| SPEC-UI-27 | Por evento | **Cuando** el usuario abre `#/tickets/{id}`, **el sistema deberá** pedir el ticket, sus hitos y su historial de estados, y mostrar el estado, el cliente, el representante, los productos, los hitos y los cambios de estado. | RF 1.7.2, RF 1.7.3, RF 1.7.4 |
| SPEC-UI-97 | No deseado | **Si** el `{id}` de `#/tickets/{id}` no es un entero positivo, **entonces la interfaz deberá** mostrar la pantalla «Página no encontrada» (SPEC-UI-20) sin llamar a la API. | RF 1.7.1 |
| SPEC-UI-28 | Ubicuo | **El sistema deberá** mostrar los hitos y los cambios de estado en el orden en que los devuelve la API, con el contenido o estado nuevo, el autor y su rol, y la fecha (estado y rol con las etiquetas de la tabla de etiquetas). | RF 1.7.2, RF 1.7.4, RF 1.5.2 |
| SPEC-UI-29 | Ubicuo | **El sistema deberá** mostrar las fechas y horas recibidas en UTC en la zona horaria del navegador, con el formato `dd/mm/aaaa HH:mm`. | RF 1.7.6 |
| SPEC-UI-30 | Por evento | **Cuando** un representante abre `#/tickets/new`, **el sistema deberá** mostrar un formulario con cliente, primer mensaje y productos opcionales. | RF 1.7.2 |
| SPEC-UI-31 | Por evento | **Cuando** un representante busca un cliente en el selector del formulario de alta, **el sistema deberá** pedir `GET /clients` con `q` y ofrecer solo los clientes que devuelve la API, mostrando su nombre. | RF 1.7.2, SPEC-USR-32, SPEC-USR-46 |
| SPEC-UI-32 | Por evento | **Cuando** un representante busca productos en el formulario de alta o al asociar productos a un ticket, **el sistema deberá** pedir `GET /products/available` con `q` y ofrecer solo los productos que devuelve la API. | RF 1.7.2, SPEC-PRD-26 |
| SPEC-UI-33 | Por evento | **Cuando** un representante envía el formulario de alta y la API crea el ticket, **el sistema deberá** mostrar el detalle del ticket creado. | RF 1.7.2 |
| SPEC-UI-34 | Por evento | **Cuando** un representante o un cliente envía un mensaje en el detalle de un ticket, **el sistema deberá** registrarlo como hito en la API. | RF 1.7.2, RF 1.7.4 |
| SPEC-UI-35 | Complejo | **Mientras** la sesión es de un representante, **cuando** se muestra el formulario de mensaje del detalle de un ticket, **el sistema deberá** ofrecer la opción «Comenzar a trabajar» (`start_progress`). | RF 1.7.2, SPEC-TKT-09 |
| SPEC-UI-36 | Por evento | **Cuando** un representante o un cliente pulsa «Cerrar», **el sistema deberá** pedir el cierre del ticket a la API. | RF 1.7.2, RF 1.7.4 |
| SPEC-UI-37 | Por evento | **Cuando** un representante o un cliente pulsa «Reabrir», **el sistema deberá** pedir la reapertura del ticket a la API. | RF 1.7.2, RF 1.7.4 |
| SPEC-UI-38 | Por evento | **Cuando** un representante elige productos y confirma en el detalle de un ticket, **el sistema deberá** pedir a la API que los asocie al ticket. | RF 1.7.2 |
| SPEC-UI-39 | Por evento | **Cuando** un representante pulsa «Quitar» junto a un producto del ticket, **el sistema deberá** pedir a la API que lo quite. | RF 1.7.2 |
| SPEC-UI-77 | Complejo | **Mientras** el ticket está en `Closed`, **cuando** se muestra su detalle a un representante o a un cliente, **el sistema no deberá** ofrecer «Cerrar». | RF 1.7.2, RF 1.7.4 |
| SPEC-UI-78 | Complejo | **Mientras** el ticket está en `Closed`, **cuando** se muestra su detalle a un representante o a un cliente, **el sistema no deberá** ofrecer «Agregar hito». | RF 1.7.2, RF 1.7.4, SPEC-MLS-05 |
| SPEC-UI-79 | Complejo | **Mientras** el ticket está en `New` o `InProgress`, **cuando** se muestra su detalle a un representante o a un cliente, **el sistema no deberá** ofrecer «Reabrir». | RF 1.7.2, RF 1.7.4 |
| SPEC-UI-80 | Complejo | **Mientras** la sesión es de un cliente, **cuando** se muestra el formulario de mensaje del detalle de un ticket, **el sistema no deberá** ofrecer la opción «Comenzar a trabajar». | RF 1.7.4, SPEC-TKT-09 |
| SPEC-UI-81 | Por evento | **Cuando** un representante envía un mensaje con la opción «Comenzar a trabajar» marcada, **el sistema deberá** enviar `start_progress` con el valor verdadero junto con el hito. | RF 1.7.2, SPEC-TKT-09 |
| SPEC-UI-40 | Complejo | **Mientras** la sesión es de un cliente, **cuando** se muestra el detalle de un ticket, **el sistema deberá** ofrecer solo registrar mensajes, cerrar y reabrir, sin crear tickets ni asociar o quitar productos. | RF 1.7.4 |
| SPEC-UI-41 | Complejo | **Mientras** la sesión es de un administrador, **cuando** se muestran el listado o el detalle de un ticket, **el sistema deberá** presentarlos solo para consulta, sin formularios ni botones que modifiquen tickets. | RF 1.7.3, RF 1.4.8 |
| SPEC-UI-42 | Por evento | **Cuando** una acción sobre un ticket termina con éxito, **el sistema deberá** volver a pedir el ticket, sus hitos y su historial a la API y mostrar lo que devuelve, sin armar el resultado por su cuenta. | RF 1.7.1, RF 1.7.2 |
| SPEC-UI-43 | Por estado | **Mientras** una acción está en curso, **el sistema deberá** deshabilitar el botón que la dispara para evitar envíos repetidos. | RF 1.7.1 |

## Administración

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-UI-44 | Por evento | **Cuando** un administrador abre `#/users`, **el sistema deberá** pedir `GET /users` y mostrar nombre, email, rol y estado de cada cuenta (rol y estado con las etiquetas de la tabla de etiquetas). | RF 1.7.3, RF 1.1.2 |
| SPEC-UI-82 | Por evento | **Cuando** un administrador ingresa un texto de búsqueda en `#/users`, **el sistema deberá** pedir el listado con `q` y mostrar el resultado. | RF 1.7.3, RF 1.1.2 |
| SPEC-UI-83 | Por evento | **Cuando** un administrador elige un estado (activo o inactivo) en el filtro de `#/users`, **el sistema deberá** pedir el listado con `is_active` y mostrar el resultado. | RF 1.7.3, RF 1.1.2 |
| SPEC-UI-45 | Por evento | **Cuando** un administrador envía el formulario de alta de usuario con nombre, email, rol, contraseña y canal opcional, **el sistema deberá** pedir el alta a la API. | RF 1.7.3, RF 1.1.1 |
| SPEC-UI-84 | Ubicuo | **El sistema deberá** ofrecer en el formulario de alta de usuario los tres roles: Administrador (`Admin`), Representante y Cliente. | RF 1.7.3, RF 1.1.5 |
| SPEC-UI-85 | Por evento | **Cuando** la API crea el usuario, **el sistema deberá** mostrarlo en el listado de `#/users`. | RF 1.7.3, RF 1.1.1 |
| SPEC-UI-46 | Por evento | **Cuando** un administrador edita el nombre, el email o el canal de un usuario, **el sistema deberá** pedir la modificación a la API. | RF 1.7.3, RF 1.1.1 |
| SPEC-UI-47 | Por evento | **Cuando** un administrador pulsa «Dar de baja» en un usuario activo o «Reactivar» en uno inactivo, **el sistema deberá** pedir a la API la baja o la reactivación. | RF 1.7.3, RF 1.1.6 |
| SPEC-UI-48 | Por evento | **Cuando** un administrador ingresa en el formulario de restablecimiento una contraseña nueva y su confirmación, y ambas coinciden, **el sistema deberá** pedir a la API el restablecimiento, sin pedir la contraseña anterior. | RF 1.7.3, RF 1.1.7 |
| SPEC-UI-100 | No deseado | **Si** la contraseña nueva y su confirmación del formulario de restablecimiento no coinciden, **entonces la interfaz deberá** indicarlo en el formulario sin enviar el pedido a la API. | RF 1.7.3, RF 1.1.7 |
| SPEC-UI-49 | Por evento | **Cuando** un administrador abre `#/categories`, **el sistema deberá** pedir `GET /categories` y mostrar las categorías. | RF 1.7.3, RF 1.2.3 |
| SPEC-UI-86 | Por evento | **Cuando** un administrador envía el formulario de alta de una categoría, **el sistema deberá** pedir la creación a la API. | RF 1.7.3, RF 1.2.3 |
| SPEC-UI-87 | Por evento | **Cuando** un administrador edita el nombre de una categoría, **el sistema deberá** pedir el cambio a la API. | RF 1.7.3, RF 1.2.3 |
| SPEC-UI-88 | Por evento | **Cuando** un administrador ingresa un texto de búsqueda en `#/categories`, **el sistema deberá** pedir el listado con `q` y mostrar el resultado. | RF 1.7.3, RF 1.2.4 |
| SPEC-UI-50 | Por evento | **Cuando** un administrador abre `#/product-types`, **el sistema deberá** pedir `GET /product-types` y mostrar los tipos agrupados por categoría. | RF 1.7.3, RF 1.2.1 |
| SPEC-UI-89 | Por evento | **Cuando** un administrador ingresa un texto de búsqueda en `#/product-types`, **el sistema deberá** pedir el listado con `q` y mostrar el resultado. | RF 1.7.3, RF 1.2.4 |
| SPEC-UI-90 | Por evento | **Cuando** un administrador envía el formulario de alta de un tipo de producto, **el sistema deberá** pedir la creación a la API. | RF 1.7.3, RF 1.2.1 |
| SPEC-UI-91 | Por evento | **Cuando** un administrador modifica el nombre o la categoría de un tipo de producto, **el sistema deberá** pedir el cambio a la API. | RF 1.7.3, RF 1.2.1 |
| SPEC-UI-51 | Por evento | **Cuando** un administrador abre `#/products`, **el sistema deberá** pedir `GET /products` y mostrar nombre, tipo, categoría y estado de cada producto. | RF 1.7.3, RF 1.3.3 |
| SPEC-UI-92 | Por evento | **Cuando** un administrador ingresa un texto de búsqueda en `#/products`, **el sistema deberá** pedir el listado con `q` y mostrar el resultado. | RF 1.7.3, RF 1.3.5 |
| SPEC-UI-93 | Por evento | **Cuando** un administrador elige un estado (activo o inactivo) en el filtro de `#/products`, **el sistema deberá** pedir el listado con `is_active` y mostrar el resultado. | RF 1.7.3, RF 1.3.5 |
| SPEC-UI-94 | Por evento | **Cuando** un administrador elige una categoría en el filtro de `#/products`, **el sistema deberá** pedir el listado con `category_id` y mostrar el resultado. | RF 1.7.3, RF 1.3.5 |
| SPEC-UI-95 | Por evento | **Cuando** un administrador elige un tipo de producto en el filtro de `#/products`, **el sistema deberá** pedir el listado con `product_type_id` y mostrar el resultado. | RF 1.7.3, RF 1.3.5 |
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
| SPEC-UI-96 | Ubicuo | **El sistema deberá** mostrar los estados de ticket, los roles y los estados de cuenta con las etiquetas de la tabla de etiquetas y, si recibe un código que no figura en ella, mostrarlo tal como llega. | RF 1.7.6 |

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
| SPEC-UI-64 | Por evento | **Cuando** el usuario envía un formulario con campos de contraseña, **el sistema deberá** vaciar esos campos tras enviar el pedido, sin importar su resultado. | RNF 2 |
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
| SPEC-UI-74 | Ubicuo | **El sistema deberá** escribir los módulos puros como módulos ES (`import` y `export`) cargados con `<script type="module">`, para que `node --test` pueda importarlos sin navegador ni compilación. | RNF 9, RNF 8 |
| SPEC-UI-75 | Ubicuo | **El sistema deberá** hacer que el cliente de la API reciba la función de red (`fetch`) como parámetro, para poder probarlo con una versión simulada. | RNF 9 |
| SPEC-UI-76 | Ubicuo | **El sistema deberá** verificar los módulos puros con pruebas unitarias ejecutadas con `node --test`, sin dependencias de ejecución ni compilación, y correrlas en el CI. | RNF 9, constitución (principio 4) |
| SPEC-UI-98 | Ubicuo | **El sistema deberá** verificar el comportamiento que solo se observa en el DOM o en un navegador con una suite de Playwright versionada en el repositorio, que se ejecuta de forma local y en el CI. | RNF 9, constitución (principios 1 y 4) |
| SPEC-UI-99 | Ubicuo | **El sistema deberá** citar en el título de cada prueba de JavaScript y de Playwright el identificador de la spec que verifica, con el formato `SPEC-UI-NN <descripción>`. | RNF 9, specs/README.md |

Convención de verificación. Cada prueba se identifica por el ID de su spec en el título (por ejemplo, `SPEC-UI-14 rechaza una confirmación distinta`), como los tests de Python lo hacen en su docstring.

| Herramienta | Specs que verifica |
|-------------|--------------------|
| `node --test` (módulos puros) | SPEC-UI-23 a 26 (armado de consultas y paginación), SPEC-UI-29 (fechas), SPEC-UI-56 a 59 y SPEC-UI-96 (traducción de errores y etiquetas), rutas por hash de SPEC-UI-04, SPEC-UI-19, SPEC-UI-20 y SPEC-UI-97 |
| Playwright (DOM y navegador) | SPEC-UI-16 a 18, 20, 22, 27, 28, 30, 40, 41, 43, 44, 49 a 51, 54, 64, 68, 70, 71 y 72, y el comportamiento de las pantallas (SPEC-UI-07 a 15, 31 a 39, 42, 45 a 48, 52, 53, 57, 63, 66, 67 y 69, 77 a 95, 100) |
| Revisión del código servido | SPEC-UI-05, 06, 60, 61, 62 y 65 |

Nota: SPEC-UI-76 y SPEC-UI-98 se verifican con el job de CI cuando exista; hoy el repositorio no tiene CI.

## Decisiones

Aprobadas el 2026-11-12 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación):

1. **Interfaz plana servida por Flask (SPEC-UI-01 a 06)**: un panel en HTML, JavaScript y CSS sin build ni dependencias, de una sola página con rutas por hash, textos en español neutro e identificadores en inglés. Flask lo sirve desde la raíz `/`, con los archivos en `/static/`. Es el mismo origen que la API: no hace falta CORS ni tokens, y la autenticación es la cookie de sesión `HttpOnly` y `SameSite=Lax` (SPEC-PLT-10). Todo `401` (salvo el `GET /me` inicial, SPEC-UI-08) significa sesión cerrada (SPEC-UI-12). Las reglas de negocio quedan en la API: la interfaz no decide transiciones ni propiedad y traduce los códigos de error a español (SPEC-UI-56).
2. **Tres experiencias**: (a) Representante: CRM de los tickets que tiene asignados (listar con filtros, detalle con hitos e historial, crear con selector de cliente y productos activos, registrar hito con `start_progress` opcional, cerrar, reabrir, asociar y quitar productos). (b) Administrador: administra usuarios (incluidas cuentas `Admin`), categorías, tipos de producto y productos, y ve **todos** los tickets en solo lectura. (c) Cliente: lista y detalle de sus tickets (hitos y estados), con registrar mensajes, cerrar y reabrir.
3. **Fuera de la v1**: métricas o tableros de resumen y listado de notificaciones.
4. **Cambios de la API que esta área requiere** (cada uno tiene specs en su área): `GET /me` (SPEC-USR-27); reactivar usuarios y productos (SPEC-USR-28 a 30, SPEC-PRD-22 a 25); listado de cuentas de cualquier rol (SPEC-USR-31); `GET /clients` para el representante, solo activos con `id` y `name` (SPEC-USR-32 a 34, reemplaza a SPEC-USR-11); rutas públicas nombradas (SPEC-USR-49, reemplaza a SPEC-USR-16); cambio y restablecimiento de contraseña (SPEC-USR-37 a 42); historial de estados (SPEC-TKT-35 a 37); lectura del `Admin` sobre tickets e hitos (SPEC-TKT-33, 34 y SPEC-MLS-12, reemplaza a SPEC-TKT-27); filtros del lado del servidor (`q`, `is_active`, `state`, `client_id`, `representative_id`, `order`); y paginación opcional y compatible hacia atrás (SPEC-PLT-17 a 27, SPEC-USR-47, SPEC-PRD-29, SPEC-TKT-45). Como esos listados sin parámetros no cambian, la API existente no se rompe.
5. **Rutas de la UI y el contrato (SPEC-PLT-14 reemplazada por SPEC-PLT-23)**: `GET /` y `GET /static/<ruta>` no se documentan en `openapi.json`; la spec de rutas expuestas las excluye de forma explícita. Son públicas, como `/health` y `/docs`.
6. **Ayuda visual y no autoridad (SPEC-UI-21, 77, 78 y 79)**: la interfaz oculta acciones solo por el rol de la sesión y por tres reglas de estado: «Cerrar» y «Agregar hito» no se ofrecen en un ticket `Closed` y «Reabrir» solo se ofrece en uno `Closed`. Esas son las únicas reglas de la tabla de transiciones que replica. Cualquier otro caso (por ejemplo, una transición inválida o un ticket que no es del usuario) lo decide la API con `409` o `403`, y su error siempre se muestra. La propiedad del ticket nunca se replica.
7. **Un `Admin` ve tickets en la misma ruta `#/tickets`** que los demás roles, con el contenido que su rol permite (todos, solo lectura). El inicio del `Admin` es `#/users`. Se descartó una ruta separada por rol para no duplicar pantallas.
8. **Node, Playwright y un navegador solo para desarrollo y CI (SPEC-UI-73 a 76, 98 y 99)**: los módulos puros se prueban con `node --test`, sin dependencias de ejecución, sin build y sin el DOM; lo que solo se observa en el DOM o en un navegador (renderizado, botón deshabilitado, campos de contraseña, controles nativos y foco, ausencia de desplazamiento horizontal desde 360 px, contraste 4,5:1) se verifica con una suite de Playwright versionada en el repositorio, local y en el CI. Ni Playwright ni el navegador son runtime ni dependencia de producción. La constitución se enmendó (principios 1 y 4) con la aprobación del equipo el 2026-11-12, que incluye Playwright. El MCP de Playwright es una herramienta del entorno de trabajo y no forma parte del proyecto.
9. **Eliminar es irreversible** para categorías y tipos (baja física, SPEC-PTY-13 y 07): la interfaz pide confirmación (SPEC-UI-54). Las bajas lógicas (usuarios y productos) son reversibles con la reactivación y no la piden.
10. **Fechas**: la API devuelve UTC y la interfaz las muestra en la zona horaria del navegador (SPEC-UI-29).

Aprobadas el 2026-11-12 (validación de requerimientos, resoluciones de la revisión):

11. **Sesión (SPEC-UI-11 y 12)**: el `GET /me` inicial sin sesión muestra el login sin aviso (SPEC-UI-08); un `401` posterior muestra el aviso «Tu sesión venció. Inicia sesión nuevamente.». Si `POST /logout` falla, la interfaz descarta igual los datos locales y muestra `#/login`.
12. **Specs divididas (SPEC-UI-19, 21, 35, 44, 45, 49, 50, 51, 48)**: cada una agrupaba varios comportamientos. Se conserva el ID original con una sola parte y el resto pasa a IDs nuevos al final del área: SPEC-UI-77 a 95 y SPEC-UI-100. De SPEC-UI-19 se quitó la segunda oración (la API ya deniega el acceso). La paginación de usuarios y productos queda cubierta por SPEC-UI-26.
13. **Etiquetas (SPEC-UI-96)**: los códigos `New`, `InProgress`, `Closed`, `Client`, `Representative` y `Admin` se muestran con la tabla de etiquetas de la cabecera del área.
14. **Rol de la sesión, no propiedad (SPEC-UI-34, 36 a 39)**: las specs hablan del rol de la sesión (representante o cliente); si el ticket no le corresponde, la API responde `404` o `403` y la interfaz muestra el error.
15. **Detalles**: las fechas se muestran como `dd/mm/aaaa HH:mm` (SPEC-UI-29); el restablecimiento de contraseña del `Admin` pide la contraseña nueva y su confirmación y las compara antes de enviar (SPEC-UI-48 y 100); un `{id}` de ticket que no es un entero positivo muestra «Página no encontrada» sin llamar a la API (SPEC-UI-97); la interfaz pide los listados con `page_size` 20 (SPEC-UI-26); SPEC-UI-64 se reformuló como un evento verificable en Playwright.
16. **Errores de parámetros de consulta**: un error `validation_error` de `page`, `state` u otro parámetro del listado no es un campo de formulario: se muestra el mensaje general de SPEC-UI-58 y no la marca de campo de SPEC-UI-57.
17. **Limitación conocida (SPEC-UI-24)**: un representante solo ve clientes activos en el selector (SPEC-USR-32), así que no puede filtrar sus tickets por un cliente inactivo. El `Admin` sí puede (SPEC-USR-34).
18. **Verificación**: SPEC-UI-76 y SPEC-UI-98 se verifican con el job de CI cuando exista; hoy no hay CI. Los diagramas se actualizan en el plan, no en esta spec.
