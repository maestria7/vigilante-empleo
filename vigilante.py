#!/usr/bin/env python3
"""Vigila ofertas de empleo docente en toda España.

- Aviso privado (Telegram, tu chat): solo primaria y educación física en tus comunidades.
- Grupo público con temas: todas las ofertas, un tema por especialidad y etiquetas por comunidad.

Uso: python3 vigilante.py [ligeras|pesadas|todas] [--volcado N]
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

import fuentes as F
from clasificar import COMUNIDADES, comunidad_y_provincia, es_docente, hashtags, tag_tema, temas, EXCLUIR, _n
from provincias import JOBSORA_LUGAR, PROVINCIAS

AQUI = Path(__file__).parent
CONFIG = json.loads((AQUI / "config.json").read_text(encoding="utf8"))
VISTOS_PRIV = AQUI / "vistos.json"
VISTOS_PUB = AQUI / "vistos_publico.json"
TEMAS_F = AQUI / "topics.json"
LIMITES_F = AQUI / "limites.json"
LOG_F = AQUI / "publicadas.json"
POR_CODIGO = {p[1]: [] for p in PROVINCIAS}
PROV_POR_SLUG = {p[2]: p for p in PROVINCIAS}


def coincide_privado(o):
    t = o["titulo"].lower()
    if any(x.lower() in t for x in CONFIG["palabras_excluir"]):
        return False
    return any(k.lower() in t for k in CONFIG["palabras_clave"])


def construir_fuentes(grupo):
    """Devuelve [(nombre, función, metadatos)] según el grupo pedido."""
    fs = []
    if grupo in ("ligeras", "todas"):
        for nombre, cod, cs, cj, tl in PROVINCIAS:
            fs.append((f"colegios.es/{cs}", lambda cs=cs: F.colegios_es(cs), {"ccaa": cod, "prov": nombre}))
        if CONFIG.get("colejobs"):  # bloquea los servidores de GitHub (403): desactivado
            fs.append(("colejobs", F.colejobs_nacional, {}))
        fs.append(("edutalent", F.edutalent, {}))
        fs.append(("maristas-iberica", F.maristas_iberica, {"completa": "maristas"}))
        fs.append(("escolapios-emaus", F.escolapios_emaus, {"completa": "escolapios"}))
        fs.append(("cdlmurcia", F.cdlmurcia, {"ccaa": "MUR", "prov": "Murcia"}))
        for u in CONFIG.get("feeds_rss", []):
            fs.append((u, lambda u=u: F.rss(u), {"solo_privado": True, "grupo": True, "agregador": True}))
        for u in CONFIG.get("paginas_a_vigilar", []):
            fs.append((u, lambda u=u: F.pagina_cambia(u), {"solo_privado": True}))
    if grupo in ("pesadas", "todas"):
        for q in CONFIG.get("talent_busquedas", []):
            for nombre, cod, cs, cj, tl in PROVINCIAS:
                fs.append((f"talent/{q}/{tl}", lambda q=q, tl=tl: F.talent(q, tl), {"ccaa": cod, "prov": nombre, "agregador": True}))
        for q in CONFIG.get("jobsora_busquedas", []):
            for cod, slug in JOBSORA_LUGAR.items():
                fs.append((f"jobsora/{q}/{slug}", lambda q=q, slug=slug: F.jobsora(q, slug), {"ccaa": cod, "agregador": True}))
    return fs


def enriquecer(o, meta):
    o.update({k: v for k, v in meta.items() if k in ("ccaa", "prov", "agregador", "solo_privado", "grupo", "completa")})
    # si la fuente no dice dónde es, lo deduzco del texto
    cod, prov = comunidad_y_provincia(o["titulo"])
    if prov:  # el texto da una provincia concreta: manda sobre la de la búsqueda
        o["ccaa"], o["prov"] = cod, prov
    elif cod and not o.get("ccaa"):
        o["ccaa"] = cod
    return o


def telegram(chat, texto, hilo=None):
    tok = os.environ.get("TELEGRAM_TOKEN")
    if not tok or not chat:
        print("[sin Telegram configurado]\n" + texto)
        return False
    datos = {"chat_id": chat, "text": texto, "disable_web_page_preview": "true"}
    if hilo:
        datos["message_thread_id"] = str(hilo)
    for intento in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=urllib.parse.urlencode(datos).encode()), timeout=30)
            return json.load(r)["result"]["message_id"]
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf8", "ignore")
            if e.code == 429:
                m = re.search(r'"retry_after":\s*(\d+)', cuerpo)
                time.sleep(int(m.group(1)) + 1 if m else 5)
                continue
            print("Telegram error", e.code, cuerpo[:200], file=sys.stderr)
            return False
    return False


def editar(chat, mid, texto):
    tok = os.environ.get("TELEGRAM_TOKEN")
    if not tok or not chat:
        return False
    datos = {"chat_id": chat, "message_id": str(mid), "text": texto, "disable_web_page_preview": "true"}
    try:
        urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/editMessageText", data=urllib.parse.urlencode(datos).encode()), timeout=30)
        return True
    except urllib.error.HTTPError as e:
        print("Telegram edit error", e.code, e.read().decode("utf8", "ignore")[:150], file=sys.stderr)
        return False


def fecha_es(iso):
    try:
        return datetime.date.fromisoformat(iso).strftime("%d/%m/%Y")
    except Exception:
        return None


def es_vieja(o, dias=None):
    """Oferta cuya fecha de publicación conocida es anterior al límite (por defecto 30 días)."""
    dias = dias or CONFIG.get("max_dias_publicar", 30)
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(o["pub"])).days > dias
    except Exception:
        return False


def cargar_log():
    try:
        return json.loads(LOG_F.read_text())
    except Exception:
        return {}


def guardar_log(log):
    corte = time.time() - 60 * 86400
    LOG_F.write_text(json.dumps({k: v for k, v in log.items() if v["ts"] > corte}, ensure_ascii=False))


def revisar_publicadas(log, grupo_id, ids_completas):
    """Marca en el grupo las ofertas cerradas (desaparecen de una bolsa que leo completa) o muy antiguas."""
    ahora = time.time()
    dias_vieja = CONFIG.get("dias_posible_cerrada", 45)
    for oid, r in log.items():
        if r.get("estado"):
            continue
        marca = None
        if r.get("f") in ids_completas:  # la bolsa se leyó bien en esta ejecución
            if oid in ids_completas[r["f"]]:
                r["aus"] = 0
            else:
                r["aus"] = r.get("aus", 0) + 1
                if r["aus"] >= 3:  # ausente 3 ejecuciones seguidas: cerrada
                    marca, r["estado"] = "🔒 CERRADA · ya no aparece en la bolsa\n\n", "cerrada"
        if not marca and ahora - r["ts"] > dias_vieja * 86400:
            marca, r["estado"] = f"⏳ Publicada hace más de {dias_vieja} días: puede estar ya cubierta\n\n", "vieja"
        if marca:
            for hilo, mid in r["m"]:
                editar(grupo_id, mid, marca + r["x"])
                time.sleep(1.2)


def mensaje_publico(o, tema_lista):
    lugar = COMUNIDADES.get(o.get("ccaa"), "Sin zona")
    if o.get("prov"):
        lugar += f" · {o['prov']}"
    etiquetas = " ".join(hashtags(o.get("ccaa"), o.get("prov")) + [tag_tema(t) for t in tema_lista])
    titulo = o["titulo"] if len(o["titulo"]) <= 110 else o["titulo"][:107].rsplit(" ", 1)[0] + "…"
    f = fecha_es(o.get("pub")) if o.get("pub") else None
    if f:
        lugar += f" · 📅 {f}"
    return f"🏫 {titulo}\n📍 {lugar}\n🔗 {o['url']}\n{etiquetas}"


def limitar_semanal(lista, salida):
    """Webs de clases particulares online (Superprof, Preply...): se repiten mucho, dejo pasar como máximo una por semana."""
    dominios = CONFIG.get("limite_semanal", ["superprof", "preply"])
    try:
        ult = json.loads(LIMITES_F.read_text())
    except Exception:
        ult = {}
    ahora, res = time.time(), []
    for o in lista:
        d = next((x for x in dominios if x in _n(o["titulo"] + " " + o["url"])), None)
        d = f"{salida}/{d}" if d else None
        if d:
            if ahora - ult.get(d, 0) < 7 * 86400:
                continue
            ult[d] = ahora
        res.append(o)
    LIMITES_F.write_text(json.dumps(ult))
    return res


def cargar(f):
    return set(json.loads(f.read_text())) if f.exists() else None


def main():
    args = sys.argv[1:]
    grupo = next((a for a in args if a in ("ligeras", "pesadas", "todas")), "todas")
    volcado = int(args[args.index("--volcado") + 1]) if "--volcado" in args else 0

    fuentes = construir_fuentes(grupo)
    ofertas, fallos, ids_completas = [], [], {}
    for nombre, fn, meta in fuentes:
        try:
            res = [enriquecer(o, meta) for o in fn()]
            ofertas += res
            if meta.get("completa"):
                ids_completas[meta["completa"]] = {o["id"] for o in res}
        except Exception as e:
            fallos.append(f"{nombre}: {e}")
        time.sleep(0.3)
    # quitar duplicados dentro de la misma ejecución
    unicas = {}
    for o in ofertas:
        unicas.setdefault(o["id"], o)
    # mismo puesto repetido en varias webs: me quedo con uno (mismo título y zona)
    vistas_clave, sin_dup = set(), []
    for o in unicas.values():
        clave = (_n(o["titulo"])[:60], o.get("prov") or o.get("ccaa"))
        if clave in vistas_clave and not o.get("solo_privado"):
            continue
        vistas_clave.add(clave)
        sin_dup.append(o)
    ofertas = sin_dup

    chat_priv = os.environ.get("TELEGRAM_CHAT_ID")
    grupo_id = os.environ.get("TELEGRAM_GRUPO_ID")
    hilos = json.loads(TEMAS_F.read_text()) if TEMAS_F.exists() else {}
    comunidades_priv = set(CONFIG.get("comunidades_privado", ["AND", "MUR", "CLM", "MAD"]))

    # ---- privado
    v_priv = cargar(VISTOS_PRIV)
    primera_priv = v_priv is None
    v_priv = v_priv or set()
    nuevas = [o for o in ofertas if o["id"] not in v_priv]
    para_mi = limitar_semanal([o for o in nuevas if o.get("solo_privado") or (coincide_privado(o) and (o.get("ccaa") in comunidades_priv or not o.get("ccaa")))], "privado")
    if not primera_priv:
        for o in para_mi:
            telegram(chat_priv, f"🔔 {o['titulo']}\n{o['origen']}\n{o['url']}")
    v_priv |= {o["id"] for o in ofertas}
    VISTOS_PRIV.write_text(json.dumps(sorted(v_priv)))

    # ---- público (grupo con temas)
    v_pub = cargar(VISTOS_PUB)
    primera_pub = v_pub is None
    v_pub = v_pub or set()
    candidatas = [o for o in ofertas if (not o.get("solo_privado") or o.get("grupo"))
                  and not re.search(EXCLUIR, _n(o["titulo"]))
                  and (not o.get("agregador") or es_docente(o["titulo"]))
                  and not es_vieja(o)]
    if volcado:
        a_publicar = limitar_semanal(candidatas, "grupo")[:volcado]
    elif primera_pub:
        a_publicar = []
    else:
        a_publicar = limitar_semanal([o for o in candidatas if o["id"] not in v_pub], "grupo")
    enviadas = 0
    log = cargar_log()
    if grupo_id and hilos:
        for o in a_publicar:
            ts = temas(o["titulo"])
            texto = mensaje_publico(o, ts)
            msgs = []
            for t in ts:
                hilo = hilos.get(t) or hilos.get("Otros")
                mid = telegram(grupo_id, texto, hilo)
                if mid:
                    enviadas += 1
                    msgs.append([hilo, mid])
                time.sleep(3.2)
            if msgs:
                log[o["id"]] = {"t": o["titulo"], "u": o["url"], "c": o.get("ccaa"), "tm": ts, "ts": int(time.time()),
                                "f": o.get("completa"), "aus": 0, "x": texto, "m": msgs, "estado": ""}
        revisar_publicadas(log, grupo_id, ids_completas)
        guardar_log(log)
    elif a_publicar:
        print(f"[grupo sin configurar: {len(a_publicar)} ofertas no publicadas]")
    v_pub |= {o["id"] for o in ofertas}
    VISTOS_PUB.write_text(json.dumps(sorted(v_pub)))

    print(f"[{grupo}] {len(ofertas)} leídas · privado: {len(para_mi)} · público: {len(a_publicar)} ({enviadas} mensajes) · {len(fallos)} fallos")
    if primera_priv or primera_pub:
        print("Primera ejecución de alguna salida: se guardan las existentes sin avisar.")
    for f in fallos:
        print("FALLO", f, file=sys.stderr)
    if fuentes and len(fallos) == len(fuentes):
        sys.exit(1)


if __name__ == "__main__":
    main()
