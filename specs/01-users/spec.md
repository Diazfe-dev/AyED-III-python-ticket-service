# 01 — Gestión de usuarios y accesos

Origen: RF 1.1 · Relacionados: RNF 2, RNF 3 · Diagramas: [secuencias](../../diagrams/sequences/01-users.md), [clases](../../diagrams/classes.md)

Roles: `Admin`, `Representative`, `Client`.

## Alta de usuarios

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-01 | Por evento | **Cuando** un administrador envía un alta de usuario con nombre, email, rol y contraseña, **el sistema deberá** crear el usuario activo con el rol indicado (`Admin`, `Representative` o `Client`). | RF 1.1.1, RF 1.1.5 |
| SPEC-USR-02 | Ubicuo | **El sistema deberá** guardar la contraseña de cada usuario únicamente como hash, nunca en texto plano. | RF 1.1.1, RNF 2 |
| SPEC-USR-03 | Ubicuo | **El sistema deberá** normalizar el email (sin espacios al inicio o al final y en minúsculas) antes de guardarlo o compararlo. | RNF 3 |
| SPEC-USR-04 | No deseado | **Si** el email de un alta ya pertenece a otro usuario, activo o inactivo, **entonces el sistema deberá** rechazar el alta e informar que el email ya existe. | RNF 3 |
| SPEC-USR-05 | No deseado | **Si** el alta no incluye nombre, email válido, rol válido o contraseña, **entonces el sistema deberá** rechazarla e indicar qué campos son inválidos. | RF 1.1.1 |
| SPEC-USR-06 | Por evento | **Cuando** se crea un usuario sin canal de notificación preferido, **el sistema deberá** asignarle el canal por defecto (`mail`). | RF 1.6, Diagrama de clases |
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

## Listados

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-11 | Por evento | **Cuando** un administrador solicita el listado de clientes, **el sistema deberá** devolver solo los usuarios con rol `Client`. | RF 1.1.2 |
| SPEC-USR-12 | Por evento | **Cuando** un administrador solicita el listado de representantes, **el sistema deberá** devolver solo los usuarios con rol `Representative`. | RF 1.1.3, RF 1.1.4 |
| SPEC-USR-13 | Ubicuo | **El sistema deberá** mostrar el rol y el estado (activo o inactivo) de cada usuario en todo listado de usuarios. | RF 1.1.2, RF 1.1.4 |

## Autenticación y autorización

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-USR-14 | Por evento | **Cuando** un usuario envía un email y una contraseña que coinciden con un usuario activo, **el sistema deberá** iniciar una sesión autenticada para ese usuario. | RNF 2 |
| SPEC-USR-15 | No deseado | **Si** el email no existe, la contraseña no coincide o el usuario está inactivo, **entonces el sistema deberá** rechazar el login con un mensaje genérico de credenciales inválidas, sin indicar el motivo. | RF 1.1.1, RNF 2 |
| SPEC-USR-16 | No deseado | **Si** un usuario sin sesión intenta acceder a cualquier funcionalidad que no sea el login, **entonces el sistema deberá** denegar el acceso y redirigirlo al login. | RNF 2 |
| SPEC-USR-17 | Por evento | **Cuando** un usuario cierra sesión, **el sistema deberá** invalidar su sesión. | RNF 2 |
| SPEC-USR-18 | No deseado | **Si** un usuario sin rol `Admin` intenta gestionar usuarios, **entonces el sistema deberá** denegar la operación. | RF 1.1.5, RNF 2 |

## Decisiones

Resueltas el 2026-11-09 y registradas en [MEMORY.md](../../MEMORY.md):

1. Se crea un rol `Admin` propio, como subclase de `User`. El primer administrador se crea con un comando CLI (SPEC-USR-20).
2. La baja de usuarios es lógica (`is_active`).
3. Las contraseñas deben tener al menos 8 caracteres, sin reglas de complejidad.
