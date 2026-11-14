# 22 · Llevar GAIA a otra PC y seguir trabajando

Escrito el 14 de noviembre de 2026 tras el commit `1c9e92f`. Sirve para copiar el proyecto por Google Drive, levantarlo en la PC del evento y dar contexto a Codex y a Claude Code en una ventana nueva.

## 1. Qué hay en la carpeta y qué se copia

Medido en la PC original:

| Carpeta | Tamaño | ¿Copiar? | Por qué |
|---|---|---|---|
| `.git` | 616 MB | **Sí** | Historia completa, ramas y commits (rama de trabajo `feat/gaia-alerta`) |
| `apps/`, `services/`, `config/`, `docs/`, `scripts/`, `tools/`, `tests/`, `packages/`, `infra/` | pequeño | **Sí** | Todo el código, la configuración y los planes |
| `art/` | 255 MB | **Sí** | Escena de Blender de la portada, modelos y verificaciones |
| `apps/web/public/` | 49 MB | **Sí** (va con `apps/`) | Videos de la portada, sonido, modelos 3D y relieve |
| `data/03_processed` | 245 MB | **Sí** | Resultados NISAR de Ayacucho (COG, manchas, series) |
| `data/04_published` | 24 MB | **Sí** | Comunidad, clima, exposición, validación, contexto |
| `data/catalog` | 3 MB | **Sí** | Manifiesto de lo ingerido, con SHA-256 |
| `data/01_raw` | **7,6 GB** | Opcional, aparte | Originales HDF5 de NISAR y demás. Solo hacen falta para **volver a procesar**; la app funciona sin ellos |
| `.venv` | 548 MB | **No** | Python de esta PC; se vuelve a crear con `uv sync` |
| `apps/web/node_modules` | 262 MB | **No** | Se vuelve a crear con `npm ci` |
| `deploy/` | 835 MB | **No** | Copias temporales de verificación y Docker; se regeneran |
| `.env` y `apps/web/.env` | — | **No por Drive** | Tienen tus claves. Ver la sección 3 |
| `.mcp.json` | — | No | Lleva rutas de esta PC (Blender MCP); se vuelve a crear si hace falta |

**Total a subir sin los originales: unos 1,3 GB.** Con `data/01_raw`, unos 9 GB.

## 2. Preparar la copia (en esta PC, PowerShell)

Google Drive sube muy lento miles de archivos sueltos. Por eso se arma una copia limpia y se comprime en un solo `.zip`.

```powershell
# 1. Copia limpia sin lo que se regenera ni las claves
robocopy "$env:USERPROFILE\Desktop\GAIA" "$env:USERPROFILE\Desktop\GAIA-viaje" /E /XD .venv node_modules deploy 01_raw 02_interim __pycache__ .pytest_cache .ruff_cache dist /XF .env .mcp.json *.blend1

# 2. Comprimir
Compress-Archive -Path "$env:USERPROFILE\Desktop\GAIA-viaje\*" -DestinationPath "$env:USERPROFILE\Desktop\GAIA-viaje.zip"
```

- `robocopy` omite las carpetas y archivos indicados en todos los niveles, así que `apps/web/.env` tampoco se copia.
- Sube `GAIA-viaje.zip` a Google Drive.
- **Opcional:** comprime aparte `data\01_raw` como `GAIA-originales.zip` (7,6 GB) solo si vas a reprocesar en el evento.
- Antes de subir, confirma que el zip no tiene claves: no debe aparecer ningún archivo llamado `.env` (sí `.env.example`).
- Antes de copiar, `git status` debe estar limpio, así todo queda en commits.

## 3. Las claves (nunca en Drive ni en el chat)

Llévalas en un gestor de contraseñas, o vuelve a copiarlas desde cada sitio:

| Variable | Dónde se consigue | Dónde va |
|---|---|---|
| `EARTHDATA_TOKEN` | urs.earthdata.nasa.gov → Generate Token | `.env` (raíz) |
| `FIRMS_MAP_KEY` | firms.modaps.eosdis.nasa.gov/api/map_key | `.env` (raíz) |
| `VITE_CESIUM_ION_TOKEN` | ion.cesium.com → Access Tokens | `apps/web/.env` |
| `GAIA_REPORTS_ADMIN_TOKEN` | La inventas tú (texto largo al azar) | `.env` (raíz); solo para moderar reportes |

En la PC nueva, el asistente del proyecto pide las tres primeras con entrada oculta y escribe ambos archivos. `GAIA_REPORTS_ADMIN_TOKEN` se añade a mano en `.env`, solo si vas a moderar reportes.

```powershell
powershell -ExecutionPolicy Bypass -File tools\configurar-credenciales.ps1
```

Si el token de Cesium está limitado por dominio, añade `http://localhost:5173` en sus URLs permitidas para trabajar en local.

## 4. Instalar en la PC del evento

