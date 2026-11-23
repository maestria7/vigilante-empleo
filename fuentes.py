"""Funciones que leen cada web de empleo y devuelven una lista de ofertas."""
import hashlib, html, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"}


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


