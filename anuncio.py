#!/usr/bin/env python3
"""Edita el anuncio fijado del grupo (se lanza una vez desde GitHub Actions)."""
import json, os, urllib.parse, urllib.request

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
TEXTO = """🍎 VACANTES DOCENTES ESPAÑA · by Maestría

Todas las ofertas de empleo docente de España, publicadas cada una en el tema de su especialidad.

🔔 RECIBE SOLO LO QUE TE INTERESA, EN TU CHAT PRIVADO
El bot de Maestría te avisa en cuanto sale una oferta que encaja contigo: tu etapa, tu especialidad y tus comunidades. Sin ruido y sin buscar.

⚙️ Cómo configurarlo (1 minuto):
1️⃣ Pulsa aquí para abrir el bot: https://t.me/Vacantes7_bot
2️⃣ Dentro del chat del bot, pulsa el botón Iniciar
3️⃣ Elige tu etapa: Infantil, Primaria, Secundaria, FP o Especialistas
4️⃣ Marca tus áreas o especialidades
5️⃣ Elige tus comunidades (o toda España)
6️⃣ Pulsa Terminar. ¡Listo! 🎉

⚠️ No escribas /start aquí, en el grupo: el bot solo responde en su chat privado. Usa el enlace del paso 1.

Si prefieres verlo todo, elige «todas las ofertas» en el bot y las verás aquí, en el grupo.

🛠 Ya dentro del bot: /ajustes para cambiar tus datos, /pausa para parar los avisos y /baja para borrarte.

🔕 ¿Demasiados avisos del grupo? Mantén pulsado un tema y elige Silenciar.

👥 Invita a tus compañeros:
https://t.me/+fuy6ZtSJm4o1Y2Q8

Tu próxima plaza puede estar publicada hoy. 🍀"""


def api(metodo, **datos):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/{metodo}", data=urllib.parse.urlencode(datos).encode())
    return json.load(urllib.request.urlopen(req, timeout=30))


r = api("editMessageText", chat_id=GRUPO, message_id=149, text=TEXTO, disable_web_page_preview="true")
print("editado", r.get("ok"))
