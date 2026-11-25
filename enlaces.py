#!/usr/bin/env python3
"""Comprueba cada día que las ofertas publicadas en el grupo siguen abiertas y marca como CERRADAS las que ya no existen.

Una oferta se da por cerrada solo si su página falla DOS comprobaciones seguidas (404/410, o una página que dice «oferta cerrada/caducada»…).
Un error de red, un bloqueo (403) o un fallo del servidor no cuentan: ante la duda, la oferta se queda como está.
Solo se miran las de los últimos 30 días. Uso: python3 enlaces.py
"""
import os, re, sys, time, urllib.error, urllib.request

import calidad
import vigilante as V

FRASES_CERRADA = (r"oferta (?:caducada|cerrada|finalizada|expirada|no disponible)|ya no est[aá] disponible|vacante cubierta|proceso (?:de selecci[oó]n )?cerrado|"
                  r"plazo (?:de solicitud |de inscripci[oó]n )?cerrado|oferta ha (?:caducado|expirado)|no longer available|this job (?:has expired|is no longer)")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
DIAS = 30
MAX_POR_PASADA = 300


def abrir(url):
    """(código HTTP, texto) de la página; (0, "") si no se pudo conectar."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
            return r.status, r.read(300_000).decode("utf8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def estado_enlace(codigo, texto):
    """'muerto' (la oferta ya no está), 'vivo' o 'incierto' (no se puede saber: no cuenta para nada)."""
    if codigo in (404, 410):
        return "muerto"
    if codigo == 200:
        return "muerto" if re.search(FRASES_CERRADA, texto[:60_000], re.I) else "vivo"
    return "incierto"


def comprobar(log, grupo_id, ahora=None, abrir_fn=abrir, editar_fn=V.editar, pausa=0.5):
    """Recorre las ofertas abiertas del registro. Devuelve {comprobadas, cerradas, sin_respuesta}."""
    ahora = ahora or time.time()
    res = {"comprobadas": 0, "cerradas": 0, "sin_respuesta": 0}
    for oid, r in sorted(log.items(), key=lambda kv: -kv[1]["ts"]):
        if r.get("estado") or ahora - r["ts"] > DIAS * 86400 or not str(r.get("u", "")).startswith("http"):
            continue
        if res["comprobadas"] >= MAX_POR_PASADA:
            break
        res["comprobadas"] += 1
        estado = estado_enlace(*abrir_fn(r["u"]))
        if estado == "muerto":
            r["enl"] = r.get("enl", 0) + 1
        elif estado == "vivo":
            r["enl"] = 0
        else:
            res["sin_respuesta"] += 1
        if r.get("enl", 0) >= 2:
            marca = "🔒 CERRADA · la página de la oferta ya no está disponible\n\n"
            for hilo, mid in r["m"]:
                editar_fn(grupo_id, mid, marca + r["x"], r.get("u"))
                time.sleep(1.2)
            r["estado"] = "cerrada"
            res["cerradas"] += 1
        time.sleep(pausa)
    return res


def main():
    grupo_id = os.environ.get("TELEGRAM_GRUPO_ID")
    log = V.cargar_log()
    res = comprobar(log, grupo_id)
    V.guardar_log(log)
    calidad.registrar("enlaces", enlaces=res)
    print(f"[enlaces] {res['comprobadas']} comprobados · {res['cerradas']} cerrados · {res['sin_respuesta']} sin respuesta")


if __name__ == "__main__":
    main()
