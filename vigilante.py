#!/usr/bin/env python3
"""Vigila ofertas de empleo docente y avisa por Telegram de las nuevas."""
import hashlib, html, json, os, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

AQUI = Path(__file__).parent
CONFIG = json.loads((AQUI / "config.json").read_text(encoding="utf8"))
VISTOS_F = AQUI / "vistos.json"
UA = {"User-Agent": "Mozilla/5.0 (vigilante-empleo)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf8", errors="ignore")


def colegios_es(provincia):
    """Ofertas de la página de una provincia de colegios.es."""
    base = f"https://colegios.es/empleoprofesores/{provincia}/"
    h = get(base)
    out, vistos = [], set()
    for href, txt in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", "", txt)).strip()
        # las ofertas terminan en una fecha ddmmaaaa
        if re.search(r"-\d{8}/?$", href) and t and href not in vistos:
            vistos.add(href)
            out.append({"id": href, "titulo": t, "url": href, "origen": f"colegios.es · {provincia}"})
    return out


def colejobs(provincia):
    """Ofertas de colegios concertados/privados en colejobs.es."""
    base = f"https://www.colejobs.es/ofertas-de-empleo/{provincia}/"
    h = get(base)
    out, vistos = [], set()
    for href, txt in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', h, re.S):
        if not re.search(r"ofertas-de-empleo/[^/]+-n[0-9A-Za-z]+/?$", href):
            continue
        url = urllib.parse.urljoin(base, href)
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", txt))).strip()
        if t and url not in vistos:
            vistos.add(url)
            out.append({"id": url, "titulo": t[:150], "url": url, "origen": f"Colejobs · {provincia}"})
    return out


def _txt(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def jobsora(consulta, lugar):
    """Resultados de es.jobsora.com (agregador; incluye CEU, Loyola, Domestiko...)."""
    h = get(f"https://es.jobsora.com/empleos-{consulta}-{lugar}")
    out = []
    for m in re.finditer(r'data-href="(https://es\.jobsora\.com/oferta-\d+)[^"]*"[^>]*>(.*?)</article>', h, re.S):
        t = _txt(m.group(2)).replace("relevancia fecha", "").strip()
        if t:
            out.append({"id": m.group(1), "titulo": t[:150], "url": m.group(1), "origen": f"Jobsora · {lugar}"})
    return out


def edutalent():
    """Últimas ofertas de edutalent.es (centros concertados; ámbito nacional)."""
    h = get("https://edutalent.es/vacantes-madrid/")
    out, vistos = [], set()
    for bloque in h.split('<div class="offer"')[1:]:
        u = re.search(r"window\.location='([^']+)'", bloque)
        if not u or u.group(1) in vistos:
            continue
        url = u.group(1)
        vistos.add(url)
        if any(x.lower() in _txt(bloque).lower() for x in CONFIG.get("edutalent_excluir_lugares", [])):
            continue
        h3 = re.search(r"<h3>(.*?)</h3>", bloque, re.S)
        t = _txt(h3.group(1)) if h3 else url.rstrip("/").split("/")[-1].replace("-", " ")
        resto = _txt(bloque[bloque.find("</h3>") + 5:])[:70] if h3 else ""
        out.append({"id": url, "titulo": f"{t} — {resto}"[:150], "url": url, "origen": "Edutalent (toda España)"})
    return out


def cdlmurcia():
    """Ofertas de empleo de Educación del Colegio de Doctores y Licenciados de Murcia."""
    url = "https://cdlmurcia.es/ofertas-de-empleo-de-educacion/"
    t = _txt(get(url))
    trozos = re.split(r"(?=Oferta de [^()]{3,80}\(\d\d/\d\d/\d{4}\))", t)
    out = []
    for z in trozos:
        m = re.match(r"(Oferta de [^()]{3,80}\(\d\d/\d\d/\d{4}\))\s*(.*)", z)
        if not m:
            continue
        pu = re.search(r"Puesto:\s*([^.]{3,90})", m.group(2))
        tit = m.group(1) + (" · " + pu.group(1) if pu else "")
        out.append({"id": f"{url}#{m.group(1)}{m.group(2)[:40]}", "titulo": tit, "url": url, "origen": "CDL Murcia"})
    return out


def talent(consulta, lugar):
    """Resultados de búsqueda en es.talent.com (agregador de ofertas)."""
    url = "https://es.talent.com/jobs?" + urllib.parse.urlencode({"k": consulta, "l": lugar})
    h = get(url)
    out = []
    for m in re.finditer(r'data-new-id="(\d+)".*?<h2[^>]*>(.*?)</h2>(?:.*?JobCard_company[^>]*>(.*?)</span>)?', h, re.S):
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        emp = re.sub(r"<[^>]+>", "", m.group(3) or "").strip()
        link = "https://es.talent.com/view?id=" + m.group(1)
        if t:
            out.append({"id": link, "titulo": t + (f" — {emp}" if emp else ""), "url": link, "origen": f"Talent.com · {lugar}"})
    return out


def rss(url):
    root = ET.fromstring(get(url))
    out = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        titulo = html.unescape(it.findtext("title") or "").strip()
        out.append({"id": link or titulo, "titulo": titulo, "url": link, "origen": "alerta/RSS", "sin_filtro": True})
    for en in root.iter("{http://www.w3.org/2005/Atom}entry"):  # Google Alerts usa Atom
        a = en.find("{http://www.w3.org/2005/Atom}link")
        link = a.get("href") if a is not None else ""
        # Google Alerts envuelve el enlace real en google.com/url?url=...
        q = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
        link = q.get("url", [link])[0]
        titulo = html.unescape(re.sub(r"<[^>]+>", "", en.findtext("{http://www.w3.org/2005/Atom}title") or "")).strip()
        out.append({"id": link, "titulo": titulo, "url": link, "origen": "alerta Google", "sin_filtro": True})
    return out


def pagina_cambia(url):
    h = re.sub(r"\s+", " ", re.sub(r"<(script|style).*?</\1>", "", get(url), flags=re.S))
    huella = hashlib.sha1(h.encode()).hexdigest()[:12]
    return [{"id": f"{url}#{huella}", "titulo": "La página ha cambiado", "url": url, "origen": "página vigilada", "sin_filtro": True}]


def coincide(o):
    if o.get("sin_filtro"):
        return True
    t = o["titulo"].lower()
    if any(x.lower() in t for x in CONFIG["palabras_excluir"]):
        return False
    return any(k.lower() in t for k in CONFIG["palabras_clave"])


def telegram(texto):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("[sin Telegram configurado]\n" + texto)
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": texto, "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data), timeout=30)


