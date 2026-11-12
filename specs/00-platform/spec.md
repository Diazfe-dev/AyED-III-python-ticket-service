# 00 — Plataforma

Origen: RNF 1, RNF 2, RNF 7, RNF 8, RNF 10 y decisiones técnicas de [AGENTS.md](../../AGENTS.md) · Diagramas: [clases — capas](../../diagrams/classes.md#2-capas-de-aplicación)

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
| SPEC-PLT-05 | Ubicuo | **El sistema deberá** activar la verificación de claves foráneas (`PRAGMA foreign_keys = ON`) en cada conexión a SQLite. | AGENTS.md, Engram `tp-final/pitfall/pragma-foreign-keys` |
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
| SPEC-PLT-14 | Ubicuo | **Reemplazada por SPEC-PLT-23.** **El sistema deberá** exponer exactamente las rutas y métodos HTTP que describe su contrato OpenAPI, ni más ni menos. | RNF 7 |
| SPEC-PLT-15 | No deseado | **Si** se solicita una ruta o un método HTTP que la API no expone (incluido un identificador no numérico en la URL), **entonces el sistema deberá** responder `404` o `405` con un cuerpo JSON de error. | RNF 7 |
| SPEC-PLT-16 | No deseado | **Si** ocurre un error no manejado durante un request, **entonces el sistema deberá** responder `500` con un cuerpo JSON de error genérico, sin exponer detalles internos. | RNF 2, RNF 7 |
| SPEC-PLT-23 | Ubicuo | **El sistema deberá** exponer exactamente las rutas y métodos HTTP que describe su contrato OpenAPI, más las rutas de la interfaz web de [07-ui](../07-ui/spec.md) (`GET /` y `GET /static/<ruta>`, SPEC-UI-01 y SPEC-UI-02), que quedan fuera del contrato por no ser parte de la API JSON, ni más ni menos. | RNF 7, RNF 8 |

## Paginación opcional de listados

Convención común. Cada área declara qué listados la admiten: usuarios (SPEC-USR-47), productos (SPEC-PRD-29) y tickets (SPEC-TKT-45). Los listados de categorías y de tipos de producto son cortos y no se paginan.

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PLT-17 | Opcional | **Donde** un listado admite paginación y el request incluye `page` o `page_size`, **el sistema deberá** responder un objeto `{items, page, page_size, total}`, con la página pedida, el tamaño aplicado y el total de resultados que cumplen los filtros; el parámetro omitido toma su valor por defecto. | RNF 10 |
| SPEC-PLT-18 | Por evento | **Cuando** el request a un listado que admite paginación no incluye `page` ni `page_size`, **el sistema deberá** responder el arreglo plano de siempre, sin paginar. | RNF 10 |
| SPEC-PLT-19 | Ubicuo | **El sistema deberá** numerar las páginas desde 1 y usar un `page_size` por defecto de 20 y máximo de 100. | RNF 10 |
| SPEC-PLT-20 | No deseado | **Si** `page` o `page_size` no es un entero positivo, o `page_size` supera el máximo, **entonces el sistema deberá** rechazar el request con `400` y el código `validation_error`, indicando el parámetro inválido. | RNF 10 |
| SPEC-PLT-21 | Ubicuo | **El sistema deberá** ordenar un listado paginado con el orden propio del listado y, ante igualdad, por identificador, para que las páginas no se solapen ni omitan resultados. | RNF 10 |
| SPEC-PLT-22 | Por evento | **Cuando** `page` supera la última página, **el sistema deberá** responder `items` vacío con el `total` real. | RNF 10 |

## Decisiones

Aprobadas el 2026-11-10 y registradas en Engram (`tp-final/decision/*`) y en [MEMORY.md](../../MEMORY.md) (Cambios y motivación):

1. La plataforma se trata como un área más (`00-platform`), para que el esqueleto respete spec-as-source y TDD sin crear excepciones a la constitución.
2. `create-admin` (SPEC-USR-20) **no** forma parte del esqueleto: se implementa con el área `01-users`, cuando esa área tenga sus cuatro archivos.
3. `/health` es la única ruta sin autenticación además del login. Sirve como prueba de humo del esqueleto y del CI. **Ampliada por la decisión 6.**

Aprobadas el 2026-11-10 (RNF 7):

4. La interfaz HTTP del sistema es una API JSON.
5. El contrato se escribe a mano primero (*contract-first*) en `docs/openapi.json` y la app lo sirve tal cual. No se genera desde el código, así que no suma dependencias de Python. Swagger UI se carga desde un CDN con una versión fija.
6. `/openapi.json` y `/docs` también son públicas: el contrato no expone datos de usuarios y los endpoints que documenta siguen protegidos.

Aprobadas el 2026-11-10 (revisión transversal de huecos):

7. Todas las respuestas de error de la API son JSON, también las de rutas inexistentes (SPEC-PLT-15) y las de errores inesperados (SPEC-PLT-16). Antes Flask devolvía páginas HTML.

Aprobadas el 2026-11-12 (nueva área [07-ui](../07-ui/spec.md) y paginación opcional):

8. La paginación es opcional y compatible hacia atrás (SPEC-PLT-17 y 18): sin `page` ni `page_size` el listado responde el arreglo plano de hoy, así que ningún cliente ni test existente cambia. Con alguno de los dos responde `{items, page, page_size, total}`. El `page_size` por defecto es 20 y el máximo 100 (SPEC-PLT-19). Un valor inválido es `400` `validation_error` (SPEC-PLT-20). Se descartó rechazar un `page_size` excesivo recortándolo en silencio.
9. **SPEC-PLT-14 reemplazada por SPEC-PLT-23**: la UI agrega `GET /` y `GET /static/<ruta>`, que no son API JSON y no se describen en `openapi.json`. En vez de documentarlas como rutas del contrato, el contrato sigue siendo solo la API y SPEC-PLT-23 las excluye de forma explícita y exacta (sin comodines de "otras rutas"). El test de contrato (rutas expuestas = rutas del contrato) pasa a comparar contra `openapi.json` más esas dos rutas. Se descartó listarlas en `openapi.json` porque mezclaría HTML y archivos con el contrato de la API. SPEC-PLT-15 no cambia: una ruta que ni la API ni la UI exponen sigue respondiendo `404` o `405` JSON, incluido `/static/<archivo inexistente>` (SPEC-UI-03). Es una decisión de diseño a confirmar por el equipo.
10. Las rutas de la UI (`GET /` y `/static/`) son públicas, como `/health`, `/openapi.json` y `/docs` (decisión 6): el HTML y los archivos no contienen datos y la autenticación vive en la API. Es una excepción más a SPEC-USR-16, que ya admite rutas públicas por spec.
