# 00 — Plataforma

Origen: RNF 1, RNF 2, RNF 7 y decisiones técnicas de [AGENTS.md](../../AGENTS.md) · Diagramas: [clases — capas](../../diagrams/classes.md#2-capas-de-aplicación)

Comportamiento técnico transversal que necesitan todas las demás áreas: configuración, conexión a la base, ciclo de vida de la sesión y comandos de administración. No contiene reglas de negocio.

## Configuración

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PLT-01 | Ubicuo | **El sistema deberá** leer la clave secreta (`SECRET_KEY`) y la URL de la base (`DATABASE_URL`) desde variables de entorno. | RNF 2, AGENTS.md |
| SPEC-PLT-02 | Opcional | **Donde** no se define `DATABASE_URL`, **el sistema deberá** usar una base SQLite en archivo dentro de la carpeta `instance/`. | AGENTS.md |
| SPEC-PLT-03 | No deseado | **Si** la aplicación se inicia sin `SECRET_KEY` y no está en modo de testing ni de debug, **entonces el sistema deberá** negarse a iniciar con un error que indique la variable faltante. | RNF 2 |
| SPEC-PLT-04 | Por evento | **Cuando** se crea la aplicación en modo de testing, **el sistema deberá** usar una base SQLite en memoria, aislada para cada instancia de la aplicación. | RNF 1 |

## Base de datos y sesión

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PLT-05 | Ubicuo | **El sistema deberá** activar la verificación de claves foráneas (`PRAGMA foreign_keys = ON`) en cada conexión a SQLite. | AGENTS.md, MEMORY.md |
| SPEC-PLT-06 | Por evento | **Cuando** se procesa un request, **el sistema deberá** proveer una sesión de base de datos propia de ese request y reutilizarla durante todo el request. | AGENTS.md |
| SPEC-PLT-07 | Por evento | **Cuando** termina un request, **el sistema deberá** cerrar su sesión de base de datos. | AGENTS.md |
| SPEC-PLT-08 | No deseado | **Si** un request termina con una excepción no manejada, **entonces el sistema deberá** revertir (rollback) los cambios pendientes de su sesión antes de cerrarla. | AGENTS.md |
| SPEC-PLT-09 | Por evento | **Cuando** se ejecuta el comando `init-db`, **el sistema deberá** crear todas las tablas del modelo que no existan, sin borrar datos existentes. | AGENTS.md |

## Seguridad y disponibilidad

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PLT-10 | Ubicuo | **El sistema deberá** emitir la cookie de sesión con los atributos `HttpOnly` y `SameSite=Lax`. | RNF 2 |
| SPEC-PLT-11 | Por evento | **Cuando** se solicita `GET /health`, **el sistema deberá** responder `200` con `{"status": "ok"}`, sin requerir autenticación. | AGENTS.md (verificación de CI) |

## Documentación de la API

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PLT-12 | Por evento | **Cuando** se solicita `GET /openapi.json`, **el sistema deberá** responder `200` con el contrato OpenAPI 3.1 de la API, sin requerir autenticación. | RNF 7 |
| SPEC-PLT-13 | Por evento | **Cuando** se solicita `GET /docs`, **el sistema deberá** responder `200` con una página de Swagger UI que carga el contrato de `/openapi.json`, sin requerir autenticación. | RNF 7 |
| SPEC-PLT-14 | Ubicuo | **El sistema deberá** exponer exactamente las rutas y métodos HTTP que describe su contrato OpenAPI, ni más ni menos. | RNF 7 |

## Decisiones

Aprobadas el 2026-11-10 y registradas en [MEMORY.md](../../MEMORY.md):

1. La plataforma se trata como un área más (`00-platform`), para que el esqueleto respete spec-as-source y TDD sin crear excepciones a la constitución.
2. `create-admin` (SPEC-USR-20) **no** forma parte del esqueleto: se implementa con el área `01-users`, cuando esa área tenga sus cuatro archivos.
3. `/health` es la única ruta sin autenticación además del login. Sirve como prueba de humo del esqueleto y del CI. **Ampliada por la decisión 6.**

Aprobadas el 2026-11-10 (RNF 7):

4. La interfaz HTTP del sistema es una API JSON.
5. El contrato se escribe a mano primero (*contract-first*) en `docs/openapi.json` y la app lo sirve tal cual. No se genera desde el código, así que no suma dependencias de Python. Swagger UI se carga desde un CDN con una versión fija.
6. `/openapi.json` y `/docs` también son públicas: el contrato no expone datos de usuarios y los endpoints que documenta siguen protegidos.
