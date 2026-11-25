#!/usr/bin/env python3
"""Borra del grupo las 4 ofertas de Cronoshare publicadas a las 08:40 UTC del 25-nov-2026 y las marca como borradas (un solo uso)."""
import json, os, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
DESDE = 1795595400  # 2026-11-25 08:30:00 UTC
F = Path("publicadas.json")


def borrar(mid):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/deleteMessage", data=urllib.parse.urlencode({"chat_id": GRUPO, "message_id": mid}).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=30)).get("ok", False)
    except urllib.error.HTTPError:
        return False


log = json.loads(F.read_text())
ok = fallos = ofertas = 0
for oid, r in log.items():
    if r["ts"] < DESDE or r.get("estado") == "borrada":
        continue
    ofertas += 1
    for hilo, mid in r["m"]:
        if borrar(mid):
            ok += 1
        else:
            fallos += 1
        time.sleep(0.1)
    r["estado"] = "borrada"
F.write_text(json.dumps(log, ensure_ascii=False))
print(f"BORRADO ofertas={ofertas} mensajes_ok={ok} fallos={fallos}")
