"""Puente MQTT -> InfluxDB 2 (reemplaza a Telegraf). Escribe en lotes por la API HTTP."""
import json, os, random, threading, time, urllib.request
import paho.mqtt.client as mqtt

ORG, BUCKET, TOKEN = os.environ["INFLUX_ORG"], os.environ["INFLUX_BUCKET"], os.environ["INFLUX_TOKEN"]
URL = f"http://influxdb:8086/api/v2/write?org={ORG}&bucket={BUCKET}&precision=ms"
buf, lock = [], threading.Lock()

def on_connect(c, u, f, rc, p):
    c.subscribe("uab/lab5/#", qos=1)
    print("bridge suscrito a uab/lab5/#", flush=True)

def on_message(c, u, m):
    try:
        d = json.loads(m.payload)
        line = (f"ambiente,sensor={d.get('sensor', 'sala1')} "
                f"temperature={float(d['temperature'])},humidity={float(d['humidity'])},"
                f"illuminance={float(d['illuminance'])} {int(d['ts'])}")
    except (ValueError, KeyError):
        return
    with lock:
        buf.append(line)

def flusher():
    while True:
        time.sleep(2)
        with lock:
            lines = buf[:]
            buf.clear()
        while lines:
            chunk = lines[:5000]
            req = urllib.request.Request(URL, data="\n".join(chunk).encode(),
                                         headers={"Authorization": f"Token {TOKEN}"})
            try:
                urllib.request.urlopen(req, timeout=10)
                lines = lines[5000:]
                print(f"escritos {len(chunk)} puntos", flush=True)
            except Exception as e:
                print("error InfluxDB, reintento:", e, flush=True)
                time.sleep(5)

threading.Thread(target=flusher, daemon=True).start()
cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"bridge-{random.randint(0, 999999)}")
cli.on_connect, cli.on_message = on_connect, on_message
while True:
    try:
        cli.connect("mosquitto", 1883, 60)
        break
    except OSError:
        time.sleep(5)
cli.loop_forever()
