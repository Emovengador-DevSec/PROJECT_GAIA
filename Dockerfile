# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS web
WORKDIR /build
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN --mount=type=secret,id=VITE_CESIUM_ION_TOKEN,mode=0400 \
    --mount=type=secret,id=web_env,target=/build/.env,mode=0400 \
    if [ -f /run/secrets/VITE_CESIUM_ION_TOKEN ]; then \
      export VITE_CESIUM_ION_TOKEN="$(cat /run/secrets/VITE_CESIUM_ION_TOKEN)"; \
    fi && npm run build

FROM python:3.12-slim-bookworm AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /usr/local/bin/
WORKDIR /srv/gaia
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
COPY services/pipeline/src/ services/pipeline/src/
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 gaia
WORKDIR /srv/gaia
ENV PATH="/srv/gaia/.venv/bin:$PATH" \
    PYTHONPATH=/srv/gaia/services/api \
    SARLAB_ROOT=/srv/gaia DATA_DIR=/srv/gaia/data \
    SARLAB_WARM_FEEDS=1 SARLAB_TILE_REQUESTS_PER_MINUTE=360 \
    PYTHONDONTWRITEBYTECODE=1
COPY --from=dependencies /srv/gaia/.venv/ .venv/
COPY --from=web /build/dist/ apps/web/dist/
COPY --from=web /build/public/globe/peru-boundaries.geojson apps/web/public/globe/peru-boundaries.geojson
COPY services/api/app/ services/api/app/
COPY config/ config/
COPY --chown=1000:1000 deploy/data/ data/
USER 1000
EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-7860}\""]
