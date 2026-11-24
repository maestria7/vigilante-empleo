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
from taxonomia import areas as areas_de

AQUI = Path(__file__).parent
CONFIG = json.loads((AQUI / "config.json").read_text(encoding="utf8"))
VISTOS_PRIV = AQUI / "vistos.json"
VISTOS_PUB = AQUI / "vistos_publico.json"
TEMAS_F = AQUI / "topics.json"
LIMITES_F = AQUI / "limites.json"
LOG_F = AQUI / "publicadas.json"
SALUD_F = AQUI / "salud.json"
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
        fs.append(("empleoo", F.empleoo, {"agregador": True}))
        if CONFIG.get("maristas"):  # cierra la conexión a los servidores de GitHub: desactivado
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


def enlace_compartir_grupo():
    """Enlace del selector de Telegram para compartir el grupo con un mensaje ya preparado."""
    texto = "Radar Docente by Maestría: todas las ofertas de empleo docente de España, ordenadas por especialidad y comunidad. Únete al grupo 👇"
    return "https://t.me/share/url?" + urllib.parse.urlencode({"url": CONFIG.get("enlace_grupo", ""), "text": texto}, quote_via=urllib.parse.quote)


def teclado_oferta(url):
    """Botones bajo cada oferta del grupo: ver la oferta y compartir el grupo."""
    fila = [{"text": "🔗 Ver oferta", "url": url}]
    if CONFIG.get("enlace_grupo"):
        fila.append({"text": "📣 Compartir grupo", "url": enlace_compartir_grupo()})
    return json.dumps({"inline_keyboard": [fila]})


def telegram(chat, texto, hilo=None, boton=None):
    tok = os.environ.get("TELEGRAM_TOKEN")
    if not tok or not chat:
        print("[sin Telegram configurado]\n" + texto)
        return False
    datos = {"chat_id": chat, "text": texto, "disable_web_page_preview": "true"}
    if hilo:
        datos["message_thread_id"] = str(hilo)
    if boton:
        datos["reply_markup"] = teclado_oferta(boton)
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


def editar(chat, mid, texto, boton=None):
    tok = os.environ.get("TELEGRAM_TOKEN")
    if not tok or not chat:
        return False
    datos = {"chat_id": chat, "message_id": str(mid), "text": texto, "disable_web_page_preview": "true"}
    if boton:
        datos["reply_markup"] = teclado_oferta(boton)
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


def datos_para_web(o):
    """Lo que la web necesita para repartir y mostrar la oferta con el mismo formato que el grupo."""
    ts = temas(o["titulo"])
    jornada, contrato = jornada_y_contrato(o["titulo"])
    return {"id": o["id"], "titulo": o["titulo"][:400], "url": o["url"], "ccaa": o.get("ccaa"), "prov": o.get("prov"),
            "areas": areas_de(o["titulo"]), "origen": o["origen"][:80], "pub": o.get("pub"),
            "etapas": [ETAPAS[k] for k in etapas_de(o["titulo"], ts)],
            "especialidades": [t for t in ts if t not in ETAPAS and t != "Otros"],
            "jornada": jornada, "contrato": contrato}


