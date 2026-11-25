#!/usr/bin/env python3
"""Reorganiza los temas del grupo por etapa (un solo uso): renombra tres y cierra los que ya no se usan."""
import json, os, urllib.error, urllib.parse, urllib.request

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]


def api(metodo, **datos):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/{metodo}", data=urllib.parse.urlencode(datos).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        return json.load(e)


RENOMBRAR = {10: "Secundaria y Bachillerato", 5: "Apoyo y orientación", 14: "Otras ofertas"}
CERRAR = {3: "Educación Física", 7: "Música", 8: "Idiomas", 12: "Religión", 4: "PT", 6: "Educación Especial", 13: "Orientación"}
for tid, nombre in RENOMBRAR.items():
    r = api("editForumTopic", chat_id=GRUPO, message_thread_id=tid, name=nombre)
    print("RENOMBRADO", tid, nombre, r.get("ok"), r.get("description", ""))
for tid, nombre in CERRAR.items():
    r = api("closeForumTopic", chat_id=GRUPO, message_thread_id=tid)
    print("CERRADO", tid, nombre, r.get("ok"), r.get("description", ""))
