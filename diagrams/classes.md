# Diagrama de clases

Versión en Mermaid del diagrama de clases. Se divide en dos vistas para que sea legible:

1. **Modelo de dominio**: entidades, relaciones y los patrones State y Strategy.
2. **Capas de aplicación**: controllers, services y repositories (Controller → Service → Repository).

Los nombres siguen la convención de Python (`snake_case` para atributos y métodos), igual que los [diagramas de secuencia](sequences/).

## 1. Modelo de dominio

```mermaid
classDiagram
    direction LR

    class User {
        <<abstract>>
        +int id
        +str name
        +str email
        +str password_hash
        +str preferred_channel
        +str role
        +bool is_active
        +deactivate() None
    }
    class Admin
    class Representative {
        +list~Ticket~ assigned_tickets
    }
    class Client {
        +list~Ticket~ tickets
    }
    User <|-- Admin
    User <|-- Representative
    User <|-- Client

    class Ticket {
        +int id
        +Client client
        +Representative representative
        +list~Product~ products
        +str state_name
        +State state
        +list~Milestone~ milestones
        +list~StateChange~ state_history
        +list~Notification~ notifications
        +close(user) None
        +reopen(user) None
        +start_progress(user) None
        +add_milestone(content, author) Milestone
        +add_products(products) None
        +remove_product(product) None
    }

    class Milestone {
        <<immutable>>
        +int id
        +str content
        +User author
        +datetime created_at
    }
    class StateChange {
        <<immutable>>
        +int id
        +User user
        +str state_name
        +datetime timestamp
    }

    Ticket "*" o-- "1" Client : client
    Ticket "*" o-- "1" Representative : representative
    Ticket "*" o-- "*" Product : products
    Ticket "1" *-- "1..*" Milestone : milestones
    Ticket "1" *-- "1..*" StateChange : state_history
    Ticket "1" *-- "*" Notification : notifications
    Milestone "*" --> "1" User : author
    StateChange "*" --> "1" User : user

    class State {
        <<abstract>>
        +str name
        +close(ticket, user) None
        +reopen(ticket, user) None
        +in_progress(ticket, user) None
    }
    class NewState {
        +close(ticket, user) None
        +in_progress(ticket, user) None
    }
    class InProgressState {
        +close(ticket, user) None
    }
    class ClosedState {
        +reopen(ticket, user) None
    }
    State <|-- NewState
    State <|-- InProgressState
    State <|-- ClosedState
    Ticket ..> State : delega transiciones

    class Category {
        +int id
        +str name
    }
    class ProductType {
        +int id
        +str name
        +Category category
    }
    class Product {
        +int id
        +str name
        +ProductType product_type
        +bool is_active
        +deactivate() None
    }
    ProductType "*" --> "1" Category : category
    Product "*" --> "1" ProductType : product_type

    class Notification {
        +int id
        +User recipient
        +str channel
        +str message
        +datetime created_at
        +str status
    }
    class NotificationStrategy {
        <<interface>>
        +send(recipient, message) None
    }
    class MailNotification {
        +send(recipient, message) None
    }
    class WhatsappNotification {
        +send(recipient, message) None
    }
    NotificationStrategy <|.. MailNotification
    NotificationStrategy <|.. WhatsappNotification
    Notification "*" --> "1" User : recipient
```

### Notas del modelo

- **Patrón State**: los métodos de `State` lanzan `InvalidTransitionError` por defecto, y cada estado concreto sobrescribe solo sus transiciones válidas. En la base solo se persiste `state_name`; la propiedad `state` lo convierte en el objeto `State` correspondiente. Las clases de estado no son entidades mapeadas.

  | Desde | `in_progress` | `close` | `reopen` |
  |-------|---------------|---------|----------|
  | `NewState` | → `InProgress` | → `Closed` | ❌ |
  | `InProgressState` | ❌ | → `Closed` | ❌ |
  | `ClosedState` | ❌ | ❌ | → `InProgress` |

- **Composición** (rombo lleno): `Milestone`, `StateChange` y `Notification` existen solo dentro de un `Ticket` y se crean únicamente a través de sus métodos.
- **Agregación** (rombo vacío): `Client`, `Representative` y `Product` tienen un ciclo de vida independiente del ticket.
- **Inmutables**: `Milestone` y `StateChange` no se pueden modificar ni borrar. Los protegen listeners del ORM y triggers de SQLite (RNF 5 y 6).
- **Baja lógica**: `User` y `Product` tienen `is_active` y nunca se borran físicamente.
- **Usuarios**: herencia de tabla única (tabla `users`) con el discriminador `role`; el registro `ROLE_CLASSES` resuelve la subclase a partir del rol. El email se normaliza al asignarlo (`normalize_email`) y `preferred_channel` solo admite `mail` o `whatsapp` (`NOTIFICATION_CHANNELS`). `User` no verifica contraseñas: el dominio solo importa `sqlalchemy`, así que el hash vive en `PasswordHasher` (capa de services).
- **Patrón Strategy**: `NotificationService` elige la estrategia según `recipient.preferred_channel`. Ambas estrategias simulan el envío.

## 2. Capas de aplicación

