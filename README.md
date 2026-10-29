# GAMEX

Catálogo de juegos de GAMEX.

- `index.html`: catálogo web (https://gamex-cu.github.io)
- `app/catalogo.html`: catálogo que descarga la app de Android
- `app/version.json`: la app lo revisa al abrirse. Sube `catalogo` en 1 cuando cambie la lista; sube `apk` cuando haya una APK nueva.
- `app/GameX-<versión>.apk`: última versión de la app (el nombre lleva la versión; `app/version.json` → `apkUrl` dice cuál es)
