# Secuencias — 01 Usuarios y accesos

Spec: [specs/01-users/spec.md](../../specs/01-users/spec.md)

Convenciones comunes a los cuatro diagramas:

- `UserService` recibe por constructor el repositorio, un `PasswordHasher` y la función `commit` (en producción, `session.commit`). El repositorio nunca hace commit.
- Las excepciones de dominio llegan a `register_error_handlers`, que las traduce a JSON con una tabla: `ValidationError` → `400`, `InvalidCredentialsError` → `401`, `UserNotFoundError` → `404`, `DuplicateUserError` y `SelfDeactivationError` → `409`.
- `admin_required` responde `401` `authentication_required` sin sesión y `403` `forbidden` si el usuario no es `Admin`. Un usuario inexistente o inactivo cuenta como sin sesión.

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
            UR-->>US: user o None
            alt el usuario no existe
                US-->>UC: raise UserNotFoundError
                UC-->>Admin: 404 user_not_found
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
