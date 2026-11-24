#!/usr/bin/env python3
"""Resumen diario (a las 9:00 de España) para el administrador: altas y bajas del grupo y del bot.

- Grupo: miembros hoy (getChatMemberCount) y variación frente a la última foto guardada (metricas.json);
  entradas y salidas de las últimas 24 h, que registra el bot de la web.
- Bot: suscriptores y movimientos (altas, bajas, bloqueos) de las últimas 24 h, que da la web (/api/vacantes/resumen).
Solo cifras: ningún nombre ni identificador. Si una de las dos partes no está disponible, se dice y se manda lo demás.

Env: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_GRUPO_ID, VACANTES_ENTREGA_URL, VACANTES_ENTREGA_SECRETO. FORZAR=1 salta la comprobación de hora.
"""
import datetime, json, os, sys, urllib.parse, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).parent
F = AQUI / "metricas.json"
TOK, CHAT, GRUPO = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID"), os.environ.get("TELEGRAM_GRUPO_ID")
URL, SECRETO = os.environ.get("VACANTES_ENTREGA_URL"), os.environ.get("VACANTES_ENTREGA_SECRETO")


def api(metodo, **datos):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOK}/{metodo}", data=urllib.parse.urlencode(datos).encode())
    return json.load(urllib.request.urlopen(req, timeout=30))


def web():
    req = urllib.request.Request(URL.replace("/entregar", "/resumen") + "?horas=24", headers={"Authorization": f"Bearer {SECRETO}"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def delta(hoy, antes):
    if antes is None:
        return " (primer día: aún sin comparación)"
    d = hoy - antes
    return f" ({'+' if d > 0 else '−' if d < 0 else '±'}{abs(d)} desde ayer)"


def main():
    ahora = datetime.datetime.now(ZoneInfo("Europe/Madrid"))
    hoy = ahora.date().isoformat()
    try:
        fotos = json.loads(F.read_text())
    except Exception:
        fotos = {}
    if not os.environ.get("FORZAR"):
        if ahora.hour not in (9, 10):  # hay dos horarios en UTC (invierno y verano); solo vale el que cae en las 9-10 h de España
            print("No son las 9 h en España: no se manda nada.")
            return
        if hoy in fotos:
            print("Ya se mandó hoy.")
            return
    previas = sorted(d for d in fotos if d < hoy)
    ayer = fotos[previas[-1]] if previas else {}

    foto = {}
    lineas = ["📊 Radar Docente · altas y bajas de las últimas 24 h", ""]
    try:
        miembros = api("getChatMemberCount", chat_id=GRUPO)["result"]
        foto["grupo"] = miembros
        lineas.append(f"👥 Grupo: {miembros} miembros" + delta(miembros, ayer.get("grupo")))
    except Exception as e:
        miembros = None
        lineas.append("👥 Grupo: no he podido contar los miembros")
        print("FALLO grupo:", e, file=sys.stderr)
    try:
        w = web()
        m, s = w["movimientos"], w["suscriptores"]
        if miembros is not None:
            lineas.append(f"   Entradas: {m['grupo_alta']} · Salidas: {m['grupo_baja']}")
        foto["bot"] = s["total"]
        v = w.get("valoraciones") or {"utiles": 0, "noUtiles": 0, "porFuente": []}
        lineas += ["", f"🤖 Bot: {s['total']} suscriptores" + delta(s["total"], ayer.get("bot")),
                   f"   Altas: {m['bot_alta']} · Bajas: {m['bot_baja']} · Bloqueos: {m['bot_bloqueo']}",
                   f"   Con avisos activos: {s['completos'] - s['pausados'] if s['completos'] >= s['pausados'] else s['completos']}"
                   f" · En pausa: {s['pausados']} · Prefieren el grupo: {s['modoGrupo']}"]
        if v["utiles"] + v["noUtiles"]:
            lineas.append(f"   Valoraciones de los avisos: 👍 {v['utiles']} · 👎 {v['noUtiles']}")
            malas = [f"{f['origen']} ({f['noUtiles']} 👎 de {f['utiles'] + f['noUtiles']})" for f in v["porFuente"] if f["noUtiles"]]
            if malas:
                lineas.append("   Fuentes con más 👎: " + ", ".join(malas[:3]))
        else:
            lineas.append("   Valoraciones de los avisos: ninguna todavía")
    except Exception as e:
        lineas += ["", "🤖 Bot: no he podido consultar las cifras"]
        print("FALLO bot:", e, file=sys.stderr)
    texto = "\n".join(lineas)

    if foto:
        fotos[hoy] = foto
        F.write_text(json.dumps({d: fotos[d] for d in sorted(fotos)[-400:]}, ensure_ascii=False, sort_keys=True))
    if TOK and CHAT:
        api("sendMessage", chat_id=CHAT, text=texto)
        print("enviado")
    else:
        print(texto)


if __name__ == "__main__":
    main()
