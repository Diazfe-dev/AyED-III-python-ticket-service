# Secuencias — 01 Usuarios y accesos

Spec: [specs/01-users/spec.md](../../specs/01-users/spec.md)

## 1. Alta de usuario

Specs: SPEC-USR-01, 02, 03, 04, 05, 06, 18, 19

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant UC as UserController
    participant US as UserService
    participant UR as UserRepository

    Admin->>UC: POST /users (name, email, role, password, preferred_channel?)
    alt current_user no es Admin
        UC-->>Admin: 403 Forbidden (SPEC-USR-18)
    else current_user es Admin
        UC->>US: create_user(name, email, role, password, preferred_channel)
        US->>US: email = email.strip().lower() (SPEC-USR-03)
        alt datos faltantes o inválidos, o password con menos de 8 caracteres
            US-->>UC: raise ValidationError(fields)
            UC-->>Admin: 400 Bad Request con campos inválidos (SPEC-USR-05, 19)
        else datos válidos
            US->>UR: find_by_email(email)
            UR-->>US: User o None
            alt el email ya existe (activo o inactivo)
                US-->>UC: raise DuplicateUserError
                UC-->>Admin: 409 Conflict (SPEC-USR-04)
            else email libre
                US->>US: password_hash = generate_password_hash(password) (SPEC-USR-02)
                US->>US: user = User(role, is_active=True, preferred_channel or "mail") (SPEC-USR-06)
                US->>UR: add(user)
                US->>UR: commit()
                Note over UR: Si la base lanza IntegrityError por UNIQUE(email),<br/>se traduce a DuplicateUserError
                US-->>UC: user
                UC-->>Admin: 201 Created (SPEC-USR-01)
            end
        end
    end
```

## 2. Login y logout

Specs: SPEC-USR-14, 15, 16, 17

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant AC as AuthController
    participant US as UserService
    participant UR as UserRepository
    participant S as Flask session

    U->>AC: POST /login (email, password)
    AC->>US: authenticate(email, password)
    US->>UR: find_by_email(email.strip().lower())
    UR-->>US: User o None
    alt no existe, está inactivo o check_password_hash falla
        US-->>AC: raise InvalidCredentialsError
        AC-->>U: 401 "Credenciales inválidas" (mensaje genérico, SPEC-USR-15)
    else credenciales válidas y usuario activo
        US-->>AC: user
        AC->>S: session["user_id"] = user.id
        AC-->>U: 302 redirect al inicio (SPEC-USR-14)
    end

    Note over U,S: Cualquier ruta protegida sin sesión → login_required → 302 /login (SPEC-USR-16)

    U->>AC: POST /logout
    AC->>S: session.clear()
    AC-->>U: 302 redirect a /login (SPEC-USR-17)
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
    alt current_user no es Admin
        UC-->>Admin: 403 Forbidden (SPEC-USR-18)
    else current_user es Admin
        UC->>US: deactivate_user(user_id, actor=current_user)
        alt user_id es el del propio admin
            US-->>UC: raise SelfDeactivationError
            UC-->>Admin: 409 Conflict (SPEC-USR-21)
        else otro usuario
            US->>UR: get(user_id)
            UR-->>US: user
            US->>US: user.deactivate() → is_active = False (SPEC-USR-09)
            US->>UR: commit()
            Note over UR: No se borra nada: tickets, hitos y StateChange<br/>del usuario se conservan (SPEC-USR-10)
            UC-->>Admin: 200 OK
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

    Op->>CLI: flask --app app create-admin (name, email, password)
    CLI->>US: create_user(name, email, role="Admin", password)
    Note over US: Aplica las mismas validaciones que el alta normal<br/>(email único, password de 8 caracteres o más)
    US->>UR: add(user) y commit()
    US-->>CLI: user
    CLI-->>Op: "Admin creado"
```
