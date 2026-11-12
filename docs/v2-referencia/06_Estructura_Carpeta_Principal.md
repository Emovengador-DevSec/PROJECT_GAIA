# Estructura de la carpeta principal

Cómo se organiza el repositorio para que crezca sin volverse un caos y para que **recibir datos nuevos sea una operación rutinaria**. El esqueleto real, con archivos listos, está en la carpeta `bailando-sars/` del paquete.

## Seis reglas contra el caos

1. **Una cosa, un lugar.** Si dudas dónde va un archivo, consulta la tabla "¿Dónde va...?" de este documento.
2. **Los datos no viven en Git.** Solo se versionan el código, la configuración y las carpetas vacías con su explicación.
3. **Lo crudo es inmutable.** Nada se edita en `data/01_raw/`. Se corrige reprocesando, no sobrescribiendo.
4. **Todo lo ajustable vive en `config/`.** Ningún umbral, zona ni paleta escrito a mano dentro del código.
5. **Los nombres se pueden predecir.** Con la convención de nombres, cualquiera encuentra un archivo sin buscarlo.
6. **Cada carpeta explica su propósito** en un `README.md` de cinco líneas.

## Árbol completo

```
bailando-sars/
├── README.md                  Qué es y cómo arrancar en un comando
├── AGENTS.md  CLAUDE.md       Reglas para el agente de código (mismo contenido)
├── CHANGELOG.md               Una línea por cambio relevante
├── LICENSE
├── Makefile                   Atajos: setup, dev, test, lint, ingest, verify
├── .env.example               Variables de entorno sin valores
├── .gitignore  .editorconfig  .pre-commit-config.yaml
├── .github/                   CI, plantilla de revisión y actualizaciones de dependencias
│
├── apps/
│   └── web/                   Interfaz (React, Vite, TypeScript)
│       └── src/
│           ├── app/           Arranque, rutas, proveedores
│           ├── features/      Una carpeta por pestaña (explorar, cambios, ...)
│           ├── components/    Piezas visuales reutilizables
│           ├── lib/           Cliente de API, utilidades, estado de filtros
│           ├── styles/        Tokens de diseño y estilos globales
│           └── i18n/          Textos en español e inglés
│
├── services/
│   ├── api/                   Servidor (FastAPI)
│   │   └── app/{routes,schemas,core,services}/
│   └── pipeline/              Procesamiento de datos
│       └── src/sarlab_pipeline/
│           ├── sources/       Un adaptador por fuente (nisar, opera, firms, usgs)
│           ├── readers/       Lectura de HDF5 y otros formatos
│           ├── processing/    dB, fase a cm, máscaras, recortes
│           ├── detection/     Cambio, clasificación, alertas
│           ├── publish/       COG, GeoJSON y manifiestos
│           └── cli/           Comandos: ingest, process, verify
│
├── packages/
│   └── contracts/             Esquemas JSON y tipos generados
│
├── config/                    Todo lo ajustable (ver archivo 07)
│   ├── app.yaml  sources.yaml  thresholds.yaml  colormaps.yaml  features.yaml
│   ├── aois/                  Una zona por archivo
│   ├── phenomena/             Un fenómeno por archivo
│   └── products/              Un producto de datos por archivo
│
├── data/                      Contenido ignorado por Git (ver zonas abajo)
│   ├── 00_inbox/              Aquí se suelta lo nuevo
│   ├── 01_raw/                Original e inmutable, por fuente
│   ├── 02_interim/            Recortes y conversiones intermedias
│   ├── 03_processed/          Resultados por zona
│   ├── 04_published/          Lo que sirve la API
│   ├── 99_quarantine/         Lo que falló la validación, con el motivo
│   └── catalog/               Índice de todo lo que existe
│
├── docs/
│   ├── agent-pack/            Estos documentos
│   ├── decisions/             Registros de decisiones (ADR)
│   ├── runbooks/              Procedimientos paso a paso
│   ├── science/               Notas de método y validación
│   └── data-notes.md          Lo que se descubre del dato real
│
├── scripts/                   doctor.py y utilidades pequeñas
├── tests/
│   ├── fixtures/{real_samples,synthetic}/
│   └── e2e/
└── infra/                     Docker, compose y despliegue
```

Las carpetas de datos llevan número porque **sí son una secuencia**: cada una es la etapa siguiente de la anterior.

## Zonas de datos

