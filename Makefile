.PHONY: setup dev-api dev-web test lint doctor search ingest inspect change build-web

AOI ?= madre-de-dios-la-pampa
START ?= 2025-10-01

setup:            ## Instala Python (uv) y la web (npm)
	uv sync
	cd apps/web && npm ci

dev-api:          ## API en http://localhost:8000
	uv run fastapi dev services/api/app/main.py

dev-web:          ## Interfaz en http://localhost:5173
	cd apps/web && npm run dev

test:
	uv run pytest -q
	cd apps/web && npm run typecheck

lint:
	uv run ruff check services

doctor:
	uv run python scripts/doctor.py

search:           ## make search AOI=chosica-rimac START=2025-12-01
	uv run sarlab search --aoi $(AOI) --start $(START)

download:         ## Descarga los 2 primeros gránulos a data/00_inbox
	uv run sarlab search --aoi $(AOI) --start $(START) --download --limit 2

inspect:          ## make inspect FILE=data/01_raw/...h5
	uv run sarlab inspect $(FILE)

ingest:
	uv run sarlab ingest

change:           ## make change AOI=... BEFORE=ruta.h5 AFTER=ruta.h5
	uv run sarlab change --aoi $(AOI) --before $(BEFORE) --after $(AFTER)

build-web:
	cd apps/web && npm run build
