import json, os, urllib.parse, urllib.request
import vigilante as V

tok, grupo = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
teclado = {"inline_keyboard": [[
    {"text": "🤖 Abrir el bot", "url": "https://t.me/Vacantes7_bot"},
    {"text": "📣 Compartir el grupo", "url": V.enlace_compartir_grupo()},
]]}
datos = {"chat_id": grupo, "message_id": "149", "reply_markup": json.dumps(teclado)}
req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/editMessageReplyMarkup", data=urllib.parse.urlencode(datos).encode())
try:
    print("BOTONES", json.load(urllib.request.urlopen(req, timeout=30)).get("ok"))
except urllib.error.HTTPError as e:
    print("BOTONES error", e.code, e.read().decode()[:200])
