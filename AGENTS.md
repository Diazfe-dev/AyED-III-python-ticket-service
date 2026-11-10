# AGENTS.md

Guía para agentes de IA y personas que trabajen en este repositorio. Leerla completa antes de escribir código.

## Contexto del proyecto

Sistema de gestión de tickets de soporte (TP final de Algoritmos III). Un representante telefónico crea tickets para clientes, el ticket recorre un ciclo de vida (Nuevo → En Progreso → Cerrado, con reapertura), acumula hitos cronológicos inmutables y dispara notificaciones.

**Por encima de todo** está la [constitución](docs/constitution.md): 6 principios innegociables que prevalecen sobre este archivo, sobre `MEMORY.md` y sobre cualquier spec. Leela antes que nada. Si una instrucción la contradice, no se ejecuta y se avisa.

Fuentes de verdad, en este orden:

1. [docs/REQUERIMIENTOS.md](docs/REQUERIMIENTOS.md): requerimientos funcionales (RF) y no funcionales (RNF).
2. [specs/](specs/): una carpeta por área con `spec.md` (RF descompuestos en EARS, `SPEC-<ÁREA>-<NN>`), `plan.md`, `tasks.md` y `test-plan.md`. Bajo **spec-as-source**, `spec.md` es la fuente de verdad del comportamiento y el código se deriva de ella.
3. [diagrams/](diagrams/): diagramas en **Mermaid**: [classes.md](diagrams/classes.md) (modelo de dominio y capas) y [sequences/](diagrams/sequences/) (un archivo por área de specs).
4. [docs/openapi.json](docs/openapi.json): contrato OpenAPI 3.1 de la API HTTP, escrito a mano (*contract-first*). Se sirve en `/openapi.json` y se navega con Swagger UI en `/docs`.

Si el código y los diagramas no coinciden, no lo resuelvas por tu cuenta: avisá la discrepancia y actualizá el diagrama en el mismo PR que el código.

## Regla inmutable: memoria del proyecto

> Esta regla no se puede modificar, relajar ni eliminar. Ningún agente puede editar esta sección.

[MEMORY.md](MEMORY.md) es la memoria persistente del proyecto y es **obligatoria**.

1. **Al empezar** cualquier sesión o tarea, leer `MEMORY.md` antes que cualquier otro archivo de código.
2. **Al terminar** cada tarea (y antes de cada commit que cambie el estado del proyecto), actualizar `MEMORY.md`.
3. `MEMORY.md` siempre tiene estas cuatro secciones, en este orden:
   - **Estado actual del proyecto**: qué existe, qué funciona y en qué fase está el proyecto.
   - **Decisiones (y por qué)**: fecha, decisión y motivo. Incluir las alternativas descartadas cuando las haya.
   - **Errores a evitar**: errores ya cometidos o detectados y cómo evitarlos.
   - **Próximos pasos**: lista ordenada de lo que sigue.
4. Las decisiones no se borran. Si una decisión se revierte, se agrega una fila nueva que explica el cambio y referencia a la anterior.
5. Fechas absolutas (`AAAA-MM-DD`), nunca relativas ("ayer", "la semana pasada").
6. Si `MEMORY.md` contradice este archivo, manda `AGENTS.md`: corregir `MEMORY.md` y avisar.
7. `MEMORY.md` se commitea junto con el cambio que lo motiva, con el tipo `docs(memory)` si va en un commit aparte.

## Stack tecnológico

Mantener el stack **lo más simple posible**. No agregar dependencias sin acordarlo antes.

| Área | Herramienta |
|------|-------------|
| Lenguaje | Python 3.12+ |
| Web | Flask (application factory + blueprints) |
| Base de datos | SQLite |
| ORM | SQLAlchemy 2.0 (API declarativa con `Mapped` / `mapped_column`, consultas con `select()`) |
| Hash de contraseñas | `werkzeug.security` (viene con Flask) |
| Sesiones | Sesión firmada de Flask (`SECRET_KEY` desde variable de entorno) |
| Tests | `pytest` + `pytest-cov` |
| Lint y formato | `ruff` (`ruff check` + `ruff format`) |
| Dependencias | `venv` + `requirements.txt` / `requirements-dev.txt` |
| CI | GitHub Actions |