def entregar_a_suscriptores(ofertas):
    """Manda las ofertas nuevas a la web de Maestría, que las reparte por privado a quien las eligió en el bot con formulario.
    Solo actúa si VACANTES_ENTREGA_URL y VACANTES_ENTREGA_SECRETO están configuradas; un fallo aquí nunca debe romper el vigilante."""
    url, secreto = os.environ.get("VACANTES_ENTREGA_URL"), os.environ.get("VACANTES_ENTREGA_SECRETO")
    if not url or not secreto or not ofertas:
        return
    carga = [datos_para_web(o) for o in ofertas if o["url"].startswith("http")]
    for i in range(0, len(carga), 40):
        try:
            req = urllib.request.Request(url, data=json.dumps({"ofertas": carga[i:i + 40]}).encode(),
                                         headers={"Content-Type": "application/json", "Authorization": f"Bearer {secreto}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                print("entrega a suscriptores:", r.read().decode()[:200])
        except Exception as e:
            print("FALLO entrega a suscriptores:", e, file=sys.stderr)


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
                editar(grupo_id, mid, marca + r["x"], r.get("u"))
                time.sleep(1.2)


ETAPAS = {"Primaria": "Educación Primaria", "Infantil": "Educación Infantil", "Secundaria": "ESO y Bachillerato", "FP": "Formación Profesional"}


def etapas_de(titulo, tema_lista):
    """Etapas que la oferta nombra (las que pida: una, o varias si pide varias); «maestro/a» sin etapa cuenta como Primaria; [] si no se sabe."""
    t = _n(titulo[:150])
    reglas = (("Infantil", r"infantil|0-3|primer ciclo|preschool"), ("Primaria", r"primaria"),
              ("Secundaria", r"secundaria|\beso\b|bachiller"),
              ("FP", r"\bfp\b|formacion profesional|ciclo formativo|cfgm|cfgs"))
    out = [k for k, rx in reglas if re.search(rx, t)]
    if not out:  # sin etapa explícita: la que sugiere la clasificación (p. ej. matemáticas → Secundaria)
        out = [k for k, _ in reglas if k in tema_lista]
    if not out and re.search(r"maestr", t):  # «maestro/a» sin más (también de EF, música, inglés…): Primaria
        out = ["Primaria"]
    return out


def jornada_y_contrato(titulo):
    """Solo lo que el título dice con claridad; si no lo dice, no se muestra."""
    t = _n(titulo)
    jornada = ("Parcial" if re.search(r"media jornada|jornada parcial|parcial|reducida", t)
               else "Completa" if re.search(r"jornada completa|tiempo completo|full ?time", t) else None)
    contrato = ("Sustitución" if re.search(r"sustitucion|baja (it|maternal|por)", t) else "Interinidad" if re.search(r"interin", t)
                else "Indefinido" if re.search(r"indefinid", t) else "Temporal" if re.search(r"temporal", t) else None)
    return jornada, contrato


def mensaje_publico(o, tema_lista):
    partes = []
    for x in (o.get("prov"), COMUNIDADES.get(o.get("ccaa"))):
        if x and x not in partes:
            partes.append(x)
    lugar = " · ".join(partes) or "Sin zona"
    etapas_k = etapas_de(o["titulo"], tema_lista)
    etiquetas = " ".join(dict.fromkeys(hashtags(o.get("ccaa"), o.get("prov")) + [tag_tema(t) for t in tema_lista if t not in ETAPAS]
                                       + [tag_tema(k) for k in etapas_k]))
    titulo = o["titulo"] if len(o["titulo"]) <= 110 else o["titulo"][:107].rsplit(" ", 1)[0] + "…"
    etapas = [ETAPAS[k] for k in etapas_k]
    especialidades = [t for t in tema_lista if t not in ETAPAS and t != "Otros"]
    jornada, contrato = jornada_y_contrato(o["titulo"])
    pub = fecha_es(o.get("pub")) if o.get("pub") else None
    hoy = datetime.date.today().strftime("%d/%m/%Y")
    lineas = ["🎯 Nueva oportunidad · Radar Docente", "", f"🏫 {titulo}", "", f"📍 Ubicación: {lugar}"]
    lineas.append("🎓 Etapa: " + (", ".join(etapas) if etapas else "No indicada en la oferta"))
    if especialidades:
        lineas.append("🧩 Especialidad: " + ", ".join(especialidades))
    if jornada:
        lineas.append(f"🕒 Jornada: {jornada}")
    if contrato:
        lineas.append(f"📝 Contrato: {contrato}")
    lineas.append("📅 " + (f"Publicada: {pub} · " if pub else "") + f"Detectada: {hoy}")
    lineas.append(f"🔎 Fuente: {o['origen']}")
    lineas += ["", etiquetas]
    return "\n".join(lineas)


def _grupo_fuente(nombre):
    """Agrupa las fuentes repetidas (colegios.es/<prov>, talent/<q>/<lugar>...) bajo un solo nombre para avisar una vez."""
    if nombre.startswith("http"):
        return "alerta de Google / página vigilada"
    return nombre.split("/")[0]


def revisar_salud(resultados, chat_priv):
    """Avisa por privado si una fuente falla varias ejecuciones seguidas o se queda vacía mucho tiempo (y avisa al recuperarse).

    resultados: {nombre_fuente: número de ofertas leídas, o None si falló}.
    Fallo: 6 ejecuciones seguidas (3 en las pesadas). Vacía: 48 ejecuciones seguidas, solo si antes dio ofertas
    (no se vigilan las alertas de Google ni las páginas, que pueden estar vacías con normalidad)."""
    try:
        salud = json.loads(SALUD_F.read_text())
    except Exception:
        salud = {}
    ahora = int(time.time())
    rotas, vacias, recuperadas = {}, {}, {}
    for nombre, n in resultados.items():
        e = salud.setdefault(nombre, {"fallos": 0, "vacias": 0, "con": 0, "aviso": ""})
        pesada = nombre.startswith(("talent/", "jobsora/"))
        if n is None:
            e["fallos"] += 1
            if e["fallos"] >= (3 if pesada else 6) and e["aviso"] != "fallo":
                e["aviso"] = "fallo"
                rotas.setdefault(_grupo_fuente(nombre), []).append(nombre)
        elif n > 0:
            if e["aviso"]:
                recuperadas.setdefault(_grupo_fuente(nombre), []).append(nombre)
            e.update(fallos=0, vacias=0, con=ahora, aviso="")
        else:
            if e["aviso"] == "fallo":  # vuelve a responder (aunque sin ofertas): ya no está rota
                recuperadas.setdefault(_grupo_fuente(nombre), []).append(nombre)
                e["aviso"] = ""
            e["fallos"] = 0
            e["vacias"] += 1
            if e["vacias"] >= 48 and e["con"] and not nombre.startswith("http") and not pesada and e["aviso"] == "":
                e["aviso"] = "vacia"
                vacias.setdefault(_grupo_fuente(nombre), []).append(nombre)
    SALUD_F.write_text(json.dumps(salud, ensure_ascii=False, sort_keys=True))

    def lista(d):
        return "\n".join(f"• {g}" + (f" ({len(v)} fuentes)" if len(v) > 1 else "") for g, v in sorted(d.items()))

    partes = []
    if rotas:
        partes.append("🔴 Fuentes que fallan desde hace varias ejecuciones:\n" + lista(rotas))
    if vacias:
        partes.append("🟠 Fuentes que llevan mucho tiempo sin dar ninguna oferta (puede haber cambiado la web):\n" + lista(vacias))
    if recuperadas:
        partes.append("🟢 Fuentes recuperadas:\n" + lista(recuperadas))
    if partes and chat_priv:
        telegram(chat_priv, "⚠️ Radar Docente · estado de las fuentes\n\n" + "\n\n".join(partes))
    elif partes:
        print("[salud] " + " | ".join(partes))


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
    ofertas, fallos, ids_completas, resultados = [], [], {}, {}
    for nombre, fn, meta in fuentes:
        try:
            res = [enriquecer(o, meta) for o in fn()]
            resultados[nombre] = len(res)
            ofertas += res
            if meta.get("completa"):
                ids_completas[meta["completa"]] = {o["id"] for o in res}
        except Exception as e:
            fallos.append(f"{nombre}: {e}")
            resultados[nombre] = None
        time.sleep(0.3)
    try:
        revisar_salud(resultados, os.environ.get("TELEGRAM_CHAT_ID"))
    except Exception as e:  # vigilar las fuentes nunca debe romper el vigilante
        print("FALLO revisando la salud de las fuentes:", e, file=sys.stderr)
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
                mid = telegram(grupo_id, texto, hilo, o.get("url") if str(o.get("url", "")).startswith("http") else None)
                if mid:
                    enviadas += 1
                    msgs.append([hilo, mid])
                time.sleep(3.2)
            if msgs:
                log[o["id"]] = {"t": o["titulo"], "u": o["url"], "c": o.get("ccaa"), "tm": ts, "ts": int(time.time()),
                                "f": o.get("completa"), "aus": 0, "x": texto, "m": msgs, "estado": ""}
        revisar_publicadas(log, grupo_id, ids_completas)
        guardar_log(log)
        if not volcado:
            entregar_a_suscriptores(a_publicar)
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
