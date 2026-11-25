#!/usr/bin/env python3
"""Lleva las publicaciones nuevas de Instagram (@soymaestria) al tema «Recursos» del grupo.

Lee las publicaciones de Zernio (que sincroniza la cuenta cada ~90 min), y de cada una nueva manda al tema un mensaje corto:
«📚 Nuevo recurso» + el arranque del texto (sin las llamadas a la acción de Instagram: «comenta», «sígueme»…) + botón «Ver la publicación».
- Solo de 9:00 a 21:00 (hora de Madrid); si algo sale fuera de horario, espera a las 9:00.
- La primera vez NO manda nada: solo anota lo que ya existe (si no, saldrían las 19 publicaciones antiguas de golpe).
- Solo publicaciones de los últimos 3 días y como máximo 2 por pasada.
Secretos: ZERNIO_API_KEY, TELEGRAM_TOKEN, TELEGRAM_GRUPO_ID. Uso: python3 instagram.py
"""
import datetime, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

import horario

AQUI = Path(__file__).parent
ESTADO = AQUI / "instagram.json"
CUENTA = "6adf42c98d612a261db63671"  # @soymaestria en Zernio
DIAS = 3
MAX_POR_PASADA = 2
MAX_CARACTERES = 320
CTA = re.compile(r"\b(comenta|comparte|s[ií]gueme|sigue|guarda|menciona|etiqueta|link en|enlace en la bio|mensaje directo|escr[ií]beme|dale like|suscr[ií]bete)\b|@\w+|^#", re.I)


def tema_recursos():
    return json.loads((AQUI / "topics_extra.json").read_text())["Recursos"]


def adelanto(texto):
    """Arranque del texto de Instagram: primer párrafo (y el segundo si el primero es muy corto), sin llamadas a la acción ni etiquetas."""
    parrafos = [re.sub(r"[ \t]+", " ", p).strip() for p in re.split(r"\n\s*\n", (texto or "").replace("\r", "")) if p.strip()]
    buenos = []
    for p in parrafos:
        lineas = [l for l in p.split("\n") if l.strip() and not CTA.search(l)]
        if lineas:
            buenos.append("\n".join(l.strip() for l in lineas))
    if not buenos:
        return ""
    salida = buenos[0]
    if len(salida) < 70 and len(buenos) > 1:
        salida += "\n\n" + buenos[1]
    if len(salida) > MAX_CARACTERES:
        salida = salida[:MAX_CARACTERES].rsplit(" ", 1)[0].rstrip(",;:.¿¡ ") + "…"
    return salida


def mensaje(post):
    return "📚 Nuevo recurso\n\n" + (adelanto(post.get("content")) or "Hay una publicación nueva con recursos para tu aula.")


def leer_publicaciones(clave, hoy=None):
    hoy = hoy or datetime.date.today()
    q = urllib.parse.urlencode({"accountId": CUENTA, "source": "external", "limit": 20, "fromDate": (hoy - datetime.timedelta(days=10)).isoformat(), "sortBy": "date", "order": "desc"})
    req = urllib.request.Request(f"https://zernio.com/api/v1/analytics?{q}", headers={"Authorization": f"Bearer {clave}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("posts", [])


def enviar(token, chat, hilo, texto, url):
    datos = {"chat_id": chat, "message_thread_id": str(hilo), "text": texto, "disable_web_page_preview": "true",
             "reply_markup": json.dumps({"inline_keyboard": [[{"text": "🔗 Ver la publicación", "url": url}]]})}
    try:
        r = urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=urllib.parse.urlencode(datos).encode()), timeout=30)
        return json.load(r)["result"]["message_id"]
    except urllib.error.HTTPError as e:
        print("Telegram error", e.code, e.read().decode("utf8", "ignore")[:200], file=sys.stderr)
    except Exception as e:
        print("Telegram error", e, file=sys.stderr)
    return None


def procesar(posts, estado, ahora, enviar_fn):
    """Decide qué enviar. `estado` = {"vistas": [ids], "enviadas": {id: mensaje}}; devuelve cuántas envió. Primera vez (estado vacío): solo siembra."""
    vistas = set(estado.get("vistas", []))
    if not estado.get("sembrado"):
        estado["vistas"] = sorted(vistas | {p["_id"] for p in posts})
        estado["sembrado"] = True
        return 0
    nuevas = []
    for p in posts:
        if p["_id"] in vistas or not p.get("platformPostUrl"):
            continue
        publicada = datetime.datetime.fromisoformat(p["publishedAt"].replace("Z", "+00:00"))
        if (ahora - publicada).days > DIAS:
            vistas.add(p["_id"])  # demasiado antigua: se da por vista sin enviar
            continue
        nuevas.append((publicada, p))
    enviadas = 0
    for _, p in sorted(nuevas, key=lambda t: t[0])[:MAX_POR_PASADA]:
        mid = enviar_fn(mensaje(p), p["platformPostUrl"])
        if mid:
            vistas.add(p["_id"])
            estado.setdefault("enviadas", {})[p["_id"]] = mid
            enviadas += 1
    estado["vistas"] = sorted(vistas)
    return enviadas


def main():
    if not horario.en_horario():
        print("Fuera de horario (9:00-21:00 Madrid): no se manda nada.")
        return 0
    clave, tok, chat = (os.environ.get(k) for k in ("ZERNIO_API_KEY", "TELEGRAM_TOKEN", "TELEGRAM_GRUPO_ID"))
    if not (clave and tok and chat):
        print("Faltan secretos (ZERNIO_API_KEY, TELEGRAM_TOKEN, TELEGRAM_GRUPO_ID).", file=sys.stderr)
        return 1
    try:
        posts = leer_publicaciones(clave)
    except Exception as e:
        print("No se pudo leer Zernio:", type(e).__name__, getattr(e, "code", ""), file=sys.stderr)
        return 1
    estado = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    hilo = tema_recursos()
    n = procesar(posts, estado, datetime.datetime.now(datetime.timezone.utc), lambda txt, url: enviar(tok, chat, hilo, txt, url))
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False))
    print(f"{len(posts)} publicaciones leídas, {n} enviadas al tema Recursos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
