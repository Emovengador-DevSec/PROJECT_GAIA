# data/

Contenido ignorado por Git. Las carpetas son etapas de una secuencia:

- `00_inbox/` aquí se suelta lo nuevo; `make ingest` lo revisa y lo mueve.
- `01_raw/` original e inmutable, por fuente.
- `02_interim/` recortes y conversiones intermedias.
- `03_processed/` resultados por zona.
- `04_published/` lo que sirve la API.
- `99_quarantine/` lo que falló la validación, con su motivo.
- `catalog/` índice de todo lo que existe.

Nunca escribas a mano dentro de `01_raw/`. Detalle en `docs/agent-pack/08_Ingesta_Nuevos_Datos.md`.
