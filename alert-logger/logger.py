"""Receptor del webhook de Grafana: guarda cada notificación en /evidencias/alertas.log."""
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG = "/evidencias/alertas.log"


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            data = json.loads(body)
            linea = {
                "recibido": datetime.now().isoformat(timespec="seconds"),
                "status": data.get("status"),
                "alertas": [
                    {
                        "regla": a.get("labels", {}).get("alertname"),
                        "estado": a.get("status"),
                        "inicio": a.get("startsAt"),
                        "valores": a.get("valueString"),
                        "resumen": a.get("annotations", {}).get("summary"),
                    }
                    for a in data.get("alerts", [])
                ],
            }
        except ValueError:
            linea = {"recibido": datetime.now().isoformat(), "raw": body.decode(errors="replace")}
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
        print(json.dumps(linea, ensure_ascii=False), flush=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("alert-logger escuchando en :8080", flush=True)
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
