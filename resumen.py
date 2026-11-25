#!/usr/bin/env python3
"""Resumen diario del grupo: ofertas publicadas en las últimas 24 h, por tema y comunidad.

Necesita TELEGRAM_TOKEN y TELEGRAM_GRUPO_ID. Lee publicadas.json (lo escribe vigilante.py).
"""
import json, os, sys, time, urllib.parse, urllib.request
from collections import Counter
from pathlib import Path

import horario
from clasificar import TEMAS
from provincias import COMUNIDADES

AQUI = Path(__file__).parent
TOK, GRUPO = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_GRUPO_ID")
log = json.loads((AQUI / "publicadas.json").read_text()) if (AQUI / "publicadas.json").exists() else {}
hilos = json.loads((AQUI / "topics.json").read_text())

if not horario.en_horario():
    print("Fuera de horario (solo se manda de 9:00 a 21:00, hora de Madrid): no envío el resumen")
    sys.exit(0)

ahora = time.time()
nuevas = [r for r in log.values() if ahora - r["ts"] <= 86400]
cerradas = sum(1 for r in log.values() if r.get("estado") == "cerrada" and ahora - r["ts"] <= 7 * 86400)
if not nuevas:
    print("Sin ofertas nuevas en 24 h: no envío resumen")
    sys.exit(0)

# enlace a un tema: t.me/c/<id sin -100>/<hilo>
base = "https://t.me/c/" + str(GRUPO).replace("-100", "", 1)
por_tema = Counter(t for r in nuevas for t in r["tm"])
lineas = [f"📰 Resumen de las últimas 24 h: {len(nuevas)} ofertas nuevas\n"]
for t in TEMAS:
    if por_tema.get(t):
        lineas.append(f"• {t}: {por_tema[t]} → {base}/{hilos[t]}")
por_ccaa = Counter(r["c"] for r in nuevas)
top = ", ".join(f"#{c or 'SinZona'} {n}" for c, n in por_ccaa.most_common(6))
lineas.append(f"\n📍 Más ofertas en: {top}")
if cerradas:
    lineas.append(f"🔒 {cerradas} oferta(s) de esta semana ya están cerradas (marcadas en su mensaje).")
texto = "\n".join(lineas)
if not TOK or not GRUPO:
    print(texto)
    sys.exit(0)
datos = {"chat_id": GRUPO, "text": texto, "disable_web_page_preview": "true"}
r = urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{TOK}/sendMessage", data=urllib.parse.urlencode(datos).encode()), timeout=30)
print("resumen enviado", json.load(r)["ok"])
