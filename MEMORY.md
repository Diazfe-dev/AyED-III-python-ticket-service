# MEMORY.md

Memoria persistente del proyecto. Se lee al empezar cada sesión y se actualiza al terminar cada tarea (ver la regla en [AGENTS.md](AGENTS.md)).

Última actualización: 2026-11-09

## Estado actual del proyecto

- Fase: diseño y especificación terminados, sin preguntas abiertas. La implementación no empezó: todavía no hay código ni repositorio git.
- Existe:
  - [README.md](README.md) (2026-11-10): descripción del proyecto, stack, metodología (SDD spec-as-source + EARS + TDD), arquitectura y guía de contribución.
  - [docs/constitution.md](docs/constitution.md): 6 principios innegociables, con la máxima precedencia.
  - [docs/REQUERIMIENTOS.md](docs/REQUERIMIENTOS.md) (movido a `docs/` el 2026-11-10): RF actualizados el 2026-11-09 con 3 RF nuevos (1.1.5 rol Admin, 1.2.3 ABM de rubros, 1.4.7 quitar productos) y 4 aclarados (1.1.1, 1.3.1, 1.4.5, 1.6.3).
  - [AGENTS.md](AGENTS.md): stack, convenciones, patrones, spec-as-source, prohibiciones, flujo de trabajo, testing/CI y estilo de commits.
  - [specs/](specs/): 90 specs EARS en 6 áreas (USR 21, PTY 14, PRD 10, TKT 22, MLS 10, NTF 13), todas con su sección **Decisiones** y sin preguntas abiertas. Migradas el 2026-11-09 a una carpeta por área (`specs/NN-<área>/spec.md`). Todavía no hay `plan.md`, `tasks.md` ni `test-plan.md`; el avance de cada área se sigue en el índice de [specs/README.md](specs/README.md).
  - [diagrams/](diagrams/): todo en Mermaid. [classes.md](diagrams/classes.md) tiene 2 vistas (dominio y capas) y [sequences/](diagrams/sequences/) tiene 22 diagramas en 6 archivos, uno por área. Se borraron los 4 diagramas de secuencia viejos (`.md` y `.jpg`); hay una copia de respaldo solo en el scratchpad de la sesión del 2026-11-09. `Diagrama.drawio` y `Diagrama-clases.jpg` también se eliminaron (2026-11-10): Mermaid es la única fuente. Los Mermaid pasaron una validación estática, pero todavía no se renderizaron con `mermaid-cli`.
- No existe todavía: `app/`, `tests/`, `requirements*.txt`, configuración de `ruff`, CI, ni los archivos `plan.md`, `tasks.md` y `test-plan.md`.

## Decisiones (y por qué)