def main():
    primera = not VISTOS_F.exists()
    vistos = set(json.loads(VISTOS_F.read_text())) if not primera else set()
    ofertas, fallos = [], []
    fuentes = [(f"colegios.es/{p}", lambda p=p: colegios_es(p)) for p in CONFIG["colegios_es_provincias"]]
    fuentes += [(f"colejobs/{p}", lambda p=p: colejobs(p)) for p in CONFIG.get("colejobs_provincias", [])]
    fuentes += [(f"jobsora/{q}/{l}", lambda q=q, l=l: jobsora(q, l)) for q in CONFIG.get("jobsora_busquedas", []) for l in CONFIG.get("jobsora_lugares", [])]
    if CONFIG.get("edutalent"):
        fuentes.append(("edutalent", edutalent))
    if CONFIG.get("cdlmurcia"):
        fuentes.append(("cdlmurcia", cdlmurcia))
    fuentes += [(f"talent/{q}/{l}", lambda q=q, l=l: talent(q, l)) for q in CONFIG.get("talent_busquedas", []) for l in CONFIG.get("talent_lugares", [])]
    fuentes += [(u, lambda u=u: rss(u)) for u in CONFIG["feeds_rss"]]
    fuentes += [(u, lambda u=u: pagina_cambia(u)) for u in CONFIG["paginas_a_vigilar"]]
    for nombre, fn in fuentes:
        try:
            ofertas += fn()
        except Exception as e:
            fallos.append(f"{nombre}: {e}")
    nuevas = [o for o in ofertas if o["id"] not in vistos]
    interesantes = [o for o in nuevas if coincide(o)]
    print(f"{len(ofertas)} leídas, {len(nuevas)} nuevas, {len(interesantes)} coinciden, {len(fallos)} fallos")
    for f in fallos:
        print("FALLO", f, file=sys.stderr)
    if primera:
        print("Primera ejecución: se guardan las existentes sin avisar.")
    else:
        for o in interesantes:
            telegram(f"🔔 {o['titulo']}\n{o['origen']}\n{o['url']}")
    vistos |= {o["id"] for o in ofertas}
    VISTOS_F.write_text(json.dumps(sorted(vistos), indent=0))
    if len(fallos) == len(fuentes):
        sys.exit(1)


if __name__ == "__main__":
    main()
