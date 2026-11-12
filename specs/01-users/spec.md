# 01 — Gestión de usuarios y accesos

Origen: RF 1.1 · Relacionados: RNF 2, RNF 3, RNF 10 · Diagramas: [secuencias](../../diagrams/sequences/01-users.md), [clases](../../diagrams/classes.md)

Roles: `Admin`, `Representative`, `Client`.

## Alta de usuarios

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-01 | Por evento | **Cuando** un administrador envía un alta de usuario con nombre, email, rol y contraseña, **el sistema deberá** crear el usuario activo con el rol indicado (`Admin`, `Representative` o `Client`). | RF 1.1.1, RF 1.1.5 |
| SPEC-USR-02 | Ubicuo | **El sistema deberá** guardar la contraseña de cada usuario únicamente como hash, nunca en texto plano. | RF 1.1.1, RNF 2 |
| SPEC-USR-03 | Ubicuo | **El sistema deberá** normalizar el email (sin espacios al inicio o al final y en minúsculas) antes de guardarlo o compararlo. | RNF 3 |
| SPEC-USR-04 | No deseado | **Si** el email de un alta ya pertenece a otro usuario, activo o inactivo, **entonces el sistema deberá** rechazar el alta e informar que el email ya existe. | RNF 3 |
| SPEC-USR-05 | No deseado | **Si** el alta no incluye nombre, email válido, rol válido o contraseña, **entonces el sistema deberá** rechazarla e indicar qué campos son inválidos. | RF 1.1.1 |
| SPEC-USR-25 | No deseado | **Si** un alta, una modificación o un login incluye un campo con un tipo de dato distinto del esperado (por ejemplo, un número donde se espera texto), **entonces el sistema deberá** rechazarlo: en el alta y en la modificación, indicando ese campo como inválido; en el login, con el mismo mensaje genérico de SPEC-USR-15. | RF 1.1.1, RNF 2 |
| SPEC-USR-06 | Por evento | **Cuando** se crea un usuario sin canal de notificación preferido, **el sistema deberá** asignarle el canal por defecto (`mail`). | RF 1.6, Diagrama de clases |
| SPEC-USR-23 | No deseado | **Si** un alta o una modificación indica un canal de notificación preferido distinto de `mail` o `whatsapp`, **entonces el sistema deberá** rechazarla e indicar que el canal es inválido. | RF 1.6.1 |
| SPEC-USR-19 | No deseado | **Si** la contraseña de un alta tiene menos de 8 caracteres, **entonces el sistema deberá** rechazar el alta. | RNF 2 |
| SPEC-USR-20 | Por evento | **Cuando** se ejecuta el comando de inicialización `create-admin` con nombre, email y contraseña, **el sistema deberá** crear un usuario con rol `Admin`. | RF 1.1.5 |

## Modificación y baja

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-07 | Por evento | **Cuando** un administrador modifica el nombre, el email o el canal preferido de un usuario, **el sistema deberá** guardar los nuevos datos. | RF 1.1.1 |
| SPEC-USR-08 | No deseado | **Si** la modificación cambia el email por uno que ya pertenece a otro usuario, **entonces el sistema deberá** rechazarla. | RNF 3 |
| SPEC-USR-09 | Por evento | **Cuando** un administrador da de baja un usuario, **el sistema deberá** marcarlo como inactivo sin eliminarlo. | RF 1.1.1 |
| SPEC-USR-10 | Ubicuo | **El sistema deberá** conservar los tickets, hitos y registros de auditoría asociados a un usuario inactivo. | RF 1.1.1, RNF 5, RNF 6 |
| SPEC-USR-21 | No deseado | **Si** un administrador intenta dar de baja su propio usuario, **entonces el sistema deberá** rechazar la operación. | RF 1.1.5 |
| SPEC-USR-26 | No deseado | **Si** se intenta modificar o dar de baja un usuario inexistente, incluido un identificador fuera del rango que admite la base, **entonces el sistema deberá** responder que el usuario no existe (`404`). | RF 1.1.1 |
| SPEC-USR-22 | No deseado | **Si** una modificación incluye un nombre vacío o un email inválido, **entonces el sistema deberá** rechazarla e indicar qué campos son inválidos. | RF 1.1.1 |

## Listados

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-11 | Por evento | **Reemplazada por SPEC-USR-32, SPEC-USR-33 y SPEC-USR-34.** **Cuando** un administrador solicita el listado de clientes, **el sistema deberá** devolver solo los usuarios con rol `Client`. | RF 1.1.2 |
| SPEC-USR-12 | Por evento | **Cuando** un administrador solicita el listado de representantes, **el sistema deberá** devolver solo los usuarios con rol `Representative`. | RF 1.1.3, RF 1.1.4 |
| SPEC-USR-13 | Ubicuo | **Reemplazada por SPEC-USR-36.** **El sistema deberá** mostrar el rol y el estado (activo o inactivo) de cada usuario en todo listado de usuarios. | RF 1.1.2, RF 1.1.4 |

