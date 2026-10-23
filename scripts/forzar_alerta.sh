#!/usr/bin/env bash
# Publica 36 °C durante 3 minutos para superar el umbral de 30 °C.
# La alerta pasa a Firing ~2-3 min después y queda en evidencias/alertas.log.
set -euo pipefail
cd "$(dirname "$0")/.."
date -Iseconds | sed 's/^/Inicio forzado: /' | tee -a evidencias/forzado.txt
docker compose run --rm publisher python -u publisher.py --force-temp 36 --count 18
date -Iseconds | sed 's/^/Fin forzado: /' | tee -a evidencias/forzado.txt
echo "Revisa: Grafana > Alerting > Alert rules, y: tail evidencias/alertas.log"
