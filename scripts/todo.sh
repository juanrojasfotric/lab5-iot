#!/usr/bin/env bash
# Hace todo en orden: levanta el stack, rellena 4 días SIMULADOS, dispara la alerta y saca la consulta.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { cp .env.example .env; sed -i "s/cambia-este-token-largo/$(openssl rand -hex 32)/" .env; }
docker compose up -d --build
echo "Esperando 30 s a que InfluxDB y Telegraf arranquen..."; sleep 30
date -Iseconds | sed 's/^/Backfill simulado inicio: /' | tee evidencias/backfill.txt
docker compose run --rm publisher python -u publisher.py --backfill-days 4 --step 60 | tee -a evidencias/backfill.txt
./scripts/forzar_alerta.sh
echo "Esperando 2 min para que la alerta pase a Firing y luego a Resolved..."; sleep 120
./scripts/consulta.sh
echo "LISTO. Ahora toma las 2 capturas (ver README) y revisa evidencias/alertas.log"
