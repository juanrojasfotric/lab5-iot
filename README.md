# Lab 5 — MQTT → InfluxDB → Grafana (con alerta de umbral)

Plataforma propia en una VM con Docker Compose. El publicador envía `temperature`, `humidity` e `illuminance` por **MQTT** (Mosquitto), Telegraf las escribe en **InfluxDB 2.7** con la marca de tiempo del publicador, y **Grafana OSS** (servicio aparte) solo lee InfluxDB: dashboard de 4 días y una alerta con webhook.

```
publisher ──MQTT uab/lab5/sala1──► mosquitto ──► telegraf ──► InfluxDB (bucket iot)
                                                                  ▲
                                         Grafana (dashboard + alerta) ──webhook──► alert-logger → evidencias/alertas.log
```

## Estructura
| Ruta | Contenido |
|---|---|
| `docker-compose.yml` | Stack completo |
| `.env.example` | Variables (copiar a `.env`, no se sube) |
| `publisher/` | Publicador MQTT en Python (paho-mqtt) |
| `telegraf/telegraf.conf` | MQTT → InfluxDB |
| `grafana/provisioning/` | Datasource, dashboard y alerta ya configurados |
| `grafana/dashboards/lab5.json` | Dashboard de 4 días |
| `alert-logger/` | Receptor del webhook de la alerta |
| `scripts/` | `consulta.sh` (evidencia TSDB + huecos), `forzar_alerta.sh` |
| `evidencias/` | Consulta, capturas del dashboard y de la alerta, `alertas.log` |

## Levantar en la VM (Ubuntu 22.04/24.04)
```bash
# 1. Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker

# 2. Proyecto
git clone <URL-del-repo> lab5 && cd lab5
cp .env.example .env        # editar claves y token (token largo, p. ej. openssl rand -hex 32)
chmod +x scripts/*.sh
docker compose up -d --build
docker compose ps           # 6 servicios "running"
```
Puertos: Grafana `3000`, InfluxDB `8086`, MQTT `1883` (abrirlos en el firewall/NAT de la VM si se accede desde fuera).

## Todo en un comando
```bash
chmod +x scripts/*.sh && ./scripts/todo.sh
```
Levanta el stack, rellena 4 días de datos **simulados** (declarado en el informe), dispara la alerta y guarda la consulta en `evidencias/`. Tarda unos 10 minutos.

## Comprobaciones
```bash
docker compose logs -f publisher                  # JSON cada 10 s
docker compose exec mosquitto mosquitto_sub -t 'uab/lab5/#' -C 3   # mensajes en el broker
./scripts/consulta.sh                             # puntos en InfluxDB -> evidencias/consulta.txt
```
Grafana: `http://IP-VM:3000` (usuario/clave del `.env`) → Dashboards → Lab5 → *Lab 5 — Sala 1*. El rango por defecto es `now-4d`.

## Alerta
- Regla **Temperatura alta sala1**: promedio de `temperature` en los últimos **2 min > 30 °C**, evaluada cada **1 min**, pendiente **1 min**.
- Acción: webhook a `alert-logger`, que escribe en `evidencias/alertas.log`.
- Dispararla: `./scripts/forzar_alerta.sh` (publica 36 °C por 3 min). Ver en Grafana → Alerting → Alert rules (Pending → Firing) y `tail evidencias/alertas.log`. Al terminar vuelve a Normal y llega un mensaje `resolved`.

## Evidencias a dejar en `/evidencias`
1. `consulta.txt` y `huecos.txt` (de `scripts/consulta.sh`).
2. `dashboard_4dias.png`: captura del dashboard con rango *Last 4 days*.
3. `alerta_firing.png`: regla en estado Firing + `alertas.log`.

## Toma de 4 días
El publicador tiene `restart: unless-stopped`; si la VM se reinicia, Docker relanza todo. Los huecos se ven en las series (corte > 2 min) y se listan con `scripts/consulta.sh`.

## Migración a Raspberry Pi
Todas las imágenes son multi-arquitectura (arm64): el mismo `docker compose up -d --build` funciona en una Pi con OS de 64 bits.
