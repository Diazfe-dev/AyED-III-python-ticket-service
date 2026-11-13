# Licencias de terceros

Archivos de terceros que la interfaz web sirve desde `app/static/fonts/`:

| Archivo | Origen | Licencia |
|---------|--------|----------|
| `roboto-latin.woff2` | Roboto (fuente variable, subconjunto latino), The Roboto Project Authors | SIL Open Font License 1.1, [roboto-OFL.txt](roboto-OFL.txt) |
| `material-symbols-subset.woff2` | Material Symbols Outlined (Google), con solo los íconos que usa el menú | Apache License 2.0, [material-symbols-Apache-2.0.txt](material-symbols-Apache-2.0.txt) |

Las licencias están fuera de `app/static/` porque el escaneo estático de SPEC-UI-05 rechaza cualquier URL absoluta en los archivos servidos.
