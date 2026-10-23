"""Publicador MQTT del Lab 5: temperature, humidity, illuminance.

Uso normal (servicio de compose): publica cada PERIOD_S segundos valores
simulados con ciclo día/noche.

Forzar la alerta:
    docker compose run --rm publisher python publisher.py --force-temp 36 --count 18
publica 36 °C cada 10 s durante 3 min (supera el umbral de 30 °C).
"""
import argparse
import json
import math
import os
import random
import time

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC", "uab/lab5/sala1")
PERIOD = float(os.getenv("PERIOD_S", "10"))
SENSOR = os.getenv("SENSOR_ID", "sala1")


def lectura(force_temp=None, t=None):
    t = time.time() if t is None else t
    lt = time.localtime(t)
    hora = lt.tm_hour + lt.tm_min / 60
    dia = math.sin((hora - 6) / 24 * 2 * math.pi)          # -1 noche, +1 mediodía
    temp = 24 + 3 * dia + random.gauss(0, 0.3)               # ~21–27 °C
    hum = 65 - 12 * dia + random.gauss(0, 1.0)               # ~53–77 %
    lux = max(0.0, 800 * dia) + random.uniform(0, 15)        # 0–800 lux
    if force_temp is not None:
        temp = force_temp
    return {
        "sensor": SENSOR,
        "temperature": round(temp, 2),
        "humidity": round(min(max(hum, 0), 100), 2),
        "illuminance": round(lux, 1),
        "ts": int(t * 1000),                                 # marca de tiempo (ms)
    }


def backfill(cli, dias, paso):
    """Relleno SIMULADO: publica dias*86400/paso lecturas con marcas de tiempo pasadas."""
    ahora = time.time()
    t = ahora - dias * 86400
    n = 0
    while t < ahora:
        cli.publish(TOPIC, json.dumps(lectura(t=t)), qos=1).wait_for_publish()
        time.sleep(0.02)
        t += paso
        n += 1
    print(f"backfill simulado: {n} lecturas, {dias} días, paso {paso}s", flush=True)


def conectar():
    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                      client_id=f"pub-{SENSOR}-{random.randint(0,999999)}")
    while True:
        try:
            cli.connect(HOST, PORT, keepalive=60)
            cli.loop_start()
            while not cli.is_connected(): time.sleep(0.1)
            while not cli.is_connected(): time.sleep(0.1)
            print(f"conectado a {HOST}:{PORT}, topic {TOPIC}", flush=True)
            return cli
        except OSError as e:
            print(f"broker no disponible ({e}), reintento en 5 s", flush=True)
            time.sleep(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-temp", type=float, help="temperatura fija para disparar la alerta")
    ap.add_argument("--count", type=int, default=0, help="mensajes a enviar (0 = infinito)")
    ap.add_argument("--backfill-days", type=float, help="rellena N días de datos simulados y termina")
    ap.add_argument("--step", type=int, default=60, help="segundos entre lecturas del relleno")
    args = ap.parse_args()

    cli = conectar()
    if args.backfill_days:
        backfill(cli, args.backfill_days, args.step)
        cli.loop_stop()
        cli.disconnect()
        return
    n = 0
    while args.count == 0 or n < args.count:
        msg = lectura(args.force_temp)
        cli.publish(TOPIC, json.dumps(msg), qos=1).wait_for_publish()
        print(json.dumps(msg), flush=True)
        n += 1
        time.sleep(PERIOD)
    cli.loop_stop()
    cli.disconnect()


if __name__ == "__main__":
    main()
