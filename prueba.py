import json, os, urllib.parse, urllib.request
tok, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
texto = open("aviso_prueba.txt", encoding="utf8").read().strip()
datos = {"chat_id": chat, "text": texto, "disable_web_page_preview": "true",
         "reply_markup": json.dumps({"inline_keyboard": [[{"text": "🔗 Ver oferta", "url": "https://t.me/Vacantes7_bot"}]]})}
r = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=urllib.parse.urlencode(datos).encode()), timeout=30))
print("ENVIADO", r.get("ok"))
