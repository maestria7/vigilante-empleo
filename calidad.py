"""Informe de calidad de las fuentes: cuántas ofertas lee, publica y descarta cada una, y cuántas se marcan como cerradas.

Cada pasada del vigilante anota sus cifras en calidad.json (una clave por pasada, solo 3 días) y el resumen de las 9:00 las suma de las últimas 24 h.
"""
import datetime, json, re
from pathlib import Path

F = Path(__file__).parent / "calidad.json"
COLUMNAS = ("leidas", "repetidas", "vistas", "filtradas", "publicadas", "tope")


def fuente_de(o):
    """Nombre corto de la fuente de una oferta («Jobsora · madrid» → «Jobsora»; «Edutalent (toda España)» → «Edutalent»)."""
    return re.split(r" [·(]", o.get("origen") or "otra")[0].strip() or "otra"


def estadisticas(leidas, sin_dup, ids_vistos, ids_candidatas, ids_publicadas):
    """Por fuente: leídas, repetidas (mismo puesto en varias webs), ya vistas, filtradas (no docentes, antiguas…), publicadas y retenidas por el tope."""
    st = {}

    def S(f):
        return st.setdefault(f, dict.fromkeys(COLUMNAS, 0))

    for o in leidas:
        S(fuente_de(o))["leidas"] += 1
    for o in sin_dup:
        f = fuente_de(o)
        s = S(f)
        if o["id"] in ids_vistos:
            s["vistas"] += 1
        elif o["id"] in ids_candidatas:
            s["publicadas" if o["id"] in ids_publicadas else "tope"] += 1
        else:
            s["filtradas"] += 1
    for f, s in st.items():
        s["repetidas"] = s["leidas"] - sum(1 for o in sin_dup if fuente_de(o) == f)
    return st


def registrar(modo, fuentes=None, enlaces=None, ahora=None, ruta=None):
    """Añade las cifras de una pasada (o de la comprobación de enlaces) y borra lo de más de 3 días."""
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    ruta = ruta or F
    try:
        datos = json.loads(Path(ruta).read_text())
    except Exception:
        datos = {}
    corte = (ahora - datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    datos = {k: v for k, v in datos.items() if k >= corte}
    datos[f'{ahora.strftime("%Y-%m-%dT%H:%M")}|{modo}'] = {"modo": modo, **({"fuentes": fuentes} if fuentes else {}), **({"enlaces": enlaces} if enlaces else {})}
    Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, sort_keys=True))


def resumen_24h(ahora=None, ruta=None):
    """Suma las pasadas de las últimas 24 h: ({fuente: cifras}, enlaces, nº de pasadas)."""
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    ruta = ruta or F
    try:
        datos = json.loads(Path(ruta).read_text())
    except Exception:
        return {}, {}, 0
    desde = (ahora - datetime.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")
    fuentes, enlaces, pasadas = {}, {"comprobadas": 0, "cerradas": 0, "sin_respuesta": 0}, 0
    for k, v in datos.items():
        if k < desde:
            continue
        if v.get("fuentes"):
            pasadas += 1
            for f, s in v["fuentes"].items():
                t = fuentes.setdefault(f, dict.fromkeys(COLUMNAS, 0))
                for c in COLUMNAS:
                    t[c] += s.get(c, 0)
        for c in enlaces:
            enlaces[c] += (v.get("enlaces") or {}).get(c, 0)
    return fuentes, enlaces, pasadas


def lineas_informe(fuentes, enlaces, pasadas):
    """Líneas para el resumen de las 9:00."""
    if not pasadas:
        return ["🔎 Calidad de las fuentes: sin datos de las últimas 24 h"]
    out = ["🔎 Calidad de las fuentes (últimas 24 h)"]
    ordenadas = sorted(fuentes.items(), key=lambda kv: (-kv[1]["publicadas"], -kv[1]["leidas"]))
    for f, s in ordenadas[:8]:
        nuevas = s["publicadas"] + s["tope"] + s["filtradas"]
        extra = f" · filtradas {s['filtradas']}" if s["filtradas"] else ""
        extra += f" · retenidas por el tope {s['tope']}" if s["tope"] else ""
        out.append(f"• {f}: leídas {s['leidas']} · nuevas {nuevas} · publicadas {s['publicadas']}{extra}")
    mudas = [f for f, s in fuentes.items() if s["leidas"] == 0]
    if mudas:
        out.append("• Sin ninguna oferta leída: " + ", ".join(sorted(mudas)))
    ruidosas = [(f, s) for f, s in fuentes.items() if (s["publicadas"] + s["tope"] + s["filtradas"]) >= 10 and s["filtradas"] / (s["publicadas"] + s["tope"] + s["filtradas"]) >= 0.6]
    for f, s in ruidosas:
        n = s["publicadas"] + s["tope"] + s["filtradas"]
        out.append(f"⚠️ {f}: descartamos el {round(100 * s['filtradas'] / n)} % de sus nuevas (mucho ruido)")
    if enlaces["comprobadas"] or enlaces["cerradas"]:
        out.append(f"🔒 Enlaces: {enlaces['comprobadas']} comprobados · {enlaces['cerradas']} marcados como cerrados · {enlaces['sin_respuesta']} sin respuesta")
    return out
