#!/usr/bin/env python3
"""Crea los temas (uno por especialidad) en el grupo de Telegram y guarda sus ids en topics.json.

Necesita: TELEGRAM_TOKEN y TELEGRAM_GRUPO_ID en el entorno. El bot debe ser administrador del
grupo con permiso para gestionar temas, y el grupo debe tener los Temas activados.
"""
import json, os, urllib.parse, urllib.request
from pathlib import Path

from clasificar import TEMAS_GRUPO
from provincias import COMUNIDADES

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
F = Path(__file__).parent / "topics.json"


def api(metodo, **datos):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/{metodo}", data=urllib.parse.urlencode(datos).encode())
    return json.load(urllib.request.urlopen(req, timeout=30))


hilos = json.loads(F.read_text()) if F.exists() else {}
for t in TEMAS_GRUPO:
    if t in hilos:
        continue
    r = api("createForumTopic", chat_id=GRUPO, name=t)
    hilos[t] = r["result"]["message_thread_id"]
    print("creado", t, hilos[t])
F.write_text(json.dumps(hilos, ensure_ascii=False, indent=2))

leyenda = ("📌 Ofertas de empleo docente en toda España\n\n"
           "Cada oferta se publica en el tema de su especialidad. Silencia los temas que no te interesen.\n"
           "Para filtrar por comunidad usa la búsqueda del grupo con su etiqueta:\n\n"
           + "\n".join(f"#{c} · {n}" for c, n in COMUNIDADES.items())
           + "\n\nTambién puedes buscar por provincia, por ejemplo #Sevilla o #Toledo.")
m = api("sendMessage", chat_id=GRUPO, text=leyenda)
try:
    api("pinChatMessage", chat_id=GRUPO, message_id=m["result"]["message_id"])
except Exception as e:
    print("No pude fijar la leyenda:", e)
