"""Consulta semanal a OpenStreetMap (API Overpass): puntos de reciclaje de pilas, celulares y
aparatos electrónicos en la Región del Biobío. Escribe data/osm_biobio.json.
Solo usa la biblioteca estándar de Python."""
import json, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

SERVIDORES = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
QUERY = """
[out:json][timeout:90];
area["ISO3166-2"="CL-BI"]->.a;
(
  nwr["amenity"="recycling"]["recycling:batteries"="yes"](area.a);
  nwr["amenity"="recycling"]["recycling:mobile_phones"="yes"](area.a);
  nwr["amenity"="recycling"]["recycling:small_electrical_appliances"="yes"](area.a);
  nwr["amenity"="recycling"]["recycling:electrical_appliances"="yes"](area.a);
  nwr["amenity"="recycling"]["recycling:computers"="yes"](area.a);
);
out center tags;
"""

def consultar():
    ultimo = None
    for url in SERVIDORES:
        for intento in range(3):
            try:
                datos = urllib.parse.urlencode({"data": QUERY}).encode()
                req = urllib.request.Request(url, data=datos, headers={"User-Agent": "e-Recicla-Biobio (proyecto academico IPVG)"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.load(r)
            except Exception as e:
                ultimo = e; time.sleep(10 * (intento + 1))
    raise SystemExit("No se pudo consultar Overpass: %s" % ultimo)

def tipos(t):
    out = []
    if t.get("recycling:mobile_phones") == "yes": out.append("celulares")
    if t.get("recycling:batteries") == "yes": out.append("pilas")
    if any(t.get("recycling:" + k) == "yes" for k in ("small_electrical_appliances", "electrical_appliances", "computers")): out.append("raee")
    return out

def direccion(t):
    calle = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    partes = [p for p in (calle, t.get("addr:city")) if p]
    return ", ".join(partes) or None

def main():
    crudo = consultar()
    puntos = []
    for el in crudo.get("elements", []):
        t = el.get("tags", {})
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lng = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lng is None: continue
        ty = tipos(t)
        if not ty: continue
        puntos.append({
            "id": "%s/%s" % (el["type"], el["id"]),
            "nombre": t.get("name") or t.get("operator") or "Punto de reciclaje (sin nombre en OpenStreetMap)",
            "tipos": ty, "dir": direccion(t), "lat": lat, "lng": lng,
            "horario": t.get("opening_hours"), "administra": t.get("operator"),
        })
    puntos.sort(key=lambda p: p["id"])
    salida = {"consultado": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "fuente": "OpenStreetMap (Overpass API)", "total": len(puntos), "puntos": puntos}
    with open("data/osm_biobio.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    print("Puntos encontrados:", len(puntos))

if __name__ == "__main__":
    main()
