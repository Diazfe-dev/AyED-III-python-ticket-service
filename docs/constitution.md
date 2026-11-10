# Constitución del proyecto

Principios innegociables. Prevalecen sobre AGENTS.md, MEMORY.md y cualquier spec.

1. **Stack**: Python 3.12, Flask, SQLAlchemy 2.0 y SQLite. Ninguna dependencia nueva entra en `requirements*.txt` sin una decisión aprobada en `MEMORY.md`.
2. **Spec y código**: `spec.md` es la fuente de verdad. Todo comportamiento se traza a un `SPEC-<ÁREA>-<NN>`, y ningún cambio de comportamiento se mergea sin modificar antes su spec.
3. **Lógica e interfaz**: la lógica de negocio vive solo en `domain/` y `services/`. Los controllers solo traducen HTTP. `domain/` nunca importa `flask`.
4. **Tests**: TDD estricto. Cada spec tiene al menos un test que la cita en su docstring. No se mergea sin el CI en verde (ruff + pytest con cobertura ≥ 90 %).
5. **Datos del usuario**: las contraseñas se guardan solo como hash. Un cliente accede solo a sus tickets (un ticket ajeno responde 404). Los hitos y cambios de estado son inmutables y registran usuario y fecha/hora UTC.
6. **Idioma**: código, identificadores, tests y commits en inglés. Specs y documentación en español neutro.

Modificar esta constitución requiere aprobación explícita del equipo y una entrada en `MEMORY.md`.