## Autenticación y autorización

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-14 | Por evento | **Cuando** un usuario envía un email y una contraseña que coinciden con un usuario activo, **el sistema deberá** iniciar una sesión autenticada para ese usuario. | RNF 2 |
| SPEC-USR-15 | No deseado | **Si** el email no existe, la contraseña no coincide o el usuario está inactivo, **entonces el sistema deberá** rechazar el login con un mensaje genérico de credenciales inválidas, sin indicar el motivo. | RF 1.1.1, RNF 2 |
| SPEC-USR-24 | No deseado | **Si** el email de un login no existe o pertenece a un usuario inactivo, **entonces el sistema deberá** verificar la contraseña contra un hash de relleno antes de rechazarlo, para que el tiempo de respuesta no revele si el email existe. | RNF 2 |
| SPEC-USR-16 | No deseado | **Reemplazada por SPEC-USR-49.** **Si** un usuario sin sesión intenta acceder a cualquier funcionalidad que no sea el login, **entonces el sistema deberá** denegar el acceso con un `401` que indique que se requiere autenticación. | RNF 2, RNF 7 |
| SPEC-USR-49 | No deseado | **Si** un request sin sesión válida solicita una ruta de la API que no es `POST /login`, `GET /`, `GET /static/<ruta>`, `GET /health`, `GET /docs` ni `GET /openapi.json`, **entonces el sistema deberá** denegar el acceso con `401` y el código `authentication_required`. | RNF 2, RNF 7 |
| SPEC-USR-17 | Por evento | **Cuando** un usuario cierra sesión, **el sistema deberá** invalidar su sesión. | RNF 2 |
| SPEC-USR-18 | No deseado | **Si** un usuario sin rol `Admin` intenta gestionar usuarios, **entonces el sistema deberá** denegar la operación. | RF 1.1.5, RNF 2 |

## Identidad, activación y contraseñas

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-27 | Por evento | **Cuando** un usuario autenticado solicita `GET /me`, **el sistema deberá** responder `200` con su `id`, `name`, `email` y `role`. | RF 1.1.8 |
| SPEC-USR-28 | Por evento | **Cuando** un administrador reactiva un usuario inactivo (`POST /users/{id}/activate`), **el sistema deberá** marcarlo como activo, de modo que pueda iniciar sesión. | RF 1.1.6 |
| SPEC-USR-29 | Por evento | **Cuando** un administrador reactiva un usuario que ya está activo, **el sistema deberá** responder con éxito sin modificarlo. | RF 1.1.6 |
| SPEC-USR-30 | No deseado | **Si** se intenta reactivar un usuario inexistente, incluido un identificador fuera del rango que admite la base, **entonces el sistema deberá** responder que el usuario no existe (`404`). | RF 1.1.6 |
| SPEC-USR-37 | Por evento | **Cuando** un usuario autenticado envía su contraseña actual y una contraseña nueva (`POST /me/password`), **el sistema deberá** guardar la nueva únicamente como hash. | RF 1.1.7, RNF 2 |
| SPEC-USR-38 | No deseado | **Si** la contraseña actual enviada no coincide con la del usuario, **entonces el sistema deberá** rechazar el cambio con `400` y el código `invalid_current_password`, sin modificar la contraseña. | RF 1.1.7, RNF 2 |
| SPEC-USR-39 | No deseado | **Si** la contraseña nueva de un cambio o de un restablecimiento tiene menos de 8 caracteres, **entonces el sistema deberá** rechazar la operación (mismas reglas que SPEC-USR-19). | RF 1.1.7, RNF 2 |
| SPEC-USR-40 | No deseado | **Si** un cambio o un restablecimiento de contraseña omite un campo obligatorio o incluye uno que no es texto, **entonces el sistema deberá** rechazarlo indicando ese campo como inválido (mismo criterio que SPEC-USR-25). | RF 1.1.7, RNF 2 |
| SPEC-USR-41 | Por evento | **Cuando** un administrador envía una contraseña nueva para un usuario (`POST /users/{id}/password`), **el sistema deberá** guardarla únicamente como hash, sin pedir la contraseña anterior. | RF 1.1.7, RF 1.1.5, RNF 2 |
| SPEC-USR-42 | No deseado | **Si** se intenta restablecer la contraseña de un usuario inexistente, incluido un identificador fuera del rango que admite la base, **entonces el sistema deberá** responder que el usuario no existe (`404`). | RF 1.1.7 |

