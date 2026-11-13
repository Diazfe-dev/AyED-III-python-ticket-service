# Secuencias — 01 Usuarios y accesos

Spec: [specs/01-users/spec.md](../../specs/01-users/spec.md)

Convenciones comunes a todos los diagramas:

- `UserService` recibe por constructor el repositorio, un `PasswordHasher` y la función `commit` (en producción, `session.commit`). El repositorio nunca hace commit.
- Las excepciones de dominio llegan a `register_error_handlers`, que las traduce a JSON con una tabla: `ValidationError` e `InvalidCurrentPasswordError` → `400`, `InvalidCredentialsError` → `401`, `PermissionDeniedError` → `403`, `UserNotFoundError` → `404`, `DuplicateUserError` y `SelfDeactivationError` → `409`. Una ruta o un método que la API no expone responde `404` `not_found` o `405` `method_not_allowed` (SPEC-PLT-15) y un error no manejado `500` `internal_error` (SPEC-PLT-16).
- `login_required` responde `401` `authentication_required` sin sesión (SPEC-USR-49). `admin_required` lo responde igual y `403` `forbidden` si el usuario no es `Admin`. Un usuario inexistente o inactivo cuenta como sin sesión.

## 1. Alta de usuario

Specs: SPEC-USR-01, 02, 03, 04, 05, 06, 18, 19, 23

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant UC as UserController
    participant US as UserService
    participant H as PasswordHasher
    participant UR as UserRepository

    Admin->>UC: POST /users (name, email, role, password, preferred_channel?)
    alt sin sesión o current_user no es Admin
        UC-->>Admin: 401 authentication_required o 403 forbidden (SPEC-USR-16, 18)
    else current_user es Admin
        UC->>US: create_user(name, email, role, password, preferred_channel)
        alt datos faltantes o inválidos, password con menos de 8 caracteres o canal desconocido
            US-->>UC: raise ValidationError(fields)
            UC-->>Admin: 400 validation_error con fields (SPEC-USR-05, 19, 23)
        else datos válidos
            US->>UR: find_by_email(email)
            Note over UR: Compara el email normalizado, strip y lower (SPEC-USR-03)
            UR-->>US: User o None
            alt el email ya existe (activo o inactivo)
                US-->>UC: raise DuplicateUserError
                UC-->>Admin: 409 duplicate_email (SPEC-USR-04)
            else email libre
                US->>H: hash(password)
                H-->>US: password_hash (SPEC-USR-02)
                US->>US: user = ROLE_CLASSES[role](is_active=True, preferred_channel o "mail") (SPEC-USR-06)
                US->>UR: add(user)
                Note over UR: add hace flush. Un IntegrityError por UNIQUE(email)<br/>se traduce a DuplicateUserError
                US->>US: commit()
                US-->>UC: user
                UC-->>Admin: 201 Created con el User, sin password_hash (SPEC-USR-01)
            end
        end
    end
```

## 2. Login y logout

Specs: SPEC-USR-14, 15, 16, 17, 24, 25

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant AC as AuthController
    participant US as UserService
    participant UR as UserRepository
    participant H as PasswordHasher
    participant S as Flask session

    U->>AC: POST /login (email, password)
    AC->>US: authenticate(email, password)
    alt falta un campo o no es texto
        US-->>AC: raise InvalidCredentialsError
        AC-->>U: 401 invalid_credentials (SPEC-USR-15, 25)
    else email y password son texto
        US->>UR: find_by_email(email)
        UR-->>US: User o None
        alt el email no existe o el usuario está inactivo
            US->>H: verify(dummy_hash(), password)
            Note over US,H: Hash de relleno calculado una vez por proceso. El login fallido<br/>cuesta un verify, igual que uno real (SPEC-USR-24)
            H-->>US: False
            US-->>AC: raise InvalidCredentialsError
            AC-->>U: 401 invalid_credentials (mensaje genérico, SPEC-USR-15)
        else usuario activo
            US->>H: verify(user.password_hash, password)
            H-->>US: True o False
            alt verify falla
                US-->>AC: raise InvalidCredentialsError
                AC-->>U: 401 invalid_credentials (mensaje genérico, SPEC-USR-15)
            else credenciales válidas
                US-->>AC: user
                AC->>S: session.clear() y session["user_id"] = user.id
                AC-->>U: 200 con id, name, email y role (SPEC-USR-14)
            end
        end
    end

    Note over U,S: Cualquier ruta protegida sin sesión responde 401 authentication_required (SPEC-USR-16)

    U->>AC: POST /logout
    alt sin sesión
        AC-->>U: 401 authentication_required (SPEC-USR-16)
    else con sesión
        AC->>S: session.clear()
        AC-->>U: 204 sin contenido (SPEC-USR-17)
    end
```