```mermaid
classDiagram
    direction TB

    class AuthController {
        +login(email, password)
        +logout()
    }
    class UserController {
        +create_user(body)
        +update_user(user_id, body)
        +deactivate_user(user_id)
        +list_clients()
        +list_representatives()
    }
    class auth {
        <<module>>
        +get_user_service() UserService
        +current_user() User
        +authenticated_user() User
        +login_required(view)
        +admin_required(view)
    }
    class errors {
        <<module>>
        +ERROR_RESPONSES dict
        +register_error_handlers(app) None
    }
    class cli {
        <<module>>
        +create_admin(name, email, password)
    }
    class TicketController {
        +create_ticket(client_id, product_ids, first_message)
        +list_tickets()
        +get_ticket(ticket_id)
        +close_ticket(ticket_id)
        +reopen_ticket(ticket_id)
        +add_products(ticket_id, product_ids)
        +remove_product(ticket_id, product_id)
    }
    class MilestoneController {
        +add_milestone(ticket_id, content, start_progress)
        +list_milestones(ticket_id)
    }
    class CatalogController {
        +create_category(name)
        +update_category(category_id, name)
        +delete_category(category_id)
        +create_product_type(name, category_id)
        +update_product_type(type_id, form)
        +delete_product_type(type_id)
        +list_product_types(category_id)
        +create_product(name, product_type_id)
        +update_product(product_id, form)
        +deactivate_product(product_id)
        +list_products(filters)
        +list_available_products()
    }

    class UserService {
        +UserRepository repository
        +PasswordHasher hasher
        +Callable commit
        +create_user(name, email, role, password, preferred_channel) User
        +update_user(user_id, name, email, preferred_channel) User
        +deactivate_user(user_id, actor) User
        +authenticate(email, password) User
        +find_active_user(user_id) User
        +list_by_role(role) list
    }
    class PasswordHasher {
        <<interface>>
        +hash(password) str
        +verify(password_hash, password) bool
    }
    class WerkzeugPasswordHasher {
        +hash(password) str
        +verify(password_hash, password) bool
    }
    class TicketService {
        +create_ticket(client_id, product_ids, first_message, representative) Ticket
        +list_tickets(actor) list
        +get_ticket(ticket_id, actor) Ticket
        +close_ticket(ticket_id, actor) Ticket
        +reopen_ticket(ticket_id, actor) Ticket
        +add_milestone(ticket_id, content, actor, start_progress) Milestone
        +list_milestones(ticket_id, actor) list
        +add_products(ticket_id, product_ids, actor) None
        +remove_product(ticket_id, product_id, actor) None
    }
    class CatalogService {
        +create_category(name) Category
        +update_category(category_id, name) Category
        +delete_category(category_id) None
        +create_product_type(name, category_id) ProductType
        +update_product_type(type_id, data) ProductType
        +delete_product_type(type_id) None
        +list_product_types(category_id) list
    }
    class ProductService {
        +create_product(name, product_type_id) Product
        +update_product(product_id, data) Product
        +deactivate_product(product_id) None
        +list_products(filters) list
        +list_available_products() list
    }
    class NotificationService {
        +dict strategies
        +notify(recipient, actor, ticket, message) None
    }

    class UserRepository {
        +get(user_id) User
        +find_by_email(email) User
        +list_by_role(role) list
        +add(user) None
    }
    class TicketRepository {
        +get_visible(ticket_id, actor) Ticket
        +list_by_client(client_id) list
        +list_by_representative(rep_id) list
        +add(ticket) None
    }
    class CategoryRepository
    class ProductTypeRepository
    class ProductRepository {
        +get_many(product_ids) list
        +list(filters) list
    }
    class NotificationRepository {
        +add(notification) None
    }

    AuthController --> auth
    UserController --> auth
    cli --> auth
    auth --> UserService
    AuthController ..> errors : DomainError a HTTP
    UserController ..> errors : DomainError a HTTP
    TicketController --> TicketService
    MilestoneController --> TicketService
    CatalogController --> CatalogService
    CatalogController --> ProductService

    UserService --> UserRepository
    UserService --> PasswordHasher
    PasswordHasher <|.. WerkzeugPasswordHasher
    TicketService --> TicketRepository
    TicketService --> UserRepository
    TicketService --> ProductRepository
    TicketService --> NotificationService
    CatalogService --> CategoryRepository
    CatalogService --> ProductTypeRepository
    ProductService --> ProductRepository
    ProductService --> ProductTypeRepository
    NotificationService --> NotificationRepository
    NotificationService --> NotificationStrategy
```

### Notas de las capas

- Los **controllers** solo traducen HTTP: validan la entrada, obtienen `current_user` de la sesión y convierten las excepciones de dominio en códigos HTTP.
- Los **services** reciben sus dependencias por constructor (repositorios, `NotificationService`, un `clock` inyectable y la función `commit`, que en producción es `session.commit`) y deciden cuándo confirmar la transacción. `UserService` recibe además un `PasswordHasher`.
- `app/auth.py` arma `UserService` para cada request (o comando CLI) y expone `current_user()` y los decoradores `login_required` (`401`) y `admin_required` (`403`). `app/controllers/errors.py` traduce cada `DomainError` a su status y código JSON con una tabla. El comando `create-admin` (`app/cli.py`) reutiliza `create_user`.
- Los **repositories** encapsulan la `Session` de SQLAlchemy y nunca hacen commit. `UserRepository.add` hace `flush()` y traduce el `IntegrityError` del email único a `DuplicateUserError`. `TicketRepository.get_visible` aplica el filtro de privacidad (RNF 4).
- No hay `MilestoneService`: los hitos forman parte del agregado `Ticket` y se gestionan desde `TicketService`.
