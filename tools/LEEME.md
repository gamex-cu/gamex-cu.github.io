# Herramientas del Catálogo GameX

- `datos/ps4.json`: lista de juegos de PS4.
- `datos/gamepass.json`: lista de Xbox Game Pass (la genera `actualizar_gamepass.py`).
- `datos/reglas_gamepass.json`: correcciones hechas a mano (nombres, juegos quitados, solo online, Xbox clásico). **No borrar.**
- `plantilla/`: diseño de la página (cabecera con estilos y logo, y el script).
- `armar.py`: genera `index.html` (web), `app/catalogo.html` (app) y `salida/catalogo-claude.html`. Sube la versión del catálogo en `app/version.json`.
- `actualizar_gamepass.py`: baja Game Pass del catálogo oficial de Microsoft y escribe `salida/reporte_gamepass.md`.

## Revisión semanal de Game Pass (domingos)
1. `python3 tools/actualizar_gamepass.py` → imprime "CAMBIOS" o "SIN CAMBIOS" y el reporte.
2. Si hay CAMBIOS: `python3 tools/armar.py`, luego commit y push a `main`.
3. Avisar al dueño con el reporte: juegos que entraron, que salieron y los que hay que revisar si son solo online.
4. Cuando el dueño diga cuáles nuevos son solo online, agregarlos a `online` en `reglas_gamepass.json`,
   pasar sus claves de `pendientes` a `revisados`, correr `armar.py` y subir.