## Listados de usuarios, búsqueda y paginación

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-31 | Por evento | **Cuando** un administrador solicita el listado de usuarios (`GET /users`), **el sistema deberá** devolver las cuentas de cualquier rol, incluido `Admin`, activas e inactivas. | RF 1.1.2, RF 1.1.5 |
| SPEC-USR-32 | Por evento | **Cuando** un representante solicita el listado de clientes (`GET /clients`), **el sistema deberá** devolver solo los usuarios con rol `Client` que están activos. | RF 1.1.9 |
| SPEC-USR-33 | Ubicuo | **El sistema deberá** devolver, en el listado de clientes de un representante, únicamente el `id` y el `name` de cada cliente, sin email, canal preferido ni otros campos. | RF 1.1.9 |
| SPEC-USR-34 | Por evento | **Cuando** un administrador solicita el listado de clientes, **el sistema deberá** devolver todos los usuarios con rol `Client`, activos e inactivos, con los campos de usuario que define el contrato (`openapi.json`), nunca el hash de la contraseña. | RF 1.1.2, RNF 2 |
| SPEC-USR-35 | No deseado | **Si** un usuario sin rol `Admin` solicita el listado de usuarios o el de representantes, o un usuario con rol `Client` solicita el de clientes, **entonces el sistema deberá** denegar la operación con `403` y el código `forbidden`. | RF 1.1.5, RNF 2 |
| SPEC-USR-36 | Ubicuo | **El sistema deberá** mostrar el rol y el estado (activo o inactivo) de cada usuario en todo listado de usuarios, salvo en el listado de clientes de un representante (SPEC-USR-33). | RF 1.1.2, RF 1.1.4, RF 1.1.9 |
| SPEC-USR-43 | Por evento | **Cuando** un administrador envía `q` en un listado de usuarios, clientes o representantes, **el sistema deberá** devolver solo los usuarios cuyo nombre o email contiene ese texto, sin distinguir mayúsculas. | RF 1.1.2 |
| SPEC-USR-44 | Por evento | **Cuando** un administrador envía `is_active` (`true` o `false`) en un listado de usuarios, clientes o representantes, **el sistema deberá** devolver solo los usuarios con ese estado. | RF 1.1.2 |
| SPEC-USR-45 | No deseado | **Si** `is_active` no es `true` ni `false`, **entonces el sistema deberá** rechazar el listado con `400` y el código `validation_error`, indicando ese parámetro como inválido. | RF 1.1.2 |
| SPEC-USR-46 | Por evento | **Cuando** un representante envía `q` en el listado de clientes, **el sistema deberá** devolver solo los clientes activos cuyo nombre contiene ese texto, sin distinguir mayúsculas y sin buscar en el email. | RF 1.1.9 |
| SPEC-USR-47 | Opcional | **Donde** se solicita un listado de usuarios, clientes o representantes con `page` o `page_size`, **el sistema deberá** paginarlo según SPEC-PLT-17 a SPEC-PLT-22. | RNF 10 |
| SPEC-USR-50 | No deseado | **Si** un representante envía `is_active` en el listado de clientes, **entonces el sistema deberá** denegar la operación (`403`, código `forbidden`), sin ignorar el parámetro; si el valor no es `true` ni `false`, el `400` de SPEC-USR-45 precede al `403`. | RF 1.1.9, RNF 2 |
| SPEC-USR-48 | Ubicuo | **El sistema deberá** ordenar los listados de usuarios, clientes y representantes por nombre (sin distinguir mayúsculas) y, ante igualdad, por identificador. | RF 1.1.2, RNF 10 |

## Decisiones

Resueltas el 2026-11-09 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación):

1. Se crea un rol `Admin` propio, como subclase de `User`. El primer administrador se crea con un comando CLI (SPEC-USR-20).
2. La baja de usuarios es lógica (`is_active`).
3. Las contraseñas deben tener al menos 8 caracteres, sin reglas de complejidad.

Resuelta el 2026-11-10:

4. Como la interfaz es una API JSON (RNF 7), un acceso sin sesión responde `401` en lugar de redirigir al login (SPEC-USR-16). La spec todavía no estaba implementada, así que se corrige en el lugar.
5. La modificación aplica las mismas validaciones de formato que el alta (SPEC-USR-22) y el canal preferido solo admite `mail` o `whatsapp` (SPEC-USR-23), los dos canales que definen las specs de notificaciones.
6. Hardening (2026-11-10): el login compara siempre contra un hash, aunque el email no exista (SPEC-USR-24), y los tipos de dato inválidos se rechazan explícitamente (SPEC-USR-25). El comando `create-admin` pide la contraseña solo con un prompt oculto y confirmado: no acepta `--password`, para que no quede en el historial de la shell (SPEC-USR-20 sin cambios de comportamiento).

7. Revisión transversal (2026-11-10): el `404` de usuario inexistente pasa a tener spec propia (SPEC-USR-26), que cubre también los identificadores fuera de rango (antes respondían `500`).

