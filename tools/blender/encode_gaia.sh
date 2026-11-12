#!/usr/bin/env bash
# PROJECT GAIA · codifica las secuencias de art/render/{h,v} a WebM (VP9) y MP4 (H.264)
# en apps/web/public/media/, más los pósteres JPG. Requiere ffmpeg.
#   bash tools/blender/encode_gaia.sh
# Cuadros 1-180 = intro (6 s); 181-480 = bucle (10 s, sin corte). 30 fps.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=apps/web/public/media
mkdir -p "$OUT"
FPS=30
# Los JPG vienen en rango completo (pc). Hay que pasar a rango de video (tv): con rango
# completo, Chromium da PIPELINE_ERROR_DECODE al reproducir el VP9.
RANGE="scale=in_range=pc:out_range=tv,format=yuv420p"

encode() {  # formato  nombre  primer_cuadro  n_cuadros  crf_x264  crf_vp9
  local fmt=$1 name=$2 start=$3 n=$4 crf264=$5 crfvp9=$6
  local in=(-framerate $FPS -start_number "$start" -i "art/render/$fmt/gaia_%04d.jpg" -frames:v "$n" -vf "$RANGE" -color_range tv)
  ffmpeg -y -loglevel error "${in[@]}" -c:v libx264 -preset slow -crf "$crf264" -movflags +faststart -an "$OUT/$name.mp4"
  ffmpeg -y -loglevel error "${in[@]}" -c:v libvpx-vp9 -profile:v 0 -b:v 0 -crf "$crfvp9" -row-mt 1 -deadline good -cpu-used 2 -an "$OUT/$name.webm"
}

encode h gaia-intro   1 180 21 32
encode h gaia-loop  181 300 21 32
encode v gaia-intro-v   1 180 22 33
encode v gaia-loop-v  181 300 22 33

# póster = último cuadro de la intro (composición de portada)
ffmpeg -y -loglevel error -i art/render/h/gaia_0180.jpg -q:v 3 "$OUT/gaia-poster.jpg"
ffmpeg -y -loglevel error -i art/render/v/gaia_0180.jpg -q:v 3 "$OUT/gaia-poster-v.jpg"
ls -la "$OUT"
