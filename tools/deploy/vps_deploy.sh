#!/usr/bin/env bash
# Build and (re)start GAIA RIKCHAY on the VPS. Run on the server: bash /opt/gaia/deploy.sh
# Secrets live only on the server, written by the owner:
#   /opt/gaia/secrets/.env           FIRMS_MAP_KEY=..., EARTHDATA_TOKEN=... (runtime)
#   /opt/gaia/secrets/cesium_token   Cesium ion token, one line (build time, goes to the browser)
set -euo pipefail
APP=/opt/gaia/app
SECRETS=/opt/gaia/secrets
mkdir -p "$SECRETS" /opt/gaia/reports
chmod 700 "$SECRETS"
chown 1000:1000 /opt/gaia/reports

build_args=()
if [ -s "$SECRETS/cesium_token" ]; then
  build_args+=(--secret "id=VITE_CESIUM_ION_TOKEN,src=$SECRETS/cesium_token")
else
  echo "Aviso: sin $SECRETS/cesium_token; el globo usará el modo sin Cesium ion."
fi
DOCKER_BUILDKIT=1 docker build "${build_args[@]}" -t gaia-rikchay "$APP"

run_args=(-d --name gaia-rikchay --restart unless-stopped -p 80:7860
          -v /opt/gaia/reports:/srv/gaia/data/reports --memory 3g)
if [ -s "$SECRETS/.env" ]; then
  run_args+=(--env-file "$SECRETS/.env")
else
  echo "Aviso: sin $SECRETS/.env; FIRMS y Earthdata usarán la caché incluida."
fi
docker rm -f gaia-rikchay >/dev/null 2>&1 || true
docker run "${run_args[@]}" gaia-rikchay
docker image prune -f >/dev/null
echo "GAIA RIKCHAY en marcha: http://$(hostname -I | awk '{print $1}')/"