Puesta en marcha:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
flask --app app init-db
flask --app app run --debug
```

## Estructura del proyecto

```
app/
  __init__.py          # create_app(): config, blueprints, manejadores de errores y comandos
  config.py            # load_config(): configuración desde el entorno
  db.py                # engine, sessionmaker, sesión por request, comando init-db (create_all), fits_integer_column
  wiring.py            # get_catalog_service: arma los services del request sin que los controllers toquen la Session
  auth.py              # get_user_service, current_user y decoradores login_required (401) y admin_required (403)
  cli.py               # comando create-admin
  domain/              # Entidades mapeadas con SQLAlchemy; sin Flask ni HTTP
    base.py            # Base(DeclarativeBase)
    errors.py          # DomainError y subclases (ValidationError, DuplicateUserError, CategoryInUseError, ...)
    ticket.py          # Ticket (agregado raíz)
    states.py          # State, NewState, InProgressState, ClosedState
    milestone.py       # Milestone (inmutable)
    state_change.py    # StateChange (registro de auditoría)
    users.py           # User, Admin, Representative, Client (tabla única) y ROLE_CLASSES
    products.py        # Category, ProductType (name + name_key) y normalize_name; Product en 03-products
    notifications.py   # Notification (interfaz), MailNotification, WhatsappNotification
  services/            # Casos de uso: orquestan dominio, repositorios y notificaciones
    passwords.py       # PasswordHasher (protocolo) y WerkzeugPasswordHasher
    validation.py      # validadores de campos compartidos (text_error, id_error, parse_id, raise_if_invalid)
    user_service.py    # UserService
    catalog_service.py # CatalogService: ABM y listados de categorías y tipos de producto
  repositories/        # Consultas con la Session de SQLAlchemy; devuelven y reciben entidades
    user_repository.py # SqlAlchemyUserRepository
    category_repository.py      # SqlAlchemyCategoryRepository
    product_type_repository.py  # SqlAlchemyProductTypeRepository
  controllers/         # Blueprints de Flask: HTTP de entrada y salida, nada más
    health.py          # /health
    api_docs.py        # /openapi.json y /docs
    auth.py            # POST /login y POST /logout
    users.py           # gestión de usuarios (solo Admin)
    catalog.py         # categorías y tipos de producto (CatalogController)
    errors.py          # tabla DomainError → status y código JSON
    serializers.py     # lectura del cuerpo JSON y representación de usuarios, categorías y tipos
tests/
  conftest.py          # fixtures: app con base en memoria, client, usuarios de prueba
  unit/                # dominio y servicios, sin Flask ni disco (fakes.py: dobles compartidos, como CommitSpy)
  integration/         # repositorios contra SQLite en memoria y endpoints con test client
specs/
  README.md            # Sintaxis EARS, convenciones e índice de áreas
  01-users/            # Una carpeta por área (USR, PTY, PRD, TKT, MLS, NTF)
    spec.md            # QUÉ: specs EARS del área (fuente de verdad)
    plan.md            # CÓMO: plan de implementación
    tasks.md           # PASOS: tareas ordenadas y su estado
    test-plan.md       # VERIFICACIÓN: matriz spec → casos de prueba
  02-product-types/ … 06-notifications/
diagrams/              # UML en Mermaid (no borrar, mantener sincronizado con specs y código)
  classes.md           # Diagrama de clases: modelo de dominio y capas
  sequences/           # Diagramas de secuencia, un archivo por área (NN-<área>.md)
docs/
  constitution.md      # Principios innegociables (máxima precedencia)
  openapi.json         # Contrato OpenAPI 3.1 de la API (contract-first)