| Fecha | Decisión | Por qué |
|-------|----------|---------|
| 2026-11-09 | Python 3.12 + Flask + SQLite | Stack lo más simple posible para un TP; SQLite no necesita servidor. |
| 2026-11-09 | SQLAlchemy 2.0 como ORM (puro, sin Flask-SQLAlchemy) | Abstrae la base sin escribir SQL a mano. Al no usar Flask-SQLAlchemy, el dominio no depende de Flask y se testea sin levantar la app. |
| 2026-11-09 | Las entidades de dominio son también los modelos ORM | Es lo más simple para el alcance del TP. Costo: el dominio queda acoplado a SQLAlchemy. Se descartó separar dominio puro con mapeo imperativo porque duplica clases. |
| 2026-11-09 | Sin Alembic; esquema con `create_all()` | Menos dependencias. Se revisa si el esquema empieza a cambiar seguido. |
| 2026-11-09 | Patrón State para el ticket, guardando solo `state_name` en la base | Respeta el diagrama de clases sin convertir los estados en tablas. |
| 2026-11-09 | Patrón Strategy para notificaciones | Agregar un canal nuevo es sumar una clase, no un `if`. |
| 2026-11-09 | Inmutabilidad de hitos con listeners del ORM + triggers de SQLite | RNF 5: protege el historial también ante SQL directo, no solo desde el ORM. |
| 2026-11-09 | Ticket ajeno → 404 (no 403) | RNF 4: no confirmar la existencia de tickets de otros clientes. |
| 2026-11-09 | Reloj inyectable en services y dominio | RNF 6: los timestamps de auditoría se pueden testear de forma determinística. |
| 2026-11-09 | `pytest` + `ruff`, cobertura mínima del 90 % | RNF 1 (TDD) y un solo tool para lint y formato. Pendiente de confirmación por el equipo. |
| 2026-11-09 | Requerimientos funcionales descompuestos en specs con sintaxis EARS, en `specs/` | Frases atómicas y verificables que se traducen 1 a 1 en tests, lo que facilita el TDD (RNF 1). Cada test referencia el ID de la spec. |
| 2026-11-09 | Specs en español con palabras clave EARS en español (Cuando, Mientras, Si … entonces, Donde) | Coherencia con `REQUERIMIENTOS.md`. El código y los tests siguen en inglés. |
| 2026-11-09 | Constitución en `docs/constitution.md` con 6 principios (stack, spec y código, lógica e interfaz, tests, datos del usuario, idioma) | Reglas cortas y verificables con máxima precedencia: constitución > AGENTS.md > MEMORY.md > specs. Aprobada por el equipo. |
| 2026-11-09 | Spec-Driven Development con enfoque spec-as-source; una carpeta por área en `specs/` con `spec.md`, `plan.md`, `tasks.md` y `test-plan.md` | La spec es la fuente de verdad y el código se deriva de ella. Se eligió agrupar por área (no por spec EARS ni por feature) para tener pocas carpetas alineadas con los RF. |
| 2026-11-09 | Supuestos provisionales en specs: reapertura → `InProgress`; no se aceptan hitos en tickets cerrados; baja de productos o tipos en uso → rechazada; notificaciones simuladas | Permiten avanzar con las specs, pero cada uno figura como pregunta abierta hasta que el equipo lo confirme. **Resueltos por las decisiones siguientes**: la baja de productos cambia a lógica; los demás se confirman. |
| 2026-11-09 | `plan.md`, `tasks.md` y `test-plan.md` se crean de forma incremental, al empezar a trabajar cada área, y no todos por adelantado | Evita planes especulativos que quedan viejos antes de implementarse. Lo que aprendamos en un área se aplica al planificar la siguiente. Regla: un área no se implementa hasta tener sus cuatro archivos. |
| 2026-11-09 | Diagramas de secuencia en Mermaid, uno por área, en `diagrams/sequences/` (22 diagramas que citan sus SPEC-ID) | Se versionan como texto y se ven en GitHub y VS Code. Siguen la arquitectura Controller → Service → Repository de AGENTS.md y usan nombres en `snake_case`. No van en `specs/NN-<área>/` porque esas carpetas admiten como máximo 4 archivos. |
| 2026-11-09 | Diagrama de clases reescrito en Mermaid (`diagrams/classes.md`) y alineado con las secuencias. **Reemplaza al de `Diagrama.drawio`** | Una sola fuente en texto, versionable y visible en GitHub. Respecto del drawio se eliminan `TicketManager` (objeto dios), `MilestoneService`/`MilestoneRepository` (los hitos son parte del agregado `Ticket`) y `NotificationController` (las notificaciones son internas y no se exponen por HTTP). `ProductsController` pasa a llamarse `CatalogController`. Se agregan `CatalogService`, `ProductService`, `AuthController` y la entidad `Notification`. |
| 2026-11-09 | Rol `Admin` propio, como subclase de `User`. El primer admin se crea con el comando CLI `create-admin` y un admin no puede darse de baja a sí mismo | Los diagramas 1 y 4 lo usaban como actor sin clase. Separa la administración de la atención de tickets. Por CLI se evita el problema de quién crea al primer admin. RF 1.1.5, SPEC-USR-20 y SPEC-USR-21. |
| 2026-11-09 | Baja lógica de usuarios (`is_active`) | La baja física rompería la auditoría de hitos y cambios de estado (RNF 5 y 6). Un usuario inactivo no puede iniciar sesión y su email sigue reservado. |
| 2026-11-09 | Contraseña de al menos 8 caracteres, sin reglas de complejidad | Sigue la recomendación actual de NIST y alcanza para el RNF 2. Se descartaron las reglas de letras y números porque agregan fricción sin mucho beneficio. |
| 2026-11-09 | Un representante solo ve sus tickets asignados; un ticket ajeno → 404 | Privacidad simétrica a la del cliente (RNF 4) y reglas más simples. Se descartó "ver todos, editar asignados". |
| 2026-11-09 | Un ticket reabierto vuelve a `InProgress` | Ya fue trabajado y vuelve al mismo representante. Se descartaron `New` y un estado `Reopened` nuevo. |
| 2026-11-09 | La reapertura por parte del cliente es directa, sin aprobación | Respeta RF 1.4.4 y 1.4.5. Un flujo de solicitud y aprobación requería una entidad nueva y mucho más alcance. |
| 2026-11-09 | Un ticket cerrado no acepta hitos: primero hay que reabrirlo | Mantiene el significado de "cerrado". Se descartó la reapertura automática por un hito del cliente porque mezcla dos acciones. |
| 2026-11-09 | El representante asignado puede quitar productos de un ticket (RF 1.4.7) | Permite corregir errores de carga. Los productos no forman parte del historial inmutable. |
| 2026-11-09 | ABM completo de categorías (RF 1.2.3); baja física rechazada si tienen tipos asociados | Consistente con el resto del catálogo y con el diagrama 4. Las categorías no tienen historial que conservar. |
| 2026-11-09 | Baja lógica de productos (`is_active`) | **Revierte el supuesto provisional** de rechazar la baja. El producto se conserva en los tickets existentes, pero no se puede asociar a tickets nuevos. Es el mismo criterio que con los usuarios. |
| 2026-11-09 | Se notifica al representante cuando el cliente cierra un ticket (RF 1.6.3 ampliado) | Simetría con la notificación al cliente: el representante se entera de que no tiene que seguir trabajando el ticket. |
| 2026-11-09 | Notificaciones simuladas (las estrategias solo registran el envío) | Sin dependencias ni credenciales externas. El patrón Strategy permite conectar envíos reales más adelante. |
| 2026-11-09 | Hitos solo de texto, sin adjuntos | Ningún RF pide adjuntos y manejar archivos excede el alcance. |
| 2026-11-09 | Diagrama de clases: `Ticket.products: List<Product>`; `State` con `close`, `reopen` e `inProgress` que por defecto lanzan `InvalidTransitionError`; sin `reopen` en `InProgressState`; `createTicket(client, products, firstMessage)` | Corrige inconsistencias con los RF y los diagramas de secuencia. El representante sale del usuario autenticado y el estado inicial lo fija el dominio. |