Programas: Git, Python 3.11 o superior, [uv](https://docs.astral.sh/uv/), Node.js (aquí se usó la versión 24) y Chrome. Docker Desktop solo hace falta para la versión empaquetada; Blender solo para tocar la portada.

```powershell
# Descomprimir GAIA-viaje.zip, por ejemplo en el Escritorio\GAIA, y entrar
cd $env:USERPROFILE\Desktop\GAIA

git status                     # debe decir rama feat/gaia-alerta y nada pendiente
uv sync                        # crea .venv con Python y el pipeline
cd apps\web; npm ci; cd ..\..  # instala la web
powershell -ExecutionPolicy Bypass -File tools\configurar-credenciales.ps1
uv run python scripts\doctor.py   # revisa el entorno
uv run pytest -q                  # deben pasar todas
```

Si `make` existe en esa PC, `make setup`, `make test` y `make doctor` hacen lo mismo.

## 5. Levantar la app

Dos terminales:

```powershell
# Terminal 1 · API (datos, NISAR, USGS, FIRMS)
uv run fastapi dev services/api/app/main.py
```

```powershell
# Terminal 2 · Interfaz
cd apps\web; npm run dev
```

- Abrir **http://localhost:5173**. La interfaz pide los datos a la API del puerto **8000**.
- Comprobar **http://localhost:8000/api/health**: debe decir `earthdata: true` y `firms: true`.

**Versión empaquetada (Docker, opcional), puerto 7860.** Según `docs/15_Despliegue_Completo.md`, Docker necesita `deploy/data/`, que no viaja. Antes hay que regenerarlo siguiendo ese documento.

```powershell
docker build --secret id=web_env,src=apps/web/.env -t gaia-alerta .
docker run --rm --name gaia-alerta -p 127.0.0.1:7860:7860 --env-file .env gaia-alerta
```

## 6. Recorrido para comprobar que todo está

1. **Portada:** se ve el video y suena al primer clic. Botón «PROJECT GAIA».
2. **Globo:** contadores 106 / 933 / 498 (cambian con los datos en vivo). Fuego rojo, naranja o marrón según la antigüedad. NISAR en órbita.
3. **Lugares → Ayacucho → Cambios:** barrido del radar y cortina del 24 de junio al 10 de octubre de 2026.
4. **Tiempo:** dos fechas radar y 45 años de NASA POWER.
5. **Calidad:** gránulos de la trayectoria 147, 99,91 % válido y OPERA.
6. **Mi comunidad → Huamanga:** semáforo, por qué, WhatsApp, ficha imprimible.
7. **Alertas:** lo más importante y «¿a quién afecta?».

## 7. Estado del proyecto (para tener a mano)

- **Rama:** `feat/gaia-alerta`. Último commit al escribir esto: `1c9e92f`. Sin repositorio remoto todavía.
- **Pruebas:** 61 en Python, más las de la web (`npm --prefix apps/web test`).
- **Hecho:**
  - portada PROJECT GAIA;
  - globo vivo con W1–W8, la órbita NISAR y «la danza»;
  - G1–G4 y G7–G10;
  - Mi comunidad, semáforo, clima y reportes (C1–C4);
  - revisión 19 cerrada (doc 20);
  - datos extra D1–D4: pendiente agrícola, HLS, calendario y MODIS (doc 21);
  - fuego por antigüedad.
- **Pendiente:**
  - publicar en internet (aplazado);
  - G5 (tendencia NISAR con 4 fechas) y G6 (deformación de Sabancaya);
  - texto del proyecto y pitch de 30 s en inglés (guion en `docs/18`);
  - envío antes del domingo 15 a las 11:59 p. m.
- **Cifras clave de Ayacucho:**
  - 938,28 ha en 498 zonas HV, de ellas 518,36 ha en cultivo;
  - 3607 ha de píxeles con caída de HV;
  - umbral de 2,63 dB y 99,91 % de área válida;
  - OPERA coincide en un 2,25 %.

## 8. Contexto para Codex y Claude Code en una ventana nueva

Abre el agente **dentro de la carpeta GAIA** y pega esto como primer mensaje:

```text
Eres parte del equipo de GAIA Alerta (NASA Space Apps 2026, reto Dancing with the SARs). Estamos
en otra PC; el proyecto se copió sin .venv, node_modules, deploy/ ni data/01_raw, y las claves ya
están en .env y apps/web/.env (no los leas).

Antes de tocar nada lee, en este orden:
1. CLAUDE.md y AGENTS.md (reglas de oro: datos reales, NISAR separado de lo complementario,
   no escribir en data/01_raw, no inventar rutas HDF5, pedir permiso para descargas > 5 GB).
2. docs/22_Arranque_en_otra_PC.md (estado actual y cómo se levanta).
3. docs/00_LEEME.md (mapa) y CHANGELOG.md (lo último hecho).
4. Los planes y revisiones más recientes: docs/13, docs/17, docs/18, docs/19, docs/20 y docs/21.

Luego comprueba el entorno sin cambiar nada: git status y git log -5, uv run pytest -q,
npm --prefix apps/web run typecheck y /api/health con la API levantada. Dime qué funciona,
qué falta y qué propones hacer primero según el horario de entrega del doc 18 (congelar
funciones a las 15:00 del domingo, enviar antes de las 11:59 p. m.). Espera mi confirmación.
```

**Para no pisarse entre agentes:** Codex y Claude Code no deben editar los mismos archivos a la vez. Asigna a cada uno una tarea distinta, cada una con su propio commit, y pide a ambos que ejecuten `git status` antes de empezar.
