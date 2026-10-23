---
title: "Laboratorio 5 — Visualización + reglas/alertas (MQTT, InfluxDB y Grafana en una VM)"
subtitle: "IoT + Cloud + Sistemas Distribuidos · UNAB"
author: "Juan Rojas"
date: "23 de octubre de 2026"
---

## 1. Arquitectura

```
Publicador (Python) --MQTT QoS1, topic uab/lab5/sala1--> Mosquitto 2.0
     --> Telegraf (mqtt_consumer) --> InfluxDB 2.7 (bucket "iot", measurement "ambiente")
     <-- Grafana OSS 11.2 (datasource Flux, dashboard 4 días, alerta) --webhook--> alert-logger
```

Todo corre en una VM con Docker Compose (6 contenedores). Grafana es un servicio aparte que solo lee InfluxDB; no participa en la ingesta. El publicador envía un JSON cada 10 s con `temperature` (°C), `humidity` (%), `illuminance` (lux) y `ts` (epoch en ms); Telegraf usa ese `ts` como marca de tiempo real del punto.

## 2. Justificación del protocolo: MQTT

- Modelo publicar/suscribir pensado para telemetría de sensores: el publicador no necesita conocer a la TSDB.
- Cabecera mínima y conexión persistente: apto para la futura Raspberry Pi y redes inestables.
- QoS 1 asegura entrega al menos una vez; Telegraf con sesión persistente no pierde mensajes si se reinicia.
- Integración directa con Telegraf (`inputs.mqtt_consumer`) sin escribir código de ingesta.
- Frente a AMQP: no necesitamos colas, enrutamiento ni confirmaciones complejas. Frente a CoAP: CoAP es petición/respuesta sobre UDP y requeriría un servidor propio que escriba en la TSDB.

## 3. Dashboard

Título: *Lab 5 — Sala 1: temperatura, humedad e iluminancia*, con una línea de qué vigila el operador. Tiene tres gauges con unidad y rango del escenario (15–35 °C, 30–90 %, 0–1000 lux) y tres series temporales con rango fijo `now-4d`. En la serie de temperatura se marca en rojo el umbral de 30 °C.

## 4. Alerta de umbral

| Elemento | Valor |
|---|---|
| Condición | promedio de `temperature` > **30 °C** |
| Ventana | últimos 2 min, evaluada cada 1 min, pendiente 1 min antes de Firing |
| Acción | webhook a `alert-logger` → `evidencias/alertas.log` |
| Prueba | `scripts/forzar_alerta.sh` publica 36 °C durante 3 min |
| Resultado | Forzado a las [hh:mm]; Firing a las [hh:mm]; Resolved a las [hh:mm] (ver `alerta_firing.png` y `alertas.log`) |

El umbral de 30 °C queda por encima del rango normal simulado (21–27 °C), así que no hay falsos positivos durante la toma.

## 5. Ventana de 4 días

**Aclaración:** la toma en vivo no alcanzó los 4 días antes de la entrega. Como permite el enunciado, se indica la **fecha de corte**. Para mostrar la ventana completa en Grafana, los 4 días previos se **rellenaron con datos simulados** (`publisher.py --backfill-days 4 --step 60`). Ese relleno usa el mismo modelo del publicador y pasa por el mismo camino MQTT → Telegraf → InfluxDB, con marcas de tiempo pasadas. Ningún dato proviene de un sensor físico.

| Dato | Valor |
|---|---|
| Relleno simulado | [inicio y fin de `evidencias/backfill.txt`], 1 lectura/min, 5 760 puntos por variable |
| Toma en vivo (cada 10 s) | desde [fecha/hora de arranque] |
| Fecha de corte | [fecha/hora de `consulta.txt`] |
| Huecos > 60 s | [ninguno / lista de `huecos.txt`] |

La toma en vivo sigue corriendo. La evidencia de los 4 días reales se adjunta al completarse, como indica el enunciado.

Evidencias: `backfill.txt`, `consulta.txt`, `huecos.txt` y `dashboard_4dias.png`, todas en `evidencias/`.

## 6. Qué falló al instalar en la VM

- [Editar con lo que les pasó. Problemas típicos que encontramos / previmos:]
- Permisos de Docker: hubo que agregar el usuario al grupo `docker` (`usermod -aG docker`) y reabrir sesión.
- Grafana no accesible desde fuera: faltaba abrir el puerto 3000 en el firewall/NAT de la VM.
- InfluxDB solo aplica `DOCKER_INFLUXDB_INIT_*` la primera vez: al cambiar el token en `.env` hubo que borrar el volumen (`docker compose down -v`).
- Desfase de hora en el dashboard: se fijó `TZ=America/Bogota` y el `ts` del publicador en UTC (epoch).

## 7. Repositorio

`docker-compose.yml`, `.env.example` (sin secretos), `publisher/`, `telegraf/`, `grafana/provisioning` (datasource, dashboard y alerta como código), `scripts/`, `README.md` y `/evidencias`.