MEMORY.md              # Memoria persistente del proyecto
```

## Spec-Driven Development (spec-as-source)

El proyecto usa **Spec-Driven Development** con el enfoque **spec-as-source**: la spec es el artefacto principal y el código es una derivación de ella. La sintaxis EARS y las convenciones de IDs están en [specs/README.md](specs/README.md).

### Principios

1. **La spec manda.** `spec.md` define el comportamiento del sistema. Si el código y la spec difieren, el código está mal, salvo que se acuerde explícitamente cambiar la spec.
2. **Primero la spec, después el código.** Ningún cambio de comportamiento (feature, fix o regla de negocio) se hace en el código sin modificar antes `spec.md`. Los refactors sin cambio de comportamiento no requieren tocar la spec.
3. **Nada de código huérfano.** Todo comportamiento del código se traza a al menos un `SPEC-<ÁREA>-<NN>`. Si aparece comportamiento sin spec, o se escribe la spec y se aprueba, o se elimina el código.
4. **Cadena derivada.** `spec.md` → `plan.md` → `tasks.md` → `test-plan.md` → tests → código. Si cambia un eslabón, se actualizan todos los que vienen después en el mismo PR.

### Estructura de cada área

Cada carpeta `specs/NN-<área>/` tiene como máximo estos cuatro archivos. `spec.md` existe siempre. Los otros tres se crean **cuando se empieza a trabajar el área**, en este orden y antes de escribir código: `plan.md` → `tasks.md` → `test-plan.md`. Un área sin los cuatro archivos no se puede implementar.

| Archivo | Responde | Contenido obligatorio |
|---------|----------|-----------------------|
| `spec.md` | **Qué** debe hacer el sistema | Origen (RF/RNF/diagramas), tablas de specs EARS (`ID`, tipo, especificación, origen), sección **Decisiones** y, si hace falta, **Preguntas abiertas**. Sin detalles de implementación. |
| `plan.md` | **Cómo** se implementa | Specs cubiertas; componentes por capa (`domain`, `services`, `repositories`, `controllers`); modelo de datos (entidades, columnas, restricciones); patrones aplicados; decisiones técnicas con su motivo; dependencias con otras áreas; riesgos. |
| `tasks.md` | **En qué orden** se hace | Checklist ordenado. Cada tarea tiene un ID `T-<ÁREA>-<NN>`, las specs que cubre, la capa, un criterio de terminado y su estado (`[ ]` pendiente, `[~]` en curso, `[x]` hecha). Tareas chicas, de un ciclo TDD cada una. |
| `test-plan.md` | **Cómo se verifica** | Matriz spec → casos de prueba: ID de spec, caso, nivel (`unit` / `integration`), datos o fixtures, resultado esperado y archivo de test. Incluye casos borde y los RNF que cubre. Cada spec tiene al menos un caso. |

### Reglas de specs EARS

- Cada spec usa un solo patrón EARS: ubicuo, por evento (**Cuando**), por estado (**Mientras**), no deseado (**Si … entonces**), opcional (**Donde**) o complejo.
- Una spec, un comportamiento verificable. Si una frase necesita "y" para dos respuestas independientes, son dos specs.
- Cada test referencia en su docstring la spec que verifica y el caso del test-plan: `"""SPEC-TKT-12 · TC-TKT-12a"""`. Una spec sin test en verde no está implementada.
- No se implementa una spec que dependa de una **pregunta abierta** sin resolver. Se consulta al equipo y la respuesta se registra en `MEMORY.md` y en la sección **Decisiones** de la spec.
- Los IDs nunca se reutilizan. Si cambia el comportamiento de una spec ya implementada, se marca `Reemplazada por SPEC-...` y se crea una nueva. Los tests de la spec reemplazada se actualizan o se eliminan en el mismo PR.

### Ciclo de un cambio

1. **Spec**: escribir o modificar las specs en `spec.md` y que el equipo las apruebe.
2. **Plan**: actualizar `plan.md` con el impacto por capa y en el modelo de datos.
3. **Tasks**: desglosar el trabajo en `tasks.md`. Si el cambio agrega o modifica un endpoint, una task actualiza `docs/openapi.json` antes del código.
4. **Test plan**: agregar los casos en `test-plan.md` para cada spec nueva o modificada.
5. **Implementar** las tasks con TDD (red → green → refactor) y marcarlas como `[x]` a medida que se terminan.
6. **Cerrar**: verificar que cada spec del cambio tenga sus tests en verde, que el diagrama esté sincronizado y que `MEMORY.md` esté actualizado.

Dirección de dependencias: `controllers → services → domain` y `services → repositories → db`. El dominio solo puede importar `sqlalchemy` (para el mapeo) y nunca Flask ni otras capas de la app.

## Patrones

- **Capas Controller → Service → Repository**, como en el diagrama de clases. El controller valida la entrada HTTP y delega; el service tiene la lógica de negocio; el repository solo persiste.
- **State** para el ciclo de vida del ticket. Cada estado concreto decide qué transiciones permite (`close`, `reopen`, `in_progress`). Una transición inválida lanza una excepción de dominio. El `Ticket` delega en su estado actual; nunca se usan `if state == "closed"`. En la base solo se guarda el nombre del estado (columna `state_name`). Al leer, una propiedad `state` lo convierte en el objeto `State` correspondiente mediante un registro `{name: StateClass}`. Las clases de estado no son entidades mapeadas.
- **Repository sobre SQLAlchemy**: los services no usan `Session` directamente; piden y guardan entidades a través de los repositorios. La transacción (`commit`/`rollback`) la maneja el service o el ciclo del request, nunca el repositorio a mitad de un caso de uso.
- **Strategy** para notificaciones. `NotificationService` elige la estrategia (`MailNotification`, `WhatsappNotification`) según el `preferred_channel` del usuario. Un canal nuevo es una clase nueva, no un `if` nuevo.
- **Composición**: `Ticket` es dueño de sus `Milestone` y `StateChange`. Solo se crean a través de los métodos del ticket (`add_milestone`, transiciones de estado), nunca sueltos.
- **Agregación**: `Client`, `Representative` y `Product` existen independientemente del ticket; se referencian por id.
- **Inyección de dependencias por constructor**: los services reciben repositorios, notificador y reloj. Eso permite testear con dobles sin parchear módulos.
- **Reloj inyectable**: el tiempo se obtiene de un `clock` inyectado (por defecto `datetime.now(UTC)`), nunca con `datetime.now()` dentro del dominio.

## Requerimientos no funcionales: cómo se cumplen

Cada RNF tiene una regla concreta en el código y al menos un test que la protege.

| RNF | Regla de implementación | Test obligatorio |
|-----|-------------------------|------------------|
| 1. TDD estricto | No se escribe código de producción sin un test que falle antes. Ciclo red → green → refactor. | El historial de commits muestra el test antes o junto con la implementación. |
| 2. Autenticación robusta | Contraseñas hasheadas con `generate_password_hash` y comparadas con `check_password_hash`. Todas las rutas salvo `/login`, `/health`, `/openapi.json` y `/docs` requieren `login_required`. `SECRET_KEY` desde el entorno; la cookie de sesión es `HttpOnly` y `SameSite=Lax`. El mensaje de error del login es genérico (no revela si el email existe). | Login correcto, contraseña incorrecta, usuario inexistente, ruta protegida sin sesión → 401 en JSON. |
| 3. Usuarios únicos | Email normalizado (`strip().lower()`) antes de guardar. `mapped_column(unique=True)` en `User.email` **y** chequeo previo en el service. Si igual ocurre un `IntegrityError`, el repositorio lo traduce a `DuplicateUserError`. | Alta duplicada (incluso con distinto uso de mayúsculas) es rechazada. |
| 4. Privacidad de tickets | El filtro por dueño se aplica en el service, no en el template. Un cliente que pide un ticket ajeno recibe **404** (no 403, para no confirmar que existe). | Cliente A no puede ver, listar, responder ni cerrar tickets del cliente B. |
| 5. Hitos inmutables | No existen métodos, rutas ni repositorios que actualicen o borren hitos. Tres barreras: (a) listeners `before_update` y `before_delete` de SQLAlchemy sobre `Milestone` que lanzan `ImmutableRecordError`; (b) triggers de SQLite que hacen `RAISE(ABORT)` ante `UPDATE` o `DELETE` sobre `milestones`, registrados con `event.listen(table, "after_create", DDL(...))`; (c) la relación `Ticket.milestones` sin `delete-orphan`. Lo mismo aplica a `StateChange`. | Modificar o borrar un hito falla en el ORM y también con SQL directo. |
| 6. Auditoría de estado | Toda transición crea un `StateChange(user, state, timestamp)` con timestamp UTC del reloj inyectado. No hay forma de cambiar el estado sin pasar por el objeto `State`. | Cada transición deja un registro con el usuario y el instante correctos. |
| 7. API documentada | `docs/openapi.json` se escribe antes que el endpoint y la app lo sirve tal cual en `/openapi.json`. Swagger UI en `/docs`, desde CDN con versión fija. Sin librerías de generación. | Las rutas de `app.url_map` y los `paths` del contrato coinciden en los dos sentidos. |

Reglas funcionales que suelen romperse, a tener en cuenta:

- El representante que crea el ticket queda asignado automáticamente (RF 1.4.3).
- La reapertura reasigna al **mismo** representante que lo gestionó (RF 1.4.5).
- Los hitos se listan siempre en orden cronológico ascendente (`ORDER BY created_at, id`) (RF 1.5.2).
- Nuevo hito o cambio de estado por el representante → se notifica al cliente; respuesta o pedido de reapertura del cliente → se notifica al representante (RF 1.6).

## Convenciones de código

- Identificadores, código y comentarios en **inglés**, igual que en los diagramas (`Ticket`, `Milestone`, `StateChange`). La documentación del repo puede estar en español.
- PEP 8, aplicado con `ruff format` (largo de línea 100).
- `snake_case` para funciones, variables y módulos; `PascalCase` para clases; `UPPER_SNAKE_CASE` para constantes.
- Type hints en todas las firmas públicas.
- Entidades con el estilo declarativo de SQLAlchemy 2.0: `Mapped[...]` y `mapped_column(...)`. No usar la API legacy (`Column` suelta, `session.query()`).
- Consultas con `select()`, `session.scalars()` y `session.get()`.
- Relaciones explícitas con `relationship(back_populates=...)`. Los hitos se ordenan con `order_by=(Milestone.created_at, Milestone.id)`.
- Prestar atención al lazy loading en los listados: usar `selectinload` para evitar consultas N+1.
- Timestamps con `DateTime(timezone=True)` y siempre en UTC.
- Excepciones de dominio propias (`DomainError` y subclases como `InvalidTransitionError`, `DuplicateUserError`, `TicketNotFoundError`). Los controllers las traducen a códigos HTTP.
- Funciones cortas, con una sola responsabilidad. Si hace falta un comentario para explicar qué hace un bloque, conviene extraerlo a una función con buen nombre.
- Una `Session` por request, que se cierra en `teardown_appcontext`. `PRAGMA foreign_keys = ON` activado con un listener `connect` del engine (SQLite lo trae desactivado).
- El esquema se crea con `Base.metadata.create_all()` desde el comando `init-db`. No usamos herramienta de migraciones (Alembic) salvo que se acuerde.

## Prohibiciones

- ❌ Escribir código de producción sin un test previo que falle.
- ❌ Cambiar el comportamiento del código sin haber modificado antes `spec.md` (spec-as-source).
- ❌ Dejar código sin trazabilidad a una spec, o specs sin tests.
- ❌ Crear archivos extra en una carpeta de área, o implementar un área a la que todavía le falta `plan.md`, `tasks.md` o `test-plan.md`.
- ❌ Agregar dependencias (Flask-SQLAlchemy, Alembic, frameworks de auth, librerías de validación, etc.) sin acordarlo.
- ❌ Poner lógica de negocio en controllers, templates o repositorios.
- ❌ Importar Flask desde `app/domain/`, o usar la `Session` desde controllers.
- ❌ Modificar o borrar hitos o registros de `StateChange`, por cualquier vía.
- ❌ Cambiar el estado de un ticket asignando un atributo directamente en lugar de usar el objeto `State`.
- ❌ Usar `if`/`elif` sobre el nombre del estado o del canal de notificación en lugar de los patrones State y Strategy.
- ❌ Guardar contraseñas en texto plano, loguearlas o devolver el hash en una respuesta.
- ❌ Commitear secretos, `.env`, ni archivos `.db`.
- ❌ SQL crudo con `text()` armado por interpolación de strings. Si hace falta SQL crudo, va con parámetros enlazados (`:param`).
- ❌ Filtrar tickets por dueño solo en la vista o el template.
- ❌ Saltear, marcar `xfail` o borrar tests para que el CI pase.
- ❌ Dejar `print()` de depuración o código comentado.

## Flujo de trabajo

1. Leer `MEMORY.md`. Elegir la próxima task pendiente de `specs/NN-<área>/tasks.md` cuyas specs no tengan preguntas abiertas. Si el cambio no tiene spec, primero se sigue el **ciclo de un cambio** (ver Spec-Driven Development).
2. Crear una rama desde `main`: `feat/<tema>`, `fix/<tema>`, `test/<tema>`, `docs/<tema>`, `refactor/<tema>`, `spec/<tema>`.
3. **Red**: escribir el test del caso definido en `test-plan.md` (con el ID de spec y de caso en el docstring) y verlo fallar.
4. **Green**: escribir el código mínimo para que pase.
5. **Refactor**: limpiar con todos los tests en verde.
6. Correr las validaciones locales antes de commitear:
   ```bash
   ruff check . && ruff format --check . && pytest
   ```
7. Marcar la task como `[x]` en `tasks.md`.
8. Commits chicos, una unidad de trabajo cada uno, con el test y la implementación juntos.
9. Abrir el PR, esperar el CI en verde y al menos una revisión antes del merge.

## Testing y CI/CD

- `pytest` es el runner. Los tests se nombran por comportamiento: `test_closed_ticket_can_be_reopened_by_client`.
- **Unit** (`tests/unit/`): dominio y services con repositorios y notificadores falsos (fakes en memoria). Sin Flask, sin disco, sin red.
- **Integration** (`tests/integration/`): repositorios contra SQLite `sqlite://` en memoria (con `StaticPool`), esquema creado con `Base.metadata.create_all()`, y endpoints con `app.test_client()`.
- Cada test es independiente: base nueva por test mediante fixtures, sin depender del orden de ejecución.
- El tiempo se controla con un reloj falso; ningún test depende de la hora real ni de `sleep`.
- Las notificaciones nunca se envían de verdad en los tests: se usa una estrategia falsa que registra los envíos para poder verificarlos.
- Cobertura mínima: **90 %** sobre `app/`, con `pytest --cov=app --cov-fail-under=90`.
- Cada RNF tiene al menos un test explícito (ver tabla de RNF).