Aprobadas el 2026-11-12 (nueva área [07-ui](../07-ui/spec.md); el login, el alta y la baja no cambian):

8. **Identidad (SPEC-USR-27)**: `GET /me` devuelve solo `id`, `name`, `email` y `role` de quien tiene la sesión. Sin sesión responde `401` por SPEC-USR-16, sin spec propia. La UI lo usa para saber el rol y no lo guarda del lado del cliente.
9. **Reactivación (SPEC-USR-28 a 30)**: reactivar es idempotente y un `404` para un usuario inexistente, con el mismo criterio que SPEC-PRD-18 y SPEC-USR-26. Un no-`Admin` recibe `403` por SPEC-USR-18. Esto levanta la exclusión de la decisión 6 de [03-products](../03-products/spec.md#decisiones) y la UI la necesita.
10. **Listado de usuarios de cualquier rol (SPEC-USR-31)**: `GET /users` es nuevo y solo para `Admin`. `GET /clients` y `GET /representatives` se mantienen.
11. **`GET /clients` para el representante (SPEC-USR-11 reemplazada)**: el representante lo necesita para elegir el cliente de un ticket. Recibe solo clientes activos y solo `id` y `name` (SPEC-USR-32 y 33), para no exponer email ni canal. El `Admin` conserva el listado completo (SPEC-USR-34); un `Client` recibe `403` (SPEC-USR-35). SPEC-USR-13 se reemplaza por SPEC-USR-36 porque exigía rol y estado en todo listado y el del representante no los incluye. La búsqueda `q` del representante no mira el email (SPEC-USR-46), para que no se pueda descubrir el email de un cliente por tanteo. **Impacto en lo implementado**: el representante pasa de `403` a `200` en `GET /clients`; el contrato (`openapi.json`) y los tests existentes de `403` del representante en ese listado cambian al implementar este cambio.
12. **Cambio y restablecimiento de contraseña (SPEC-USR-37 a 42)**: el cambio propio es `POST /me/password` con la contraseña actual y la nueva; el restablecimiento del `Admin` es `POST /users/{id}/password` con la nueva. Los nombres de campo quedan para el contrato. La contraseña actual incorrecta responde `400` con `invalid_current_password` y **no** `401`, porque la UI interpreta todo `401` como sesión cerrada. Las reglas de la contraseña nueva son las de SPEC-USR-19 y SPEC-USR-25. Cambiar la contraseña no invalida la sesión vigente (no hay decisión que lo pida). Un no-`Admin` que restablece la contraseña de otro recibe `403` por SPEC-USR-18.
13. **Filtros y paginación (SPEC-USR-43 a 48)**: `q` busca por nombre o email, `is_active` filtra por estado y el orden es por nombre (antes no estaba especificado). La paginación sigue la convención común de [00-platform](../00-platform/spec.md#paginación-opcional-de-listados). Los listados sin esos parámetros no cambian de forma.

Aprobadas el 2026-11-12 (validación de requerimientos de [07-ui](../07-ui/spec.md)):

14. **Orden por nombre (SPEC-USR-48)**: cambia el orden actual por `id` de `GET /clients` y `GET /representatives` (y define el de `GET /users`) a nombre sin distinguir mayúsculas y, ante igualdad, por `id`. **Impacto en lo implementado**: el contrato (`openapi.json`) debe documentarlo y los tests existentes que esperan el orden por `id` deben actualizarse al implementar este cambio.
15. **Rutas públicas (SPEC-USR-49 reemplaza a SPEC-USR-16)**: SPEC-USR-16 decía "cualquier funcionalidad que no sea el login", pero la UI, `/health`, `/docs` y `/openapi.json` también son públicas. SPEC-USR-49 las nombra todas y exige `401` en cualquier otra ruta de la API sin sesión; una ruta que no existe sigue respondiendo `404` o `405` (SPEC-PLT-15). El test de guarda del plan debe usar esta lista.
16. **`is_active` del representante (SPEC-USR-50)**: un representante que envía `is_active` a `GET /clients` recibe `403`, con el mismo criterio que la decisión 24 de [04-tickets](../04-tickets/spec.md#decisiones) (un filtro que no puede usar no se ignora en silencio). El `400` de formato precede al `403` (SPEC-TKT-48).
17. **Campos del cliente para el `Admin` (SPEC-USR-34)**: en vez de "todos sus campos", la spec remite a los campos de usuario del contrato y excluye el hash de la contraseña (SPEC-USR-02). Es una precisión; el comportamiento previsto no cambia.
18. **`q` vacío**: en SPEC-USR-43 y 46, un `q` vacío o con solo espacios equivale a no enviar `q` (SPEC-PLT-27).
