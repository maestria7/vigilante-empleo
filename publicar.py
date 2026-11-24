#!/usr/bin/env python3
"""Publica en el grupo el mensaje de bienvenida y las dos encuestas (un solo uso, desde GitHub Actions)."""
import json, os, urllib.error, urllib.parse, urllib.request

TOK, GRUPO = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_GRUPO_ID"]
TEXTO = """👋 ¡Gracias por estar aquí!

Ya somos más de 70 docentes. Quiero que esto sea una comunidad donde nos ayudemos unos a otros. Podría haberme quedado el bot solo para mí y enterarme antes que nadie de las ofertas, pero prefiero compartirlo: creo que así nos va mejor a todos.

✨ Novedades del asistente:
• Avisos solo de lo tuyo: etapa, especialidad, comunidad y provincia, a la hora que elijas.
• Un botón para pasar una oferta a un compañero por Telegram o WhatsApp.
• 👍👎 en cada aviso, para que acierte cada vez más.

👉 Para empezar: pulsa el enlace del mensaje fijado y luego «Iniciar».

💬 Quiero crear un foro entre docentes para compartir experiencias y problemas y ayudarnos. Por ejemplo: «No sé bien cómo llevar a cabo esta adaptación curricular, ¿alguien me echa una mano?» o «Me ha pedido un informe la inspección, ¿a alguien le ha pasado?».

🙋 Soy Julián, docente y especialista en IA, con varios cursos de formación y un máster. Si quieres saber más de mí, en mi Instagram comparto cada semana recursos gratuitos, interactivos y consejos sobre inteligencia artificial aplicada a la educación:
👉 https://www.instagram.com/soymaestria/

🗳️ Responded a las dos encuestas de abajo, son anónimas. ¡Me ayudan mucho! Y si conoces a alguien, pásale el grupo.

Un abrazo,
Julián"""

TEMAS = ["Recursos tecnológicos para el aula", "Formación del profesorado", "Inteligencia artificial en el aula",
         "Programación didáctica y situaciones de aprendizaje", "Recursos interactivos y juegos educativos", "Evaluación y rúbricas",
         "Atención a la diversidad (ACI, PT, AL)", "Gestión del aula y convivencia", "Oposiciones y bolsas de empleo", "Otro tema distinto"]
FORO = ["Sí, me encantaría participar", "Me interesaría leerlo, pero no tanto escribir", "Por ahora prefiero solo recibir ofertas"]


def api(metodo, **datos):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/{metodo}", data=urllib.parse.urlencode(datos).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        return json.load(e)


m = api("sendMessage", chat_id=GRUPO, text=TEXTO, disable_web_page_preview="true")
print("MENSAJE", m.get("ok"), m.get("result", {}).get("message_id"), m.get("description", ""))
if m.get("ok"):
    p1 = api("sendPoll", chat_id=GRUPO, question="¿Sobre qué temas te gustaría que preparara recursos y contenidos?", options=json.dumps(TEMAS, ensure_ascii=False),
             is_anonymous="true", allows_multiple_answers="true")
    print("ENCUESTA 1", p1.get("ok"), p1.get("result", {}).get("message_id"), p1.get("description", ""))
    p2 = api("sendPoll", chat_id=GRUPO, question="¿Te interesaría un foro entre docentes para compartir experiencias y ayudarnos?", options=json.dumps(FORO, ensure_ascii=False),
             is_anonymous="true", allows_multiple_answers="false")
    print("ENCUESTA 2", p2.get("ok"), p2.get("result", {}).get("message_id"), p2.get("description", ""))