| Zona | Quién escribe | ¿Se modifica? | ¿En Git? | ¿Se puede borrar? |
|---|---|---|---|---|
| `00_inbox` | Tú o un script de descarga | Sí, es de paso | No | Sí, tras ingerir |
| `01_raw` | Solo el comando `ingest` | **Nunca** | No | Solo con respaldo, es recuperable de la fuente |
| `02_interim` | El pipeline | Sí | No | Sí, se regenera |
| `03_processed` | El pipeline | Sí | No | Sí, se regenera |
| `04_published` | El comando `publish` | Sí, con versión | No | Sí, se regenera |
| `99_quarantine` | El comando `ingest` | No | No | Tras revisar el motivo |
| `catalog` | `ingest` y `process` | Sí | No | Se reconstruye desde `01_raw` |

## ¿Dónde va...?

| Quiero agregar | Va en | Además |
|---|---|---|
| Una zona nueva | `config/aois/<id>.yaml` | Nada más: aparece en la app |
| Un fenómeno nuevo | `config/phenomena/<id>.yaml` | Y un detector en `detection/` si necesita lógica propia |
| Un producto de datos nuevo | `config/products/<id>.yaml` | Y un lector en `readers/` si el formato es nuevo |
| Una fuente nueva (ej. otro satélite) | Adaptador en `sources/` y entrada en `config/sources.yaml` | Pruebas con una muestra real |
| Una paleta nueva | `config/colormaps.yaml` | |
| Un umbral | `config/thresholds.yaml` | Nunca en el código |
| Una pestaña nueva | `apps/web/src/features/<nombre>/` | Y registro en `config/features.yaml` |
| Un texto de la interfaz | `apps/web/src/i18n/` | Español primero |
| Un gráfico reutilizable | `apps/web/src/components/` | |
| Una ruta de API | `services/api/app/routes/` | Y su esquema en `packages/contracts` |
| Una decisión importante | `docs/decisions/NNNN-titulo.md` | Una página con contexto y motivo |
| Un hallazgo del dato real | `docs/data-notes.md` | Con fecha y archivo de origen |
| Un procedimiento repetible | `docs/runbooks/` | |
| Datos descargados | `data/00_inbox/` | Nunca en otro sitio |

## Convenciones de nombres

| Elemento | Formato | Ejemplo |
|---|---|---|
| Identificador de zona | minúsculas con guiones | `madre-de-dios-la-pampa` |
| Fecha | ISO `AAAA-MM-DD` | `2026-10-01` |
| Par de fechas | `A__B` con doble guion bajo | `2026-08-02__2026-10-01` |
| Resultado procesado | `03_processed/<zona>/<producto>/<fechaA>__<fechaB>/<tipo>.tif` | `…/gcov/2026-08-02__2026-10-01/diff_hv_db.tif` |
| Capa publicada | `lyr_<zona>_<producto>_<tipo>_<fechaA>_<fechaB>` | `lyr_madre-de-dios_gcov_diff-hv_2026-08-02_2026-10-01` |
| Rama de Git | `tipo/descripcion-corta` | `feat/perfil-de-desplazamiento` |
| Mensaje de commit | `tipo(ámbito): resumen` | `feat(pipeline): máscara por coherencia` |
| Archivo de Python | `snake_case.py` | `coherence_mask.py` |
| Componente de React | `PascalCase.tsx` | `ChangeSlider.tsx` |

Los archivos originales de NISAR **conservan el nombre que trae la fuente**, aunque sea larguísimo, porque ese nombre es su identidad.

## Cómo crece sin romperse

- **Un archivo de más de 300 líneas se divide.** Una carpeta con más de 12 archivos se subdivide.
- **No se crean carpetas "varios", "utils2" ni "nuevo".** Si algo no encaja, se añade una fila a la tabla de arriba y se crea su lugar.
- **Cada paquete se prueba por separado** y declara sus dependencias.
- **Las dependencias entre carpetas van en una dirección:** `web` depende de `contracts`; `api` y `pipeline` dependen de `contracts` y de `config`; nadie depende de `web`.

## Reglas para el agente de código

- Antes de crear un archivo, consulta "¿Dónde va...?". Si no está, pregunta y propón la fila nueva.
- Nunca escribas dentro de `data/01_raw/`.
- No guardes datos en Git. Si necesitas una muestra pequeña para pruebas, usa el script de descarga de muestras y deja constancia en `tests/fixtures/real_samples/README.md`.
- Al terminar una tarea, actualiza `CHANGELOG.md` y, si descubriste algo del dato, `docs/data-notes.md`.