## Errores a evitar

- No usar `frozen=True` de dataclass en entidades mapeadas por SQLAlchemy: el ORM necesita poder setear atributos. La inmutabilidad de hitos se resuelve con listeners y triggers.
- No olvidar `PRAGMA foreign_keys = ON` en cada conexión: SQLite trae las claves foráneas desactivadas por defecto.
- No usar la API legacy de SQLAlchemy (`session.query()`, `Column` suelta).
- No cambiar el estado del ticket asignando el atributo directamente: siempre a través del objeto `State`, para que quede el `StateChange`.
- No filtrar los tickets por dueño solo en la vista: el filtro va en el service.
- No implementar specs que dependan de preguntas abiertas sin resolver.
- No escribir specs con dos comportamientos en una sola frase: rompe la trazabilidad spec → test.
- En EARS no se escribe "deberá no …": un comportamiento negativo se expresa con el patrón **Si … entonces** (pasó con SPEC-NTF-11).
- No editar `Diagrama.drawio` a mano sobre el XML: usar un script con `xml.etree` y validar que el archivo se pueda parsear. Después de cualquier cambio, reexportar los `.jpg` desde draw.io. (Histórico: ahora los diagramas son Mermaid.)
- En los bloques Mermaid no usar `;` ni `#` dentro de los mensajes (cortan la sentencia) y evitar `&`. Mantener balanceados los bloques `alt`/`opt` con su `end`.
- El archivo de memoria se llama `MEMORY.md`, en mayúsculas. GitHub distingue mayúsculas en los links aunque macOS no.
- No hacer una baja física de entidades con historial (usuarios, productos): usar `is_active`.
- No tomar el representante ni el estado inicial de los parámetros del request: el representante sale de la sesión y el estado lo fija el dominio.

## Próximos pasos

1. Verificar en GitHub que los diagramas Mermaid se rendericen correctamente.
2. Inicializar git, `.gitignore` (`.venv`, `*.db`, `.env`, `__pycache__`) y la rama `main`. Considerar un `CODEOWNERS` para `AGENTS.md` y `docs/constitution.md`.
3. Crear `requirements.txt` (Flask, SQLAlchemy) y `requirements-dev.txt` (pytest, pytest-cov, ruff), y configurar `ruff` en `pyproject.toml`.
4. Esqueleto: `create_app()`, `db.py` (engine, sesión por request, `init-db`, `create-admin`), `conftest.py` con base en memoria.
5. Configurar el CI en GitHub Actions (ruff + pytest con cobertura ≥ 90 %).
6. Crear `plan.md`, `tasks.md` y `test-plan.md` de `specs/01-users/` (con revisión) antes de su primer ciclo TDD.
7. Primer ciclo TDD (área 01-users): `User` con roles e `is_active`, alta con email único (RNF 3) y login (RNF 2).
8. Después: `Ticket` con el patrón State y `StateChange` (RNF 6), hitos inmutables (RNF 5), privacidad (RNF 4), catálogo y notificaciones.
