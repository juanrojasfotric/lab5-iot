#!/usr/bin/env bash
# Evidencia de la TSDB: puntos guardados, resumen de la ventana y huecos > 60 s.
# Uso: ./scripts/consulta.sh [ventana]   (por defecto 4d)
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
R="${1:-4d}"
OUT=evidencias
mkdir -p "$OUT"
q() { docker compose exec -T influxdb influx query --org "$INFLUX_ORG" --token "$INFLUX_TOKEN" --raw "$1"; }

echo "== Últimos 10 puntos ==" | tee "$OUT/consulta.txt"
q "from(bucket:\"$INFLUX_BUCKET\") |> range(start:-$R) |> filter(fn:(r)=> r._measurement==\"ambiente\") |> pivot(rowKey:[\"_time\"], columnKey:[\"_field\"], valueColumn:\"_value\") |> keep(columns:[\"_time\",\"temperature\",\"humidity\",\"illuminance\"]) |> tail(n:10)" | tee -a "$OUT/consulta.txt"

echo "== Inicio, fin y número de puntos (temperature) ==" | tee -a "$OUT/consulta.txt"
q "d = from(bucket:\"$INFLUX_BUCKET\") |> range(start:-$R) |> filter(fn:(r)=> r._measurement==\"ambiente\" and r._field==\"temperature\") |> group()
union(tables:[d |> first() |> set(key:\"stat\",value:\"inicio\"), d |> last() |> set(key:\"stat\",value:\"fin\"), d |> count() |> map(fn:(r)=>({r with _value: float(v:r._value)})) |> set(key:\"stat\",value:\"puntos\")])
 |> keep(columns:[\"stat\",\"_time\",\"_value\"])" | tee -a "$OUT/consulta.txt"

echo "== Huecos mayores a 60 s ==" | tee "$OUT/huecos.txt"
q "from(bucket:\"$INFLUX_BUCKET\") |> range(start:-$R) |> filter(fn:(r)=> r._measurement==\"ambiente\" and r._field==\"temperature\") |> group() |> elapsed(unit:1s) |> filter(fn:(r)=> r.elapsed > 60) |> keep(columns:[\"_time\",\"elapsed\"])" | tee -a "$OUT/huecos.txt"
echo "Guardado en $OUT/consulta.txt y $OUT/huecos.txt"