## 3. Baja lógica de usuario

Specs: SPEC-USR-09, 10, 18, 21

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant UC as UserController
    participant US as UserService
    participant UR as UserRepository

    Admin->>UC: POST /users/{id}/deactivate
    alt sin sesión o current_user no es Admin
        UC-->>Admin: 401 authentication_required o 403 forbidden (SPEC-USR-16, 18)
    else current_user es Admin
        UC->>US: deactivate_user(user_id, actor=current_user)
        alt user_id es el del propio admin
            US-->>UC: raise SelfDeactivationError
            UC-->>Admin: 409 self_deactivation (SPEC-USR-21)
        else otro usuario
            US->>UR: get(user_id)
            UR-->>US: user o None (None también para un id fuera del rango de SQLite)
            alt el usuario no existe
                US-->>UC: raise UserNotFoundError
                UC-->>Admin: 404 user_not_found (SPEC-USR-26)
            else el usuario existe
                US->>US: user.deactivate() pone is_active = False (SPEC-USR-09)
                US->>US: commit()
                Note over UR: No se borra nada. Tickets, hitos y StateChange<br/>del usuario se conservan (SPEC-USR-10)
                US-->>UC: user
                UC-->>Admin: 200 con el User e is_active false
            end
        end
    end
```

## 4. Creación del primer administrador (CLI)

Specs: SPEC-USR-20

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operador
    participant CLI as flask create-admin
    participant US as UserService
    participant UR as UserRepository

    Op->>CLI: flask --app app create-admin --name N --email E
    Note over Op,CLI: No existe la opción --password, click la rechaza con No such option
    CLI->>Op: click.prompt pide la contraseña dos veces, sin mostrarla
    Op->>CLI: password
    CLI->>US: create_user(name, email, role="Admin", password)
    Note over US: Aplica las mismas validaciones que el alta normal<br/>(email único, password de 8 caracteres o más)
    alt datos inválidos o email existente
        US-->>CLI: raise ValidationError o DuplicateUserError
        CLI-->>Op: "Error: ..." y código de salida 1
    else datos válidos
        US->>UR: add(user)
        US->>US: commit()
        US-->>CLI: user
        CLI-->>Op: "Admin created."
    end
```

## 5. Identidad de la sesión (GET /me)

Specs: SPEC-USR-27, 49

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant AC as AuthController

    U->>AC: GET /me
    alt sin sesión
        AC-->>U: 401 authentication_required (SPEC-USR-49)
    else con sesión
        AC-->>U: 200 con id, name, email y role de current_user (SPEC-USR-27)
    end
```

## 6. Reactivación de usuario

Specs: SPEC-USR-18, 28, 29, 30

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant UC as UserController
    participant US as UserService
    participant UR as UserRepository

    Admin->>UC: POST /users/{id}/activate
    alt sin sesión o current_user no es Admin
        UC-->>Admin: 401 authentication_required o 403 forbidden (SPEC-USR-18, 49)
    else current_user es Admin
        UC->>US: activate_user(user_id)
        US->>UR: get(user_id)
        UR-->>US: user o None (None también para un id fuera del rango de SQLite)
        alt el usuario no existe
            US-->>UC: raise UserNotFoundError
            UC-->>Admin: 404 user_not_found (SPEC-USR-30)
        else el usuario existe
            US->>US: user.activate() pone is_active = True (SPEC-USR-28)
            Note over US: Si ya estaba activo no cambia nada y responde igual (SPEC-USR-29)
            US->>US: commit()
            US-->>UC: user
            UC-->>Admin: 200 con el User e is_active true
        end
    end
```

## 7. Cambio de la contraseña propia

Specs: SPEC-USR-37, 38, 39, 40, 49

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant AC as AuthController
    participant US as UserService
    participant H as PasswordHasher

    U->>AC: POST /me/password (current_password, new_password)
    alt sin sesión
        AC-->>U: 401 authentication_required (SPEC-USR-49)
    else con sesión
        AC->>US: change_own_password(actor=current_user, current_password, new_password)
        alt un campo falta, es null o no es texto, o new_password tiene menos de 8 caracteres
            US-->>AC: raise ValidationError(fields)
            AC-->>U: 400 validation_error con fields (SPEC-USR-39, 40)
        else formato válido
            US->>H: verify(actor.password_hash, current_password)
            H-->>US: True o False
            alt la contraseña actual no coincide
                US-->>AC: raise InvalidCurrentPasswordError
                AC-->>U: 400 invalid_current_password, no 401 (SPEC-USR-38)
            else coincide
                US->>H: hash(new_password)
                H-->>US: password_hash (SPEC-USR-37)
                US->>US: actor.password_hash = password_hash
                US->>US: commit()
                AC-->>U: 204 sin contenido
            end
        end
    end
