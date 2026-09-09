#!/bin/bash
# run_pi.sh — Script de arranque optimizado para Raspberry Pi Zero 2W
# Uso: bash scripts/run_pi.sh --video video.mp4
# O con cámara USB: bash scripts/run_pi.sh --video /dev/video0

set -e

# Directorio del script
cd "$(dirname "$0")/.."

python main.py \
  --video "${1:-video.mp4}" \
  --roi-x 900 \
  --roi-y 600 \
  --roi-r 220 \
  --num-threads 4 \
  --skip-frames 2 \
  --no-output \
  --log "results_$(date +%Y%m%d_%H%M%S).csv" \
  --dashboard \
  --snapshot-every 300 \
  --snapshot-dir snapshots
