#!/usr/bin/env python3
"""Borra del grupo las ofertas publicadas desde las 05:00 UTC del 25-nov-2026 (la avalancha de Jobsora) y las marca como borradas (un solo uso)."""
import json, os, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
DESDE = 1795582800  # 2026-11-25 05:00:00 UTC
F = Path("publicadas.json")


def borrar(mid):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/deleteMessage", data=urllib.parse.urlencode({"chat_id": GRUPO, "message_id": mid}).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=30)).get("ok", False), ""
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf8", "ignore")
        if e.code == 429:
            time.sleep(5)
            return borrar(mid)
        return False, cuerpo[:120]


log = json.loads(F.read_text())
ok = fallos = ofertas = 0
errores = {}
for oid, r in log.items():
    if r["ts"] < DESDE or r.get("estado") == "borrada":
        continue
    ofertas += 1
    for hilo, mid in r["m"]:
        bien, motivo = borrar(mid)
        if bien:
            ok += 1
        else:
            fallos += 1
            errores[motivo] = errores.get(motivo, 0) + 1
        time.sleep(0.08)
    r["estado"] = "borrada"
F.write_text(json.dumps(log, ensure_ascii=False))
print(f"BORRADO ofertas={ofertas} mensajes_ok={ok} fallos={fallos} errores={errores}")
