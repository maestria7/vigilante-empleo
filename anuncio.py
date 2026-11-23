#!/usr/bin/env python3
"""Publica y fija el anuncio del bot en el grupo (se lanza una vez desde GitHub Actions)."""
import json, os, urllib.parse, urllib.request

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
TEXTO = """🍎 VACANTES DOCENTES ESPAÑA · by Maestría

Aquí se publican las ofertas de empleo docente de toda España, cada una en el tema de su especialidad.

🔔 ¿Quieres recibir SOLO lo que te interesa, directamente en tu chat privado?
Elige tu etapa, tu especialidad y tus comunidades, y el bot te avisa cuando salga una oferta que encaje contigo.

👉 Abre el bot y pulsa Iniciar (1 minuto):
https://t.me/Vacantes7_bot

🔕 ¿Demasiados avisos? Mantén pulsado un tema y elige Silenciar.

👥 Invita a tus compañeros:
https://t.me/+fuy6ZtSJm4o1Y2Q8

Tu próxima plaza puede estar publicada hoy. 🍀"""


def api(metodo, **datos):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/{metodo}", data=urllib.parse.urlencode(datos).encode())
    return json.load(urllib.request.urlopen(req, timeout=30))


m = api("sendMessage", chat_id=GRUPO, text=TEXTO, disable_web_page_preview="true")
print("publicado", m["result"]["message_id"])
r = api("pinChatMessage", chat_id=GRUPO, message_id=m["result"]["message_id"], disable_notification="true")
print("fijado", r.get("ok"))
