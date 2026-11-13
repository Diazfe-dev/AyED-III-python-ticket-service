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

Convención común. Cada área declara qué listados la admiten: usuarios (SPEC-USR-47), productos (SPEC-PRD-29) y tickets (SPEC-TKT-45). Los listados de categorías y de tipos de producto (SPEC-PTY-24), y los de hitos (SPEC-MLS-13) y de cambios de estado de un ticket (SPEC-TKT-47), son cortos y no se paginan.

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PLT-17 | Opcional | **Donde** un listado admite paginación y el request incluye `page` o `page_size`, **el sistema deberá** responder un objeto `{items, page, page_size, total}`, con la página pedida, el tamaño aplicado y el total de resultados que cumplen los filtros; el parámetro omitido toma su valor por defecto. | RNF 10 |
| SPEC-PLT-18 | Por evento | **Cuando** el request a un listado que admite paginación no incluye `page` ni `page_size`, **el sistema deberá** responder el arreglo plano de siempre, sin paginar. | RNF 10 |
| SPEC-PLT-19 | Ubicuo | **El sistema deberá** numerar las páginas desde 1. (El valor por defecto de `page` y el valor por defecto y el máximo de `page_size` pasan a SPEC-PLT-24, SPEC-PLT-25 y SPEC-PLT-26.) | RNF 10 |
| SPEC-PLT-20 | No deseado | **Si** `page` o `page_size` no es un entero positivo, o `page_size` supera el máximo, **entonces el sistema deberá** rechazar el request con `400` y el código `validation_error`, indicando el parámetro inválido. | RNF 10 |
| SPEC-PLT-21 | Ubicuo | **El sistema deberá** ordenar un listado paginado con el orden propio del listado y, ante igualdad, por identificador, para que las páginas no se solapen ni omitan resultados. | RNF 10 |
| SPEC-PLT-22 | Por evento | **Cuando** `page` supera la última página, **el sistema deberá** responder `items` vacío con el `total` real. | RNF 10 |
| SPEC-PLT-24 | Opcional | **Donde** un listado admite paginación y el request incluye `page_size` pero no `page`, **el sistema deberá** usar `page` igual a 1. | RNF 10 |
| SPEC-PLT-25 | Opcional | **Donde** un listado admite paginación y el request incluye `page` pero no `page_size`, **el sistema deberá** usar un `page_size` de 20. | RNF 10 |
| SPEC-PLT-26 | Ubicuo | **El sistema deberá** limitar `page_size` a un máximo de 100 (SPEC-PLT-20 rechaza un valor mayor). | RNF 10 |

## Búsqueda por texto en los listados

Convención común para todo listado que admite `q`: usuarios, clientes y representantes (SPEC-USR-43 y 46), categorías y tipos de producto (SPEC-PTY-21 a 23), productos (SPEC-PRD-26) y tickets (SPEC-TKT-41).

| ID | Tipo | Especificación | Origen |
|----|------|----------------|--------|
| SPEC-PLT-27 | Ubicuo | **El sistema deberá** tratar un `q` vacío (incluido `q=`) o que solo tiene espacios como si no se hubiera enviado `q`, en todo listado que admite `q`. | RF 1.2.4, RF 1.1.2, RF 1.3.5, RF 1.4.9 |

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

8. La paginación es opcional y compatible hacia atrás (SPEC-PLT-17 y 18): sin `page` ni `page_size` el listado responde el arreglo plano de hoy, así que ningún cliente ni test existente cambia. Con alguno de los dos responde `{items, page, page_size, total}`. El `page_size` por defecto es 20 (SPEC-PLT-25) y el máximo 100 (SPEC-PLT-26). Un valor inválido es `400` `validation_error` (SPEC-PLT-20). Se descartó rechazar un `page_size` excesivo recortándolo en silencio.
9. **SPEC-PLT-14 reemplazada por SPEC-PLT-23**: la UI agrega `GET /` y `GET /static/<ruta>`, que no son API JSON y no se describen en `openapi.json`. En vez de documentarlas como rutas del contrato, el contrato sigue siendo solo la API y SPEC-PLT-23 las excluye de forma explícita y exacta (sin comodines de "otras rutas"). El test de contrato (rutas expuestas = rutas del contrato) pasa a comparar contra `openapi.json` más esas dos rutas. Se descartó listarlas en `openapi.json` porque mezclaría HTML y archivos con el contrato de la API. SPEC-PLT-15 no cambia: una ruta que ni la API ni la UI exponen sigue respondiendo `404` o `405` JSON, incluido `/static/<archivo inexistente>` (SPEC-UI-03). Aprobada por el equipo el 2026-11-12.
10. Las rutas de la UI (`GET /` y `/static/`) son públicas, como `/health`, `/openapi.json` y `/docs` (decisión 6): el HTML y los archivos no contienen datos y la autenticación vive en la API. Es una excepción más a la exigencia de sesión: SPEC-USR-16 (reemplazada por SPEC-USR-49) ya admitía rutas públicas, y SPEC-USR-49 las nombra una por una.

Aprobadas el 2026-11-12 (validación de requerimientos de [07-ui](../07-ui/spec.md)):

11. **`page` y `page_size` por defecto (SPEC-PLT-19, 24, 25 y 26)**: SPEC-PLT-19 agrupaba tres comportamientos; queda solo con la numeración desde 1 y el resto se separa en specs nuevas. `page` vale 1 si se omite (SPEC-PLT-24), `page_size` vale 20 si se omite (SPEC-PLT-25) y el máximo es 100 (SPEC-PLT-26). El comportamiento no cambia.
12. **`q` vacío (SPEC-PLT-27)**: un `q` vacío o con solo espacios equivale a no enviar `q` en todos los listados con búsqueda (SPEC-USR-43 y 46, SPEC-PTY-21 a 23, SPEC-PRD-26, SPEC-TKT-41). Se define una sola vez acá y las demás áreas la referencian en sus decisiones.
13. **Listados que no se paginan**: categorías y tipos de producto (SPEC-PTY-24, decisión del usuario), hitos de un ticket (SPEC-MLS-13) y cambios de estado de un ticket (SPEC-TKT-47). Ignoran `page` y `page_size` y siguen respondiendo el arreglo plano.
14. **Rutas públicas (SPEC-USR-49 reemplaza a SPEC-USR-16)**: la lista de rutas sin sesión es cerrada: `POST /login`, `GET /`, `GET /static/<ruta>`, `GET /health`, `GET /docs` y `GET /openapi.json`. Cualquier otra ruta que expone la API responde `401` sin sesión.