```

## 8. Restablecimiento de la contraseña de otro usuario

Specs: SPEC-USR-18, 39, 40, 41, 42

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant UC as UserController
    participant US as UserService
    participant H as PasswordHasher
    participant UR as UserRepository

    Admin->>UC: POST /users/{id}/password (new_password)
    alt sin sesión o current_user no es Admin
        UC-->>Admin: 401 authentication_required o 403 forbidden (SPEC-USR-18, 49)
    else current_user es Admin
        UC->>US: reset_password(user_id, new_password)
        US->>UR: get(user_id)
        UR-->>US: user o None (None también para un id fuera del rango de SQLite)
        alt el usuario no existe
            US-->>UC: raise UserNotFoundError
            UC-->>Admin: 404 user_not_found (SPEC-USR-42)
        else el usuario existe
            alt new_password falta, es null, no es texto o tiene menos de 8 caracteres
                US-->>UC: raise ValidationError(fields)
                UC-->>Admin: 400 validation_error con fields (SPEC-USR-39, 40)
            else new_password válida
                US->>H: hash(new_password)
                H-->>US: password_hash (SPEC-USR-41)
                US->>US: user.password_hash = password_hash, sin pedir la contraseña anterior
                US->>US: commit()
                UC-->>Admin: 204 sin contenido
            end
        end
    end
```

## 9. Listados de usuarios, clientes y representantes

Specs: SPEC-USR-31, 32, 33, 34, 35, 36, 43, 44, 45, 46, 47, 48, 50

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant UC as UserController
    participant US as UserService
    participant UR as UserRepository

    U->>UC: GET /users o /representatives (is_active?, q?, page?, page_size?)
    alt sin sesión o current_user no es Admin
        UC-->>U: 401 authentication_required o 403 forbidden (SPEC-USR-35, 49)
    else current_user es Admin
        UC->>US: list_users(role, is_active, q, page, page_size)
        Note over US: role es None en /users (todos los roles) y Representative en /representatives
        alt is_active no es true ni false, o page o page_size son inválidos
            US-->>UC: raise ValidationError(fields)
            UC-->>U: 400 validation_error con fields (SPEC-USR-45, 47)
        else parámetros válidos
            US->>UR: search(role, is_active, q, window=PageRequest o None)
            Note over UR: q busca por nombre o email, sin distinguir mayúsculas (casefold).<br/>Orden por nombre sin distinguir mayúsculas y por id (SPEC-USR-43, 48)
            UR-->>US: list o Page
            US-->>UC: usuarios
            UC-->>U: 200 con id, name, email, role e is_active de cada usuario (SPEC-USR-31, 36, 44)
        end
    end

    U->>UC: GET /clients (is_active?, q?, page?, page_size?)
    alt sin sesión
        UC-->>U: 401 authentication_required (SPEC-USR-49)
    else con sesión
        UC->>US: list_clients(actor=current_user, is_active, q, page, page_size)
        alt actor es Client
            US-->>UC: raise PermissionDeniedError
            UC-->>U: 403 forbidden, antes de validar el formato (SPEC-USR-35)
        else actor es Admin o Representative
            alt is_active inválido, o page o page_size inválidos
                US-->>UC: raise ValidationError(fields)
                UC-->>U: 400 validation_error con fields (SPEC-USR-45, 47)
            else formato válido
                alt actor es Representative y envió is_active
                    US-->>UC: raise PermissionDeniedError
                    UC-->>U: 403 forbidden (SPEC-USR-50)
                else actor es Representative
                    US->>UR: search(role="Client", is_active=True, q, search_email=False, window)
                    UR-->>US: list o Page
                    UC-->>U: 200 solo con id y name de cada cliente activo (SPEC-USR-32, 33, 46)
                else actor es Admin
                    US->>UR: search(role="Client", is_active, q, window)
                    UR-->>US: list o Page
                    UC-->>U: 200 con los campos de usuario, activos e inactivos (SPEC-USR-34, 36)
                end
            end
        end
    end
```