CI con GitHub Actions (`.github/workflows/ci.yml`), en cada push y PR a `main`:

1. Configurar Python 3.12 e instalar dependencias.
2. `ruff check .`
3. `ruff format --check .`
4. `pytest --cov=app --cov-fail-under=90`

Si algún paso falla, el PR no se mergea. No hay despliegue continuo: el entregable se ejecuta localmente.

## Estilo de commits y PRs

**Commits**: [Conventional Commits](https://www.conventionalcommits.org/), en inglés y en modo imperativo.

```
<type>(<scope>): <description>

feat(ticket): reopen closed ticket with same representative
test(auth): reject login with wrong password
fix(milestone): order milestones chronologically
```

- Tipos: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `ci`, `spec` (cambios en `specs/`: spec, plan, tasks o test-plan).
- Scopes sugeridos: `auth`, `user`, `ticket`, `state`, `milestone`, `notification`, `product`, `db`, `ci`.
- Sin trailers de coautoría de IA (`Co-Authored-By`) ni otras atribuciones automáticas.
- No mezclar refactors con cambios de comportamiento en un mismo commit.

**PRs**:

- Título con el mismo formato que los commits.
- Tamaño chico: idealmente menos de 400 líneas cambiadas. Si es más grande, dividirlo en PRs encadenados.
- La descripción incluye:
  - **Qué** cambia y **por qué**.
  - Specs que implementa (ej.: `SPEC-TKT-11`, `SPEC-TKT-12`), tasks que cierra (ej.: `T-TKT-04`) y RNF que toca (ej.: `RNF 5`).
  - Si cambia comportamiento: el diff de `spec.md` va en el mismo PR (o en un PR `spec(...)` previo ya mergeado).
  - Cómo se probó (tests nuevos o modificados).
  - Diagramas actualizados, si corresponde.
- Merge con squash a `main` una vez que el CI esté en verde y haya una aprobación.
