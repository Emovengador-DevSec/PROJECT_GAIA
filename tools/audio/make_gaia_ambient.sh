#!/usr/bin/env bash
# PROJECT GAIA · genera el sonido ambiente de la portada (original, sintetizado con ffmpeg).
#   bash tools/audio/make_gaia_ambient.sh
# Un acorde grave y abierto (La) con batidos lentos distintos en cada oído, armónicos que
# respiran y un fondo de "aire". Todo es periódico en 32 s, así que el bucle no tiene corte:
# se sintetizan 96 s, se aplica la reverberación y se recorta el tramo central.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=apps/web/public/media
mkdir -p "$OUT"
P="2*PI*t"

# canal izquierdo y derecho: mismas notas, desafinadas 1/16 Hz (batido de 16 s) y con
# respiraciones desfasadas, para que el sonido envuelva en vez de sonar en el centro
L="0.20*sin(55*$P)*(0.72+0.28*sin($P/16))+0.12*sin(82.5*$P)*(0.7+0.3*sin($P/32+1))+0.10*sin(110*$P)*(0.55+0.45*sin($P/16+2))+0.05*sin(137.5*$P)*(0.5+0.5*sin($P/8))+0.05*sin(165*$P)*(0.5+0.5*sin($P/16+4))+0.020*sin(330*$P)*(0.5+0.5*sin($P/8+1))+0.012*sin(440*$P)*(0.5+0.5*sin($P/16+3))+0.007*sin(660*$P)*(0.5+0.5*sin($P/32+5))"
R="0.20*sin(55.0625*$P)*(0.72+0.28*sin($P/16+3))+0.12*sin(82.5625*$P)*(0.7+0.3*sin($P/32+4))+0.10*sin(110.0625*$P)*(0.55+0.45*sin($P/16+5))+0.05*sin(137.5625*$P)*(0.5+0.5*sin($P/8+2))+0.05*sin(165.0625*$P)*(0.5+0.5*sin($P/16+1))+0.020*sin(330.0625*$P)*(0.5+0.5*sin($P/8+4))+0.012*sin(440.125*$P)*(0.5+0.5*sin($P/16))+0.007*sin(660.125*$P)*(0.5+0.5*sin($P/32+2))"

ffmpeg -y -loglevel error \
  -f lavfi -i "aevalsrc=$L|$R:s=48000:d=96" \
  -f lavfi -i "anoisesrc=color=pink:seed=11:r=48000:d=96:a=0.5" \
  -f lavfi -i "anoisesrc=color=pink:seed=29:r=48000:d=96:a=0.5" \
  -filter_complex "\
[1:a]highpass=f=120,lowpass=f=900,tremolo=f=0.125:d=0.6,volume=0.09[nl];\
[2:a]highpass=f=120,lowpass=f=900,tremolo=f=0.25:d=0.5,volume=0.09[nr];\
[nl][nr]join=inputs=2:channel_layout=stereo[air];\
[0:a][air]amix=inputs=2:normalize=0,\
aecho=0.8:0.75:740|1130|1690:0.34|0.26|0.18,\
lowpass=f=5200,atrim=start=32:end=64,asetpts=N/SR/TB,volume=1.9,alimiter=limit=0.85[out]" \
  -map "[out]" -c:a pcm_s16le art/render_audio.wav

ffmpeg -y -loglevel error -i art/render_audio.wav -c:a libopus -b:a 80k "$OUT/gaia-ambient.ogg"
ffmpeg -y -loglevel error -i art/render_audio.wav -c:a aac -b:a 112k -movflags +faststart "$OUT/gaia-ambient.m4a"
rm -f art/render_audio.wav
ls -la "$OUT"/gaia-ambient.*
