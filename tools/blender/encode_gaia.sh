#!/usr/bin/env bash
# Codifica los PNG originales a rango de vídeo. Uso: bash tools/blender/encode_gaia.sh [h|v]
set -euo pipefail
cd "$(dirname "$0")/../.."
frames=art/render/v4
public=apps/web/public/media
mkdir -p "$public"

encode_format() {
  local fmt=$1 suffix=$2
  local source="$frames/$fmt/gaia_%04d.png"
  local stage="$frames/media-$fmt"
  mkdir -p "$stage"
  for segment in intro loop; do
    local start=1 count=180
    if [[ $segment == loop ]]; then start=181; count=300; fi
    local name="gaia-$segment$suffix"
    local input=(-y -nostdin -loglevel error -framerate 30 -start_number "$start" -i "$source"
      -frames:v "$count" -vf "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p"
      -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 -an)
    ffmpeg "${input[@]}" -c:v libx264 -threads 8 -preset medium -crf 19 -movflags +faststart "$stage/$name.mp4"
    ffmpeg "${input[@]}" -c:v libvpx-vp9 -threads 8 -tile-columns 2 -row-mt 1 -profile:v 0 \
      -b:v 0 -crf 26 -deadline good -cpu-used 4 "$stage/$name.webm"
    for ext in mp4 webm; do
      local encoded
      encoded=$(ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets \
        -of default=nk=1:nw=1 "$stage/$name.$ext")
      [[ $encoded == "$count" ]] || { echo "$name.$ext: $encoded / $count" >&2; return 1; }
    done
  done
  local poster="gaia-poster$suffix.jpg"
  ffmpeg -y -nostdin -loglevel error -i "$frames/$fmt/gaia_0180.png" -frames:v 1 \
    -q:v 2 -pix_fmt yuvj444p "$stage/$poster"
  for file in "$stage"/*.mp4 "$stage"/*.webm "$stage/$poster"; do
    mv -f "$file" "$public/"
  done
  echo "GAIA_ENCODE_DONE $fmt"
}

case "${1:-all}" in
  h)   encode_format h "" ;;
  v)   encode_format v "-v" ;;
  all) encode_format h ""; encode_format v "-v" ;;
  *)   echo "Uso: $0 [h|v]" >&2; exit 2 ;;
esac
